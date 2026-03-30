"""
Service-layer tests for CatalogService CRUD update methods.

populated_db reference:
  Song 1: "Smells Like Teen Spirit", dur=200s, year=1991, bpm=None, isrc=None, is_active=True
    - Credits: Nirvana (name_id=20, role_id=1 Performer)
    - Album: Nevermind (album_id=100, track=1)
    - Publisher: DGC Records (pub_id=10)
    - Tag: Grunge (tag_id=1, Genre)
  Song 2: "Everlong", year=1997
    - Credits: Foo Fighters (name_id=30, Performer)
    - Album: The Colour and the Shape (album_id=200, track=11)
  Album 100: "Nevermind", year=1991, credits=[Nirvana/Performer], publishers=[DGC(10), Sub Pop(5)]
  Publishers: DGC(10), Sub Pop(5), Roswell(4), BMI(2), ASCAP(3), Parent(1)
  Tags: Grunge(1/Genre), Energetic(2/Mood), 90s(3/Era), Electronic(4/Style), English(5/Jezik)
"""

import pytest
from src.services.catalog_service import CatalogService


class TestUpdateSongScalars:
    def test_update_title_returns_hydrated_song(self, populated_db):
        service = CatalogService(populated_db)
        song = service.update_song_scalars(1, {"media_name": "New Title"})
        assert song.id == 1, f"Expected id=1, got {song.id}"
        assert song.title == "New Title", f"Expected 'New Title', got '{song.title}'"
        # Other fields unchanged
        assert song.year == 1991, f"Expected year=1991, got {song.year}"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.isrc is None, f"Expected isrc=None, got {song.isrc}"
        assert song.is_active is True, f"Expected is_active=True, got {song.is_active}"

    def test_update_year_valid_returns_hydrated_song(self, populated_db):
        service = CatalogService(populated_db)
        song = service.update_song_scalars(1, {"year": 1995})
        assert song.year == 1995, f"Expected year=1995, got {song.year}"
        assert song.title == "Smells Like Teen Spirit", "Title should not change"

    def test_update_bpm_valid_returns_hydrated_song(self, populated_db):
        service = CatalogService(populated_db)
        song = service.update_song_scalars(1, {"bpm": 120})
        assert song.bpm == 120, f"Expected bpm=120, got {song.bpm}"
        assert song.year == 1991, "Year should not change"

    def test_update_isrc_valid_strips_dashes_and_saves(self, populated_db):
        service = CatalogService(populated_db)
        song = service.update_song_scalars(1, {"isrc": "US-RC1-99-00001"})
        assert (
            song.isrc == "USRC19900001"
        ), f"Expected 'USRC19900001' (dashes stripped), got '{song.isrc}'"

    def test_update_isrc_no_dashes_saves_as_is(self, populated_db):
        service = CatalogService(populated_db)
        song = service.update_song_scalars(1, {"isrc": "USRC19900001"})
        assert (
            song.isrc == "USRC19900001"
        ), f"Expected 'USRC19900001', got '{song.isrc}'"

    def test_update_is_active_false(self, populated_db):
        service = CatalogService(populated_db)
        song = service.update_song_scalars(1, {"is_active": False})
        assert (
            song.is_active is False
        ), f"Expected is_active=False, got {song.is_active}"

    def test_update_multiple_fields_at_once(self, populated_db):
        service = CatalogService(populated_db)
        song = service.update_song_scalars(1, {"year": 1992, "bpm": 145})
        assert song.year == 1992, f"Expected year=1992, got {song.year}"
        assert song.bpm == 145, f"Expected bpm=145, got {song.bpm}"
        assert song.title == "Smells Like Teen Spirit", "Title should not change"

    def test_update_empty_title_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="media_name"):
            service.update_song_scalars(1, {"media_name": ""})

    def test_update_whitespace_title_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="media_name"):
            service.update_song_scalars(1, {"media_name": "   "})

    def test_update_year_too_low_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="year"):
            service.update_song_scalars(1, {"year": 1000})

    def test_update_year_too_high_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="year"):
            service.update_song_scalars(1, {"year": 9999})

    def test_update_bpm_zero_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="bpm"):
            service.update_song_scalars(1, {"bpm": 0})

    def test_update_bpm_over_300_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="bpm"):
            service.update_song_scalars(1, {"bpm": 301})

    def test_update_isrc_too_short_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="isrc"):
            service.update_song_scalars(1, {"isrc": "USRC123"})

    def test_update_isrc_invalid_format_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="isrc"):
            service.update_song_scalars(1, {"isrc": "123456789012"})

    def test_update_non_editable_field_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="Non-editable"):
            service.update_song_scalars(1, {"duration_s": 999})

    def test_update_nullable_field_to_none_saves_correctly(self, populated_db):
        service = CatalogService(populated_db)
        # First set a value
        service.update_song_scalars(1, {"bpm": 120})
        # Then clear it
        song = service.update_song_scalars(1, {"bpm": None})
        assert song.bpm is None, f"Expected bpm=None after clearing, got {song.bpm}"


class TestAddSongCredit:
    def test_add_new_credit_returns_song_credit(self, populated_db):
        service = CatalogService(populated_db)
        credit = service.add_song_credit(2, "Dave Grohl", "Composer")
        assert credit.credit_id is not None, "Expected credit_id to be assigned"
        assert (
            credit.display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got '{credit.display_name}'"
        assert (
            credit.role_name == "Composer"
        ), f"Expected 'Composer', got '{credit.role_name}'"

    def test_add_credit_persisted_on_get_song(self, populated_db):
        service = CatalogService(populated_db)
        service.add_song_credit(2, "Dave Grohl", "Composer")
        song = service.get_song(2)
        names = [c.display_name for c in song.credits]
        assert "Dave Grohl" in names, f"Expected 'Dave Grohl' in credits, got {names}"

    def test_add_credit_existing_artist_reuses_record(self, populated_db):
        service = CatalogService(populated_db)
        # "Dave Grohl" (name_id=10) already exists in fixture
        credit = service.add_song_credit(2, "Dave Grohl", "Performer")
        assert (
            credit.display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got '{credit.display_name}'"
        # Verify no duplicate ArtistNames row created
        import sqlite3

        conn = sqlite3.connect(populated_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM ArtistNames WHERE DisplayName = 'Dave Grohl'"
        ).fetchone()[0]
        conn.close()
        assert count == 1, f"Expected 1 ArtistNames row for 'Dave Grohl', got {count}"


class TestRemoveSongCredit:
    def test_remove_existing_credit_link_deleted(self, populated_db):
        service = CatalogService(populated_db)
        # Song 1 has Nirvana/Performer — add a credit to get its credit_id
        credit = service.add_song_credit(1, "Dave Grohl", "Composer")
        credit_id = credit.credit_id
        service.remove_song_credit(1, credit_id)
        song = service.get_song(1)
        credit_ids = [c.credit_id for c in song.credits]
        assert credit_id not in credit_ids, f"Credit {credit_id} should be removed"

    def test_remove_credit_keeps_artist_name_record(self, populated_db):
        service = CatalogService(populated_db)
        credit = service.add_song_credit(1, "Dave Grohl", "Composer")
        service.remove_song_credit(1, credit.credit_id)
        import sqlite3

        conn = sqlite3.connect(populated_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM ArtistNames WHERE DisplayName = 'Dave Grohl'"
        ).fetchone()[0]
        conn.close()
        assert count == 1, "ArtistNames record should survive credit removal"


class TestUpdateCreditName:
    def test_rename_updates_globally(self, populated_db):
        service = CatalogService(populated_db)
        # Dave Grohl (name_id=10) credited on Song 6 and Song 8
        service.update_credit_name(10, "Dave Grohl Jr.")
        song6 = service.get_song(6)
        names_6 = [c.display_name for c in song6.credits]
        assert (
            "Dave Grohl Jr." in names_6
        ), f"Expected 'Dave Grohl Jr.' in song 6 credits, got {names_6}"

    def test_rename_empty_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="empty"):
            service.update_credit_name(10, "")


class TestAddSongAlbum:
    def test_link_existing_album_returns_song_album(self, populated_db):
        service = CatalogService(populated_db)
        # Song 3 has no album — link to Nevermind (100)
        song_album = service.add_song_album(3, 100, track_number=5, disc_number=1)
        assert (
            song_album.source_id == 3
        ), f"Expected source_id=3, got {song_album.source_id}"
        assert (
            song_album.album_id == 100
        ), f"Expected album_id=100, got {song_album.album_id}"
        assert (
            song_album.track_number == 5
        ), f"Expected track=5, got {song_album.track_number}"

    def test_link_persisted_on_get_song(self, populated_db):
        service = CatalogService(populated_db)
        service.add_song_album(3, 100, track_number=5)
        song = service.get_song(3)
        album_ids = [a.album_id for a in song.albums]
        assert 100 in album_ids, f"Expected album 100 in song albums, got {album_ids}"


class TestRemoveSongAlbum:
    def test_unlink_removes_link_keeps_album(self, populated_db):
        service = CatalogService(populated_db)
        # Song 1 is linked to Nevermind (100)
        service.remove_song_album(1, 100)
        song = service.get_song(1)
        album_ids = [a.album_id for a in song.albums]
        assert (
            100 not in album_ids
        ), f"Album 100 should be unlinked from song 1, got {album_ids}"
        # Album itself still exists
        album = service.get_album(100)
        assert album is not None, "Album 100 should still exist after unlink"
        assert album.title == "Nevermind", f"Expected 'Nevermind', got '{album.title}'"


class TestUpdateSongAlbumLink:
    def test_update_track_number(self, populated_db):
        service = CatalogService(populated_db)
        # Song 1 / Album 100 / Track 1
        service.update_song_album_link(1, 100, track_number=3, disc_number=2)
        song = service.get_song(1)
        link = next((a for a in song.albums if a.album_id == 100), None)
        assert link is not None, "Expected song-album link to exist"
        assert link.track_number == 3, f"Expected track=3, got {link.track_number}"
        assert link.disc_number == 2, f"Expected disc=2, got {link.disc_number}"


class TestUpdateAlbum:
    def test_update_album_title_returns_hydrated_album(self, populated_db):
        service = CatalogService(populated_db)
        album = service.update_album(100, {"title": "Nevermind (Remaster)"})
        assert album.id == 100, f"Expected id=100, got {album.id}"
        assert (
            album.title == "Nevermind (Remaster)"
        ), f"Expected 'Nevermind (Remaster)', got '{album.title}'"

    def test_update_album_persisted(self, populated_db):
        service = CatalogService(populated_db)
        service.update_album(100, {"title": "Nevermind (Remaster)"})
        album = service.get_album(100)
        assert (
            album.title == "Nevermind (Remaster)"
        ), f"Expected updated title, got '{album.title}'"


class TestAddSongTag:
    def test_add_existing_tag_returns_tag(self, populated_db):
        service = CatalogService(populated_db)
        # Song 2 has no tags — add Grunge (tag_id=1)
        tag = service.add_song_tag(2, "Grunge", "Genre")
        assert tag.id is not None, "Expected tag id"
        assert tag.name == "Grunge", f"Expected 'Grunge', got '{tag.name}'"
        assert tag.category == "Genre", f"Expected 'Genre', got '{tag.category}'"

    def test_add_tag_persisted_on_get_song(self, populated_db):
        service = CatalogService(populated_db)
        service.add_song_tag(2, "Grunge", "Genre")
        song = service.get_song(2)
        tag_names = [t.name for t in song.tags]
        assert "Grunge" in tag_names, f"Expected 'Grunge' in tags, got {tag_names}"

    def test_add_new_tag_creates_and_links(self, populated_db):
        service = CatalogService(populated_db)
        tag = service.add_song_tag(1, "Live Recording", "Type")
        assert (
            tag.name == "Live Recording"
        ), f"Expected 'Live Recording', got '{tag.name}'"
        assert tag.category == "Type", f"Expected 'Type', got '{tag.category}'"


class TestRemoveSongTag:
    def test_remove_tag_unlinks_keeps_record(self, populated_db):
        service = CatalogService(populated_db)
        # Song 1 has Grunge (tag_id=1)
        service.remove_song_tag(1, 1)
        song = service.get_song(1)
        tag_ids = [t.id for t in song.tags]
        assert 1 not in tag_ids, f"Tag 1 should be unlinked from song 1, got {tag_ids}"
        # Tag record still exists
        import sqlite3

        conn = sqlite3.connect(populated_db)
        count = conn.execute("SELECT COUNT(*) FROM Tags WHERE TagID = 1").fetchone()[0]
        conn.close()
        assert count == 1, "Tag record should survive unlink"


class TestUpdateTag:
    def test_rename_tag_globally(self, populated_db):
        service = CatalogService(populated_db)
        service.update_tag(1, "Alternative Rock", "Genre")
        song = service.get_song(1)
        tag_names = [t.name for t in song.tags]
        assert (
            "Alternative Rock" in tag_names
        ), f"Expected 'Alternative Rock' in tags, got {tag_names}"
        assert "Grunge" not in tag_names, f"'Grunge' should be renamed, got {tag_names}"

    def test_rename_tag_empty_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="empty"):
            service.update_tag(1, "", "Genre")


class TestAddSongPublisher:
    def test_add_existing_publisher_returns_publisher(self, populated_db):
        service = CatalogService(populated_db)
        # Song 2 has no publisher — add Sub Pop (pub_id=5)
        publisher = service.add_song_publisher(2, "Sub Pop")
        assert publisher.id is not None, "Expected publisher id"
        assert (
            publisher.name == "Sub Pop"
        ), f"Expected 'Sub Pop', got '{publisher.name}'"

    def test_add_publisher_persisted_on_get_song(self, populated_db):
        service = CatalogService(populated_db)
        service.add_song_publisher(2, "Sub Pop")
        song = service.get_song(2)
        pub_names = [p.name for p in song.publishers]
        assert (
            "Sub Pop" in pub_names
        ), f"Expected 'Sub Pop' in publishers, got {pub_names}"

    def test_add_new_publisher_creates_and_links(self, populated_db):
        service = CatalogService(populated_db)
        publisher = service.add_song_publisher(1, "Brand New Label")
        assert (
            publisher.name == "Brand New Label"
        ), f"Expected 'Brand New Label', got '{publisher.name}'"


class TestRemoveSongPublisher:
    def test_remove_publisher_unlinks_keeps_record(self, populated_db):
        service = CatalogService(populated_db)
        # Song 1 has DGC Records (pub_id=10)
        service.remove_song_publisher(1, 10)
        song = service.get_song(1)
        pub_ids = [p.id for p in song.publishers]
        assert (
            10 not in pub_ids
        ), f"Publisher 10 should be unlinked from song 1, got {pub_ids}"
        # Publisher record still exists
        import sqlite3

        conn = sqlite3.connect(populated_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM Publishers WHERE PublisherID = 10"
        ).fetchone()[0]
        conn.close()
        assert count == 1, "Publisher record should survive unlink"


class TestUpdatePublisher:
    def test_rename_publisher_globally(self, populated_db):
        service = CatalogService(populated_db)
        service.update_publisher(10, "DGC Records International")
        song = service.get_song(1)
        pub_names = [p.name for p in song.publishers]
        assert (
            "DGC Records International" in pub_names
        ), f"Expected 'DGC Records International' in publishers, got {pub_names}"

    def test_rename_publisher_empty_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError, match="empty"):
            service.update_publisher(10, "")


class TestSetPublisherParent:
    def test_set_parent_assigns_parent(self, populated_db):
        """Set Sub Pop (5, parent=NULL) to have parent Universal Music Group (1)."""
        service = CatalogService(populated_db)
        service.set_publisher_parent(5, 1)

        publisher = service.get_publisher(5)
        assert publisher.parent_id == 1, f"Expected parent_id=1, got {publisher.parent_id}"
        assert publisher.name == "Sub Pop", f"Expected name='Sub Pop' unchanged, got '{publisher.name}'"

    def test_clear_parent_sets_none(self, populated_db):
        """Clear parent from DGC Records (10, parent=1) → parent=None."""
        service = CatalogService(populated_db)
        service.set_publisher_parent(10, None)

        publisher = service.get_publisher(10)
        assert publisher.parent_id is None, f"Expected parent_id=None after clear, got {publisher.parent_id}"
        assert publisher.name == "DGC Records", f"Expected name='DGC Records' unchanged, got '{publisher.name}'"

    def test_set_parent_nonexistent_publisher_raises(self, populated_db):
        """set_publisher_parent on nonexistent publisher should raise LookupError."""
        service = CatalogService(populated_db)
        with pytest.raises(LookupError):
            service.set_publisher_parent(9999, 1)
