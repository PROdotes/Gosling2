import sqlite3
import pytest
from src.data.song_repository import SongRepository
from src.models.domain import Song


class TestInsert:
    """Verifies atomic insertion into MediaSources and Songs tables."""

    def test_insert_new_song_persists_all_fields(self, populated_db):
        repo = SongRepository(populated_db)
        # 1. Create a transient Song object (no ID)
        transient_song = Song(
            media_name="TDD Anthem",
            source_path="/music/tdd_anthem.mp3",
            duration_s=180.5,  # 180.5 seconds
            audio_hash="abc_123_hash",
            processing_status=1,
            is_active=True,
            bpm=120,
            year=2026,
            isrc="US-ABC-26-00001",
        )

        # 2. Execute Insert
        with repo._get_connection() as conn:
            new_id = repo.insert(transient_song, conn)
            conn.commit()

        # 3. Assert return value
        assert isinstance(new_id, int), f"Expected int, got {type(new_id)}"
        assert new_id > 0, f"Expected positive ID, got {new_id}"

        # 4. Verify persistence via get_by_id (Exhaustive Assertion)
        saved_song = repo.get_by_id(new_id)
        assert saved_song is not None, f"Expected saved song with ID {new_id}, got None"

        # Core MediaSources fields
        assert saved_song.id == new_id, f"Expected ID {new_id}, got {saved_song.id}"
        assert (
            saved_song.media_name == "TDD Anthem"
        ), f"Expected 'TDD Anthem', got '{saved_song.media_name}'"
        assert (
            saved_song.source_path == "/music/tdd_anthem.mp3"
        ), f"Expected path, got '{saved_song.source_path}'"
        assert (
            saved_song.duration_s == 180.5
        ), f"Expected 180500ms, got {saved_song.duration_ms}"
        assert (
            saved_song.audio_hash == "abc_123_hash"
        ), f"Expected hash, got '{saved_song.audio_hash}'"
        assert (
            saved_song.processing_status == 1
        ), f"Expected status 1, got {saved_song.processing_status}"
        assert (
            saved_song.is_active is True
        ), f"Expected True, got {saved_song.is_active}"

        # Song-specific fields
        assert saved_song.bpm == 120, f"Expected BPM 120, got {saved_song.bpm}"
        assert saved_song.year == 2026, f"Expected Year 2026, got {saved_song.year}"
        assert (
            saved_song.isrc == "US-ABC-26-00001"
        ), f"Expected ISRC, got '{saved_song.isrc}'"

        # 5. Raw DB Side-Effect Check (TDD Standard Check)
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT SourceDuration FROM MediaSources WHERE SourceID = ?", (new_id,)
            ).fetchone()
            assert (
                row["SourceDuration"] == 180.5
            ), f"Expected 180.5s in DB, got {row['SourceDuration']}"

    def test_insert_duplicate_hash_raises_integrity_error(self, populated_db):
        repo = SongRepository(populated_db)
        song = Song(
            media_name="Duplicate Hash",
            source_path="/music/dup.mp3",
            duration_s=1.0,
            audio_hash="unique_hash_1",
            processing_status=2,
        )

        with repo._get_connection() as conn:
            repo.insert(song, conn)
            conn.commit()

        # Insert again with same hash but different path
        song2 = song.model_copy(update={"source_path": "/music/dup2.mp3"})
        with pytest.raises(sqlite3.IntegrityError):
            with repo._get_connection() as conn:
                repo.insert(song2, conn)
                conn.commit()

    def test_insert_duplicate_path_raises_integrity_error(self, populated_db):
        repo = SongRepository(populated_db)
        song = Song(
            media_name="Duplicate Path",
            source_path="/music/same.mp3",
            duration_s=1.0,
            audio_hash="hash_a",
            processing_status=2,
        )

        with repo._get_connection() as conn:
            repo.insert(song, conn)
            conn.commit()

        # Insert again with same path but different hash
        song2 = song.model_copy(update={"audio_hash": "hash_b"})
        with pytest.raises(sqlite3.IntegrityError):
            with repo._get_connection() as conn:
                repo.insert(song2, conn)
                conn.commit()
