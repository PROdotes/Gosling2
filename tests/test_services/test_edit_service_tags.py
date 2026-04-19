import pytest
from src.services.edit_service import EditService
from src.services.library_service import LibraryService


class TestSetPrimarySongTag:
    def test_valid_genre_tag_sets_primary(self, populated_db):
        """Should promote the specified genre tag and demote others."""
        edit_service = EditService(populated_db)
        lib_service = LibraryService(populated_db)

        # Baseline: Song 9 has Grunge(id=1, is_primary=False) and Alt Rock(id=6, is_primary=False) originally
        # In populated_db none might be primary yet. Let's not assert the baseline is_primary, but set it explicitly or just use the current state.
        baseline = lib_service.get_song(9)
        # Actually in test_data/test_tag_repository_write.py: test_set_primary_tag_updates_single_tag:
        # "Song 9 has 2 genres: Grunge (id=1, primary?), Alt Rock (id=6)"
        # We can just check it has both tags.
        assert next((t for t in baseline.tags if t.id == 1), None) is not None
        assert next((t for t in baseline.tags if t.id == 6), None) is not None

        tag = edit_service.set_primary_song_tag(9, 6)

        # Assert returned object
        assert tag is not None, "Expected returned tag, got None"
        assert tag.id == 6, f"Expected id=6, got {tag.id}"
        assert tag.name == "Alt Rock", f"Expected 'Alt Rock', got '{tag.name}'"
        assert tag.category == "Genre", f"Expected 'Genre', got '{tag.category}'"
        assert tag.is_primary is True, f"Expected is_primary=True, got {tag.is_primary}"

        # Assert persisted state via LibraryService
        song = lib_service.get_song(9)
        alt_rock = next((t for t in song.tags if t.id == 6), None)
        grunge = next((t for t in song.tags if t.id == 1), None)

        assert alt_rock is not None, "Expected Alt Rock tag on Song 9"
        assert alt_rock.is_primary is True, "Expected Alt Rock to be primary"
        assert grunge is not None, "Expected Grunge tag on Song 9"
        assert grunge.is_primary is False, "Expected Grunge to be demoted"

    def test_invalid_song_id_raises_lookup_error(self, populated_db):
        """Should raise LookupError when song ID does not exist."""
        edit_service = EditService(populated_db)

        with pytest.raises(LookupError) as exc_info:
            edit_service.set_primary_song_tag(999, 1)

        assert "not found" in str(exc_info.value).lower()

    def test_invalid_tag_id_raises_value_error(self, populated_db):
        """Should raise ValueError when tag ID does not exist, per EditService check."""
        edit_service = EditService(populated_db)

        with pytest.raises(ValueError) as exc_info:
            edit_service.set_primary_song_tag(1, 999)

        assert "Only Genre tags can be primary" in str(exc_info.value)

    def test_non_genre_tag_raises_value_error(self, populated_db):
        """Should raise ValueError when the tag category is not Genre."""
        edit_service = EditService(populated_db)
        lib_service = LibraryService(populated_db)

        # Song 4 has Electronic (id=4, Style)
        with pytest.raises(ValueError) as exc_info:
            edit_service.set_primary_song_tag(4, 4)

        assert "Only Genre tags can be primary" in str(exc_info.value)

        # Verify state unchanged
        song = lib_service.get_song(4)
        electronic = next((t for t in song.tags if t.id == 4), None)
        assert (
            electronic.is_primary is False
        ), "Expected Electronic to remain non-primary"

    def test_unlinked_genre_tag_raises_lookup_error(self, populated_db):
        """Should raise LookupError when tag exists but is not linked to the song."""
        edit_service = EditService(populated_db)
        lib_service = LibraryService(populated_db)

        # Song 4 has Electronic (Style), but not Grunge (Genre, id=1)
        with pytest.raises(LookupError) as exc_info:
            edit_service.set_primary_song_tag(4, 1)

        assert "Link between song 4 and tag 1 not found" in str(exc_info.value)

        # Verify state unchanged
        song = lib_service.get_song(4)
        grunge = next((t for t in song.tags if t.id == 1), None)
        assert grunge is None, "Expected Grunge to remain unlinked"
