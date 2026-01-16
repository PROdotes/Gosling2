"""
Reproduction test for artist type change bug.

BUG: Changing an artist from Person to Group (or vice versa) doesn't properly
clean up GroupMemberships, leading to:
1. Orphaned membership records
2. Potential circular alias references when trying to fix quickly

Expected behavior:
- When Person -> Group: Remove all GroupMemberships where this identity is a MEMBER
- When Group -> Person: Remove all GroupMemberships where this identity is a GROUP
"""
import pytest
import uuid
from src.business.services.contributor_service import ContributorService


class TestArtistTypeChange:
    """Tests for artist type change functionality."""
    
    @pytest.fixture
    def service(self):
        """Create a real contributor service for testing."""
        return ContributorService()
    
    def test_person_to_group_clears_memberships(self, service):
        """
        When a Person becomes a Group, they should be removed from all groups
        they were previously a member of.
        
        Scenario:
        - Create Queen (group)
        - Create Freddie (person)
        - Add Freddie as member of Queen
        - Change Freddie to a Group
        - Result: Freddie should no longer be a member of Queen
        """
        # 1. Setup (use unique names to avoid DB conflicts)
        uid = str(uuid.uuid4())[:8]
        queen = service.create(f"Queen TypeChg {uid}", type="group")
        freddie = service.create(f"Freddie TypeChg {uid}", type="person")
        
        # Add Freddie as member of Queen
        assert service.add_member(queen.contributor_id, freddie.contributor_id)
        
        # Verify membership exists
        members_before = service.get_members(queen.contributor_id)
        assert len(members_before) == 1
        freddie_groups_before = service.get_groups(freddie.contributor_id)
        assert len(freddie_groups_before) == 1
        
        # 2. Change Freddie from Person to Group
        freddie.type = "group"
        result = service.update(freddie)
        assert result is True
        
        # 3. Verify memberships are cleared
        # Freddie should no longer be a member of any group
        freddie_groups_after = service.get_groups(freddie.contributor_id)
        assert len(freddie_groups_after) == 0, \
            f"Expected 0 group memberships after type change, got {len(freddie_groups_after)}"
        
        # Queen should have 0 members now
        members_after = service.get_members(queen.contributor_id)
        assert len(members_after) == 0, \
            f"Expected 0 members after type change, got {len(members_after)}"
    
    def test_group_to_person_clears_members(self, service):
        """
        When a Group becomes a Person, all its members should be removed.
        
        Scenario:
        - Create Band (group)
        - Create Singer (person)
        - Add Singer as member of Band
        - Change Band to a Person
        - Result: Band should have no members
        """
        # 1. Setup (use unique names to avoid DB conflicts)
        uid = str(uuid.uuid4())[:8]
        band = service.create(f"Band TypeChg {uid}", type="group")
        singer = service.create(f"Singer TypeChg {uid}", type="person")
        
        # Add Singer as member of Band
        assert service.add_member(band.contributor_id, singer.contributor_id)
        
        # Verify membership exists
        members_before = service.get_members(band.contributor_id)
        assert len(members_before) == 1
        
        # 2. Change Band from Group to Person
        band.type = "person"
        result = service.update(band)
        assert result is True
        
        # 3. Verify members are cleared
        # Band (now a person) should have no members
        members_after = service.get_members(band.contributor_id)
        assert len(members_after) == 0, \
            f"Expected 0 members after type change, got {len(members_after)}"
        
        # Singer should not be in any groups anymore (the group became a person)
        singer_groups_after = service.get_groups(singer.contributor_id)
        # Filter out any other groups Singer might be in (just check Band is gone)
        # Actually, since Band was the only group, should be 0
        assert len(singer_groups_after) == 0, \
            f"Expected 0 group memberships for singer, got {len(singer_groups_after)}"

    def test_type_change_with_no_memberships_succeeds(self, service):
        """
        Type change should work cleanly when there are no memberships.
        """
        # 1. Setup - solo artist with no group memberships
        uid = str(uuid.uuid4())[:8]
        solo = service.create(f"Solo TypeChg {uid}", type="person")
        
        # 2. Change to group
        solo.type = "group"
        result = service.update(solo)
        assert result is True
        
        # Verify type changed
        updated = service.get_by_id(solo.contributor_id)
        assert updated.type == "group"
        
        # 3. Change back to person
        updated.type = "person"
        result = service.update(updated)
        assert result is True
        
        # Verify type changed again
        final = service.get_by_id(solo.contributor_id)
        assert final.type == "person"

    def test_type_change_does_not_affect_unrelated_memberships(self, service):
        """
        Changing one artist's type should not affect OTHER artists' memberships.
        
        Scenario:
        - Create Band1 (group) with Member1
        - Create Band2 (group) with Member2
        - Change Member1 to a group
        - Result: Member2 should STILL be in Band2
        """
        uid = str(uuid.uuid4())[:8]
        
        # Setup two independent groups with members
        band1 = service.create(f"Band1 TypeChg {uid}", type="group")
        member1 = service.create(f"Member1 TypeChg {uid}", type="person")
        
        band2 = service.create(f"Band2 TypeChg {uid}", type="group")
        member2 = service.create(f"Member2 TypeChg {uid}", type="person")
        
        assert service.add_member(band1.contributor_id, member1.contributor_id)
        assert service.add_member(band2.contributor_id, member2.contributor_id)
        
        # Verify both memberships exist
        assert len(service.get_members(band1.contributor_id)) == 1
        assert len(service.get_members(band2.contributor_id)) == 1
        
        # Change Member1 to a group
        member1.type = "group"
        service.update(member1)
        
        # Band2's membership should be UNAFFECTED
        band2_members = service.get_members(band2.contributor_id)
        assert len(band2_members) == 1
        assert band2_members[0].name == f"Member2 TypeChg {uid}"
        
        # Member2 should still be in Band2
        member2_groups = service.get_groups(member2.contributor_id)
        assert len(member2_groups) == 1
        assert member2_groups[0].name == f"Band2 TypeChg {uid}"

    def test_identity_graph_resolution_after_type_change(self, service):
        """
        The resolve_identity_graph function should still work correctly
        after an artist's type has been changed.
        """
        uid = str(uuid.uuid4())[:8]
        
        # Create a group with a member who has an alias
        group = service.create(f"TestGroup {uid}", type="group")
        person = service.create(f"TestPerson {uid}", type="person")
        
        # Add person to group
        assert service.add_member(group.contributor_id, person.contributor_id)
        
        # Add an alias to the person
        assert service.add_alias(person.contributor_id, f"TestAlias {uid}")
        
        # Verify resolve works BEFORE type change
        # Searching for the alias should find both the person and the group
        resolved = service.resolve_identity_graph(f"TestAlias {uid}")
        assert f"TestPerson {uid}" in resolved
        assert f"TestAlias {uid}" in resolved
        assert f"TestGroup {uid}" in resolved  # Through membership
        
        # Now change the person to a group (clears their memberships)
        person.type = "group"
        service.update(person)
        
        # Resolve should STILL work, but now won't include the group
        # (since person is no longer a member)
        resolved_after = service.resolve_identity_graph(f"TestAlias {uid}")
        assert f"TestPerson {uid}" in resolved_after
        assert f"TestAlias {uid}" in resolved_after
        # TestGroup should NO LONGER appear (membership was cleared)
        assert f"TestGroup {uid}" not in resolved_after

