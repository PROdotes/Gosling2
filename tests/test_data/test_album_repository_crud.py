"""
Tests for AlbumRepository CRUD methods
=========================================
create_album, update_album, add_album_credit, remove_album_credit, set_album_publisher

populated_db albums:
  AlbumID=100: "Nevermind" (1991, type=None)   Credit: Nirvana (NameID=20, Performer)  Publisher: DGC Records(10), Sub Pop(5)
  AlbumID=200: "The Colour and the Shape" (1997, type=None)  Credit: Foo Fighters (NameID=30, Performer)  Publisher: Roswell Records(4)

populated_db publishers:
  4: Roswell Records, 5: Sub Pop, 10: DGC Records
"""

import sqlite3
from src.data.album_repository import AlbumRepository
from src.data.album_credit_repository import AlbumCreditRepository


class TestCreateAlbum:
    def test_create_new_album(self, populated_db):
        """Create a brand-new album — should insert and return new album_id."""
        repo = AlbumRepository(populated_db)

        with repo._get_connection() as conn:
            album_id = repo.create_album("In Utero", "LP", 1993, conn)
            conn.commit()

        assert album_id is not None, "Expected album_id to be set, got None"

        album = repo.get_by_id(album_id)
        assert album is not None, f"Expected album to exist with id={album_id}"
        assert album.title == "In Utero", f"Expected title='In Utero', got '{album.title}'"
        assert album.release_year == 1993, f"Expected year=1993, got {album.release_year}"

    def test_create_album_reuses_existing(self, populated_db):
        """Creating an album with same title+year as existing should return existing id."""
        repo = AlbumRepository(populated_db)

        with repo._get_connection() as conn:
            album_id = repo.create_album("Nevermind", None, 1991, conn)
            conn.commit()

        assert album_id == 100, f"Expected to reuse AlbumID=100, got {album_id}"

        # No duplicate row
        with repo._get_connection() as conn:
            rows = conn.execute("SELECT AlbumID FROM Albums WHERE AlbumTitle = 'Nevermind'").fetchall()
            assert len(rows) == 1, f"Expected 1 Nevermind row (no duplicate), got {len(rows)}"

    def test_create_album_reactivates_soft_deleted(self, populated_db):
        """Creating an album matching a soft-deleted record should reactivate it."""
        repo = AlbumRepository(populated_db)

        # Soft-delete Nevermind
        with repo._get_connection() as conn:
            conn.execute("UPDATE Albums SET IsDeleted = 1 WHERE AlbumID = 100")
            conn.commit()

        with repo._get_connection() as conn:
            album_id = repo.create_album("Nevermind", None, 1991, conn)
            conn.commit()

        assert album_id == 100, f"Expected reactivated AlbumID=100, got {album_id}"
        album = repo.get_by_id(100)
        assert album is not None, "Expected reactivated album to be visible"


class TestUpdateAlbum:
    def test_update_title(self, populated_db):
        """Update album title."""
        repo = AlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_album(100, {"title": "Nevermind (Deluxe)"}, conn)
            conn.commit()

        album = repo.get_by_id(100)
        assert album.title == "Nevermind (Deluxe)", f"Expected updated title, got '{album.title}'"

    def test_update_release_year(self, populated_db):
        """Update album release year."""
        repo = AlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_album(100, {"release_year": 2011}, conn)
            conn.commit()

        album = repo.get_by_id(100)
        assert album.release_year == 2011, f"Expected year=2011, got {album.release_year}"

    def test_update_partial_does_not_affect_other_fields(self, populated_db):
        """Updating only title should leave year unchanged."""
        repo = AlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_album(100, {"title": "Changed Title"}, conn)
            conn.commit()

        album = repo.get_by_id(100)
        assert album.title == "Changed Title", f"Expected 'Changed Title', got '{album.title}'"
        assert album.release_year == 1991, f"Expected year=1991 unchanged, got {album.release_year}"

    def test_update_album_does_not_affect_other_albums(self, populated_db):
        """Updating Album 100 should not affect Album 200."""
        repo = AlbumRepository(populated_db)
        before = repo.get_by_id(200)

        with repo._get_connection() as conn:
            repo.update_album(100, {"title": "Changed", "release_year": 2000}, conn)
            conn.commit()

        after = repo.get_by_id(200)
        assert after.title == before.title, f"Album 200 title should not change, got '{after.title}'"
        assert after.release_year == before.release_year, f"Album 200 year should not change, got {after.release_year}"


class TestAddAlbumCredit:
    def test_add_credit_with_existing_name(self, populated_db):
        """Add an existing artist to Album 200 — should create AlbumCredits link, not duplicate ArtistName."""
        repo = AlbumRepository(populated_db)
        credit_repo = AlbumCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_album_credit(200, "Nirvana", "Performer", conn)
            conn.commit()

        credits = credit_repo.get_credits_for_albums([200])
        names = [c.display_name for c in credits]
        assert "Nirvana" in names, f"Expected 'Nirvana' in Album 200 credits, got {names}"

        # No duplicate ArtistName
        with repo._get_connection() as conn:
            rows = conn.execute("SELECT NameID FROM ArtistNames WHERE DisplayName = 'Nirvana'").fetchall()
            assert len(rows) == 1, f"Expected 1 Nirvana ArtistName row, got {len(rows)}"

    def test_add_credit_with_new_name(self, populated_db):
        """Add a brand-new artist to Album 100 — should create ArtistName row."""
        repo = AlbumRepository(populated_db)
        credit_repo = AlbumCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_album_credit(100, "Krist Novoselic", "Performer", conn)
            conn.commit()

        credits = credit_repo.get_credits_for_albums([100])
        names = [c.display_name for c in credits]
        assert "Krist Novoselic" in names, f"Expected 'Krist Novoselic' in Album 100 credits, got {names}"

    def test_add_credit_idempotent(self, populated_db):
        """Adding the same credit twice should not create duplicate AlbumCredits rows."""
        repo = AlbumRepository(populated_db)
        credit_repo = AlbumCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_album_credit(100, "Nirvana", "Performer", conn)
            repo.add_album_credit(100, "Nirvana", "Performer", conn)
            conn.commit()

        credits = credit_repo.get_credits_for_albums([100])
        nirvana = [c for c in credits if c.display_name == "Nirvana"]
        assert len(nirvana) == 1, f"Expected 1 Nirvana credit (idempotent), got {len(nirvana)}"

    def test_add_credit_does_not_affect_other_albums(self, populated_db):
        """Adding a credit to Album 100 should not affect Album 200's credits."""
        repo = AlbumRepository(populated_db)
        credit_repo = AlbumCreditRepository(populated_db)
        before = credit_repo.get_credits_for_albums([200])

        with repo._get_connection() as conn:
            repo.add_album_credit(100, "Krist Novoselic", "Performer", conn)
            conn.commit()

        after = credit_repo.get_credits_for_albums([200])
        assert len(after) == len(before), f"Album 200 credit count should not change: expected {len(before)}, got {len(after)}"


class TestRemoveAlbumCredit:
    def test_remove_credit_deletes_link(self, populated_db):
        """Remove Nirvana (NameID=20) from Album 100 — link gone, ArtistName remains."""
        repo = AlbumRepository(populated_db)
        credit_repo = AlbumCreditRepository(populated_db)

        with repo._get_connection() as conn:
            repo.remove_album_credit(100, 20, conn)
            conn.commit()

        credits = credit_repo.get_credits_for_albums([100])
        name_ids = [c.name_id for c in credits]
        assert 20 not in name_ids, f"Expected NameID=20 removed from Album 100, got {name_ids}"

        # ArtistName persists
        with repo._get_connection() as conn:
            row = conn.execute("SELECT NameID FROM ArtistNames WHERE NameID = 20").fetchone()
            assert row is not None, "Expected ArtistName (NameID=20) to persist after link removal"

    def test_remove_credit_does_not_affect_other_albums(self, populated_db):
        """Removing a credit from Album 100 should not affect Album 200's credits."""
        repo = AlbumRepository(populated_db)
        credit_repo = AlbumCreditRepository(populated_db)
        before = credit_repo.get_credits_for_albums([200])

        with repo._get_connection() as conn:
            repo.remove_album_credit(100, 20, conn)
            conn.commit()

        after = credit_repo.get_credits_for_albums([200])
        assert len(after) == len(before), f"Album 200 credit count should not change: expected {len(before)}, got {len(after)}"


class TestSetAlbumPublisher:
    def test_set_publisher_replaces_existing(self, populated_db):
        """Set Album 100's publisher to Sub Pop (5) — should replace DGC Records."""
        repo = AlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.set_album_publisher(100, 5, conn)
            conn.commit()

        with repo._get_connection() as conn:
            rows = conn.execute("SELECT PublisherID FROM AlbumPublishers WHERE AlbumID = 100").fetchall()
            pub_ids = [r[0] for r in rows]
            assert pub_ids == [5], f"Expected only PublisherID=5, got {pub_ids}"

    def test_set_publisher_on_album_with_no_publisher(self, populated_db):
        """Set a publisher on an album that has none — should create the link."""
        repo = AlbumRepository(populated_db)

        # Verify Album 100 has no publisher first by clearing it
        with repo._get_connection() as conn:
            conn.execute("DELETE FROM AlbumPublishers WHERE AlbumID = 100")
            conn.commit()

        with repo._get_connection() as conn:
            repo.set_album_publisher(100, 4, conn)
            conn.commit()

        with repo._get_connection() as conn:
            rows = conn.execute("SELECT PublisherID FROM AlbumPublishers WHERE AlbumID = 100").fetchall()
            assert len(rows) == 1, f"Expected 1 publisher link, got {len(rows)}"
            assert rows[0][0] == 4, f"Expected PublisherID=4, got {rows[0][0]}"

    def test_set_publisher_does_not_affect_other_albums(self, populated_db):
        """Changing Album 100's publisher should not affect Album 200's publisher."""
        repo = AlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.set_album_publisher(100, 5, conn)
            conn.commit()

        with repo._get_connection() as conn:
            rows = conn.execute("SELECT PublisherID FROM AlbumPublishers WHERE AlbumID = 200").fetchall()
            pub_ids = [r[0] for r in rows]
            assert 4 in pub_ids, f"Expected Album 200 to still have Roswell Records (4), got {pub_ids}"
