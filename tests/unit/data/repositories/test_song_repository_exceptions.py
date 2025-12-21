
import pytest
from unittest.mock import MagicMock, patch
from src.data.repositories.song_repository import SongRepository

class TestSongRepositoryExceptions:
    """Test exception handling in SongRepository"""

    @patch('src.data.database.sqlite3')
    def test_get_all_songs_error(self, mock_sqlite):
        """Test get_all_songs handles DB error gracefully"""
        mock_conn = MagicMock()
        mock_sqlite.connect.return_value = mock_conn
        
        repo = SongRepository("test.db")
        
        # Apply side effect only now
        mock_conn.execute.side_effect = Exception("DB Error")
        
        headers, data = repo.get_all()
        
        assert headers == []
        assert data == []

    @patch('src.data.database.sqlite3')
    def test_delete_song_error(self, mock_sqlite):
        """Test delete_song handles DB error gracefully"""
        mock_conn = MagicMock()
        mock_sqlite.connect.return_value = mock_conn
        
        repo = SongRepository("test.db")
        
        # Context manager enter returns conn, execute raises
        # We need to set it on the cursor returned by the NEW connection context
        # repo.get_connection() calls sqlite3.connect again!
        # So our mock_sqlite.connect returns the SAME mock_conn?
        # Yes, standard Mock behavior unless side_effect set.
        
        mock_conn.cursor.return_value.execute.side_effect = Exception("DB Error")
        
        # Should catch exception and not crash
        try:
            repo.delete(1)
        except Exception:
            pytest.fail("delete raised exception but should have handled it")
