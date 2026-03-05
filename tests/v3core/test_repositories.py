import pytest
import sqlite3
from src.v3core.data.base_repository import BaseRepository
from src.v3core.data.song_repository import SongRepository
from src.v3core.data.song_credit_repository import SongCreditRepository


def test_song_repository_get_by_ids(populated_db):
    repo = SongRepository(populated_db)
    songs = repo.get_by_ids([1, 2])
    assert len(songs) == 2
    assert {s.title for s in songs} == {"Smells Like Teen Spirit", "Everlong"}


def test_song_repository_get_by_ids_empty(populated_db):
    """LAW: Batch-fetching with empty list returns empty list immediately."""
    repo = SongRepository(populated_db)
    assert repo.get_by_ids([]) == []


def test_base_repository_log_change(mock_db_path):
    """LAW: _log_change must write a record to ChangeLog only if value actually changes."""
    repo = BaseRepository(mock_db_path)
    batch_id = "test-batch-123"

    with repo._get_connection() as conn:
        cursor = conn.cursor()

        # 1. No change (old == new) -> No row should be added
        repo._log_change(cursor, "Songs", 1, "TempoBPM", "120", "120", batch_id)
        count = cursor.execute("SELECT COUNT(*) FROM ChangeLog").fetchone()[0]
        assert count == 0

        # 2. Actual change -> Row should be added
        repo._log_change(cursor, "Songs", 1, "TempoBPM", "120", "130", batch_id)
        row = cursor.execute(
            "SELECT LogTableName, RecordID, OldValue, NewValue FROM ChangeLog"
        ).fetchone()
        assert row is not None
        assert row[0] == "Songs"
        assert row[1] == 1
        assert row[2] == "120"
        assert row[3] == "130"


def test_song_credit_repository_strict_validation(populated_db):
    repo = SongCreditRepository(populated_db)

    # Manually insert a corrupted row with NULL RoleID
    conn = sqlite3.connect(populated_db)
    conn.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) "
        "VALUES (99, 10, NULL)"
    )
    conn.commit()
    conn.close()

    # This should trigger our VIOLATION logic
    with pytest.raises(ValueError, match="VIOLATION: Database integrity error"):
        repo.get_credits_for_song(99)
