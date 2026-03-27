import pytest
import sqlite3
from src.data.album_credit_repository import AlbumCreditRepository

class TestAlbumCreditRepository:
    def test_add_credit_with_existing_name(self, populated_db):
        """Add an existing artist to Album 200 — should create AlbumCredits link, not duplicate ArtistName."""
        repo = AlbumCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_credit(200, "Nirvana", "Performer", conn)
            conn.commit()

        credits = repo.get_credits_for_albums([200])
        names = [c.display_name for c in credits]
        assert "Nirvana" in names, f"Expected 'Nirvana' in Album 200 credits, got {names}"

        # No duplicate ArtistName
        with repo._get_connection() as conn:
            rows = conn.execute("SELECT NameID FROM ArtistNames WHERE DisplayName = 'Nirvana'").fetchall()
            assert len(rows) == 1, f"Expected 1 Nirvana ArtistName row, got {len(rows)}"

    def test_add_credit_with_new_name(self, populated_db):
        """Add a brand-new artist to Album 100 — should create ArtistName row."""
        repo = AlbumCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_credit(100, "Krist Novoselic", "Performer", conn)
            conn.commit()

        credits = repo.get_credits_for_albums([100])
        names = [c.display_name for c in credits]
        assert "Krist Novoselic" in names, f"Expected 'Krist Novoselic' in Album 100 credits, got {names}"

    def test_add_credit_idempotent(self, populated_db):
        """Adding the same credit twice should not create duplicate AlbumCredits rows."""
        repo = AlbumCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_credit(100, "Nirvana", "Performer", conn)
            repo.add_credit(100, "Nirvana", "Performer", conn)
            conn.commit()

        credits = repo.get_credits_for_albums([100])
        nirvana = [c for c in credits if c.display_name == "Nirvana"]
        assert len(nirvana) == 1, f"Expected 1 Nirvana credit (idempotent), got {len(nirvana)}"

    def test_remove_credit_deletes_link(self, populated_db):
        """Remove Nirvana (NameID=20) from Album 100 — link gone, ArtistName remains."""
        repo = AlbumCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.remove_credit(100, 20, conn)
            conn.commit()

        credits = repo.get_credits_for_albums([100])
        name_ids = [c.name_id for c in credits]
        assert 20 not in name_ids, f"Expected NameID=20 removed from Album 100, got {name_ids}"

        # ArtistName persists
        with repo._get_connection() as conn:
            row = conn.execute("SELECT NameID FROM ArtistNames WHERE NameID = 20").fetchone()
            assert row is not None, "Expected ArtistName (NameID=20) to persist after link removal"

    def test_add_credit_does_not_affect_other_albums(self, populated_db):
        """Adding a credit to Album 100 should not affect Album 200's credits."""
        repo = AlbumCreditRepository(populated_db)
        before = repo.get_credits_for_albums([200])

        with repo._get_connection() as conn:
            repo.add_credit(100, "Krist Novoselic", "Performer", conn)
            conn.commit()

        after = repo.get_credits_for_albums([200])
        assert len(after) == len(before), f"Album 200 credit count should not change: expected {len(before)}, got {len(after)}"

    def test_remove_credit_does_not_affect_other_albums(self, populated_db):
        """Removing a credit from Album 100 should not affect Album 200's credits."""
        repo = AlbumCreditRepository(populated_db)
        before = repo.get_credits_for_albums([200])

        with repo._get_connection() as conn:
            repo.remove_credit(100, 20, conn)
            conn.commit()

        after = repo.get_credits_for_albums([200])
        assert len(after) == len(before), f"Album 200 credit count should not change: expected {len(before)}, got {len(after)}"
