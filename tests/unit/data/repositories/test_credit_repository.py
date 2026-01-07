"""Unit tests for CreditRepository"""
import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
from src.data.repositories.credit_repository import CreditRepository


class TestCreditRepository:
    """Tests for CreditRepository operations."""
    
    @pytest.fixture
    def repo(self):
        """Create repository instance."""
        return CreditRepository()
    
    def test_add_song_credit(self, repo):
        """Test adding a song credit."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 500
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            # source_id, name_id, role_id, position
            result = repo.add_song_credit(1, 10, 1, 0)
            
            assert result == 500
            mock_cursor.execute.assert_called()
            call_sql = mock_cursor.execute.call_args[0][0]
            assert "INSERT INTO SongCredits" in call_sql

    def test_get_song_credits(self, repo):
        """Test fetching song credits."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # CreditID, SourceID, CreditedNameID, RoleID, CreditPosition, DisplayName, RoleName
        mock_cursor.fetchall.return_value = [
            (500, 1, 10, 1, 0, "David Bowie", "Performer"),
            (501, 1, 11, 2, 1, "Brian Eno", "Producer")
        ]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            results = repo.get_song_credits(1)
            
            assert len(results) == 2
            assert results[0]["display_name"] == "David Bowie"
            assert results[0]["role_name"] == "Performer"
            assert results[1]["display_name"] == "Brian Eno"

    def test_remove_song_credit(self, repo):
        """Test removing a song credit."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            repo.remove_song_credit(1, 10, 1)
            
            mock_cursor.execute.assert_called()
            call_sql = mock_cursor.execute.call_args[0][0]
            assert "DELETE FROM SongCredits" in call_sql
            assert "WHERE SourceID = ? AND CreditedNameID = ? AND RoleID = ?" in call_sql
