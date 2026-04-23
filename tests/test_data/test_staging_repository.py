from src.data.staging_repository import StagingRepository

class TestStagingRepository:
    def test_set_origin_valid_creates_mapping(self, populated_db):
        """Writing an origin path to a song id allows it to be retrieved."""
        repo = StagingRepository(populated_db)
        song_id = 1
        origin_path = "/fake/downloads/song.mp3"
        
        repo.set_origin(song_id, origin_path)
        
        result = repo.get_origin(song_id)
        assert result == origin_path, f"Expected {origin_path}, got {result}"

    def test_get_origin_missing_returns_none(self, empty_db):
        """Fetching an origin for a song ID that has no record returns None."""
        repo = StagingRepository(empty_db)
        
        result = repo.get_origin(8888)
        assert result is None, f"Expected None, got {result}"

    def test_clear_origin_valid_removes_mapping(self, populated_db):
        """Clearing an existing mapping removes it from the database."""
        repo = StagingRepository(populated_db)
        song_id = 2
        origin_path = "/fake/downloads/delete_me.wav"
        
        repo.set_origin(song_id, origin_path)
        result_before = repo.get_origin(song_id)
        assert result_before == origin_path, f"Expected {origin_path}, got {result_before}"
        
        repo.clear_origin(song_id)
        
        result_after = repo.get_origin(song_id)
        assert result_after is None, f"Expected None, got {result_after}"
