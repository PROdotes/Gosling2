import os
import pytest
import tempfile
from src.data.repositories.song_repository import SongRepository

class TestDuplicateReproduction:
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        # Create temp file
        import tempfile
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Monkey patch config
        from src.data.database_config import DatabaseConfig
        original_path = DatabaseConfig.get_database_path
        DatabaseConfig.get_database_path = lambda: db_path
        
        yield db_path
        
        # Cleanup
        DatabaseConfig.get_database_path = original_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def repo(self, temp_db):
        return SongRepository(temp_db)

    def test_duplicate_paths_different_separators(self, repo):
        # Insert using forward slashes
        path1 = os.path.normcase(os.path.abspath("C:/Music/test_song.mp3"))
        id1 = repo.insert("C:/Music/test_song.mp3")
        assert id1 is not None

        # Insert same file using backslashes - attempt to duplicate
        id2 = repo.insert("C:\\Music\\test_song.mp3")
        
        # Should now return None (caught by existing unique constraint after normalization)
        assert id2 is None, "Fix Failed: Different separators still create duplicate entries"

    def test_duplicate_paths_different_case(self, repo):
        # Insert uppercase (will be normalized)
        id1 = repo.insert("C:\\Music\\TEST_SONG.mp3")
        assert id1 is not None

        # Insert lowercase - attempt to duplicate
        id2 = repo.insert("c:\\music\\test_song.mp3")
        
        assert id2 is None, "Fix Failed: Case difference still create duplicate entries"
