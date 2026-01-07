
import pytest
from src.business.services.contributor_service import ContributorService
from src.data.repositories.contributor_repository import ContributorRepository

@pytest.fixture
def service():
    # Use in-memory DB for isolation if possible, or assume test DB handling
    # The existing tests seem to run against a test DB implicitly or mock it.
    # We'll use the default service which uses the real repo/DB.
    # Ideally we'd use a transaction rollback, but let's assume the test runner handles DB setup/teardown
    # or we can use the existing pattern.
    return ContributorService()

def test_alias_group_member_linking(service):
    """
    Verify that adding a member with an alias correctly sets CreditedAsNameID
    and that fetching members returns the alias name.
    """
    # 1. Setup Data
    freddie = service.create("Freddie Mercury Test", type="person")
    queen = service.create("Queen Test", type="group")
    
    # Create Alias
    service.add_alias(freddie.contributor_id, "Ziggy Stardust Test")
    aliases = service.get_aliases(freddie.contributor_id)
    ziggy_alias = next(a for a in aliases if a.alias_name == "Ziggy Stardust Test")
    
    # 2. Add Member as Alias
    # This calls the UPSERT logic we added
    result = service.add_member(queen.contributor_id, freddie.contributor_id, member_alias_id=ziggy_alias.alias_id)
    assert result is True, "Failed to add member"
    
    # 3. Verify Members List (Should show Ziggy)
    members = service.get_members(queen.contributor_id)
    assert len(members) == 1
    member = members[0]
    
    assert member.name == "Ziggy Stardust Test", f"Expected 'Ziggy Stardust Test', got '{member.name}'"
    assert member.matched_alias == "Ziggy Stardust Test", "matched_alias should be set"
    assert member.contributor_id == ziggy_alias.alias_id, "ID should be the Alias NameID"
    
    # 4. Verify Raw DB State (Optional but good)
    # We can inspect matched_alias which comes from the LEFT JOIN we added.
    
    # 5. Verify Removal
    # We pass the ID returned by get_members (which is Ziggy's NameID)
    remove_result = service.remove_member(queen.contributor_id, member.contributor_id)
    assert remove_result is True, "Failed to remove member"
    
    members_after = service.get_members(queen.contributor_id)
    assert len(members_after) == 0, "Member was not removed"

def test_add_member_update_alias(service):
    """
    Verify that adding an alias to an EXISTING member updates the alias.
    """
    john = service.create("John Deacon Test", type="person")
    queen = service.create("Queen Test 2", type="group")
    
    # Add as Primary first
    service.add_member(queen.contributor_id, john.contributor_id)
    
    members = service.get_members(queen.contributor_id)
    assert members[0].name == "John Deacon Test"
    
    # Add Alias
    service.add_alias(john.contributor_id, "Deacy Test")
    aliases = service.get_aliases(john.contributor_id)
    deacy_alias = next(a for a in aliases if a.alias_name == "Deacy Test")
    
    # Re-Add as Alias (Should Update via UPSERT)
    service.add_member(queen.contributor_id, john.contributor_id, member_alias_id=deacy_alias.alias_id)
    
    members_updated = service.get_members(queen.contributor_id)
    assert members_updated[0].name == "Deacy Test", "Member alias was not updated"
