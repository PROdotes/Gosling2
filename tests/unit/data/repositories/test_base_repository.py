
import pytest
from unittest.mock import MagicMock, patch
from src.data.repositories.base_repository import BaseRepository
import sqlite3

class TestBaseRepository:
    """Tests for BaseRepository logic"""

    @patch('src.data.repositories.base_repository.sqlite3')
    def test_get_connection_rollback_on_error(self, mock_sqlite):
        """Test that transaction is rolled back when exception occurs"""
        mock_conn = MagicMock()
        mock_sqlite.connect.return_value = mock_conn
        
        repo = BaseRepository("test.db")
        
        # Reset mocks to ignore calls made during _ensure_schema
        mock_conn.reset_mock()
        
        # We need to suppress the exception to verify the mock calls
        with pytest.raises(ValueError):
            with repo.get_connection() as conn:
                raise ValueError("Simulated DB Error")
        
        mock_conn.commit.assert_not_called()
        mock_conn.rollback.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('src.data.repositories.base_repository.sqlite3')
    def test_get_connection_commit_on_success(self, mock_sqlite):
        """Test that transaction is committed on success"""
        mock_conn = MagicMock()
        mock_sqlite.connect.return_value = mock_conn
        
        repo = BaseRepository("test.db")
        
        # Reset mocks to ignore calls made during _ensure_schema
        mock_conn.reset_mock()
        
        with repo.get_connection() as conn:
            pass # successful block
        
        mock_conn.commit.assert_called_once()
        mock_conn.rollback.assert_not_called()
        mock_conn.close.assert_called_once()
