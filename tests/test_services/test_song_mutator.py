"""
Tests for SongMutator — scalar field writes (step 5).

Uses populated_db (songs 1-9, Dave Grohl fixture).

Covers:
  - update writes a scalar field to the DB
  - update with null clears a nullable field
  - absent fields are left alone (exclude_unset)
  - unknown song_id raises LookupError
  - unsupported action raises ValueError
  - no-op (no fields set) returns without error
"""
import sqlite3

import pytest

from src.engine.routers.mutation_models import UpdateSongItem
from src.services.mutators.song_mutator import SongMutator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_song_row(conn: sqlite3.Connection, song_id: int) -> sqlite3.Row:
    return conn.execute(
        """
        SELECT m.MediaName, m.IsActive, m.SourceNotes, s.TempoBPM, s.RecordingYear, s.ISRC
        FROM MediaSources m JOIN Songs s ON m.SourceID = s.SourceID
        WHERE m.SourceID = ?
        """,
        (song_id,),
    ).fetchone()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mutator(populated_db):
    return SongMutator(populated_db)


@pytest.fixture
def conn(populated_db):
    c = _make_conn(populated_db)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSongMutatorUpdate:
    def test_update_bpm(self, mutator, conn):
        item = UpdateSongItem.model_validate({"type": "song", "id": 1, "bpm": 140})
        mutator.apply_within("update", item, conn, None)
        conn.commit()
        row = _fetch_song_row(conn, 1)
        assert row["TempoBPM"] == 140

    def test_update_media_name(self, mutator, conn):
        item = UpdateSongItem.model_validate({"type": "song", "id": 1, "media_name": "New Title"})
        mutator.apply_within("update", item, conn, None)
        conn.commit()
        row = _fetch_song_row(conn, 1)
        assert row["MediaName"] == "New Title"

    def test_update_notes(self, mutator, conn):
        item = UpdateSongItem.model_validate({"type": "song", "id": 1, "notes": "some note"})
        mutator.apply_within("update", item, conn, None)
        conn.commit()
        row = _fetch_song_row(conn, 1)
        assert row["SourceNotes"] == "some note"

    def test_clear_notes_with_null(self, mutator, conn):
        # First set a note
        item = UpdateSongItem.model_validate({"type": "song", "id": 1, "notes": "temporary"})
        mutator.apply_within("update", item, conn, None)
        conn.commit()
        # Then clear it
        item2 = UpdateSongItem.model_validate({"type": "song", "id": 1, "notes": None})
        mutator.apply_within("update", item2, conn, None)
        conn.commit()
        row = _fetch_song_row(conn, 1)
        assert row["SourceNotes"] is None

    def test_absent_field_is_not_written(self, mutator, conn):
        before = _fetch_song_row(conn, 1)
        original_name = before["MediaName"]
        # Only update bpm — media_name must be untouched
        item = UpdateSongItem.model_validate({"type": "song", "id": 1, "bpm": 99})
        mutator.apply_within("update", item, conn, None)
        conn.commit()
        after = _fetch_song_row(conn, 1)
        assert after["MediaName"] == original_name
        assert after["TempoBPM"] == 99

    def test_no_fields_set_is_noop(self, mutator, conn):
        before = _fetch_song_row(conn, 1)
        item = UpdateSongItem.model_validate({"type": "song", "id": 1})
        mutator.apply_within("update", item, conn, None)
        conn.commit()
        after = _fetch_song_row(conn, 1)
        assert dict(before) == dict(after)

    def test_unknown_song_raises_lookup_error(self, mutator, conn):
        item = UpdateSongItem.model_validate({"type": "song", "id": 99999, "bpm": 100})
        with pytest.raises(LookupError):
            mutator.apply_within("update", item, conn, None)

    def test_unsupported_action_raises_value_error(self, mutator, conn):
        item = UpdateSongItem.model_validate({"type": "song", "id": 1, "bpm": 100})
        with pytest.raises(ValueError):
            mutator.apply_within("add", item, conn, None)
