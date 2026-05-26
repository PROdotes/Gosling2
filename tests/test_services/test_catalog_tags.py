"""
Tests for CatalogService Tag Methods
=====================================
Covers:
- get_all_tags (directory fetch)
- search_tags (name match)
- get_tag (single fetch)
- get_songs_by_tag (reverse lookup with hydration)

Uses populated_db which has:
    Tags: 1=Grunge/Genre, 2=Energetic/Mood, 3=90s/Era, 4=Electronic/Style, 5=English/Jezik, 6=Alt Rock/Genre, 7=Rock/Genre
    Songs: 1-9 (various)
    MediaSourceTags: Song 1 -> Grunge,Energetic,English; Song 2 -> 90s; Song 4 -> Electronic; Song 9 -> Grunge,Alt Rock
"""

import pytest
from src.services.catalog_service import CatalogService
from src.services.mutation_coordinator import MutationCoordinator
from src.engine.routers.mutation_models import MutationRequest, UpdateTagEntityItem, AddTagItem


class TestGetAllTags:
    def test_returns_all_tags_sorted(self, populated_db):
        """Should return all 7 tags from populated_db, sorted by name."""
        service = CatalogService(populated_db)
        tags = service.get_all_tags()

        assert len(tags) == 7, f"Expected 7 tags, got {len(tags)}"

        # Verify sorted order
        names = [t.name for t in tags]
        expected_order = [
            "90s",
            "Alt Rock",
            "Electronic",
            "Energetic",
            "English",
            "Grunge",
            "Rock",
        ]
        assert names == expected_order, f"Expected {expected_order}, got {names}"

        # Verify complete fields for first tag (90s)
        tag = tags[0]
        assert tag.id == 3, f"Expected id=3, got {tag.id}"
        assert tag.name == "90s", f"Expected '90s', got '{tag.name}'"
        assert tag.category == "Era", f"Expected 'Era', got '{tag.category}'"

    def test_empty_db_returns_empty_list(self, empty_db):
        """Empty database should return empty list."""
        service = CatalogService(empty_db)
        tags = service.get_all_tags()

        assert len(tags) == 0, f"Expected 0 tags in empty db, got {len(tags)}"


class TestSearchTags:
    def test_exact_match_returns_single_result(self, populated_db):
        """Search 'Grunge' should return exactly that tag."""
        service = CatalogService(populated_db)
        tags = service.search_tags("Grunge")

        assert len(tags) == 1, f"Expected 1 result for 'Grunge', got {len(tags)}"

        tag = tags[0]
        assert tag.id == 1, f"Expected id=1, got {tag.id}"
        assert tag.name == "Grunge", f"Expected 'Grunge', got '{tag.name}'"
        assert tag.category == "Genre", f"Expected 'Genre', got '{tag.category}'"

        # Verify Alt Rock is NOT included
        names = [t.name for t in tags]
        assert "Alt Rock" not in names, "'Alt Rock' should not match 'Grunge' search"

    def test_partial_match_returns_matching_tags(self, populated_db):
        """Search 'e' should return tags containing 'e'."""
        service = CatalogService(populated_db)
        tags = service.search_tags("e")

        # Should match: Grunge, Energetic, Electronic, English (4 tags)
        assert len(tags) >= 4, f"Expected at least 4 matches for 'e', got {len(tags)}"

        names = [t.name for t in tags]
        assert "Grunge" in names, "Expected 'Grunge' to match 'e' (contains e)"
        assert "Energetic" in names, "Expected 'Energetic' to match 'e'"
        assert "Electronic" in names, "Expected 'Electronic' to match 'e'"
        assert "English" in names, "Expected 'English' to match 'e'"

    def test_case_insensitive_search(self, populated_db):
        """Search 'GRUNGE' should match 'Grunge'."""
        service = CatalogService(populated_db)
        tags = service.search_tags("GRUNGE")

        assert len(tags) == 1, f"Expected 1 result (case-insensitive), got {len(tags)}"
        assert tags[0].name == "Grunge", f"Expected 'Grunge', got '{tags[0].name}'"

    def test_no_matches_returns_empty_list(self, populated_db):
        """Search for nonexistent term returns empty."""
        service = CatalogService(populated_db)
        tags = service.search_tags("xyz_does_not_exist")

        assert (
            len(tags) == 0
        ), f"Expected 0 results for nonexistent term, got {len(tags)}"


class TestGetTag:
    def test_existing_tag_returns_complete_object(self, populated_db):
        """Tag 1 (Grunge) should return with all fields."""
        service = CatalogService(populated_db)
        tag = service.get_tag(1)

        assert tag is not None, "Expected tag object, got None"
        assert tag.id == 1, f"Expected id=1, got {tag.id}"
        assert tag.name == "Grunge", f"Expected 'Grunge', got '{tag.name}'"
        assert tag.category == "Genre", f"Expected 'Genre', got '{tag.category}'"

    def test_nonexistent_id_returns_none(self, populated_db):
        """Tag 999 doesn't exist, should return None."""
        service = CatalogService(populated_db)
        tag = service.get_tag(999)

        assert tag is None, f"Expected None for nonexistent ID, got {tag}"

    def test_multiple_tags_independently(self, populated_db):
        """Verify multiple tags can be fetched with correct data."""
        service = CatalogService(populated_db)

        # Tag 2: Energetic/Mood
        tag2 = service.get_tag(2)
        assert tag2 is not None, "Expected tag 2 to exist"
        assert tag2.id == 2, f"Expected id=2, got {tag2.id}"
        assert tag2.name == "Energetic", f"Expected 'Energetic', got '{tag2.name}'"
        assert tag2.category == "Mood", f"Expected 'Mood', got '{tag2.category}'"

        # Tag 6: Alt Rock/Genre
        tag6 = service.get_tag(6)
        assert tag6 is not None, "Expected tag 6 to exist"
        assert tag6.id == 6, f"Expected id=6, got {tag6.id}"
        assert tag6.name == "Alt Rock", f"Expected 'Alt Rock', got '{tag6.name}'"
        assert tag6.category == "Genre", f"Expected 'Genre', got '{tag6.category}'"


class TestGetSongsSlimByTag:
    def test_tag_with_single_song_returns_slim_dict(self, populated_db):
        """Tag 3 (90s) is only on Song 2."""
        service = CatalogService(populated_db)
        songs = service.get_songs_slim_by_tag(3)

        assert len(songs) == 1, f"Expected 1 song for Tag 3 (90s), got {len(songs)}"

        song = songs[0]
        assert song["SourceID"] == 2, f"Expected song_id=2, got {song['SourceID']}"
        assert (
            song["MediaName"] == "Everlong"
        ), f"Expected 'Everlong', got '{song['MediaName']}'"

    def test_tag_with_multiple_songs(self, populated_db):
        """Tag 1 (Grunge) is on Song 1 and Song 9."""
        service = CatalogService(populated_db)
        songs = service.get_songs_slim_by_tag(1)

        assert len(songs) == 2, f"Expected 2 songs for Tag 1 (Grunge), got {len(songs)}"

        # Sort by ID for consistent assertion
        songs_sorted = sorted(songs, key=lambda s: s["SourceID"] or 0)

        assert songs_sorted[0]["SourceID"] == 1
        assert songs_sorted[0]["MediaName"] == "Smells Like Teen Spirit"
        
        assert songs_sorted[1]["SourceID"] == 9
        assert songs_sorted[1]["MediaName"] == "Priority Test"

    def test_tag_with_no_songs_returns_empty(self, populated_db):
        """Create a tag with no song links, should return empty."""
        service = CatalogService(populated_db)

        # Insert a tag directly without any MediaSourceTags link
        from src.data.tag_repository import TagRepository

        repo = TagRepository(populated_db)
        with repo._get_connection() as conn:
            conn.execute(
                "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (100, 'Orphan Tag', 'Test')"
            )
            conn.commit()

        songs = service.get_songs_slim_by_tag(100)
        assert len(songs) == 0, f"Expected 0 songs for orphan tag, got {len(songs)}"

    def test_nonexistent_tag_returns_empty(self, populated_db):
        """Tag 999 doesn't exist, should return empty."""
        service = CatalogService(populated_db)
        songs = service.get_songs_slim_by_tag(999)

        assert (
            len(songs) == 0
        ), f"Expected 0 songs for nonexistent tag, got {len(songs)}"


class TestUpdateTag:
    def test_update_tag_success(self, populated_db):
        """Should update tag name and category globally."""
        service = CatalogService(populated_db)
        coord = MutationCoordinator(populated_db)

        coord.apply(MutationRequest(update=[UpdateTagEntityItem(type="tag", id=1, name="Post-Grunge", category="Style")]))

        updated = service.get_tag(1)
        assert updated.name == "Post-Grunge"
        assert updated.category == "Style"

        song1 = service.get_song(1)
        tag1_on_song = next(t for t in song1.tags if t.id == 1)
        assert tag1_on_song.name == "Post-Grunge"
        assert tag1_on_song.category == "Style"

    def test_update_tag_nonexistent_raises_lookup_error(self, populated_db):
        """Should raise LookupError when updating nonexistent tag."""
        coord = MutationCoordinator(populated_db)
        with pytest.raises(LookupError):
            coord.apply(MutationRequest(update=[UpdateTagEntityItem(type="tag", id=999, name="New Name", category="New Category")]))

    def test_add_tag_normalizes_whitespace_but_retains_case(self, populated_db):
        """Duplicate adds with different casing should map to the same tag ID."""
        service = CatalogService(populated_db)
        coord = MutationCoordinator(populated_db)
        song_id = 1

        coord.apply(MutationRequest(add=[AddTagItem(type="tag", song_id=song_id, name="NormalizationTest", category="Category")]))
        song_after_first = service.get_song(song_id)
        t1 = next(t for t in song_after_first.tags if t.name == "NormalizationTest")
        assert t1.name == "NormalizationTest", "Expected original casing to be retained"

        coord.apply(MutationRequest(add=[AddTagItem(type="tag", song_id=song_id, name="NORMALIZATIONtest", category="category")]))
        song_after_second = service.get_song(song_id)
        t2 = next((t for t in song_after_second.tags if t.id == t1.id), None)
        assert t2 is not None, f"Expected tag with id={t1.id} to still exist after NOCASE re-add"
