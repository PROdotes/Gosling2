"""Unit tests for ArtistNameRepository"""
import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
from src.data.repositories.artist_name_repository import ArtistNameRepository
from src.data.models.artist_name import ArtistName


class TestArtistNameRepository:
    """Tests for ArtistNameRepository CRUD operations."""
    
    @pytest.fixture
    def repo(self):
        """Create repository instance."""
        return ArtistNameRepository()
    
    def test_get_by_id_success(self, repo):
        """Test fetching name by ID returns ArtistName object."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # row: NameID, OwnerIdentityID, DisplayName, SortName, IsPrimaryName, DisambiguationNote
        mock_cursor.fetchone.return_value = (10, 1, "Ziggy Stardust", "Stardust, Ziggy", 0, "Alter ego")
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.get_by_id(10)
            
            assert result is not None
            assert result.name_id == 10
            assert result.display_name == "Ziggy Stardust"
            assert result.owner_identity_id == 1
            assert result.is_primary_name is False

    def test_create_artist_name(self, repo):
        """Test creating a new artist name."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 100
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        name = ArtistName(display_name="David Bowie", owner_identity_id=1, is_primary_name=True)
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            new_id = repo.create(name)
            
            assert new_id == 100
            mock_cursor.execute.assert_called()
            call_sql = mock_cursor.execute.call_args[0][0]
            assert "INSERT INTO ArtistNames" in call_sql

    def test_get_by_owner(self, repo):
        """Test fetching names for an owner."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (10, 1, "Ziggy Stardust", "Stardust, Ziggy", 0, "Alter ego"),
            (11, 1, "David Bowie", "Bowie, David", 1, None)
        ]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            results = repo.get_by_owner(1)
            
            assert len(results) == 2
            assert results[0].display_name == "Ziggy Stardust"
            assert results[1].display_name == "David Bowie"

    def test_search(self, repo):
        """Test searching for artist names."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (10, 1, "Ziggy Stardust", "Stardust, Ziggy", 0, "Alter ego")
        ]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            results = repo.search("Ziggy")
            
            assert len(results) == 1
            assert results[0].display_name == "Ziggy Stardust"
            mock_cursor.execute.assert_called()
            call_sql = mock_cursor.execute.call_args[0][0]
            assert "WHERE DisplayName LIKE ?" in call_sql or "WHERE DisplayName COLLATE NOCASE LIKE ?" in call_sql
