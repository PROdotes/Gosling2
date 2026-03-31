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

from src.data.album_repository import AlbumRepository


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
        assert (
            album.title == "In Utero"
        ), f"Expected title='In Utero', got '{album.title}'"
        assert (
            album.release_year == 1993
        ), f"Expected year=1993, got {album.release_year}"

    def test_create_album_reuses_existing(self, populated_db):
        """Creating an album with same title+year as existing should return existing id."""
        repo = AlbumRepository(populated_db)

        with repo._get_connection() as conn:
            album_id = repo.create_album("Nevermind", None, 1991, conn)
            conn.commit()

        assert album_id == 100, f"Expected to reuse AlbumID=100, got {album_id}"

        # No duplicate row
        with repo._get_connection() as conn:
            rows = conn.execute(
                "SELECT AlbumID FROM Albums WHERE AlbumTitle = 'Nevermind'"
            ).fetchall()
            assert (
                len(rows) == 1
            ), f"Expected 1 Nevermind row (no duplicate), got {len(rows)}"

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
        assert (
            album.title == "Nevermind (Deluxe)"
        ), f"Expected updated title, got '{album.title}'"

    def test_update_release_year(self, populated_db):
        """Update album release year."""
        repo = AlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_album(100, {"release_year": 2011}, conn)
            conn.commit()

        album = repo.get_by_id(100)
        assert (
            album.release_year == 2011
        ), f"Expected year=2011, got {album.release_year}"

    def test_update_partial_does_not_affect_other_fields(self, populated_db):
        """Updating only title should leave year unchanged."""
        repo = AlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_album(100, {"title": "Changed Title"}, conn)
            conn.commit()

        album = repo.get_by_id(100)
        assert (
            album.title == "Changed Title"
        ), f"Expected 'Changed Title', got '{album.title}'"
        assert (
            album.release_year == 1991
        ), f"Expected year=1991 unchanged, got {album.release_year}"

    def test_update_album_does_not_affect_other_albums(self, populated_db):
        """Updating Album 100 should not affect Album 200."""
        repo = AlbumRepository(populated_db)
        before = repo.get_by_id(200)

        with repo._get_connection() as conn:
            repo.update_album(100, {"title": "Changed", "release_year": 2000}, conn)
            conn.commit()

        after = repo.get_by_id(200)
        assert (
            after.title == before.title
        ), f"Album 200 title should not change, got '{after.title}'"
        assert (
            after.release_year == before.release_year
        ), f"Album 200 year should not change, got {after.release_year}"
