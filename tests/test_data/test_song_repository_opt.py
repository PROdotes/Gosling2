"""
Optimization verification for SongRepository.
Verifies that get_by_path and get_by_hash return fully hydrated Song objects
in a single (optimized) query context.
"""

from src.data.song_repository import SongRepository


class TestSongRepositoryOptimization:

    def test_get_by_path_hydrates_all_fields(self, populated_db):
        """
        Test that get_by_path (optimized) returns all song-specific fields
        (bpm, year, isrc) in addition to base media fields.
        """
        repo = SongRepository(populated_db)

        # In populated_db:
        # Song 7: "Hollow Song", /path/7, bpm=128, isrc="ISRC123", year=None, status=1
        song = repo.get_by_path("/path/7")

        assert song is not None
        assert song.id == 7
        assert song.title == "Hollow Song"
        assert song.bpm == 128
        assert song.isrc == "ISRC123"
        assert song.processing_status == 1
        assert song.year is None

    def test_get_by_hash_hydrates_all_fields(self, populated_db):
        """
        Test that get_by_hash (optimized) returns all song-specific fields.
        """
        repo = SongRepository(populated_db)

        # Song 1: "Smells Like Teen Spirit", hash="hash_1", year=1991, bpm=None
        song = repo.get_by_hash("hash_1")

        assert song is not None
        assert song.id == 1
        assert song.audio_hash == "hash_1"
        assert song.year == 1991
        assert song.title == "Smells Like Teen Spirit"
        assert song.bpm is None

    def test_get_by_path_nonexistent_returns_none(self, populated_db):
        repo = SongRepository(populated_db)
        song = repo.get_by_path("/nonexistent/path")
        assert song is None

    def test_get_by_hash_nonexistent_returns_none(self, populated_db):
        repo = SongRepository(populated_db)
        song = repo.get_by_hash("nonexistent_hash")
        assert song is None
