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


class TestIdentityMerge:
    """Integration tests for identity merge with group memberships."""
    
    @pytest.fixture
    def contributor_service(self):
        """Create a real contributor service for integration testing."""
        from src.business.services.contributor_service import ContributorService
        return ContributorService()
    
    def test_merge_transfers_group_memberships(self, contributor_service):
        """
        Verify that merging two identities transfers group memberships.
        
        Scenario:
        - Freddie is a member of Queen
        - Ziggy is a member of Queen
        - Merge Ziggy into Freddie
        - Result: Only Freddie is a member (no duplicate), Ziggy is an alias of Freddie
        """
        # 1. Setup
        queen = contributor_service.create("Queen Test Merge", type="group")
        freddie = contributor_service.create("Freddie Test Merge", type="person")
        ziggy = contributor_service.create("Ziggy Test Merge", type="person")
        
        # Add both as members of Queen
        contributor_service.add_member(queen.contributor_id, freddie.contributor_id)
        contributor_service.add_member(queen.contributor_id, ziggy.contributor_id)
        
        # Verify both are members
        members_before = contributor_service.get_members(queen.contributor_id)
        assert len(members_before) == 2
        
        # 2. Merge Ziggy INTO Freddie
        result = contributor_service.merge(ziggy.contributor_id, freddie.contributor_id)
        assert result is True
        
        # 3. Verify
        # Only Freddie should remain as a member (Ziggy's membership merged/skipped)
        members_after = contributor_service.get_members(queen.contributor_id)
        assert len(members_after) == 1, f"Expected 1 member, got {len(members_after)}"
        assert members_after[0].name == "Freddie Test Merge"
        
        # Ziggy should now be an alias of Freddie
        aliases = contributor_service.get_aliases(freddie.contributor_id)
        alias_names = [a.alias_name for a in aliases]
        assert "Ziggy Test Merge" in alias_names, "Ziggy should be an alias of Freddie"

