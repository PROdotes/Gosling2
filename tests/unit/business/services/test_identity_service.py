"""Unit tests for IdentityService"""
import pytest
from unittest.mock import MagicMock
from src.business.services.identity_service import IdentityService
from src.data.models.identity import Identity


class TestIdentityService:
    """Tests for IdentityService logic."""
    
    @pytest.fixture
    def service(self):
        """Create service with mock repository."""
        mock_repo = MagicMock()
        return IdentityService(mock_repo)

    def test_get_identity(self, service):
        """Test fetching identity."""
        service._repo.get_by_id.return_value = Identity(identity_id=1, legal_name="David Bowie")
        
        result = service.get_identity(1)
        
        assert result.legal_name == "David Bowie"
        service._repo.get_by_id.assert_called_with(1)

    def test_link_name_to_identity(self, service):
        """Test linking a name to an identity."""
        mock_name_repo = MagicMock()
        service._name_repo = mock_name_repo
        
        service.link_name_to_identity(10, 1)
        
        mock_name_repo.get_by_id.assert_called_with(10)
        mock_name_repo.update.assert_called()
