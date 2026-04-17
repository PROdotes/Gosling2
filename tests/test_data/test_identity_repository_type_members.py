"""
Tests for IdentityRepository: set_type, add_member, remove_member.
populated_db identity fixtures:
  ID=1: person  "Dave Grohl"    (aliases: Grohlton/11, Late!/12, Ines Prajo/33)
  ID=2: group   "Nirvana"       (members: Dave/1)
  ID=3: group   "Foo Fighters"  (members: Dave/1, Taylor/4)
  ID=4: person  "Taylor Hawkins"
"""

import pytest
from src.data.identity_repository import IdentityRepository

# ---------------------------------------------------------------------------
# set_type
# ---------------------------------------------------------------------------


class TestSetType:
    def test_person_to_group_succeeds(self, populated_db):
        """Converting a person identity to group should persist."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            repo.set_type(4, "group", conn)
            conn.commit()
        identity = repo.get_by_id(4)
        assert identity.type == "group", f"Expected 'group', got {identity.type!r}"

    def test_group_to_person_succeeds_when_no_members(self, populated_db):
        """Converting a group with no members to person should succeed."""
        repo = IdentityRepository(populated_db)
        # Nirvana (ID=2) has Dave as member — remove him first
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM GroupMemberships WHERE GroupIdentityID = 2")
            conn.commit()

        with repo.get_connection() as conn:
            repo.set_type(2, "person", conn)
            conn.commit()
        identity = repo.get_by_id(2)
        assert identity.type == "person", f"Expected 'person', got {identity.type!r}"

    def test_group_to_person_blocked_when_has_members(self, populated_db):
        """Converting a group that still has members should raise ValueError."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            with pytest.raises(ValueError, match="member"):
                repo.set_type(2, "person", conn)

    def test_invalid_type_raises(self, populated_db):
        """Passing an unrecognised type string should raise ValueError."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            with pytest.raises(ValueError, match="Invalid"):
                repo.set_type(1, "band", conn)

    def test_not_found_raises(self, populated_db):
        """Non-existent identity should raise LookupError."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            with pytest.raises(LookupError):
                repo.set_type(9999, "group", conn)

    def test_set_same_type_is_noop(self, populated_db):
        """Setting the same type should not raise."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            repo.set_type(1, "person", conn)  # already person

    def test_group_to_person_blocked_state_unchanged(self, populated_db):
        """After a blocked conversion, the identity type must remain unchanged."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            with pytest.raises(ValueError):
                repo.set_type(2, "person", conn)
        identity = repo.get_by_id(2)
        assert identity.type == "group", (
            f"Expected type unchanged, got {identity.type!r}"
        )


# ---------------------------------------------------------------------------
# add_member
# ---------------------------------------------------------------------------


class TestAddMember:
    def test_add_member_succeeds(self, populated_db):
        """Adding Taylor (4) as a member of Nirvana (2) should persist."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            repo.add_member(2, 4, cursor)
            conn.commit()

        members = repo.get_members_batch([2])
        member_ids = {m.id for m in members[2]}
        assert 4 in member_ids, f"Expected Taylor (4) in members, got {member_ids}"

    def test_add_member_idempotent(self, populated_db):
        """Adding an existing member again should not raise or duplicate."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            repo.add_member(2, 1, cursor)  # Dave already in Nirvana
            conn.commit()

            count = cursor.execute(
                "SELECT COUNT(*) FROM GroupMemberships WHERE GroupIdentityID = 2 AND MemberIdentityID = 1"
            ).fetchone()[0]
        assert count == 1, f"Expected 1 membership row, got {count}"

    def test_add_member_self_raises(self, populated_db):
        """A group cannot be a member of itself."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            with pytest.raises(ValueError, match="itself"):
                repo.add_member(2, 2, cursor)

    def test_add_member_group_not_found_raises(self, populated_db):
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            with pytest.raises(LookupError):
                repo.add_member(9999, 1, cursor)

    def test_add_member_member_not_found_raises(self, populated_db):
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            with pytest.raises(LookupError):
                repo.add_member(2, 9999, cursor)

    def test_add_group_as_member_raises(self, populated_db):
        """A group identity cannot be a member of another group."""
        repo = IdentityRepository(populated_db)
        # Nirvana (2) and Foo Fighters (3) are both groups
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            with pytest.raises(ValueError, match="group"):
                repo.add_member(2, 3, cursor)


# ---------------------------------------------------------------------------
# remove_member
# ---------------------------------------------------------------------------


class TestRemoveMember:
    def test_remove_member_succeeds(self, populated_db):
        """Removing Dave (1) from Nirvana (2) should delete the link."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            repo.remove_member(2, 1, cursor)
            conn.commit()

        members = repo.get_members_batch([2])
        member_ids = {m.id for m in members[2]}
        assert 1 not in member_ids, f"Expected Dave removed, got {member_ids}"

    def test_remove_member_identity_record_survives(self, populated_db):
        """Removing a member must not delete the identity itself."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            repo.remove_member(2, 1, cursor)
            conn.commit()

        assert repo.get_by_id(1) is not None, (
            "Dave's identity should survive member removal"
        )

    def test_remove_member_noop_if_not_linked(self, populated_db):
        """Removing a member that isn't linked should not raise."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            repo.remove_member(2, 4, cursor)  # Taylor not in Nirvana

    def test_remove_member_does_not_affect_other_groups(self, populated_db):
        """Removing Dave from Nirvana should not affect his Foo Fighters membership."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            repo.remove_member(2, 1, cursor)
            conn.commit()

        groups = repo.get_groups_batch([1])
        group_ids = {g.id for g in groups[1]}
        assert 3 in group_ids, f"Expected Foo Fighters (3) unaffected, got {group_ids}"
