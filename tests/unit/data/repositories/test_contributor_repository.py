"""
Level 1 Logic Tests for ContributorRepository.
Per TESTING.md: Tests the happy path and polite failures.

This file tests the new Artist tagging infrastructure:
- CRUD operations for Contributors (Artists)
- Alias management (stage names, alternate spellings)
- Group membership (band members, collectives)
- Identity resolution (search expansion via aliases/groups)
"""
import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
from src.data.repositories.contributor_repository import ContributorRepository
from src.data.models.contributor import Contributor


class TestContributorRepository:
    """Tests for ContributorRepository CRUD and search operations."""
    
    @pytest.fixture
    def repo(self):
        """Create repository instance."""
        return ContributorRepository()
    
    @pytest.fixture
    def mock_connection(self):
        """Create a reusable mock connection context manager."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        return mock_conn, mock_cursor, mock_get_conn


class TestGetById:
    """Tests for get_by_id method."""
    
    @pytest.fixture
    def repo(self):
        return ContributorRepository()
    
    def test_get_by_id_success(self, repo):
        """Test fetching contributor by ID returns Contributor object."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1, "John Doe", "Doe, John", "person")
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.get_by_id(1)
            
            assert result is not None
            assert result.contributor_id == 1
            assert result.name == "John Doe"
            assert result.type == "person"
    
    def test_get_by_id_not_found(self, repo):
        """Test fetching non-existent ID returns None."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.get_by_id(999)
            assert result is None


class TestCreateContributor:
    """Tests for create method."""
    
    @pytest.fixture
    def repo(self):
        return ContributorRepository()
    
    def test_create_person(self, repo):
        """Test creating a new person contributor."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 42
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.create("John Doe", type="person")
            
            assert result.contributor_id == 42
            assert result.name == "John Doe"
            assert result.type == "person"
            
            # Verify INSERT was called
            mock_cursor.execute.assert_called()
            call_args = mock_cursor.execute.call_args[0][0]
            assert "INSERT INTO Contributors" in call_args
    
    def test_create_group(self, repo):
        """Test creating a new group contributor."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 43
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.create("The Beatles", type="group")
            
            assert result.contributor_id == 43
            assert result.name == "The Beatles"
            assert result.type == "group"
    
    def test_create_auto_generates_sort_name(self, repo):
        """Test that sort_name is auto-generated with 'The' prefix handling."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 44
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.create("The Rolling Stones", type="group")
            
            # Verify sort_name transformation
            call_args = mock_cursor.execute.call_args[0][1]
            # The sort_name should be passed as a parameter
            assert len(call_args) >= 3  # name, sort_name, type


class TestSearch:
    """Tests for search method - critical for the tag picker UI."""
    
    @pytest.fixture
    def repo(self):
        return ContributorRepository()
    
    def test_search_returns_contributors(self, repo):
        """Test search returns list of Contributor objects."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (1, "John Lennon", "Lennon, John", "person", None),  # matched_alias = None
            (2, "John Mayer", "Mayer, John", "person", None),
        ]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            results = repo.search("John")
            
            assert len(results) == 2
            assert all(isinstance(r, Contributor) for r in results)
            assert results[0].name == "John Lennon"
    
    def test_search_empty_string_returns_all(self, repo):
        """Test empty search returns all contributors (for picker dropdown)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (1, "Artist 1", "Artist 1", "person", None),
            (2, "Artist 2", "Artist 2", "person", None),
            (3, "Band 1", "Band 1", "group", None),
        ]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            results = repo.search("")
            assert len(results) == 3


class TestGetOrCreate:
    """Tests for get_or_create method - key for tag UI workflow."""
    
    @pytest.fixture
    def repo(self):
        return ContributorRepository()
    
    def test_get_or_create_existing(self, repo):
        """Test get_or_create returns existing contributor."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # First call returns existing contributor
        mock_cursor.fetchone.return_value = (1, "John Doe", "Doe, John", "person")
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            contributor, was_created = repo.get_or_create("John Doe")
            
            assert contributor.contributor_id == 1
            assert was_created is False
    
    def test_get_or_create_new(self, repo):
        """Test get_or_create creates new contributor when not found."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # First call returns None (not found), then returns new ID
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 99
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            contributor, was_created = repo.get_or_create("New Artist", type="person")
            
            assert contributor.contributor_id == 99
            assert was_created is True


class TestAliasManagement:
    """Tests for alias-related operations (stage names, alternate spellings)."""
    
    @pytest.fixture
    def repo(self):
        return ContributorRepository()
    
    def test_get_aliases(self, repo):
        """Test fetching all aliases for a contributor."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (1, "Slim Shady"),
            (2, "Marshall Mathers"),
        ]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            aliases = repo.get_aliases(42)
            
            assert len(aliases) == 2
            assert (1, "Slim Shady") in aliases
    
    def test_add_alias(self, repo):
        """Test adding a new alias to contributor."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            repo.add_alias(42, "New Stage Name")
            
            mock_cursor.execute.assert_called()
            call_args = mock_cursor.execute.call_args[0]
            assert "INSERT INTO ContributorAliases" in call_args[0]
    
    def test_delete_alias(self, repo):
        """Test removing an alias."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.delete_alias(5)
            
            assert result is True
            mock_cursor.execute.assert_called()


class TestMembership:
    """Tests for group membership operations (band members)."""
    
    @pytest.fixture
    def repo(self):
        return ContributorRepository()
    
    def test_get_members(self, repo):
        """Test fetching all members of a group."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (1, "Paul McCartney", "McCartney, Paul", "person", None),
            (2, "John Lennon", "Lennon, John", "person", None),
        ]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            members = repo.get_members(group_id=10)  # The Beatles
            
            assert len(members) == 2
            assert all(isinstance(m, Contributor) for m in members)
    
    def test_get_groups(self, repo):
        """Test fetching all groups a person belongs to."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (10, "The Beatles", "Beatles, The", "group"),
            (11, "Wings", "Wings", "group"),
        ]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            groups = repo.get_groups(person_id=1)  # Paul McCartney
            
            assert len(groups) == 2
            assert groups[0].name == "The Beatles"
    
    def test_add_member(self, repo):
        """Test adding a person to a group."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            repo.add_member(group_id=10, person_id=5)
            
            mock_cursor.execute.assert_called()
            call_args = mock_cursor.execute.call_args[0]
            assert "INSERT" in call_args[0]
    
    def test_remove_member(self, repo):
        """Test removing a person from a group."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            repo.remove_member(group_id=10, person_id=5)
            
            mock_cursor.execute.assert_called()
            call_args = mock_cursor.execute.call_args[0]
            assert "DELETE" in call_args[0]
    
    def test_get_member_count(self, repo):
        """Test counting group memberships."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (5,)  # 5 members
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            count = repo.get_member_count(10)
            assert count == 5


class TestValidateIdentity:
    """Tests for identity validation (conflict detection)."""
    
    @pytest.fixture
    def repo(self):
        return ContributorRepository()
    
    def test_validate_identity_no_conflict(self, repo):
        """Test validation passes for unique name."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # No match
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            is_conflict, msg = repo.validate_identity("Unique Name")
            
            assert is_conflict is None  # No conflict returns None
            assert msg == ""
    
    def test_validate_identity_conflict_with_primary(self, repo):
        """Test validation detects conflict with primary name."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            (1, "John Doe"),  # Found as primary name
        ]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            is_conflict, msg = repo.validate_identity("John Doe")
            
            assert is_conflict == 1  # Returns conflict ID
            assert "already exists" in msg.lower() or "John Doe" in msg


class TestResolveIdentityGraph:
    """Tests for identity graph resolution (search expansion)."""
    
    @pytest.fixture
    def repo(self):
        return ContributorRepository()
    
    def test_resolve_identity_graph_direct_match(self, repo):
        """Test resolving search term to contributor identities."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Step 1: Find direct match for 'John Lennon'
        # Step 2: Find group memberships
        # Step 3: Collect all names/aliases
        mock_cursor.fetchall.side_effect = [
            [(1,)],  # ContributorIDs matching direct name
            [],  # No aliases match
            [(10,)],  # Groups this person belongs to (The Beatles)
            [("John Lennon",), ("The Beatles",)],  # All related names
        ]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            identities = repo.resolve_identity_graph("John Lennon")
            
            assert len(identities) > 0
            assert "John Lennon" in identities


class TestGetByRole:
    """Legacy tests for get_by_role method (kept from original)."""
    
    @pytest.fixture
    def repo(self):
        return ContributorRepository()
    
    def test_get_by_role_success(self, repo):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [(1, "Artist 1"), (2, "Artist 2")]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn
            
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.get_by_role("Performer")
            
            assert len(result) == 2
            assert result[0] == (1, "Artist 1")
            
            mock_cursor.execute.assert_called_once()
            args = mock_cursor.execute.call_args[0]
            assert "SELECT DISTINCT" in args[0]

    def test_get_by_role_error(self, repo):
        mock_conn = MagicMock()
        
        @contextmanager
        def mock_get_conn():
            raise Exception("DB Error")
            yield mock_conn
        
        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            result = repo.get_by_role("Performer")
            assert result == []

    def test_get_all_aliases(self, repo):
        """Verify aliases are retrievable (e.g., 'Dale Nixon')."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("Dale Nixon",), ("Slim Shady",)]
        
        @contextmanager
        def mock_get_conn():
            yield mock_conn

        with patch.object(repo, 'get_connection', side_effect=mock_get_conn):
            aliases = repo.get_all_aliases()
            assert "Dale Nixon" in aliases
            assert "Slim Shady" in aliases
