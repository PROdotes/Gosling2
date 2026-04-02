"""
Write tests for IdentityRepository (Aliases and Hierarchy).
Verifies that mutations follow the 'Truth-First' integrity rules.
"""

import sqlite3
import pytest
from src.data.identity_repository import IdentityRepository


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


def test_soft_delete_newly_added_alias(populated_db):
    """Repo should successfully remove an alias that is not in use."""
    repo = IdentityRepository(populated_db)
    identity_id = 1
    new_alias = "Unused Alias"

    with repo._get_connection() as conn:
        cursor = conn.cursor()
        alias_id = repo.add_alias(identity_id, new_alias, cursor)
        conn.commit()

        # Verify it exists
        row = cursor.execute(
            "SELECT NameID FROM ArtistNames WHERE NameID = ?", (alias_id,)
        ).fetchone()
        assert row is not None

        # Delete it
        repo.delete_alias(alias_id, cursor)
        conn.commit()

        # Verify gone
        row = cursor.execute(
            "SELECT IsDeleted FROM ArtistNames WHERE NameID = ?", (alias_id,)
        ).fetchone()
        assert row[0] == 1, f"Expected IsDeleted=1, got {row[0]}"


def test_soft_delete_alias_in_use(populated_db):
    """Repo mutations MUST NOT orphan credits; they use soft-deletion."""
    repo = IdentityRepository(populated_db)
    alias_id = 11  # 'Grohlton' (used in populated_db)

    with repo._get_connection() as conn:
        cursor = conn.cursor()
        # Delete it (Soft-delete)
        repo.delete_alias(alias_id, cursor)
        conn.commit()

        # Verify it still exists in DB but is marked deleted
        row = cursor.execute(
            "SELECT IsDeleted FROM ArtistNames WHERE NameID = ?", (alias_id,)
        ).fetchone()
        assert row is not None
        assert row[0] == 1, f"Expected IsDeleted=1, got {row[0]}"


def test_delete_alias_primary_forbidden(populated_db):
    """Repo MUST NOT allow deletion of the primary name for an identity (Logical check)."""
    repo = IdentityRepository(populated_db)
    primary_alias = 10  # 'Dave Grohl' (primary)

    with repo._get_connection() as conn:
        cursor = conn.cursor()
        with pytest.raises(ValueError, match="Cannot delete the primary name"):
            repo.delete_alias(primary_alias, cursor)


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
