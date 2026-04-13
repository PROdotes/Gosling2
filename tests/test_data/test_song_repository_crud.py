"""
Tests for SongRepository.update_scalars
========================================
Verifies partial updates to MediaSources and Songs tables.

populated_db Song 1: "Smells Like Teen Spirit", duration=200s, BPM=None, Year=1991, ISRC=None, IsActive=True
populated_db Song 2: "Everlong", BPM=None, Year=1997
"""

import sqlite3
from src.data.song_repository import SongRepository


class TestUpdateScalars:
    def test_update_title(self, populated_db):
        """Update media_name — should change MediaSources.MediaName."""
        repo = SongRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_scalars(
                1, {"media_name": "Smells Like Teen Spirit (Remaster)"}, conn
            )
            conn.commit()

        song = repo.get_by_id(1)
        assert (
            song.title == "Smells Like Teen Spirit (Remaster)"
        ), f"Expected updated title, got '{song.title}'"

    def test_update_bpm(self, populated_db):
        """Update bpm — should change Songs.TempoBPM."""
        repo = SongRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_scalars(1, {"bpm": 117}, conn)
            conn.commit()

        song = repo.get_by_id(1)
        assert song.bpm == 117, f"Expected bpm=117, got {song.bpm}"

    def test_update_year(self, populated_db):
        """Update year — should change Songs.RecordingYear."""
        repo = SongRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_scalars(1, {"year": 1992}, conn)
            conn.commit()

        song = repo.get_by_id(1)
        assert song.year == 1992, f"Expected year=1992, got {song.year}"

    def test_update_isrc(self, populated_db):
        """Update isrc — should change Songs.ISRC."""
        repo = SongRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_scalars(1, {"isrc": "USRC99999999"}, conn)
            conn.commit()

        song = repo.get_by_id(1)
        assert (
            song.isrc == "USRC99999999"
        ), f"Expected isrc='USRC99999999', got '{song.isrc}'"

    def test_update_is_active_false(self, populated_db):
        """Update is_active to False — should change MediaSources.IsActive."""
        repo = SongRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_scalars(1, {"is_active": False}, conn)
            conn.commit()

        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT IsActive FROM MediaSources WHERE SourceID = 1"
            ).fetchone()
            assert (
                bool(row["IsActive"]) is False
            ), f"Expected IsActive=False, got {row['IsActive']}"

    def test_update_bpm_does_not_affect_other_fields(self, populated_db):
        """Updating only bpm should leave title, year, isrc, and is_active unchanged."""
        repo = SongRepository(populated_db)
        before = repo.get_by_id(1)

        with repo._get_connection() as conn:
            repo.update_scalars(1, {"bpm": 200}, conn)
            conn.commit()

        after = repo.get_by_id(1)
        assert after.bpm == 200, f"Expected bpm=200, got {after.bpm}"
        assert (
            after.title == before.title
        ), f"Title should not change, got '{after.title}'"
        assert after.year == before.year, f"Year should not change, got {after.year}"
        assert after.isrc == before.isrc, f"ISRC should not change, got '{after.isrc}'"
        assert (
            after.is_active == before.is_active
        ), f"is_active should not change, got {after.is_active}"

    def test_update_multiple_fields_at_once(self, populated_db):
        """Update bpm + year + title in a single call — all three should change."""
        repo = SongRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_scalars(
                1, {"bpm": 170, "year": 2000, "media_name": "New Title"}, conn
            )
            conn.commit()

        song = repo.get_by_id(1)
        assert song.bpm == 170, f"Expected bpm=170, got {song.bpm}"
        assert song.year == 2000, f"Expected year=2000, got {song.year}"
        assert (
            song.title == "New Title"
        ), f"Expected title='New Title', got '{song.title}'"

    def test_update_one_song_does_not_affect_another(self, populated_db):
        """Updating Song 1 should not affect Song 2."""
        repo = SongRepository(populated_db)
        before_song2 = repo.get_by_id(2)

        with repo._get_connection() as conn:
            repo.update_scalars(
                1, {"bpm": 170, "year": 2000, "media_name": "Changed"}, conn
            )
            conn.commit()

        after_song2 = repo.get_by_id(2)
        assert (
            after_song2.title == before_song2.title
        ), f"Song 2 title should not change, got '{after_song2.title}'"
        assert (
            after_song2.year == before_song2.year
        ), f"Song 2 year should not change, got {after_song2.year}"
        assert (
            after_song2.bpm == before_song2.bpm
        ), f"Song 2 bpm should not change, got {after_song2.bpm}"


# ---------------------------------------------------------------------------
# SongRepository.get_by_processing_status
# ---------------------------------------------------------------------------


class TestGetByProcessingStatus:
    """Group 1: new repo method for WAV ingest (status=3 = Converting)."""

    def test_returns_song_with_matching_status(self, populated_db):
        """A song manually set to status=3 is returned."""
        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute("UPDATE MediaSources SET ProcessingStatus = 3 WHERE SourceID = 1")
        conn.commit()
        conn.close()

        repo = SongRepository(populated_db)
        results = repo.get_by_processing_status(3)
        ids = [s.id for s in results]
        assert 1 in ids, f"Expected song 1 in status=3 results, got ids={ids}"

    def test_returns_empty_when_no_match(self, populated_db):
        """No songs with status=3 → returns empty list."""
        repo = SongRepository(populated_db)
        # populated_db songs are all status 1/2 by default — no status=3
        results = repo.get_by_processing_status(3)
        assert results == [], f"Expected [], got {results}"

    def test_soft_deleted_song_is_excluded(self, populated_db):
        """A soft-deleted song with status=3 must NOT appear in results."""
        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET ProcessingStatus = 3, IsDeleted = 1 WHERE SourceID = 2"
        )
        conn.commit()
        conn.close()

        repo = SongRepository(populated_db)
        results = repo.get_by_processing_status(3)
        ids = [s.id for s in results]
        assert (
            2 not in ids
        ), f"Soft-deleted song 2 should not appear in status=3 results, got ids={ids}"

    def test_returns_all_matching_songs(self, populated_db):
        """All non-deleted songs with matching status are returned, not just the first."""
        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute("UPDATE MediaSources SET ProcessingStatus = 3 WHERE SourceID IN (1, 2)")
        conn.commit()
        conn.close()

        repo = SongRepository(populated_db)
        results = repo.get_by_processing_status(3)
        ids = [s.id for s in results]
        assert 1 in ids, f"Expected song 1 in results, got {ids}"
        assert 2 in ids, f"Expected song 2 in results, got {ids}"
