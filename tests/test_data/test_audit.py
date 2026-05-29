"""
Audit system tests.

Three concerns:
  1. Drift — every non-excluded table has INSERT/UPDATE/DELETE triggers covering all columns.
  2. Flush — after a write through the coordinator, no NULL batch_ids remain.
  3. Tripwire — get_connection() raises if a previous commit left NULL batch_ids.

Test DBs never have triggers installed (conftest._create_db runs SCHEMA_SQL only).
Audit-specific fixtures install triggers explicitly via build_trigger_sql().
"""

import sqlite3
import pytest

from src.data.base_repository import BaseRepository
from src.data.schema import EXCLUDED_FROM_AUDIT, build_trigger_sql
from src.engine.routers.mutation_models import MutationRequest
from src.services.mutation_coordinator import MutationCoordinator

# ---------------------------------------------------------------------------
# Fixture: DB with triggers installed
# ---------------------------------------------------------------------------


@pytest.fixture
def audit_db(populated_db):
    conn = sqlite3.connect(populated_db)
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    conn.executescript(build_trigger_sql(conn))
    conn.close()
    return populated_db


# ---------------------------------------------------------------------------
# 1. Drift test
# ---------------------------------------------------------------------------


def test_every_table_has_triggers(audit_db):
    conn = sqlite3.connect(audit_db)
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        if row[0] not in EXCLUDED_FROM_AUDIT
    ]
    triggers = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    }
    for table in tables:
        for suffix in ("INSERT", "UPDATE", "DELETE"):
            assert (
                f"trg_{table}_{suffix}" in triggers
            ), f"Missing trigger: trg_{table}_{suffix}"
    conn.close()


def test_update_triggers_cover_all_columns(audit_db):
    conn = sqlite3.connect(audit_db)
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        if row[0] not in EXCLUDED_FROM_AUDIT
    ]
    for table in tables:
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        trigger_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
            (f"trg_{table}_UPDATE",),
        ).fetchone()[0]
        for col in cols:
            assert col in trigger_sql, f"trg_{table}_UPDATE missing column: {col}"
    conn.close()


# ---------------------------------------------------------------------------
# 2. Flush — no NULL batch_ids after a coordinator mutation
# ---------------------------------------------------------------------------


def test_no_null_batch_ids_after_mutation(audit_db):
    coordinator = MutationCoordinator(audit_db)
    coordinator.apply(
        MutationRequest.model_validate(
            {"update": [{"type": "song", "id": 1, "notes": "audit test"}]}
        )
    )
    conn = sqlite3.connect(audit_db)
    count = conn.execute(
        "SELECT COUNT(*) FROM ChangeLog WHERE batch_id IS NULL"
    ).fetchone()[0]
    conn.close()
    assert count == 0


def test_changelog_rows_have_batch_label(audit_db):
    coordinator = MutationCoordinator(audit_db)
    coordinator.apply(
        MutationRequest.model_validate(
            {"update": [{"type": "song", "id": 1, "notes": "label test"}]}
        )
    )
    conn = sqlite3.connect(audit_db)
    null_label = conn.execute(
        "SELECT COUNT(*) FROM ChangeLog WHERE batch_label IS NULL"
    ).fetchone()[0]
    conn.close()
    assert null_label == 0


# ---------------------------------------------------------------------------
# 3. Tripwire — get_connection raises on orphaned NULL rows
# ---------------------------------------------------------------------------


def test_tripwire_raises_on_orphaned_null_rows(audit_db):
    # Simulate a bad write path: write directly without flush_batch, then commit.
    conn = sqlite3.connect(audit_db)
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    conn.execute("UPDATE Songs SET TempoBPM = 99 WHERE SourceID = 1")
    conn.commit()  # triggers fired → NULL batch_id rows now committed
    conn.close()

    repo = BaseRepository(audit_db)
    with pytest.raises(RuntimeError, match="NULL batch_id"):
        repo.get_connection()


# ---------------------------------------------------------------------------
# 4. Null → Null — no audit entries for no-op updates
# ---------------------------------------------------------------------------


def test_null_to_null_update_not_logged(audit_db):
    coordinator = MutationCoordinator(audit_db)
    # RecordingYear is nullable in Songs; start with NULL, update to NULL
    conn = sqlite3.connect(audit_db)
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    conn.executescript(build_trigger_sql(conn))
    # Ensure RecordingYear is NULL on a test song
    conn.execute("UPDATE Songs SET RecordingYear = NULL WHERE SourceID = 1")
    conn.commit()
    # Clear changelog to start fresh
    conn.execute("DELETE FROM ChangeLog")
    conn.commit()
    conn.close()

    # Update with same NULL value (no change)
    coordinator.apply(
        MutationRequest.model_validate(
            {"update": [{"type": "song", "id": 1, "recording_year": None}]}
        )
    )

    # Verify no changelog entry for RecordingYear
    conn = sqlite3.connect(audit_db)
    rows = conn.execute(
        "SELECT field_name FROM ChangeLog WHERE field_name = 'RecordingYear'"
    ).fetchall()
    conn.close()
    assert len(rows) == 0, "NULL→NULL RecordingYear update should not be logged"


def test_null_to_value_update_is_logged(audit_db):
    coordinator = MutationCoordinator(audit_db)
    conn = sqlite3.connect(audit_db)
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    conn.executescript(build_trigger_sql(conn))
    # Ensure SourceNotes is NULL
    conn.execute("UPDATE MediaSources SET SourceNotes = NULL WHERE SourceID = 1")
    conn.commit()
    # Clear changelog
    conn.execute("DELETE FROM ChangeLog")
    conn.commit()
    conn.close()

    # Update NULL to a value
    coordinator.apply(
        MutationRequest.model_validate(
            {"update": [{"type": "song", "id": 1, "notes": "test notes"}]}
        )
    )

    # Verify changelog entry exists for SourceNotes
    conn = sqlite3.connect(audit_db)
    rows = conn.execute(
        "SELECT old_value, new_value FROM ChangeLog WHERE field_name = 'SourceNotes'"
    ).fetchall()
    conn.close()
    assert len(rows) > 0, "NULL→value SourceNotes update should be logged"
    assert rows[0][0] is None, "Old value should be NULL"
    assert rows[0][1] is not None, "New value should not be NULL"


def test_value_to_null_update_is_logged(audit_db):
    coordinator = MutationCoordinator(audit_db)
    conn = sqlite3.connect(audit_db)
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    conn.executescript(build_trigger_sql(conn))
    # Ensure SourceNotes has a value
    conn.execute("UPDATE MediaSources SET SourceNotes = 'initial note' WHERE SourceID = 2")
    conn.commit()
    # Clear changelog
    conn.execute("DELETE FROM ChangeLog")
    conn.commit()
    conn.close()

    # Now update back to NULL
    coordinator.apply(
        MutationRequest.model_validate(
            {"update": [{"type": "song", "id": 2, "notes": None}]}
        )
    )

    # Verify changelog entry exists for SourceNotes
    conn = sqlite3.connect(audit_db)
    rows = conn.execute(
        "SELECT old_value, new_value FROM ChangeLog WHERE field_name = 'SourceNotes'"
    ).fetchall()
    conn.close()
    assert len(rows) > 0, "value→NULL SourceNotes update should be logged"
    assert rows[0][0] is not None, "Old value should not be NULL"
    assert rows[0][1] is None, "New value should be NULL"
