"""
Contributor Service Logic Tests

Tests for ContributorService business logic (happy path and basic errors).
Follows Law of Separation: This is Level 1 (Logic) testing.
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.business.services.contributor_service import ContributorService
from src.data.models.contributor import Contributor


@pytest.fixture
def mock_repositories():
    """Create mocked repositories for testing."""
    # Mock credit repository
    credit_repo = Mock()
    credit_repo.swap_song_contributor_credits = Mock(return_value=True)
    credit_repo.get_connection = Mock(return_value=Mock(__enter__=Mock(return_value=Mock()), __exit__=Mock(return_value=None)))

    # Mock identity repository
    identity_repo = Mock()
    identity_repo.remove_all_group_members = Mock(return_value=True)
    identity_repo.remove_member_from_all_groups = Mock(return_value=True)
    identity_repo.update = Mock(return_value=True)
    identity_repo.get_connection = Mock(return_value=Mock(__enter__=Mock(return_value=Mock()), __exit__=Mock(return_value=None)))

    # Mock identity service
    identity_service = Mock()
    identity_service.abdicate = Mock(return_value=True)

    # Mock artist name service
    name_service = Mock()
    name_service.get_name = Mock(return_value=Mock(contributor_id=1, name="Test", type="person"))

    return {
        'credit_repo': credit_repo,
        'identity_repo': identity_repo,
        'identity_service': identity_service,
        'name_service': name_service
    }


@pytest.fixture
def contributor_service(mock_repositories):
    """Create ContributorService with mocked dependencies."""
    service = ContributorService.__new__(ContributorService)  # Create without calling __init__

    # Inject mocked repositories
    service._credit_repo = mock_repositories['credit_repo']
    service._identity_repo = mock_repositories['identity_repo']
    service._identity_service = mock_repositories['identity_service']
    service._name_service = mock_repositories['name_service']

    return service


class TestContributorServiceLogic:
    """Logic tests for ContributorService happy paths and basic errors."""

    def test_swap_song_contributor_success(self, contributor_service, mock_repositories):
        """Test successful contributor swap on a song."""
        # Execute swap
        result = contributor_service.swap_song_contributor(100, 1, 2, batch_id="test-batch")

        # Verify result
        assert result is True

        # Verify repository method was called correctly
        mock_repositories['credit_repo'].swap_song_contributor_credits.assert_called_once_with(
            100, 1, 2, "test-batch"
        )

    def test_swap_song_contributor_no_batch_id(self, contributor_service, mock_repositories):
        """Test swap works without batch_id."""
        result = contributor_service.swap_song_contributor(100, 1, 2)

        assert result is True
        mock_repositories['credit_repo'].swap_song_contributor_credits.assert_called_once_with(
            100, 1, 2, None
        )

    # Note: Complex update logic with merge handling is tested through integration tests
    # The key refactoring (moving SQL to repositories) is verified by audit test suite passing
    def test_update_nonexistent_contributor(self, contributor_service, mock_repositories):
        """Test updating a contributor that doesn't exist."""
        # Mock name service to return None (contributor not found)
        mock_repositories['name_service'].get_name.return_value = None

        contributor = Contributor(contributor_id=999, name="Nonexistent", type="person")
        result = contributor_service.update(contributor)

        assert result is False