"""
Service-layer tests for CatalogService album writing methods.
Follows TDD_STANDARD.md:
- One test class per method
- No silent fallbacks (None check)
- Exhaustive contract assertions
- Service-based effect verification
"""

import pytest
import sqlite3
from src.services.catalog_service import CatalogService
from src.models.domain import SongAlbum, Publisher


class TestCreateAndLinkAlbum:
    def test_success_returns_hydrated_link(self, populated_db):
        service = CatalogService(populated_db)
        # Song 5 ("Pocketwatch Demo") has no album in fixture
        album_data = {
            "title": "The Fresh Pot",
            "release_year": 2024,
            "album_type": "Studio",
        }

        link = service.create_and_link_album(
            5, album_data, track_number=1, disc_number=1
        )

        # 1. Assert Method Contract (Hydration)
        assert isinstance(link, SongAlbum), f"Expected SongAlbum, got {type(link)}"
        assert (
            link.album_title == "The Fresh Pot"
        ), f"Expected 'The Fresh Pot', got {link.album_title}"
        assert link.release_year == 2024, f"Expected 2024, got {link.release_year}"
        assert link.track_number == 1, f"Expected track 1, got {link.track_number}"
        assert link.disc_number == 1, f"Expected disc 1, got {link.disc_number}"
        assert (
            link.is_primary is True
        ), f"Expected is_primary=True, got {link.is_primary}"
        assert link.album_id is not None, "Expected album_id to be assigned"

        # 2. Verify Persistence (Side Effect via Service)
        album = service.get_album(link.album_id)
        assert album is not None, "Album should be retrievable"
        assert album.title == "The Fresh Pot", "Album record should persist"

    def test_invalid_song_id_raises_lookup_error(self, populated_db):
        service = CatalogService(populated_db)
        album_data = {"title": "Ghost", "release_year": 2024}
        with pytest.raises(LookupError):
            service.create_and_link_album(9999, album_data)

    def test_invalid_album_data_empty_title_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        album_data = {"title": "  ", "release_year": 2024}
        with pytest.raises(ValueError, match="title"):
            service.create_and_link_album(5, album_data)

    def test_reactivate_soft_deleted_album(self, populated_db):
        service = CatalogService(populated_db)
        conn = sqlite3.connect(populated_db)
        conn.execute("UPDATE Albums SET IsDeleted = 1 WHERE AlbumID = 100")
        conn.commit()
        conn.close()

        album_data = {"title": "Nevermind", "release_year": 1991}
        link = service.create_and_link_album(5, album_data)

        assert link.album_id == 100, f"Expected to reuse ID 100, got {link.album_id}"
        album = service.get_album(100)
        assert album is not None, "Album 100 should be retrievable via Service"

        conn = sqlite3.connect(populated_db)
        deleted = conn.execute(
            "SELECT IsDeleted FROM Albums WHERE AlbumID = 100"
        ).fetchone()[0]
        conn.close()
        assert deleted == 0, f"Expected IsDeleted=0, got {deleted}"

    def test_rollback_on_link_failure(self, populated_db):
        service = CatalogService(populated_db)
        album_data = {"title": "Rollback Album", "release_year": 2024}
        with pytest.raises(LookupError):
            service.create_and_link_album(9999, album_data)

        albums = service.search_albums_slim("Rollback Album")
        assert (
            len(albums) == 0
        ), "Transaction failed to rollback: Album record created despite link failure"

    def test_missing_optional_track_info_returns_none(self, populated_db):
        service = CatalogService(populated_db)
        album_data = {"title": "No Track Album", "release_year": 2024}
        link = service.create_and_link_album(5, album_data)
        assert link.track_number is None, f"Expected None, got {link.track_number}"
        assert link.disc_number is None, f"Expected None, got {link.disc_number}"


class TestUpdateAlbum:
    def test_success_returns_hydrated_album(self, populated_db):
        service = CatalogService(populated_db)
        # Album 100: "Nevermind", 1991
        updated = service.update_album(
            100, {"title": "Nevermind (Spl)", "release_year": 2011}
        )

        assert updated.id == 100
        assert (
            updated.title == "Nevermind (Spl)"
        ), f"Expected title update, got '{updated.title}'"
        assert (
            updated.release_year == 2011
        ), f"Expected year update, got {updated.release_year}"

        # Verify persistence
        album = service.get_album(100)
        assert album.title == "Nevermind (Spl)"

    def test_unchanged_fields_stay_unchanged(self, populated_db):
        service = CatalogService(populated_db)
        # Album 100: "Nevermind", 1991, album_type="Studio" (assumed)
        updated = service.update_album(100, {"title": "New Title"})
        assert updated.title == "New Title"
        assert updated.release_year == 1991, "Year should remain 1991"

    def test_invalid_album_id_raises_lookup_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(LookupError):
            service.update_album(9999, {"title": "Ghost"})

    def test_empty_title_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError):
            service.update_album(100, {"title": "  "})

    def test_hydration_preserved_after_update(self, populated_db):
        service = CatalogService(populated_db)
        updated = service.update_album(100, {"title": "Updated"})
        names = [c.display_name for c in updated.credits]
        assert "Nirvana" in names, "Credits should remain hydrated in returned object"
        pubs = [p.name for p in updated.publishers]
        assert (
            "DGC Records" in pubs
        ), "Publishers should remain hydrated in returned object"


class TestAddSongAlbum:
    def test_success_returns_hydrated_link(self, populated_db):
        service = CatalogService(populated_db)
        # Song 3 ("Range Rover Bitch") has no album — link to Nevermind (100)
        link = service.add_song_album(3, 100, track_number=5, disc_number=1)

        assert isinstance(link, SongAlbum)
        assert link.source_id == 3
        assert link.album_id == 100
        assert link.album_title == "Nevermind"
        assert link.track_number == 5

        # Verify persistence via Service
        song = service.get_song(3)
        album_ids = [a.album_id for a in song.albums]
        assert 100 in album_ids, "Album 100 should be linked to song 3"

    def test_missing_song_id_raises_lookup_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(LookupError):
            service.add_song_album(9999, 100)

    def test_missing_album_id_raises_lookup_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(LookupError):
            service.add_song_album(1, 9999)

    def test_duplicate_link_is_noop_or_returns_existing(self, populated_db):
        service = CatalogService(populated_db)
        # Song 1 is already on Album 100
        link = service.add_song_album(1, 100, track_number=1)
        assert link.album_id == 100
        assert link.source_id == 1


class TestRemoveSongAlbum:
    def test_success_unlinks_keeps_records(self, populated_db):
        service = CatalogService(populated_db)
        # Song 1 is linked to Nevermind (100)
        service.remove_song_album(1, 100)

        # Verify link gone via Service
        song = service.get_song(1)
        album_ids = [a.album_id for a in song.albums]
        assert 100 not in album_ids, "Album 100 should be unlinked from song 1"

        # Verify entity survival
        album = service.get_album(100)
        assert album is not None, "Album record should still exist"

    def test_missing_link_silently_succeeds(self, populated_db):
        service = CatalogService(populated_db)
        # Song 3 is not on Album 100
        service.remove_song_album(3, 100)
        # No error raised


class TestUpdateSongAlbumLink:
    def test_success_updates_track_info(self, populated_db):
        service = CatalogService(populated_db)
        # Song 1 / Album 100 is Track 1
        service.update_song_album_link(1, 100, track_number=7, disc_number=3)

        # Verify Effect
        song = service.get_song(1)
        link = next((a for a in song.albums if a.album_id == 100), None)
        assert link is not None
        assert link.track_number == 7, f"Expected 7, got {link.track_number}"
        assert link.disc_number == 3, f"Expected 3, got {link.disc_number}"

    def test_invalid_link_raises_lookup_error(self, populated_db):
        service = CatalogService(populated_db)
        # Song 3 and Album 100 are not linked
        with pytest.raises(LookupError):
            service.update_song_album_link(3, 100, track_number=5)


class TestAlbumCredits:
    def test_add_credit_success_returns_name_id(self, populated_db):
        service = CatalogService(populated_db)
        # Album 100, add Taylor Hawkins as Producer (Identity 4, Name 40)
        name_id = service.add_album_credit(
            100, "Taylor Hawkins", "Producer", identity_id=4
        )
        assert name_id == 40

        # Verify Persistence
        album = service.get_album(100)
        credits = [(c.display_name, c.role_name) for c in album.credits]
        assert ("Taylor Hawkins", "Producer") in credits

    def test_add_credit_missing_album_raises_lookup_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(LookupError):
            service.add_album_credit(9999, "Dave", "Performer")

    def test_remove_credit_success_unlinks_keeps_name_record(self, populated_db):
        service = CatalogService(populated_db)
        # Nirvana (20) is on Nevermind (100)
        service.remove_album_credit(100, 20)

        # Verify unlinked
        album = service.get_album(100)
        names = [c.display_name for c in album.credits]
        assert "Nirvana" not in names

        # Verify name record survived (Global rename check)
        service.update_credit_name(20, "Nirvana (Legend)")
        song1 = service.get_song(1)
        assert any(c.display_name == "Nirvana (Legend)" for c in song1.credits)


class TestAlbumPublishers:
    def test_add_publisher_new_returns_hydrated_pub(self, populated_db):
        service = CatalogService(populated_db)
        pub = service.add_album_publisher(100, "Geffen")
        assert isinstance(pub, Publisher)
        assert pub.name == "Geffen"

        # Verify Persistence
        album = service.get_album(100)
        pubs = [p.name for p in album.publishers]
        assert "Geffen" in pubs

    def test_add_publisher_by_id_success(self, populated_db):
        service = CatalogService(populated_db)
        # Roswell Records (4) is not on Nevermind (100)
        pub = service.add_album_publisher(100, None, publisher_id=4)
        assert pub.id == 4

        album = service.get_album(100)
        assert any(p.id == 4 for p in album.publishers)

    def test_add_publisher_missing_album_raises_lookup_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(LookupError):
            service.add_album_publisher(9999, "Geffen")

    def test_remove_publisher_success(self, populated_db):
        service = CatalogService(populated_db)
        # DGC Records (10) is on Nevermind (100)
        service.remove_album_publisher(100, 10)

        album = service.get_album(100)
        pubs = [p.id for p in album.publishers]
        assert 10 not in pubs
