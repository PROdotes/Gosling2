
import pytest
import os
from unittest.mock import MagicMock, patch
from src.data.database import BaseRepository
from src.data.repositories.song_repository import SongRepository
from src.data.models.song import Song


# --- Fixtures (shared for security tests) ---

@pytest.fixture
def temp_db(tmp_path):
    """Fixture creating a temporary database with the schema."""
    db_path = tmp_path / "test_mutation.db"
    db = BaseRepository(str(db_path))
    return str(db_path)

@pytest.fixture
def song_repo(temp_db):
    """Fixture providing a SongRepository connected to the temporary database."""
    return SongRepository(temp_db)

class TestSongRepositoryMutation:
    @pytest.fixture
    def repository(self):
        return SongRepository()

    def test_get_all_headers_integrity(self, repository):
        """Kill Mutant: Verify get_all returns correct headers"""
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        
        # description is list of (name, type_code, ...)
        # If mutant changes index 0 to 1, we get type_code
        mock_cursor.description = [
            ("FileID", "STRING"), 
            ("Title", "STRING")
        ]
        mock_cursor.fetchall.return_value = []
        
        with patch.object(repository, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection
            
            headers, _ = repository.get_all()
            
            # If mutated to index 1, headers would be ["STRING", "STRING"]
            assert headers == ["FileID", "Title"]

    def test_get_by_performer_headers_integrity(self, repository):
        """Kill Mutant: Verify get_by_performer returns correct headers"""
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        
        mock_cursor.description = [
            ("FileID", "INTEGER"), 
            ("performers", "STRING")
        ]
        mock_cursor.fetchall.return_value = []
        
        with patch.object(repository, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection
            
            headers, _ = repository.get_by_performer("Any")
            
            assert headers == ["FileID", "performers"]


class TestSongRepoSecurity:
    """Security/Injection tests (Robustness - per TESTING.md Law 7)."""

    def test_insert_malicious_filename(self, song_repo):
        """Test insertion of SQL injection string in filename."""
        bad_path_raw = "C:/Music/'; DROP TABLE Songs; --.mp3"
        bad_path = os.path.normcase(os.path.abspath(bad_path_raw))
        s = Song(name="Safe", source=bad_path, source_id=None)
        
        # Insert and update
        file_id = song_repo.insert(s.path)
        s.source_id = file_id
        song_repo.update(s)
        
        # Verify by path
        found = song_repo.get_by_path(bad_path)
        assert found is not None
        assert found.path == bad_path

    def test_update_malicious_artist_name(self, song_repo):
        """Test SQL injection in contributor names."""
        bad_artist = "Robert'); DROP TABLE Contributors; --"
        path = os.path.normcase(os.path.abspath("C:/Music/bobby.mp3"))
        s = Song(name="Bobby Tables", source=path, performers=[bad_artist], source_id=None)
        
        file_id = song_repo.insert(s.path)
        s.source_id = file_id
        song_repo.update(s)
        
        fetched = song_repo.get_by_path(path)
        assert bad_artist in fetched.performers

    def test_unicode_and_international_characters(self, song_repo):
        """Test full Unicode support."""
        unicode_path_raw = "C:/Music/おはよう/🎵.mp3"
        unicode_path = os.path.normcase(os.path.abspath(unicode_path_raw))
        s = Song(name="Morning", source=unicode_path, source_id=None)
        
        file_id = song_repo.insert(s.path)
        s.source_id = file_id
        song_repo.update(s)
        
        found = song_repo.get_by_path(unicode_path)
        assert found is not None
        assert found.path == unicode_path

