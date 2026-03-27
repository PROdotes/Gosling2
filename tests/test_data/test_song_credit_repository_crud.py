"""
Tests for SongCreditRepository CRUD methods
=============================================
add_credit, remove_credit, update_credit_name

populated_db credits:
  Song 1: Nirvana (NameID=20, RoleID=1 Performer)
  Song 2: Foo Fighters (NameID=30, RoleID=1 Performer)
  Song 3: Taylor Hawkins (NameID=40, RoleID=1 Performer)
  Song 6: Dave Grohl (NameID=10, RoleID=1 Performer) + Taylor Hawkins (NameID=40, RoleID=2 Composer)
  Song 7: no credits
"""

from src.data.song_credit_repository import SongCreditRepository


class TestAddCredit:
    def test_add_new_credit_with_existing_name_and_role(self, populated_db):
        """Add a credit using an existing ArtistName + Role — should create link, not duplicate records."""
        repo = SongCreditRepository(populated_db)

        with repo._get_connection() as conn:
            result = repo.add_credit(7, "Nirvana", "Performer", conn)
            conn.commit()

        assert result.source_id == 7, f"Expected source_id=7, got {result.source_id}"
        assert (
            result.name_id == 20
        ), f"Expected name_id=20 (existing Nirvana), got {result.name_id}"
        assert (
            result.role_id == 1
        ), f"Expected role_id=1 (Performer), got {result.role_id}"
        assert (
            result.role_name == "Performer"
        ), f"Expected role_name='Performer', got '{result.role_name}'"
        assert (
            result.display_name == "Nirvana"
        ), f"Expected display_name='Nirvana', got '{result.display_name}'"
        assert result.credit_id is not None, "Expected credit_id to be set, got None"

        # Verify no duplicate ArtistName row
        with repo._get_connection() as conn:
            rows = conn.execute(
                "SELECT NameID FROM ArtistNames WHERE DisplayName = 'Nirvana'"
            ).fetchall()
            assert (
                len(rows) == 1
            ), f"Expected 1 Nirvana row (no duplicate), got {len(rows)}"

    def test_add_new_credit_with_new_name_creates_artist(self, populated_db):
        """Add a credit with a brand-new name — should create ArtistName + Identity."""
        repo = SongCreditRepository(populated_db)

        with repo._get_connection() as conn:
            result = repo.add_credit(7, "Courtney Love", "Performer", conn)
            conn.commit()

        assert result.source_id == 7, f"Expected source_id=7, got {result.source_id}"
        assert (
            result.display_name == "Courtney Love"
        ), f"Expected display_name='Courtney Love', got '{result.display_name}'"
        assert (
            result.role_name == "Performer"
        ), f"Expected role_name='Performer', got '{result.role_name}'"
        assert result.name_id is not None, "Expected name_id to be set, got None"
        assert result.credit_id is not None, "Expected credit_id to be set, got None"

        # Verify ArtistName row created
        with repo._get_connection() as conn:
            row = conn.execute(
                "SELECT NameID FROM ArtistNames WHERE DisplayName = 'Courtney Love'"
            ).fetchone()
            assert (
                row is not None
            ), "Expected ArtistName row for 'Courtney Love' to exist"

    def test_add_new_credit_with_new_role(self, populated_db):
        """Add a credit with a brand-new role — should create Role row."""
        repo = SongCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_credit(7, "Nirvana", "Arranger", conn)
            conn.commit()

        with repo._get_connection() as conn:
            row = conn.execute(
                "SELECT RoleID FROM Roles WHERE RoleName = 'Arranger'"
            ).fetchone()
            assert row is not None, "Expected Role row for 'Arranger' to be created"

    def test_add_credit_idempotent_on_duplicate(self, populated_db):
        """Adding the same credit twice should not create duplicate SongCredits rows."""
        repo = SongCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_credit(7, "Nirvana", "Performer", conn)
            repo.add_credit(7, "Nirvana", "Performer", conn)
            conn.commit()

        credits = repo.get_credits_for_songs([7])
        nirvana_credits = [c for c in credits if c.display_name == "Nirvana"]
        assert (
            len(nirvana_credits) == 1
        ), f"Expected 1 Nirvana credit (idempotent), got {len(nirvana_credits)}"

    def test_add_credit_does_not_affect_other_songs(self, populated_db):
        """Adding a credit to Song 7 should not affect Song 1's credits."""
        repo = SongCreditRepository(populated_db)
        before = repo.get_credits_for_songs([1])

        with repo._get_connection() as conn:
            repo.add_credit(7, "Nirvana", "Performer", conn)
            conn.commit()

        after = repo.get_credits_for_songs([1])
        assert len(after) == len(
            before
        ), f"Song 1 credit count should not change: expected {len(before)}, got {len(after)}"


class TestRemoveCredit:
    def test_remove_credit_deletes_link(self, populated_db):
        """Remove a credit link — SongCredits row should be gone, ArtistName should remain."""
        repo = SongCreditRepository(populated_db)

        # Get the credit_id for Song 1 -> Nirvana
        credits_before = repo.get_credits_for_songs([1])
        nirvana_credit = next(c for c in credits_before if c.display_name == "Nirvana")
        credit_id = nirvana_credit.credit_id

        with repo._get_connection() as conn:
            repo.remove_credit(credit_id, conn)
            conn.commit()

        # Link is gone
        credits_after = repo.get_credits_for_songs([1])
        assert (
            len(credits_after) == 0
        ), f"Expected 0 credits on Song 1 after remove, got {len(credits_after)}"

        # ArtistName record persists
        with repo._get_connection() as conn:
            row = conn.execute(
                "SELECT NameID FROM ArtistNames WHERE NameID = 20"
            ).fetchone()
            assert (
                row is not None
            ), "Expected ArtistName (NameID=20) to persist after link removal"

    def test_remove_credit_does_not_affect_other_songs(self, populated_db):
        """Removing a credit from Song 1 should not affect Song 2's credits."""
        repo = SongCreditRepository(populated_db)

        credits_song1 = repo.get_credits_for_songs([1])
        credit_id = credits_song1[0].credit_id

        with repo._get_connection() as conn:
            repo.remove_credit(credit_id, conn)
            conn.commit()

        credits_song2 = repo.get_credits_for_songs([2])
        assert (
            len(credits_song2) == 1
        ), f"Expected Song 2 to still have 1 credit, got {len(credits_song2)}"
        assert (
            credits_song2[0].display_name == "Foo Fighters"
        ), f"Expected 'Foo Fighters', got '{credits_song2[0].display_name}'"


class TestUpdateCreditName:
    def test_update_credit_name_changes_display_name(self, populated_db):
        """Update a credit name globally — DisplayName should change."""
        repo = SongCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_credit_name(20, "Nirvana (Band)", conn)
            conn.commit()

        credits = repo.get_credits_for_songs([1])
        assert len(credits) == 1, f"Expected 1 credit on Song 1, got {len(credits)}"
        assert (
            credits[0].display_name == "Nirvana (Band)"
        ), f"Expected 'Nirvana (Band)', got '{credits[0].display_name}'"

    def test_update_credit_name_is_global(self, populated_db):
        """Updating NameID=40 (Taylor Hawkins) affects all songs that credit him."""
        repo = SongCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_credit_name(40, "Taylor Hawkins (Updated)", conn)
            conn.commit()

        # Song 3 credits Taylor
        credits_song3 = repo.get_credits_for_songs([3])
        assert (
            credits_song3[0].display_name == "Taylor Hawkins (Updated)"
        ), f"Expected updated name on Song 3, got '{credits_song3[0].display_name}'"

        # Song 6 also credits Taylor
        credits_song6 = repo.get_credits_for_songs([6])
        taylor = next(c for c in credits_song6 if c.name_id == 40)
        assert (
            taylor.display_name == "Taylor Hawkins (Updated)"
        ), f"Expected updated name on Song 6, got '{taylor.display_name}'"

    def test_update_credit_name_does_not_affect_other_names(self, populated_db):
        """Updating Nirvana's name should not affect Foo Fighters."""
        repo = SongCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_credit_name(20, "Nirvana Renamed", conn)
            conn.commit()

        credits_song2 = repo.get_credits_for_songs([2])
        assert (
            credits_song2[0].display_name == "Foo Fighters"
        ), f"Expected 'Foo Fighters' unchanged, got '{credits_song2[0].display_name}'"
