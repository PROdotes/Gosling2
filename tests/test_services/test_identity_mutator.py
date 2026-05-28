"""
Tests for IdentityMutator — alias/member/type/merge operations on identities.

Uses populated_db. Reference data:
  Identities: 1=Dave Grohl (person), 2=Nirvana (group), 3=Foo Fighters (group), 4=Taylor Hawkins (person)
  ArtistNames: 10=Dave Grohl (primary, owner=1), 11=Grohlton (alias, owner=1), 12=Late! (alias, owner=1),
               20=Nirvana (primary, owner=2), 30=Foo Fighters (primary, owner=3),
               40=Taylor Hawkins (primary, owner=4), 33=Ines Prajo (alias, owner=1)
  GroupMemberships: (2,1) Dave in Nirvana, (3,1) Dave in Foo Fighters, (3,4) Taylor in Foo Fighters
"""

import sqlite3

import pytest

from src.engine.routers.mutation_models import (
    AddIdentityAliasItem,
    AddIdentityMemberItem,
    MergeIdentityItem,
    RemoveIdentityAliasItem,
    RemoveIdentityMemberItem,
    UpdateIdentityItem,
)
from src.services.mutators.identity_mutator import IdentityMutator


def _make_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    return conn


def _get_name_row(conn: sqlite3.Connection, name_id: int):
    return conn.execute(
        "SELECT NameID, DisplayName, OwnerIdentityID, IsPrimaryName, IsDeleted FROM ArtistNames WHERE NameID = ?",
        (name_id,),
    ).fetchone()


def _get_identity_row(conn: sqlite3.Connection, identity_id: int):
    return conn.execute(
        "SELECT IdentityID, IdentityType, IsDeleted FROM Identities WHERE IdentityID = ?",
        (identity_id,),
    ).fetchone()


def _get_aliases_for(conn: sqlite3.Connection, identity_id: int):
    return conn.execute(
        "SELECT NameID, DisplayName, IsPrimaryName FROM ArtistNames WHERE OwnerIdentityID = ? AND IsDeleted = 0",
        (identity_id,),
    ).fetchall()


def _get_members(conn: sqlite3.Connection, group_id: int):
    return conn.execute(
        "SELECT MemberIdentityID FROM GroupMemberships WHERE GroupIdentityID = ?",
        (group_id,),
    ).fetchall()


@pytest.fixture
def mutator(populated_db):
    return IdentityMutator(populated_db)


@pytest.fixture
def conn(populated_db):
    c = _make_conn(populated_db)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# add alias
# ---------------------------------------------------------------------------


class TestIdentityMutatorAddAlias:
    def test_add_new_alias_by_name(self, mutator, conn):
        item = AddIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 1, "display_name": "Davey G"}
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        aliases = _get_aliases_for(conn, 1)
        assert any(
            a["DisplayName"] == "Davey G" and not a["IsPrimaryName"] for a in aliases
        )

    def test_add_alias_by_existing_name_id_relinks(self, mutator, conn):
        # NameID=40 (Taylor Hawkins) currently owned by identity 4 as primary.
        # Re-link it as an alias under identity 1 (Dave).
        item = AddIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 1, "name_id": 40}
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        row = _get_name_row(conn, 40)
        assert row["OwnerIdentityID"] == 1

    def test_add_duplicate_alias_is_idempotent(self, mutator, conn):
        # 'Grohlton' (NameID=11) already belongs to identity 1. Adding it by name
        # again should not produce a second row.
        before = len(_get_aliases_for(conn, 1))
        item = AddIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 1, "display_name": "Grohlton"}
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        after = len(_get_aliases_for(conn, 1))
        assert after == before

    def test_add_alias_reclaims_soft_deleted_name_from_another_identity(
        self, mutator, conn
    ):
        # Pre-existing soft-deleted name 'Ghost' under identity 4.
        # Adding the same display_name under identity 1 should reclaim the row,
        # not raise a collision error.
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ArtistNames (OwnerIdentityID, DisplayName, IsPrimaryName, IsDeleted) VALUES (4, 'Ghost', 0, 1)"
        )
        reclaimed_name_id = cur.lastrowid
        conn.commit()

        item = AddIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 1, "display_name": "Ghost"}
        )
        mutator.apply_within("add", item, conn)
        conn.commit()

        # Same NameID, re-parented to identity 1, no longer soft-deleted, not primary.
        row = _get_name_row(conn, reclaimed_name_id)
        assert row["OwnerIdentityID"] == 1
        assert row["IsDeleted"] == 0
        assert row["IsPrimaryName"] == 0

    def test_add_alias_invalid_identity_raises(self, mutator, conn):
        item = AddIdentityAliasItem.model_validate(
            {
                "type": "identity_alias",
                "identity_id": 9999,
                "display_name": "Ghost Alias",
            }
        )
        with pytest.raises((LookupError, sqlite3.IntegrityError, ValueError)):
            mutator.apply_within("add", item, conn)

    def test_relink_primary_name_of_multi_alias_identity_raises(self, mutator, conn):
        # NameID=10 is Dave's primary, and identity 1 has other aliases.
        # Stealing the primary would orphan the parent. Should raise.
        item = AddIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 4, "name_id": 10}
        )
        with pytest.raises(ValueError):
            mutator.apply_within("add", item, conn)

    def test_relink_primary_of_solo_identity_succeeds(self, mutator, conn):
        # Build a solo identity (one primary name, no other aliases) and re-link
        # its primary onto identity 1. Allowed because the source has no orphans.
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Identities (IdentityType, IsDeleted) VALUES ('person', 0)"
        )
        solo_identity_id = cur.lastrowid
        cur.execute(
            "INSERT INTO ArtistNames (OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (?, 'Solo Artist', 1)",
            (solo_identity_id,),
        )
        solo_name_id = cur.lastrowid
        conn.commit()

        item = AddIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 1, "name_id": solo_name_id}
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        row = _get_name_row(conn, solo_name_id)
        assert row["OwnerIdentityID"] == 1

    def test_add_requires_name_or_id(self):
        with pytest.raises(ValueError):
            AddIdentityAliasItem.model_validate(
                {"type": "identity_alias", "identity_id": 1}
            )

    def test_add_new_alias_populates_search_shadow(self, mutator, conn):
        # Diacritics in the display name must produce a lowercase ASCII shadow.
        item = AddIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 1, "display_name": "Noëp"}
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        row = conn.execute(
            "SELECT DisplayName, DisplayName_Search FROM ArtistNames "
            "WHERE OwnerIdentityID = 1 AND DisplayName = 'Noëp'"
        ).fetchone()
        assert row is not None
        assert row["DisplayName"] == "Noëp"
        assert row["DisplayName_Search"] == "noep"


# ---------------------------------------------------------------------------
# remove alias
# ---------------------------------------------------------------------------


class TestIdentityMutatorRemoveAlias:
    def test_remove_alias_detaches_to_new_identity(self, mutator, conn):
        # NameID=11 (Grohlton) is an alias of identity 1; detach it.
        item = RemoveIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 1, "name_id": 11}
        )
        mutator.apply_within("remove", item, conn)
        conn.commit()
        row = _get_name_row(conn, 11)
        assert row["OwnerIdentityID"] != 1
        assert row["IsPrimaryName"] == 1  # now primary on its new identity
        # And a fresh identity was created
        new_identity = _get_identity_row(conn, row["OwnerIdentityID"])
        assert new_identity is not None
        assert new_identity["IsDeleted"] == 0

    def test_remove_alias_mismatched_identity_raises(self, mutator, conn):
        # NameID=11 belongs to identity 1, not 4.
        item = RemoveIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 4, "name_id": 11}
        )
        with pytest.raises(ValueError, match="belongs to identity 1"):
            mutator.apply_within("remove", item, conn)
        # State unchanged
        row = _get_name_row(conn, 11)
        assert row["OwnerIdentityID"] == 1

    def test_remove_primary_alias_raises(self, mutator, conn):
        # NameID=10 is Dave's primary name.
        item = RemoveIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 1, "name_id": 10}
        )
        with pytest.raises(ValueError, match="primary name"):
            mutator.apply_within("remove", item, conn)

    def test_remove_nonexistent_alias_is_noop(self, mutator, conn):
        item = RemoveIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 1, "name_id": 9999}
        )
        # Should not raise — repo's delete_alias returns silently when the row is missing.
        mutator.apply_within("remove", item, conn)
        conn.commit()

    def test_remove_alias_leaves_other_aliases_intact(self, mutator, conn):
        # Identity 1 has aliases at NameIDs 10 (primary), 11, 12, 33.
        # Removing 11 should leave 12 and 33 still attached.
        item = RemoveIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 1, "name_id": 11}
        )
        mutator.apply_within("remove", item, conn)
        conn.commit()
        remaining = {r["NameID"] for r in _get_aliases_for(conn, 1)}
        assert 12 in remaining
        assert 33 in remaining


# ---------------------------------------------------------------------------
# add / remove member
# ---------------------------------------------------------------------------


class TestIdentityMutatorMembers:
    def test_add_member(self, mutator, conn):
        # Add Taylor (id=4) to Nirvana (id=2). Currently only Dave is in Nirvana.
        item = AddIdentityMemberItem.model_validate(
            {"type": "identity_member", "group_id": 2, "member_id": 4}
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        members = _get_members(conn, 2)
        ids = {m["MemberIdentityID"] for m in members}
        assert 4 in ids

    def test_add_member_invalid_group_raises(self, mutator, conn):
        item = AddIdentityMemberItem.model_validate(
            {"type": "identity_member", "group_id": 9999, "member_id": 1}
        )
        with pytest.raises((LookupError, sqlite3.IntegrityError, ValueError)):
            mutator.apply_within("add", item, conn)

    def test_add_member_self_membership_raises(self, mutator, conn):
        # A group cannot be a member of itself.
        item = AddIdentityMemberItem.model_validate(
            {"type": "identity_member", "group_id": 2, "member_id": 2}
        )
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            mutator.apply_within("add", item, conn)

    def test_remove_member(self, mutator, conn):
        # Remove Taylor (id=4) from Foo Fighters (id=3).
        item = RemoveIdentityMemberItem.model_validate(
            {"type": "identity_member", "group_id": 3, "member_id": 4}
        )
        mutator.apply_within("remove", item, conn)
        conn.commit()
        members = _get_members(conn, 3)
        ids = {m["MemberIdentityID"] for m in members}
        assert 4 not in ids

    def test_remove_member_not_linked_is_noop(self, mutator, conn):
        # Taylor (id=4) is not in Nirvana (id=2). Removing should not raise.
        item = RemoveIdentityMemberItem.model_validate(
            {"type": "identity_member", "group_id": 2, "member_id": 4}
        )
        mutator.apply_within("remove", item, conn)
        conn.commit()


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestIdentityMutatorUpdate:
    def test_update_identity_type(self, mutator, conn):
        # Flip identity 4 (Taylor) from person to group.
        item = UpdateIdentityItem.model_validate(
            {"type": "identity", "id": 4, "identity_type": "group"}
        )
        mutator.apply_within("update", item, conn)
        conn.commit()
        row = _get_identity_row(conn, 4)
        assert row["IdentityType"] == "group"

    def test_update_invalid_type_rejected_by_model(self):
        with pytest.raises(ValueError):
            UpdateIdentityItem.model_validate(
                {"type": "identity", "id": 4, "identity_type": "robot"}
            )

    def test_update_type_nonexistent_identity_raises(self, mutator, conn):
        item = UpdateIdentityItem.model_validate(
            {"type": "identity", "id": 9999, "identity_type": "group"}
        )
        with pytest.raises((LookupError, ValueError)):
            mutator.apply_within("update", item, conn)

    def test_update_group_to_person_with_members_raises(self, mutator, conn):
        # Identity 2 (Nirvana) is a group with at least one member (Dave).
        # Flipping it to 'person' should fail.
        item = UpdateIdentityItem.model_validate(
            {"type": "identity", "id": 2, "identity_type": "person"}
        )
        with pytest.raises((LookupError, ValueError)):
            mutator.apply_within("update", item, conn)


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------


class TestIdentityMutatorMerge:
    def test_merge_orphan_into_existing_repoints_credits(self, mutator, conn):
        # Build an orphan identity with a single name, give it a credit on song 7,
        # then merge into Dave's primary (NameID=10).
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Identities (IdentityType, IsDeleted) VALUES ('person', 0)"
        )
        orphan_id = cur.lastrowid
        cur.execute(
            "INSERT INTO ArtistNames (OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (?, 'Orphan Name', 1)",
            (orphan_id,),
        )
        orphan_name_id = cur.lastrowid
        cur.execute(
            "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (7, ?, 1)",
            (orphan_name_id,),
        )
        conn.commit()

        item = MergeIdentityItem.model_validate(
            {
                "type": "identity_merge",
                "source_name_id": orphan_name_id,
                "target_name_id": 10,
            }
        )
        mutator.apply_within("merge", item, conn)
        conn.commit()

        # Source name + identity soft-deleted
        assert _get_name_row(conn, orphan_name_id)["IsDeleted"] == 1
        assert _get_identity_row(conn, orphan_id)["IsDeleted"] == 1
        # Credit on song 7 now points at target (NameID 10)
        credit = conn.execute(
            "SELECT CreditedNameID FROM SongCredits WHERE SourceID = 7"
        ).fetchone()
        assert credit["CreditedNameID"] == 10

    def test_merge_non_orphan_source_raises(self, mutator, conn):
        # Identity 1 (Dave) has multiple aliases — not an orphan; merging it should fail.
        item = MergeIdentityItem.model_validate(
            {"type": "identity_merge", "source_name_id": 10, "target_name_id": 40}
        )
        with pytest.raises(ValueError, match="not an orphan"):
            mutator.apply_within("merge", item, conn)

    def test_merge_source_not_found_raises(self, mutator, conn):
        item = MergeIdentityItem.model_validate(
            {"type": "identity_merge", "source_name_id": 9999, "target_name_id": 10}
        )
        with pytest.raises(LookupError):
            mutator.apply_within("merge", item, conn)


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------


class TestIdentityMutatorRouting:
    def test_unsupported_action_raises(self, mutator, conn):
        item = AddIdentityAliasItem.model_validate(
            {"type": "identity_alias", "identity_id": 1, "display_name": "X"}
        )
        with pytest.raises(ValueError):
            mutator.apply_within("bad_action", item, conn)
