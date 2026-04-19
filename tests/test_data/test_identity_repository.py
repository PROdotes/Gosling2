"""
Contract tests for IdentityRepository.
Every assertion verifies EXACT values from the populated_db fixture.
"""

from src.data.identity_repository import IdentityRepository


class TestGetById:
    """IdentityRepository.get_by_id contracts."""

    def test_person_identity(self, populated_db):
        """Test that get_by_id returns complete person identity."""
        repo = IdentityRepository(populated_db)
        identity = repo.get_by_id(1)

        assert identity is not None, f"Expected identity object, got {identity}"
        assert identity.id == 1, f"Expected 1, got {identity.id}"
        assert identity.type == "person", f"Expected 'person', got '{identity.type}'"
        assert (
            identity.display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got '{identity.display_name}'"
        assert (
            identity.legal_name == "David Eric Grohl"
        ), f"Expected 'David Eric Grohl' for legal_name, got {identity.legal_name}"
        assert (
            identity.aliases == []
        ), f"Expected empty list for aliases, got {identity.aliases}"
        assert (
            identity.members == []
        ), f"Expected empty list for members, got {identity.members}"
        assert (
            identity.groups == []
        ), f"Expected empty list for groups, got {identity.groups}"

    def test_group_identity(self, populated_db):
        """Test that get_by_id returns complete group identity."""
        repo = IdentityRepository(populated_db)
        identity = repo.get_by_id(2)

        assert identity is not None, f"Expected identity object, got {identity}"
        assert identity.id == 2, f"Expected 2, got {identity.id}"
        assert identity.type == "group", f"Expected 'group', got '{identity.type}'"
        assert (
            identity.display_name == "Nirvana"
        ), f"Expected 'Nirvana', got '{identity.display_name}'"
        assert (
            identity.legal_name is None
        ), f"Expected None for legal_name, got {identity.legal_name}"
        assert (
            identity.aliases == []
        ), f"Expected empty list for aliases, got {identity.aliases}"
        assert (
            identity.members == []
        ), f"Expected empty list for members, got {identity.members}"
        assert (
            identity.groups == []
        ), f"Expected empty list for groups, got {identity.groups}"

    def test_nonexistent_returns_none(self, populated_db):
        """Test that get_by_id returns None for non-existent ID."""
        repo = IdentityRepository(populated_db)
        identity = repo.get_by_id(999)
        assert identity is None, f"Expected None for nonexistent ID, got {identity}"


class TestGetByIds:
    """IdentityRepository.get_by_ids contracts."""

    def test_batch_fetch_returns_complete_objects(self, populated_db):
        """Test that get_by_ids returns complete identity objects."""
        repo = IdentityRepository(populated_db)
        identities = repo.get_by_ids([1, 2, 3, 4])

        assert len(identities) == 4, f"Expected 4 identities, got {len(identities)}"

        # Identity 1: Dave Grohl - exhaustive assertions
        assert identities[0].id == 1, f"Expected 1, got {identities[0].id}"
        assert (
            identities[0].display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got '{identities[0].display_name}'"
        assert (
            identities[0].type == "person"
        ), f"Expected 'person', got '{identities[0].type}'"

        # Identity 2: Nirvana - exhaustive assertions
        assert identities[1].id == 2, f"Expected 2, got {identities[1].id}"
        assert (
            identities[1].display_name == "Nirvana"
        ), f"Expected 'Nirvana', got '{identities[1].display_name}'"
        assert (
            identities[1].type == "group"
        ), f"Expected 'group', got '{identities[1].type}'"

        # Identity 3: Foo Fighters - exhaustive assertions
        assert identities[2].id == 3, f"Expected 3, got {identities[2].id}"
        assert (
            identities[2].display_name == "Foo Fighters"
        ), f"Expected 'Foo Fighters', got '{identities[2].display_name}'"
        assert (
            identities[2].type == "group"
        ), f"Expected 'group', got '{identities[2].type}'"

        # Identity 4: Taylor Hawkins - exhaustive assertions
        assert identities[3].id == 4, f"Expected 4, got {identities[3].id}"
        assert (
            identities[3].display_name == "Taylor Hawkins"
        ), f"Expected 'Taylor Hawkins', got '{identities[3].display_name}'"
        assert (
            identities[3].type == "person"
        ), f"Expected 'person', got '{identities[3].type}'"

    def test_empty_list_returns_empty(self, populated_db):
        """Test that get_by_ids returns empty list for empty input."""
        repo = IdentityRepository(populated_db)
        identities = repo.get_by_ids([])
        assert identities == [], f"Expected empty list, got {identities}"

    def test_mixed_valid_invalid_returns_only_valid(self, populated_db):
        """Test that get_by_ids returns only found items."""
        repo = IdentityRepository(populated_db)
        identities = repo.get_by_ids([1, 999])

        assert len(identities) == 1, f"Expected 1 identity, got {len(identities)}"
        assert identities[0].id == 1, f"Expected 1, got {identities[0].id}"
        assert (
            identities[0].display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got '{identities[0].display_name}'"
        assert (
            identities[0].type == "person"
        ), f"Expected 'person', got '{identities[0].type}'"


class TestGetAllIdentities:
    """IdentityRepository.get_all_identities contracts."""

    def test_returns_all_four_ordered(self, populated_db):
        """Test that get_all_identities returns all identities ordered by name."""
        repo = IdentityRepository(populated_db)
        identities = repo.get_all_identities()

        assert len(identities) == 4, f"Expected 4 identities, got {len(identities)}"

        # Ordered by DisplayName COLLATE NOCASE ASC
        assert identities[0].id == 1, f"Expected 1, got {identities[0].id}"
        assert (
            identities[0].display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got '{identities[0].display_name}'"
        assert (
            identities[0].type == "person"
        ), f"Expected 'person', got '{identities[0].type}'"

        assert identities[1].id == 3, f"Expected 3, got {identities[1].id}"
        assert (
            identities[1].display_name == "Foo Fighters"
        ), f"Expected 'Foo Fighters', got '{identities[1].display_name}'"
        assert (
            identities[1].type == "group"
        ), f"Expected 'group', got '{identities[1].type}'"

        assert identities[2].id == 2, f"Expected 2, got {identities[2].id}"
        assert (
            identities[2].display_name == "Nirvana"
        ), f"Expected 'Nirvana', got '{identities[2].display_name}'"
        assert (
            identities[2].type == "group"
        ), f"Expected 'group', got '{identities[2].type}'"

        assert identities[3].id == 4, f"Expected 4, got {identities[3].id}"
        assert (
            identities[3].display_name == "Taylor Hawkins"
        ), f"Expected 'Taylor Hawkins', got '{identities[3].display_name}'"
        assert (
            identities[3].type == "person"
        ), f"Expected 'person', got '{identities[3].type}'"

    def test_empty_db_returns_empty(self, empty_db):
        """Test that get_all_identities returns empty on empty DB."""
        repo = IdentityRepository(empty_db)
        identities = repo.get_all_identities()
        assert identities == [], f"Expected empty list on empty DB, got {identities}"


class TestSearchIdentities:
    """IdentityRepository.search_identities contracts."""

    def test_exact_name_match(self, populated_db):
        """Test that exact name match returns identity."""
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("Nirvana")

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 2, f"Expected 2, got {results[0].id}"
        assert (
            results[0].display_name == "Nirvana"
        ), f"Expected 'Nirvana', got '{results[0].display_name}'"
        assert results[0].type == "group", f"Expected 'group', got '{results[0].type}'"

    def test_partial_name_match(self, populated_db):
        """Test that partial name match returns identity."""
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("Dave")

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 1, f"Expected 1, got {results[0].id}"
        assert (
            results[0].display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got '{results[0].display_name}'"

    def test_alias_match_returns_primary_identity(self, populated_db):
        """Searching 'Grohlton' should return Dave Grohl (identity 1) with primary display name."""
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("Grohlton")

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 1, f"Expected 1, got {results[0].id}"
        assert (
            results[0].display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got '{results[0].display_name}'"

    def test_another_alias(self, populated_db):
        """Searching 'Late!' should also return Dave Grohl."""
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("Late!")

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 1, f"Expected 1, got {results[0].id}"
        assert (
            results[0].display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got '{results[0].display_name}'"

    def test_case_insensitive(self, populated_db):
        """Test that search is case-insensitive."""
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("nirvana")

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 2, f"Expected 2, got {results[0].id}"
        assert (
            results[0].display_name == "Nirvana"
        ), f"Expected 'Nirvana', got '{results[0].display_name}'"

    def test_no_match_returns_empty(self, populated_db):
        """Test that search returns empty list for no matches."""
        repo = IdentityRepository(populated_db)
        results = repo.search_identities("ZZZZNONEXISTENT")
        assert results == [], f"Expected empty list for no match, got {results}"


class TestGetGroupIdsForMembers:
    """IdentityRepository.get_group_ids_for_members contracts."""

    def test_dave_groups(self, populated_db):
        """Dave (ID=1) is member of Nirvana(2) and Foo Fighters(3)."""
        repo = IdentityRepository(populated_db)
        group_ids = repo.get_group_ids_for_members([1])
        assert set(group_ids) == {2, 3}, f"Expected {{2, 3}}, got {set(group_ids)}"

    def test_taylor_groups(self, populated_db):
        """Taylor (ID=4) is member of Foo Fighters(3) only."""
        repo = IdentityRepository(populated_db)
        group_ids = repo.get_group_ids_for_members([4])
        assert group_ids == [3], f"Expected [3], got {group_ids}"

    def test_group_has_no_groups(self, populated_db):
        """A group (Nirvana ID=2) is not a member of any group."""
        repo = IdentityRepository(populated_db)
        group_ids = repo.get_group_ids_for_members([2])
        assert group_ids == [], f"Expected empty list for group, got {group_ids}"

    def test_empty_input_returns_empty(self, populated_db):
        """Test that empty input returns empty list."""
        repo = IdentityRepository(populated_db)
        group_ids = repo.get_group_ids_for_members([])
        assert group_ids == [], f"Expected empty list for empty input, got {group_ids}"

    def test_multiple_members(self, populated_db):
        """Both Dave(1) and Taylor(4) - should return Nirvana(2) and Foo Fighters(3)."""
        repo = IdentityRepository(populated_db)
        group_ids = set(repo.get_group_ids_for_members([1, 4]))
        assert group_ids == {2, 3}, f"Expected {{2, 3}}, got {group_ids}"


class TestGetAliasesBatch:
    """IdentityRepository.get_aliases_batch contracts."""

    def test_dave_aliases(self, populated_db):
        """Dave (ID=1) has: Dave Grohl(10/primary), Grohlton(11), Late!(12), Ines Prajo(33)."""
        repo = IdentityRepository(populated_db)
        aliases = repo.get_aliases_batch([1])

        assert (
            1 in aliases
        ), f"Expected key 1 in aliases dict, got keys: {aliases.keys()}"
        assert len(aliases[1]) == 4, f"Expected 4 aliases, got {len(aliases[1])}"
        alias_names = {a.display_name for a in aliases[1]}
        assert alias_names == {
            "Dave Grohl",
            "Grohlton",
            "Late!",
            "Ines Prajo",
        }, f"Unexpected alias names: {alias_names}"

        # Verify primary flag
        primary = [a for a in aliases[1] if a.is_primary]
        assert len(primary) == 1, f"Expected 1 primary alias, got {len(primary)}"
        assert (
            primary[0].display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl' as primary, got '{primary[0].display_name}'"

    def test_group_aliases(self, populated_db):
        """Nirvana (ID=2) has one name: 'Nirvana' (primary)."""
        repo = IdentityRepository(populated_db)
        aliases = repo.get_aliases_batch([2])

        assert (
            2 in aliases
        ), f"Expected key 2 in aliases dict, got keys: {aliases.keys()}"
        assert len(aliases[2]) == 1, f"Expected 1 alias, got {len(aliases[2])}"
        assert (
            aliases[2][0].display_name == "Nirvana"
        ), f"Expected 'Nirvana', got '{aliases[2][0].display_name}'"
        assert (
            aliases[2][0].is_primary is True
        ), f"Expected True for is_primary, got {aliases[2][0].is_primary}"

    def test_empty_input_returns_empty_dict(self, populated_db):
        """Test that empty input returns empty dict."""
        repo = IdentityRepository(populated_db)
        aliases = repo.get_aliases_batch([])
        assert aliases == {}, f"Expected empty dict for empty input, got {aliases}"

    def test_identity_with_no_aliases(self, populated_db):
        """If an identity has no ArtistNames, the batch should return an empty list for that ID."""
        repo = IdentityRepository(populated_db)
        # ID 999 doesn't exist but the batch method pre-fills keys
        aliases = repo.get_aliases_batch([999])
        assert (
            999 in aliases
        ), f"Expected key 999 in aliases dict, got keys: {aliases.keys()}"
        assert (
            aliases[999] == []
        ), f"Expected empty list for nonexistent identity, got {aliases[999]}"


class TestGetMembersBatch:
    """IdentityRepository.get_members_batch contracts."""

    def test_nirvana_members(self, populated_db):
        """Nirvana (ID=2) has one member: Dave Grohl (ID=1)."""
        repo = IdentityRepository(populated_db)
        members = repo.get_members_batch([2])

        assert (
            2 in members
        ), f"Expected key 2 in members dict, got keys: {members.keys()}"
        assert len(members[2]) == 1, f"Expected 1 member, got {len(members[2])}"
        assert members[2][0].id == 1, f"Expected 1, got {members[2][0].id}"
        assert (
            members[2][0].display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got '{members[2][0].display_name}'"

    def test_foo_fighters_members(self, populated_db):
        """Foo Fighters (ID=3) has two members: Dave(1) and Taylor(4)."""
        repo = IdentityRepository(populated_db)
        members = repo.get_members_batch([3])

        assert (
            3 in members
        ), f"Expected key 3 in members dict, got keys: {members.keys()}"
        assert len(members[3]) == 2, f"Expected 2 members, got {len(members[3])}"
        member_names = {m.display_name for m in members[3]}
        assert member_names == {
            "Dave Grohl",
            "Taylor Hawkins",
        }, f"Unexpected member names: {member_names}"

    def test_person_has_no_members(self, populated_db):
        """A person (Dave ID=1) has no members."""
        repo = IdentityRepository(populated_db)
        members = repo.get_members_batch([1])

        assert (
            1 in members
        ), f"Expected key 1 in members dict, got keys: {members.keys()}"
        assert members[1] == [], f"Expected empty list for person, got {members[1]}"

    def test_empty_input_returns_empty_dict(self, populated_db):
        """Test that empty input returns empty dict."""
        repo = IdentityRepository(populated_db)
        members = repo.get_members_batch([])
        assert members == {}, f"Expected empty dict for empty input, got {members}"


class TestGetGroupsBatch:
    """IdentityRepository.get_groups_batch contracts."""

    def test_dave_groups(self, populated_db):
        """Dave (ID=1) belongs to Nirvana(2) and Foo Fighters(3)."""
        repo = IdentityRepository(populated_db)
        groups = repo.get_groups_batch([1])

        assert 1 in groups, f"Expected key 1 in groups dict, got keys: {groups.keys()}"
        group_names = {g.display_name for g in groups[1]}
        assert group_names == {
            "Nirvana",
            "Foo Fighters",
        }, f"Unexpected group names: {group_names}"

    def test_taylor_groups(self, populated_db):
        """Taylor (ID=4) belongs to Foo Fighters(3) only."""
        repo = IdentityRepository(populated_db)
        groups = repo.get_groups_batch([4])

        assert 4 in groups, f"Expected key 4 in groups dict, got keys: {groups.keys()}"
        assert len(groups[4]) == 1, f"Expected 1 group, got {len(groups[4])}"
        assert groups[4][0].id == 3, f"Expected 3, got {groups[4][0].id}"
        assert (
            groups[4][0].display_name == "Foo Fighters"
        ), f"Expected 'Foo Fighters', got '{groups[4][0].display_name}'"

    def test_group_has_no_groups(self, populated_db):
        """Nirvana (group ID=2) does not belong to any group."""
        repo = IdentityRepository(populated_db)
        groups = repo.get_groups_batch([2])

        assert 2 in groups, f"Expected key 2 in groups dict, got keys: {groups.keys()}"
        assert groups[2] == [], f"Expected empty list for group, got {groups[2]}"

    def test_empty_input_returns_empty_dict(self, populated_db):
        """Test that empty input returns empty dict."""
        repo = IdentityRepository(populated_db)
        groups = repo.get_groups_batch([])
        assert groups == {}, f"Expected empty dict for empty input, got {groups}"


class TestFallbackDisplayName:
    """Contract: COALESCE(an.DisplayName, i.LegalName, 'Unknown Artist #ID')."""

    def test_identity_with_no_artist_name(self, edge_case_db):
        """Identity 100 has no ArtistName at all -> should fallback to 'Unknown Artist #100'."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(100)

        assert identity is not None, f"Expected identity object, got {identity}"
        assert identity.id == 100, f"Expected 100, got {identity.id}"
        assert (
            identity.display_name == "Unknown Artist #100"
        ), f"Expected 'Unknown Artist #100', got '{identity.display_name}'"
        assert identity.type == "person", f"Expected 'person', got '{identity.type}'"


# ===================================================================
# Mapper Tests: _row_to_identity
# ===================================================================
class TestRowToIdentity:
    def test_all_fields_present(self, mock_db_path):
        mock_row = {
            "IdentityID": 1,
            "IdentityType": "person",
            "LegalName": "David Eric Grohl",
            "DisplayName": "Dave Grohl",
        }
        repo = IdentityRepository(mock_db_path)
        result = repo._row_to_identity(mock_row)
        assert result.id == 1
        assert result.type == "person"
        assert result.display_name == "Dave Grohl"
        assert result.legal_name == "David Eric Grohl"

    def test_null_fields(self, mock_db_path):
        mock_row = {
            "IdentityID": 1,
            "IdentityType": "person",
            "LegalName": None,
            "DisplayName": "Dave Grohl",
        }
        repo = IdentityRepository(mock_db_path)
        result = repo._row_to_identity(mock_row)
        assert result.id == 1
        assert result.type == "person"
        assert result.display_name == "Dave Grohl"
        assert result.legal_name is None

    def test_identity_with_legal_name_only(self, edge_case_db):
        """Identity 101 has LegalName='John Legal' but no ArtistName -> should fallback to LegalName."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(101)

        assert identity is not None, f"Expected identity object, got {identity}"
        assert identity.id == 101, f"Expected 101, got {identity.id}"
        assert (
            identity.display_name == "John Legal"
        ), f"Expected 'John Legal', got '{identity.display_name}'"
        assert identity.type == "person", f"Expected 'person', got '{identity.type}'"
