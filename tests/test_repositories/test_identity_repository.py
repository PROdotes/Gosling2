"""
Contract tests for IdentityRepository.
Every assertion verifies EXACT values from the populated_db fixture.
"""

from src.data.identity_repository import IdentityRepository


class TestGetById:
    """IdentityRepository.get_by_id contracts."""

    def test_person_identity(self, populated_db):
        repo = IdentityRepository(populated_db)
        identity = repo.get_by_id(1)

        assert identity is not None
        assert identity.id == 1
        assert identity.type == "person"
        assert identity.display_name == "Dave Grohl"

    def test_group_identity(self, populated_db):
        repo = IdentityRepository(populated_db)
        identity = repo.get_by_id(2)

        assert identity is not None
        assert identity.id == 2
        assert identity.type == "group"
        assert identity.display_name == "Nirvana"

    def test_nonexistent_returns_none(self, populated_db):
        repo = IdentityRepository(populated_db)
        assert repo.get_by_id(999) is None


class TestGetByIds:
    """IdentityRepository.get_by_ids contracts."""

    def test_batch_fetch(self, populated_db):
        repo = IdentityRepository(populated_db)
        ids = repo.get_by_ids([1, 2, 3, 4])

        assert len(ids) == 4
        names = {i.display_name for i in ids}
        assert names == {"Dave Grohl", "Nirvana", "Foo Fighters", "Taylor Hawkins"}

    def test_empty_list(self, populated_db):
        repo = IdentityRepository(populated_db)
        assert repo.get_by_ids([]) == []

    def test_mixed_valid_invalid(self, populated_db):
        repo = IdentityRepository(populated_db)
        result = repo.get_by_ids([1, 999])
        assert len(result) == 1
        assert result[0].display_name == "Dave Grohl"


class TestGetAllIdentities:
    """IdentityRepository.get_all_identities contracts."""

    def test_returns_all_four(self, populated_db):
        repo = IdentityRepository(populated_db)
        identities = repo.get_all_identities()

        assert len(identities) == 4
        names = [i.display_name for i in identities]
        # Ordered by DisplayName COLLATE NOCASE ASC
        assert names == ["Dave Grohl", "Foo Fighters", "Nirvana", "Taylor Hawkins"]

    def test_types_are_correct(self, populated_db):
        repo = IdentityRepository(populated_db)
        identities = repo.get_all_identities()
        type_map = {i.display_name: i.type for i in identities}
        assert type_map == {
            "Dave Grohl": "person",
            "Foo Fighters": "group",
            "Nirvana": "group",
            "Taylor Hawkins": "person",
        }

    def test_empty_db_returns_empty(self, empty_db):
        repo = IdentityRepository(empty_db)
        assert repo.get_all_identities() == []


class TestSearchIdentities:
    """IdentityRepository.search_identities contracts."""

    def test_exact_name_match(self, populated_db):
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("Nirvana")
        assert len(results) == 1
        assert results[0].display_name == "Nirvana"
        assert results[0].id == 2

    def test_partial_name_match(self, populated_db):
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("Dave")
        assert len(results) == 1
        assert results[0].display_name == "Dave Grohl"

    def test_alias_match_returns_primary_identity(self, populated_db):
        """Searching 'Grohlton' should return Dave Grohl (identity 1) with primary display name."""
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("Grohlton")
        assert len(results) == 1
        assert results[0].id == 1
        assert results[0].display_name == "Dave Grohl"

    def test_another_alias(self, populated_db):
        """Searching 'Late!' should also return Dave Grohl."""
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("Late!")
        assert len(results) == 1
        assert results[0].id == 1

    def test_case_insensitive(self, populated_db):
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("nirvana")
        assert len(results) == 1
        assert results[0].display_name == "Nirvana"

    def test_no_match(self, populated_db):
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("ZZZZNONEXISTENT")
        assert results == []


class TestGetGroupIdsForMembers:
    """IdentityRepository.get_group_ids_for_members contracts."""

    def test_dave_groups(self, populated_db):
        """Dave (ID=1) is member of Nirvana(2) and Foo Fighters(3)."""
        repo = IdentityRepository(populated_db)
        group_ids = repo.get_group_ids_for_members([1])
        assert set(group_ids) == {2, 3}

    def test_taylor_groups(self, populated_db):
        """Taylor (ID=4) is member of Foo Fighters(3) only."""
        repo = IdentityRepository(populated_db)
        group_ids = repo.get_group_ids_for_members([4])
        assert group_ids == [3]

    def test_group_has_no_groups(self, populated_db):
        """A group (Nirvana ID=2) is not a member of any group."""
        repo = IdentityRepository(populated_db)
        group_ids = repo.get_group_ids_for_members([2])
        assert group_ids == []

    def test_empty_input(self, populated_db):
        repo = IdentityRepository(populated_db)
        assert repo.get_group_ids_for_members([]) == []

    def test_multiple_members(self, populated_db):
        """Both Dave(1) and Taylor(4) - should return Nirvana(2) and Foo Fighters(3)."""
        repo = IdentityRepository(populated_db)
        group_ids = set(repo.get_group_ids_for_members([1, 4]))
        assert group_ids == {2, 3}


class TestGetAliasesBatch:
    """IdentityRepository.get_aliases_batch contracts."""

    def test_dave_aliases(self, populated_db):
        """Dave (ID=1) has: Dave Grohl(10/primary), Grohlton(11), Late!(12), Ines Prajo(33)."""
        repo = IdentityRepository(populated_db)
        aliases = repo.get_aliases_batch([1])

        assert 1 in aliases
        alias_names = {a.display_name for a in aliases[1]}
        assert alias_names == {"Dave Grohl", "Grohlton", "Late!", "Ines Prajo"}

        # Verify primary flag
        primary = [a for a in aliases[1] if a.is_primary]
        assert len(primary) == 1
        assert primary[0].display_name == "Dave Grohl"

    def test_group_aliases(self, populated_db):
        """Nirvana (ID=2) has one name: 'Nirvana' (primary)."""
        repo = IdentityRepository(populated_db)
        aliases = repo.get_aliases_batch([2])
        assert len(aliases[2]) == 1
        assert aliases[2][0].display_name == "Nirvana"
        assert aliases[2][0].is_primary is True

    def test_empty_input(self, populated_db):
        repo = IdentityRepository(populated_db)
        assert repo.get_aliases_batch([]) == {}

    def test_identity_with_no_aliases(self, populated_db):
        """If an identity has no ArtistNames, the batch should return an empty list for that ID."""
        repo = IdentityRepository(populated_db)
        # ID 999 doesn't exist but the batch method pre-fills keys
        aliases = repo.get_aliases_batch([999])
        assert aliases[999] == []


class TestGetMembersBatch:
    """IdentityRepository.get_members_batch contracts."""

    def test_nirvana_members(self, populated_db):
        """Nirvana (ID=2) has one member: Dave Grohl (ID=1)."""
        repo = IdentityRepository(populated_db)
        members = repo.get_members_batch([2])
        assert len(members[2]) == 1
        assert members[2][0].display_name == "Dave Grohl"
        assert members[2][0].id == 1

    def test_foo_fighters_members(self, populated_db):
        """Foo Fighters (ID=3) has two members: Dave(1) and Taylor(4)."""
        repo = IdentityRepository(populated_db)
        members = repo.get_members_batch([3])
        member_names = {m.display_name for m in members[3]}
        assert member_names == {"Dave Grohl", "Taylor Hawkins"}

    def test_person_has_no_members(self, populated_db):
        """A person (Dave ID=1) has no members."""
        repo = IdentityRepository(populated_db)
        members = repo.get_members_batch([1])
        assert members[1] == []

    def test_empty_input(self, populated_db):
        repo = IdentityRepository(populated_db)
        assert repo.get_members_batch([]) == {}


class TestGetGroupsBatch:
    """IdentityRepository.get_groups_batch contracts."""

    def test_dave_groups(self, populated_db):
        """Dave (ID=1) belongs to Nirvana(2) and Foo Fighters(3)."""
        repo = IdentityRepository(populated_db)
        groups = repo.get_groups_batch([1])
        group_names = {g.display_name for g in groups[1]}
        assert group_names == {"Nirvana", "Foo Fighters"}

    def test_taylor_groups(self, populated_db):
        """Taylor (ID=4) belongs to Foo Fighters(3) only."""
        repo = IdentityRepository(populated_db)
        groups = repo.get_groups_batch([4])
        assert len(groups[4]) == 1
        assert groups[4][0].display_name == "Foo Fighters"

    def test_group_has_no_groups(self, populated_db):
        """Nirvana (group ID=2) does not belong to any group."""
        repo = IdentityRepository(populated_db)
        groups = repo.get_groups_batch([2])
        assert groups[2] == []

    def test_empty_input(self, populated_db):
        repo = IdentityRepository(populated_db)
        assert repo.get_groups_batch([]) == {}


class TestFallbackDisplayName:
    """Contract: COALESCE(an.DisplayName, i.LegalName, 'Unknown Artist #ID')."""

    def test_identity_with_no_artist_name(self, edge_case_db):
        """Identity 100 has no ArtistName at all -> should fallback to 'Unknown Artist #100'."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(100)
        assert identity is not None
        assert identity.display_name == "Unknown Artist #100"

    def test_identity_with_legal_name_only(self, edge_case_db):
        """Identity 101 has LegalName='John Legal' but no ArtistName -> should fallback to LegalName."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(101)
        assert identity is not None
        assert identity.display_name == "John Legal"
