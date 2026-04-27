"""
Write tests for IdentityRepository (Aliases and Hierarchy).
Verifies that mutations follow the 'Truth-First' integrity rules.
"""

import pytest
from src.data.identity_repository import IdentityRepository

# ---------------------------------------------------------------------------
# update_legal_name
# ---------------------------------------------------------------------------


class TestUpdateLegalName:
    def test_update_legal_name_success(self, populated_db):
        """Update LegalName on an existing identity."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            repo.update_legal_name(1, "David Eric Grohl Jr.", conn)
            conn.commit()
        result = repo.get_by_id(1)
        assert (
            result.legal_name == "David Eric Grohl Jr."
        ), f"Expected updated name, got {result.legal_name}"

    def test_update_legal_name_clears_to_none(self, populated_db):
        """Setting legal_name to None clears the field."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            repo.update_legal_name(1, None, conn)
            conn.commit()
        result = repo.get_by_id(1)
        assert result.legal_name is None, f"Expected None, got {result.legal_name}"

    def test_update_legal_name_invalid_id_raises(self, populated_db):
        """Updating a non-existent identity should raise LookupError."""
        repo = IdentityRepository(populated_db)
        with repo.get_connection() as conn:
            with pytest.raises(LookupError):
                repo.update_legal_name(9999, "Ghost", conn)


def test_add_alias_basic(populated_db):
    """Repo should successfully add a new alias to an existing identity."""
    repo = IdentityRepository(populated_db)
    identity_id = 1  # Dave Grohl
    new_alias = "The Drummer From Nirvana"

    with repo._get_connection() as conn:
        cursor = conn.cursor()
        repo.add_alias(identity_id, new_alias, cursor)
        conn.commit()

    # Verify via read
    aliases = repo.get_aliases_batch([identity_id])
    names = {a.display_name for a in aliases[identity_id]}
    assert new_alias in names


def test_add_alias_duplicate_ignore(populated_db):
    """Repo should not create duplicate name records for the same identity (idempotent)."""
    repo = IdentityRepository(populated_db)
    identity_id = 1
    existing_alias = "Grohlton"

    with repo._get_connection() as conn:
        cursor = conn.cursor()
        # Get count before
        before = cursor.execute(
            "SELECT COUNT(*) FROM ArtistNames WHERE OwnerIdentityID = ?", (identity_id,)
        ).fetchone()[0]

        # Try to add existing
        repo.add_alias(identity_id, existing_alias, cursor)
        conn.commit()

        after = cursor.execute(
            "SELECT COUNT(*) FROM ArtistNames WHERE OwnerIdentityID = ?", (identity_id,)
        ).fetchone()[0]
        assert before == after, "Duplicate alias should not have been added"


def test_detach_newly_added_alias(populated_db):
    """Repo should successfully detach an alias by re-homing it to a new identity."""
    repo = IdentityRepository(populated_db)
    identity_id = 1
    new_alias = "Unused Alias"

    with repo._get_connection() as conn:
        cursor = conn.cursor()
        alias_id = repo.add_alias(identity_id, new_alias, cursor)
        conn.commit()

        # Verify it belongs to identity 1
        row = cursor.execute(
            "SELECT OwnerIdentityID FROM ArtistNames WHERE NameID = ?", (alias_id,)
        ).fetchone()
        assert row[0] == identity_id

        # Delete (Detach) it
        repo.delete_alias(alias_id, cursor)
        conn.commit()

        # Verify it now belongs to a NEW identity and is primary/active
        row = cursor.execute(
            "SELECT OwnerIdentityID, IsPrimaryName, IsDeleted FROM ArtistNames WHERE NameID = ?", (alias_id,)
        ).fetchone()
        assert row[0] != identity_id, "Alias was not re-homed to a new identity"
        assert row[1] == 1, f"Expected IsPrimaryName=1, got {row[1]}"
        assert row[2] == 0, f"Expected IsDeleted=0, got {row[2]}"


def test_detach_alias_in_use(populated_db):
    """Repo detachment MUST NOT delete names; they are re-homed to protect historical credits."""
    repo = IdentityRepository(populated_db)
    alias_id = 11  # 'Grohlton' (used in populated_db)

    with repo._get_connection() as conn:
        cursor = conn.cursor()
        # Delete (Detach) it
        repo.delete_alias(alias_id, cursor)
        conn.commit()

        # Verify it was re-homed, NOT soft-deleted
        row = cursor.execute(
            "SELECT OwnerIdentityID, IsDeleted FROM ArtistNames WHERE NameID = ?", (alias_id,)
        ).fetchone()
        assert row[0] != 1, "Alias should have been moved from identity 1"
        assert row[1] == 0, f"Expected IsDeleted=0 (reactivated/active), got {row[1]}"


def test_delete_alias_primary_forbidden(populated_db):
    """Repo MUST NOT allow deletion of the primary name for an identity (Logical check)."""
    repo = IdentityRepository(populated_db)
    primary_alias = 10  # 'Dave Grohl' (primary)

    with repo._get_connection() as conn:
        cursor = conn.cursor()
        with pytest.raises(ValueError, match="Cannot detach the primary name of an identity"):
            repo.delete_alias(primary_alias, cursor)


def test_detach_alias_preserves_credits(populated_db):
    """
    Contract: Detaching an alias must preserve song credits linked to that name.
    Scenario: 'Grohlton' (11) is alias of 'Dave Grohl' (1) and credited on 'Song A' (1).
    After detaching 'Grohlton', the credit must still point to 'Grohlton' (11).
    """
    repo = IdentityRepository(populated_db)
    alias_id = 11  # 'Grohlton'
    original_owner_id = 1
    song_id = 4

    with repo._get_connection() as conn:
        cursor = conn.cursor()

        # 1. Verify initial state: Grohlton belongs to identity 1 and is credited on song 1
        row = cursor.execute("SELECT OwnerIdentityID FROM ArtistNames WHERE NameID = ?", (alias_id,)).fetchone()
        assert row[0] == original_owner_id

        row = cursor.execute("SELECT CreditedNameID FROM SongCredits WHERE SourceID = ? AND CreditedNameID = ?", (song_id, alias_id)).fetchone()
        assert row is not None, "Initial credit not found"

        # 2. Detach 'Grohlton'
        repo.delete_alias(alias_id, cursor)
        conn.commit()

        # 3. Verify: Grohlton has a NEW owner
        row = cursor.execute("SELECT OwnerIdentityID FROM ArtistNames WHERE NameID = ?", (alias_id,)).fetchone()
        new_owner_id = row[0]
        assert new_owner_id != original_owner_id

        # 4. Verify: Song 1 STILL credits 'Grohlton' (NameID 11)
        row = cursor.execute("SELECT CreditedNameID FROM SongCredits WHERE SourceID = ? AND CreditedNameID = ?", (song_id, alias_id)).fetchone()
        assert row is not None, "Credit was lost during detachment"
        assert row[0] == alias_id, f"Expected credit to still point to NameID {alias_id}, got {row[0]}"


def test_add_alias_rollback(populated_db):
    """Repo mutations should respect transaction boundaries."""
    repo = IdentityRepository(populated_db)
    identity_id = 1

    conn = repo.get_connection()
    try:
        cursor = conn.cursor()
        repo.add_alias(identity_id, "Temp Alias", cursor)
        # Force an error before commit
        conn.rollback()
    finally:
        conn.close()

    # Verify not in DB
    aliases = repo.get_aliases_batch([identity_id])
    names = {a.display_name for a in aliases[identity_id]}
    assert "Temp Alias" not in names


# ---------------------------------------------------------------------------
# merge_orphan_into
# ---------------------------------------------------------------------------


class TestMergeOrphanInto:
    def test_song_credits_repointed(self, populated_db):
        """SongCredits for the source name should point to the target name after merge."""
        repo = IdentityRepository(populated_db)
        # Taylor Hawkins (NameID=40, IdentityID=4) is a solo identity — one alias only.
        # Merge him as an alias under Dave Grohl (NameID=10).
        source_name_id = 40  # Taylor Hawkins
        target_name_id = 10  # Dave Grohl

        with repo._get_connection() as conn:
            cursor = conn.cursor()
            repo.merge_orphan_into(source_name_id, target_name_id, cursor)
            conn.commit()

            # Song 3 credited Taylor (40) — should now credit Dave (10)
            row = cursor.execute(
                "SELECT CreditedNameID FROM SongCredits WHERE SourceID = 3"
            ).fetchone()
            assert row[0] == target_name_id

    def test_album_credits_repointed(self, populated_db):
        """AlbumCredits for the source name should point to the target name after merge."""
        repo = IdentityRepository(populated_db)
        # Nirvana (NameID=20, IdentityID=2) — sole alias, so it's a valid orphan.
        # Merge Nirvana into Foo Fighters (NameID=30).
        source_name_id = 20  # Nirvana
        target_name_id = 30  # Foo Fighters

        with repo._get_connection() as conn:
            cursor = conn.cursor()
            repo.merge_orphan_into(source_name_id, target_name_id, cursor)
            conn.commit()

            # Album 100 credited Nirvana (20) — should now credit Foo Fighters (30)
            row = cursor.execute(
                "SELECT CreditedNameID FROM AlbumCredits WHERE AlbumID = 100"
            ).fetchone()
            assert row[0] == target_name_id

    def test_source_name_soft_deleted(self, populated_db):
        """The source ArtistName should be soft-deleted after the merge."""
        repo = IdentityRepository(populated_db)
        source_name_id = 40  # Taylor Hawkins

        with repo._get_connection() as conn:
            cursor = conn.cursor()
            repo.merge_orphan_into(source_name_id, 10, cursor)
            conn.commit()

            row = cursor.execute(
                "SELECT IsDeleted FROM ArtistNames WHERE NameID = ?", (source_name_id,)
            ).fetchone()
            assert row[0] == 1

    def test_source_identity_soft_deleted(self, populated_db):
        """The source Identity should be soft-deleted after the merge."""
        repo = IdentityRepository(populated_db)
        source_identity_id = 4  # Taylor Hawkins

        with repo._get_connection() as conn:
            cursor = conn.cursor()
            repo.merge_orphan_into(40, 10, cursor)
            conn.commit()

            row = cursor.execute(
                "SELECT IsDeleted FROM Identities WHERE IdentityID = ?",
                (source_identity_id,),
            ).fetchone()
            assert row[0] == 1

    def test_raises_if_source_not_found(self, populated_db):
        """Should raise LookupError if the source NameID does not exist."""
        repo = IdentityRepository(populated_db)
        with repo._get_connection() as conn:
            cursor = conn.cursor()
            with pytest.raises(LookupError):
                repo.merge_orphan_into(9999, 10, cursor)

    def test_raises_if_source_identity_has_multiple_aliases(self, populated_db):
        """Should raise ValueError if the source identity owns more than one alias."""
        repo = IdentityRepository(populated_db)
        # Dave Grohl (IdentityID=1) has multiple aliases — not an orphan.
        # Try to merge his primary name (NameID=10) into Taylor (40).
        with repo._get_connection() as conn:
            cursor = conn.cursor()
            with pytest.raises(ValueError, match="not an orphan"):
                repo.merge_orphan_into(10, 40, cursor)
