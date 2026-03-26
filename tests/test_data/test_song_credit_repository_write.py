"""
Tests for SongCreditRepository.insert_credits
===============================================
Verifies get-or-create logic for Roles + ArtistNames, and link insertion into SongCredits.
Uses populated_db which already has:
    Roles: 1=Performer, 2=Composer, 3=Lyricist, 4=Producer
    ArtistNames: 10=Dave Grohl(ID1), 11=Grohlton(ID1), 12=Late!(ID1),
                 20=Nirvana(ID2), 30=Foo Fighters(ID3), 40=Taylor Hawkins(ID4), 33=Ines Prajo(ID1)
    Songs 7 and 9 have ZERO credits.
"""

import sqlite3
from src.data.song_credit_repository import SongCreditRepository
from src.models.domain import SongCredit


class TestInsertCredits:
    def test_insert_new_artist_creates_identity_and_links(self, populated_db):
        """A brand-new artist name should create an Identity, an ArtistNames row
        linked to it, and a SongCredits link."""
        repo = SongCreditRepository(populated_db)

        credits = [
            SongCredit(role_name="Performer", display_name="Ella Maren"),
        ]

        with repo._get_connection() as conn:
            repo.insert_credits(7, credits, conn)
            conn.commit()

        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row

            # Verify Identity was created
            identity = conn.execute(
                "SELECT IdentityID, LegalName FROM Identities WHERE LegalName = 'Ella Maren'"
            ).fetchone()
            assert identity is not None, "Expected Identity for 'Ella Maren' to be created"

            # Verify ArtistNames row is linked to that Identity
            row = conn.execute(
                "SELECT NameID, OwnerIdentityID, IsPrimaryName FROM ArtistNames WHERE DisplayName = 'Ella Maren'"
            ).fetchone()
            assert row is not None, "Expected 'Ella Maren' ArtistNames row to exist"
            assert (
                row["OwnerIdentityID"] == identity["IdentityID"]
            ), f"Expected OwnerIdentityID={identity['IdentityID']}, got {row['OwnerIdentityID']}"
            assert (
                row["IsPrimaryName"] == 1
            ), f"Expected IsPrimaryName=1, got {row['IsPrimaryName']}"

        # Verify credit is readable
        result = repo.get_credits_for_songs([7])
        assert len(result) == 1, f"Expected 1 credit on Song 7, got {len(result)}"
        assert result[0].display_name == "Ella Maren"
        assert result[0].role_name == "Performer"

    def test_insert_existing_artist_reuses_name_id(self, populated_db):
        """'Dave Grohl' already exists (NameID=10). Should reuse, not duplicate."""
        repo = SongCreditRepository(populated_db)

        credits = [
            SongCredit(role_name="Performer", display_name="Dave Grohl"),
        ]

        with repo._get_connection() as conn:
            repo.insert_credits(7, credits, conn)
            conn.commit()

        # Verify no duplicate ArtistNames row
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT NameID FROM ArtistNames WHERE DisplayName = 'Dave Grohl'"
            ).fetchall()
            assert (
                len(rows) == 1
            ), f"Expected 1 'Dave Grohl' row (reused), got {len(rows)}"
            assert (
                rows[0]["NameID"] == 10
            ), f"Expected NameID=10 (original), got {rows[0]['NameID']}"

        # Verify credit link
        result = repo.get_credits_for_songs([7])
        assert len(result) == 1, f"Expected 1 credit on Song 7, got {len(result)}"
        assert result[0].display_name == "Dave Grohl"
        assert result[0].name_id == 10

    def test_insert_existing_role_reuses_role_id(self, populated_db):
        """'Performer' already exists (RoleID=1). Should reuse, not duplicate."""
        repo = SongCreditRepository(populated_db)

        credits = [
            SongCredit(role_name="Performer", display_name="New Artist"),
        ]

        with repo._get_connection() as conn:
            repo.insert_credits(7, credits, conn)
            conn.commit()

        # Verify only 1 Performer role row
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT RoleID FROM Roles WHERE RoleName = 'Performer'"
            ).fetchall()
            assert len(rows) == 1, f"Expected 1 'Performer' role row, got {len(rows)}"
            assert rows[0]["RoleID"] == 1, f"Expected RoleID=1, got {rows[0]['RoleID']}"

    def test_insert_new_role_creates_role_row(self, populated_db):
        """A role that doesn't exist yet (e.g. 'Mixer') should be created."""
        repo = SongCreditRepository(populated_db)

        credits = [
            SongCredit(role_name="Mixer", display_name="Some Engineer"),
        ]

        with repo._get_connection() as conn:
            repo.insert_credits(7, credits, conn)
            conn.commit()

        # Verify Roles table has the new entry
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT RoleID, RoleName FROM Roles WHERE RoleName = 'Mixer'"
            ).fetchone()
            assert row is not None, "Expected 'Mixer' role row to exist"
            assert row["RoleName"] == "Mixer"

        # Verify credit uses the new role
        result = repo.get_credits_for_songs([7])
        assert len(result) == 1
        assert result[0].role_name == "Mixer"

    def test_insert_multiple_credits_different_roles(self, populated_db):
        """Insert a Performer + Composer credit on Song 7."""
        repo = SongCreditRepository(populated_db)

        credits = [
            SongCredit(role_name="Performer", display_name="Test Artist"),
            SongCredit(role_name="Composer", display_name="Test Writer"),
        ]

        with repo._get_connection() as conn:
            repo.insert_credits(7, credits, conn)
            conn.commit()

        result = repo.get_credits_for_songs([7])
        assert len(result) == 2, f"Expected 2 credits on Song 7, got {len(result)}"

        names = sorted([c.display_name for c in result])
        roles = sorted([c.role_name for c in result])
        assert names == ["Test Artist", "Test Writer"]
        assert roles == ["Composer", "Performer"]

    def test_insert_empty_list_is_noop(self, populated_db):
        """Passing empty list should not crash or create any rows."""
        repo = SongCreditRepository(populated_db)

        before = repo.get_credits_for_songs([7])
        assert len(before) == 0

        with repo._get_connection() as conn:
            repo.insert_credits(7, [], conn)
            conn.commit()

        after = repo.get_credits_for_songs([7])
        assert len(after) == 0

    def test_insert_same_artist_same_role_twice_no_duplicate(self, populated_db):
        """The UNIQUE(SourceID, CreditedNameID, RoleID) constraint should prevent dupes.
        insert_credits should handle this gracefully (INSERT OR IGNORE or similar)."""
        repo = SongCreditRepository(populated_db)

        credits = [
            SongCredit(role_name="Performer", display_name="Dupe Artist"),
        ]

        with repo._get_connection() as conn:
            repo.insert_credits(7, credits, conn)
            conn.commit()

        # Insert the same credit again
        with repo._get_connection() as conn:
            repo.insert_credits(7, credits, conn)
            conn.commit()

        result = repo.get_credits_for_songs([7])
        assert len(result) == 1, f"Expected 1 credit (no dupe), got {len(result)}"

    def test_same_artist_different_roles_both_persist(self, populated_db):
        """Same artist as both Performer and Composer should create 2 SongCredits rows."""
        repo = SongCreditRepository(populated_db)

        credits = [
            SongCredit(role_name="Performer", display_name="Multi-Role Artist"),
            SongCredit(role_name="Composer", display_name="Multi-Role Artist"),
        ]

        with repo._get_connection() as conn:
            repo.insert_credits(7, credits, conn)
            conn.commit()

        result = repo.get_credits_for_songs([7])
        assert len(result) == 2, f"Expected 2 credits on Song 7, got {len(result)}"

        roles = sorted([c.role_name for c in result])
        assert roles == ["Composer", "Performer"]
        # But only 1 ArtistNames row
        assert (
            result[0].name_id == result[1].name_id
        ), "Expected same NameID for both credits"
