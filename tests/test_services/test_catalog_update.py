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
from pathlib import Path
from src.services.catalog_service import CatalogService
from tests.conftest import _connect


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

    def test_activate_reviewed_song_succeeds(self, populated_db):
        """Case 01: Song in status 0 (Reviewed) can be activated."""
        service = CatalogService(populated_db)
        # Song 1 is Status 0 in fixture. Deactivate then reactivate.
        service.update_song_scalars(1, {"is_active": False})
        song = service.update_song_scalars(1, {"is_active": True})
        assert song.is_active is True, f"Expected is_active=True, got {song.is_active}"

    def test_activate_unreviewed_song_raises_value_error(self, populated_db):
        """Case 03/05: Setting is_active=True fails if status is 1 or 2."""
        service = CatalogService(populated_db)
        # Song 7 is Status 1. Ensure it is deactivated first.
        service.update_song_scalars(7, {"is_active": False})

        # Attempting to activate (is_active=True) must fail validation for status 1.
        with pytest.raises(
            ValueError, match="Cannot activate song unless processing_status is 0"
        ):
            service.update_song_scalars(7, {"is_active": True})

        # Verify state did NOT change to True
        refreshed = service.get_song(7)
        assert refreshed.is_active is False

    def test_deactivate_unreviewed_song_succeeds(self, populated_db):
        """Case 04/06: Deactivation (is_active=False) is always allowed regardless of status."""
        service = CatalogService(populated_db)
        # Song 7 is Status 1 in fixture.
        song = service.update_song_scalars(7, {"is_active": False})
        assert (
            song.is_active is False
        ), f"Expected is_active=False, got {song.is_active}"

    def test_activate_and_review_validation_interaction(self, populated_db):
        """Verify that is_active=True check uses the NEW status if provided in same call."""
        service = CatalogService(populated_db)
        # Song 7 is Status 1. Ensure it is deactivated first.
        service.update_song_scalars(7, {"is_active": False})

        # If we try to set is_active=True, it fails.
        with pytest.raises(
            ValueError, match="Cannot activate song unless processing_status is 0"
        ):
            service.update_song_scalars(7, {"is_active": True})

        # Verify state did NOT change to True
        refreshed = service.get_song(7)
        assert refreshed.is_active is False

    def test_invalid_song_id_raises_lookup_error(self, populated_db):
        """Case 08: Updating a non-existent song raises LookupError."""
        service = CatalogService(populated_db)
        with pytest.raises(LookupError, match="not found"):
            service.update_song_scalars(99999, {"is_active": True})


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

        # 1. Assert Contract (Method works)
        assert (
            credit.display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got '{credit.display_name}'"
        assert (
            credit.role_name == "Performer"
        ), f"Expected 'Performer', got '{credit.role_name}'"
        assert credit.identity_id == 1, "Should have linked to existing identity ID 1"

        # 2. Assert Effect (Verify no duplicate link via Service)
        song = service.get_song(2)
        matches = [c for c in song.credits if c.display_name == "Dave Grohl"]
        assert len(matches) == 1, "Duplicate credit link created for same artist"

    def test_add_credit_with_identity_id_links_to_identity(self, populated_db):
        service = CatalogService(populated_db)
        # Identity 1 is Dave Grohl
        credit = service.add_song_credit(2, "David Grohl", "Performer", identity_id=1)
        assert credit.identity_id == 1
        assert credit.display_name == "David Grohl"

        # Verify through get_song
        song = service.get_song(2)
        target = next(c for c in song.credits if c.display_name == "David Grohl")
        assert (
            target.identity_id == 1
        ), f"Expected link to identity 1, got {target.identity_id}"


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

        # Verify link gone via Service
        song = service.get_song(1)
        credit_ids = [c.credit_id for c in song.credits]
        assert credit.credit_id not in credit_ids, "Credit link should be removed"

        # Verify name record survives via secondary Service call
        # (We check Dave Grohl's existing name_id=10 is still renameable)
        service.update_credit_name(10, "Dave G.")
        revived = service.get_song(6)  # Song 6 uses name_id 10
        assert any(
            c.display_name == "Dave G." for c in revived.credits
        ), "Artist record should survive credit removal"


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


# Redundant Album tests moved to test_album_write.py


class TestAddSongTag:
    def test_add_existing_tag_by_name_returns_tag(self, populated_db):
        service = CatalogService(populated_db)
        # Song 2 has no tags — add Grunge (tag_id=1) by name
        tag = service.add_song_tag(2, "Grunge", "Genre")
        assert tag.id is not None, "Expected tag id"
        assert tag.name == "Grunge", f"Expected 'Grunge', got '{tag.name}'"
        assert tag.category == "Genre", f"Expected 'Genre', got '{tag.category}'"

    def test_add_tag_by_name_persisted_on_get_song(self, populated_db):
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

    def test_add_tag_by_id_links_existing(self, populated_db):
        service = CatalogService(populated_db)
        # Song 2 has no tags — link Grunge (tag_id=1) by ID, no name/category passed
        tag = service.add_song_tag(2, None, None, tag_id=1)
        assert tag.id == 1, f"Expected tag id=1, got {tag.id}"
        assert tag.name == "Grunge", f"Expected 'Grunge', got '{tag.name}'"
        assert tag.category == "Genre", f"Expected 'Genre', got '{tag.category}'"

    def test_add_tag_by_id_persisted_on_get_song(self, populated_db):
        service = CatalogService(populated_db)
        service.add_song_tag(2, None, None, tag_id=1)
        song = service.get_song(2)
        tag_ids = [t.id for t in song.tags]
        assert 1 in tag_ids, f"Expected tag_id=1 linked to song 2, got {tag_ids}"

    def test_add_tag_by_id_not_found_raises_lookup_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(LookupError):
            service.add_song_tag(2, None, None, tag_id=9999)

    def test_add_tag_by_name_missing_category_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError):
            service.add_song_tag(2, "Grunge", None)


class TestRemoveSongTag:
    def test_remove_tag_unlinks_keeps_record(self, populated_db):
        service = CatalogService(populated_db)
        # Song 1 has Grunge (tag_id=1)
        service.remove_song_tag(1, 1)

        # 1. Verify link gone via Service (Method effect on focus object)
        song = service.get_song(1)
        tag_ids = [t.id for t in song.tags]
        assert 1 not in tag_ids, f"Tag 1 should be unlinked from song 1, got {tag_ids}"

        # 2. Verify record survives via second song that uses it (Persistence check)
        service.update_tag(1, "Grunge Rock", "Genre")
        song9 = service.get_song(9)  # Song 9 also has Grunge (1)
        matches = [t for t in song9.tags if t.id == 1]
        assert len(matches) == 1, "Tag 1 should still be on song 9"
        assert (
            matches[0].name == "Grunge Rock"
        ), "Renaming should have applied to surviving tag record"

        # 3. Final global check via search
        tags = service.search_tags("Grunge Rock")
        assert any(
            t.id == 1 for t in tags
        ), "Tag should be globally searchable after being unlinked from one song"


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
    def test_add_existing_publisher_by_name_returns_publisher(self, populated_db):
        service = CatalogService(populated_db)
        # Song 2 has no publisher — add Sub Pop (pub_id=5) by name
        publisher = service.add_song_publisher(2, "Sub Pop")
        assert publisher.id is not None, "Expected publisher id"
        assert (
            publisher.name == "Sub Pop"
        ), f"Expected 'Sub Pop', got '{publisher.name}'"

    def test_add_publisher_by_name_persisted_on_get_song(self, populated_db):
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

    def test_add_publisher_by_id_links_existing(self, populated_db):
        service = CatalogService(populated_db)
        # Song 2 has no publisher — link Sub Pop (pub_id=5) by ID
        publisher = service.add_song_publisher(2, None, publisher_id=5)
        assert publisher.id == 5, f"Expected publisher id=5, got {publisher.id}"
        assert (
            publisher.name == "Sub Pop"
        ), f"Expected 'Sub Pop', got '{publisher.name}'"

    def test_add_publisher_by_id_persisted_on_get_song(self, populated_db):
        service = CatalogService(populated_db)
        service.add_song_publisher(2, None, publisher_id=5)
        song = service.get_song(2)
        pub_ids = [p.id for p in song.publishers]
        assert 5 in pub_ids, f"Expected pub_id=5 linked to song 2, got {pub_ids}"

    def test_add_publisher_by_id_not_found_raises_lookup_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(LookupError):
            service.add_song_publisher(2, None, publisher_id=9999)

    def test_add_publisher_by_name_missing_name_raises_value_error(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError):
            service.add_song_publisher(2, None)


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

        conn = _connect(populated_db)
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
        assert (
            publisher.parent_id == 1
        ), f"Expected parent_id=1, got {publisher.parent_id}"
        assert (
            publisher.name == "Sub Pop"
        ), f"Expected name='Sub Pop' unchanged, got '{publisher.name}'"

    def test_clear_parent_sets_none(self, populated_db):
        """Clear parent from DGC Records (10, parent=1) → parent=None."""
        service = CatalogService(populated_db)
        service.set_publisher_parent(10, None)


class TestAutoMoveOnApprove:
    """AUTO_MOVE_ON_APPROVE: when True and song is REVIEWED, scalar saves auto-trigger move_to_library."""

    def test_reviewed_auto_moves_when_enabled(self, populated_db, tmp_path, monkeypatch):
        """REVIEWED song + AUTO_MOVE_ON_APPROVE=True + scalar save → file moved to computed target."""
        import shutil
        from src.services.edit_service import EditService
        from src.services.library_service import LibraryService
        from src.services.filing_service import FilingService
        from src.engine.config import AUTO_MOVE_ON_APPROVE, LIBRARY_ROOT
        from tests.conftest import _connect

        # Setup: library root and a source file in a staging dir
        library_root = tmp_path / "library"
        library_root.mkdir()
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        source_file = staging_dir / "Nirvana - Smells Like Teen Spirit.mp3"
        source_file.write_bytes(b"mp3 content")

        monkeypatch.setattr("src.engine.config.LIBRARY_ROOT", library_root)
        monkeypatch.setattr("src.engine.config.AUTO_MOVE_ON_APPROVE", True)

        # Write rules so filing_service knows where to put it
        rules_path = tmp_path / "rules.json"
        rules_path.write_text(
            '{"routing_rules":[], "default_rule":"{year}/{artist} - {title}"}'
        )

        # Update the DB source_path to point at our real file
        conn = _connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (str(source_file),),
        )
        conn.execute(
            "UPDATE MediaSources SET ProcessingStatus = 0 WHERE SourceID = 1"
        )
        conn.commit()
        conn.close()

        edit = EditService(populated_db)
        lib = LibraryService(populated_db)

        edit.update_song_scalars(
            1, {"media_name": "Smells Like Teen Spirit (Live)"}
        )

        # File should now be under library_root
        moved = list(library_root.rglob("*.mp3"))
        assert len(moved) == 1, f"Expected 1 file under library_root, got {moved}"
        assert moved[0].read_bytes() == b"mp3 content"
        assert not source_file.exists(), (
            "Source file should be unlinked after move"
        )

        # DB source_path updated
        song = lib.get_song(1)
        assert song.source_path == str(moved[0])

    def test_reviewed_no_auto_move_when_disabled(self, populated_db, tmp_path, monkeypatch):
        """REVIEWED song + AUTO_MOVE_ON_APPROVE=False + scalar save → no move."""
        from src.services.edit_service import EditService
        from src.services.filing_service import FilingService
        from src.engine.config import AUTO_MOVE_ON_APPROVE
        from tests.conftest import _connect

        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        source_file = staging_dir / "Nirvana - Song.mp3"
        source_file.write_bytes(b"unchanged content")

        monkeypatch.setattr("src.engine.config.AUTO_MOVE_ON_APPROVE", False)

        conn = _connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ?, ProcessingStatus = 0 WHERE SourceID = 1",
            (str(source_file),),
        )
        conn.commit()
        conn.close()

        edit = EditService(populated_db)
        edit.update_song_scalars(1, {"year": 1992})

        assert source_file.exists(), "Source file should not be moved when auto-move is disabled"
        assert not list(
            (tmp_path / "library").rglob("*.mp3")
        ), "No file should exist under library_root"

    def test_not_reviewed_no_auto_move_even_when_enabled(self, populated_db, tmp_path, monkeypatch):
        """NOT_REVIEWED song + AUTO_MOVE_ON_APPROVE=True + scalar save → no move."""
        from src.services.edit_service import EditService
        from src.engine.config import AUTO_MOVE_ON_APPROVE
        from tests.conftest import _connect

        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        source_file = staging_dir / "Nirvana - Song.mp3"
        source_file.write_bytes(b"unchanged content")

        monkeypatch.setattr("src.engine.config.AUTO_MOVE_ON_APPROVE", True)

        conn = _connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ?, ProcessingStatus = 1 WHERE SourceID = 1",
            (str(source_file),),
        )
        conn.commit()
        conn.close()

        edit = EditService(populated_db)
        edit.update_song_scalars(1, {"year": 1992})

        assert source_file.exists(), "Source file should not be moved when song is not REVIEWED"
        assert not list(
            (tmp_path / "library").rglob("*.mp3")
        ), "No file should exist under library_root"

    def test_reviewed_file_already_at_target_no_op(self, populated_db, tmp_path, monkeypatch):
        """REVIEWED + AUTO_MOVE=True + source_path already equals computed target → no copy, no unlink."""
        from src.services.edit_service import EditService
        from src.engine.config import AUTO_MOVE_ON_APPROVE
        from tests.conftest import _connect

        monkeypatch.setattr("src.engine.config.AUTO_MOVE_ON_APPROVE", True)

        # Put source directly under library_root/year/artist - title so it IS the target
        library_root = tmp_path / "library"
        library_root.mkdir()
        (library_root / "1991").mkdir()
        perfect_file = (
            library_root / "1991" / "Nirvana - Smells Like Teen Spirit.mp3"
        )
        perfect_file.write_bytes(b"the only copy do not lose this")

        rules_path = tmp_path / "rules.json"
        rules_path.write_text(
            '{"routing_rules":[], "default_rule":"{year}/{artist} - {title}"}'
        )

        conn = _connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ?, ProcessingStatus = 0 WHERE SourceID = 1",
            (str(perfect_file),),
        )
        conn.commit()
        conn.close()

        edit = EditService(populated_db)
        edit.update_song_scalars(1, {"year": 1992})

        assert perfect_file.exists(), (
            "Source file was deleted during same-file auto-move — critical regression"
        )
        assert perfect_file.read_bytes() == b"the only copy do not lose this", (
            "File contents were modified during same-file auto-move"
        )

    def test_auto_move_updates_source_path_to_target(self, populated_db, tmp_path, monkeypatch):
        """After auto-move, DB source_path points to new location, not old staging path."""
        from src.services.edit_service import EditService
        from src.services.library_service import LibraryService
        from src.engine.config import AUTO_MOVE_ON_APPROVE
        from tests.conftest import _connect

        library_root = tmp_path / "library"
        library_root.mkdir()
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        source_file = staging_dir / "Nirvana - Smells Like Teen Spirit.mp3"
        source_file.write_bytes(b"mp3")

        monkeypatch.setattr("src.engine.config.LIBRARY_ROOT", library_root)
        monkeypatch.setattr("src.engine.config.AUTO_MOVE_ON_APPROVE", True)

        rules_path = tmp_path / "rules.json"
        rules_path.write_text(
            '{"routing_rules":[], "default_rule":"{year}/{artist} - {title}"}'
        )

        conn = _connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ?, ProcessingStatus = 0 WHERE SourceID = 1",
            (str(source_file),),
        )
        conn.commit()
        conn.close()

        edit = EditService(populated_db)
        lib = LibraryService(populated_db)

        edit.update_song_scalars(1, {"media_name": "Smells Like Teen Spirit"})

        song = lib.get_song(1)
        new_path = Path(song.source_path)
        assert new_path.parent.parent == library_root, (
            f"source_path should point under library_root, got {song.source_path}"
        )

        publisher = service.get_publisher(10)
        assert (
            publisher.parent_id is None
        ), f"Expected parent_id=None after clear, got {publisher.parent_id}"
        assert (
            publisher.name == "DGC Records"
        ), f"Expected name='DGC Records' unchanged, got '{publisher.name}'"

    def test_set_parent_nonexistent_publisher_raises(self, populated_db):
        """set_publisher_parent on nonexistent publisher should raise LookupError."""
        service = CatalogService(populated_db)
        with pytest.raises(LookupError):
            service.set_publisher_parent(9999, 1)
