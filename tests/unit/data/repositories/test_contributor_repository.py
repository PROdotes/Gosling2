import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
from src.data.repositories.contributor_repository import ContributorRepository

class TestContributorRepository:
    @pytest.fixture
    def repo(self):
        return ContributorRepository()

    def test_get_by_role_success(self, repo):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [(1, "Artist 1"), (2, "Artist 2")]
        
        # Manually mock the context manager method
        @contextmanager
        def mock_get_conn():
            yield mock_conn
            
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.get_by_role("Performer")
            
            assert len(result) == 2
            assert result[0] == (1, "Artist 1")
            
            # Verify query structure
            mock_cursor.execute.assert_called_once()
            args = mock_cursor.execute.call_args[0]
            assert "SELECT DISTINCT" in args[0]

    def test_get_by_role_error(self, repo):
        mock_conn = MagicMock()
        
        @contextmanager
        def mock_get_conn():
            # Simulate error during execution inside context
            raise Exception("DB Error")
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.get_by_role("Performer")
            assert result == []
