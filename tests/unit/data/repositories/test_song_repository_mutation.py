
import pytest
from unittest.mock import MagicMock, patch
from src.data.repositories.song_repository import SongRepository

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
