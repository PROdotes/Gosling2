"""Unit tests for IdentityRepository"""
import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
from src.data.repositories.identity_repository import IdentityRepository
from src.data.models.identity import Identity


class TestIdentityRepository:
    """Tests for IdentityRepository CRUD operations."""
    
    @pytest.fixture
    def repo(self):
        """Create repository instance."""
        return IdentityRepository()
    
    def test_get_by_id_success(self, repo):
        """Test fetching identity by ID returns Identity object."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # row: IdentityID, IdentityType, LegalName, DOB, DOD, Nationality, FormationDate, DisbandDate, Biography, Notes
        mock_cursor.fetchone.return_value = (1, "person", "David Bowie", "1947-01-08", None, "British", None, None, "Legend", "Notes")
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.get_by_id(1)
            
            assert result is not None
            assert result.identity_id == 1
            assert result.legal_name == "David Bowie"
            assert result.identity_type == "person"
            assert result.biography == "Legend"

    def test_create_identity(self, repo):
        """Test creating a new identity."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 10
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        identity = Identity(identity_type="group", legal_name="The Beatles")
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            new_id = repo.create(identity)
            
            assert new_id == 10
            mock_cursor.execute.assert_called()
            call_sql = mock_cursor.execute.call_args[0][0]
            assert "INSERT INTO Identities" in call_sql

    def test_update_identity(self, repo):
        """Test updating an existing identity."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        identity = Identity(identity_id=1, legal_name="Updated Name")
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            repo.update(identity)
            
            mock_cursor.execute.assert_called()
            call_sql = mock_cursor.execute.call_args[0][0]
            assert "UPDATE Identities" in call_sql
            assert "WHERE IdentityID = ?" in call_sql

    def test_delete_identity(self, repo):
        """Test deleting an identity."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            repo.delete(1)
            
            # Verify multiple calls (Select, Delete, Audit)
            assert mock_cursor.execute.call_count >= 2
            sqls = [call[0][0] for call in mock_cursor.execute.call_args_list]
            assert any("DELETE FROM Identities" in s for s in sqls)
            assert any("WHERE IdentityID = ?" in s for s in sqls)
