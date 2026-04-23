"""
Tests for TagRepository Read Operations
========================================
Covers:
- get_tags_for_songs (batch M2M fetch)
- get_all (directory fetch)
- search (name match)
- get_by_id (single fetch)
- get_song_ids_by_tag (reverse lookup)
- _row_to_tag (mapper)

Uses populated_db which has:
    Tags: 1=Grunge/Genre, 2=Energetic/Mood, 3=90s/Era, 4=Electronic/Style, 5=English/Jezik, 6=Alt Rock/Genre, 7=Rock/Genre
    MediaSourceTags: Song 1 -> Grunge,Energetic,English; Song 2 -> 90s; Song 4 -> Electronic; Song 9 -> Grunge,Alt Rock
"""

from src.data.tag_repository import TagRepository


class TestGetTagsForSongs:
    def test_single_song_multiple_tags_returns_all(self, populated_db):
        """Song 1 has 3 tags: Grunge, Energetic, English."""
        repo = TagRepository(populated_db)
        result = repo.get_tags_for_songs([1])

        assert len(result) == 3, f"Expected 3 tags for Song 1, got {len(result)}"

        # All results should be for song_id=1
        for song_id, tag in result:
            assert song_id == 1, f"Expected song_id=1, got {song_id}"

        # Extract tag names and sort for consistent assertion
        tag_names = sorted([t.name for _, t in result])
        assert tag_names == [
            "Energetic",
            "English",
            "Grunge",
        ], f"Expected ['Energetic', 'English', 'Grunge'], got {tag_names}"

        # Verify complete fields for each tag
        tag_map = {t.name: t for _, t in result}

        grunge = tag_map["Grunge"]
        assert grunge.id == 1, f"Expected id=1, got {grunge.id}"
        assert grunge.name == "Grunge", f"Expected 'Grunge', got '{grunge.name}'"
        assert grunge.category == "Genre", f"Expected 'Genre', got '{grunge.category}'"
        assert (
            grunge.is_primary is True
        ), f"Expected is_primary=True (Grunge is primary genre for SLTS), got {grunge.is_primary}"

        energetic = tag_map["Energetic"]
        assert energetic.id == 2, f"Expected id=2, got {energetic.id}"
        assert (
            energetic.name == "Energetic"
        ), f"Expected 'Energetic', got '{energetic.name}'"
        assert (
            energetic.category == "Mood"
        ), f"Expected 'Mood', got '{energetic.category}'"
        assert (
            energetic.is_primary is False
        ), f"Expected is_primary=False, got {energetic.is_primary}"

        english = tag_map["English"]
        assert english.id == 5, f"Expected id=5, got {english.id}"
        assert english.name == "English", f"Expected 'English', got '{english.name}'"
        assert (
            english.category == "Jezik"
        ), f"Expected 'Jezik', got '{english.category}'"
        assert (
            english.is_primary is False
        ), f"Expected is_primary=False, got {english.is_primary}"

    def test_multiple_songs_returns_grouped_correctly(self, populated_db):
        """Song 1 has 3 tags, Song 2 has 1 tag, Song 4 has 1 tag."""
        repo = TagRepository(populated_db)
        result = repo.get_tags_for_songs([1, 2, 4])

        # Total of 6 tag links
        assert len(result) == 6, f"Expected 6 total tag links, got {len(result)}"

        # Group by song_id
        tags_by_song = {}
        for song_id, tag in result:
            tags_by_song.setdefault(song_id, []).append(tag)

        # Song 1: 3 tags
        assert (
            len(tags_by_song[1]) == 3
        ), f"Expected 3 tags for Song 1, got {len(tags_by_song[1])}"
        song1_names = sorted([t.name for t in tags_by_song[1]])
        assert song1_names == [
            "Energetic",
            "English",
            "Grunge",
        ], f"Expected ['Energetic', 'English', 'Grunge'], got {song1_names}"

        # Song 2: 1 tag
        assert (
            len(tags_by_song[2]) == 2
        ), f"Expected 2 tags for Song 2, got {len(tags_by_song[2])}"
        assert (
            tags_by_song[2][0].name == "90s"
        ), f"Expected '90s', got '{tags_by_song[2][0].name}'"
        assert (
            tags_by_song[2][0].category == "Era"
        ), f"Expected 'Era', got '{tags_by_song[2][0].category}'"

        # Song 4: 1 tag
        assert (
            len(tags_by_song[4]) == 1
        ), f"Expected 1 tag for Song 4, got {len(tags_by_song[4])}"
        assert (
            tags_by_song[4][0].name == "Electronic"
        ), f"Expected 'Electronic', got '{tags_by_song[4][0].name}'"
        assert (
            tags_by_song[4][0].category == "Style"
        ), f"Expected 'Style', got '{tags_by_song[4][0].category}'"

    def test_song_with_no_tags_excluded_from_results(self, populated_db):
        """Song 3 has no tags, should not appear in results."""
        repo = TagRepository(populated_db)
        result = repo.get_tags_for_songs([3])

        assert len(result) == 0, f"Expected 0 tags for Song 3, got {len(result)}"

    def test_empty_list_returns_empty_results(self, populated_db):
        """Passing empty list should return empty results."""
        repo = TagRepository(populated_db)
        result = repo.get_tags_for_songs([])

        assert (
            len(result) == 0
        ), f"Expected 0 results for empty input, got {len(result)}"

    def test_nonexistent_song_id_returns_empty(self, populated_db):
        """Song 999 doesn't exist, should return empty."""
        repo = TagRepository(populated_db)
        result = repo.get_tags_for_songs([999])

        assert (
            len(result) == 0
        ), f"Expected 0 tags for nonexistent song, got {len(result)}"

    def test_partial_results_skip_missing_songs(self, populated_db):
        """Mix of existing and nonexistent songs returns only found tags."""
        repo = TagRepository(populated_db)
        result = repo.get_tags_for_songs([1, 999, 2])

        # Should get 5 tags: 3 from Song 1, 2 from Song 2
        assert len(result) == 5, f"Expected 5 tags (3+2), got {len(result)}"

        song_ids = set([s_id for s_id, _ in result])
        assert song_ids == {1, 2}, f"Expected song_ids {{1, 2}}, got {song_ids}"
        assert 999 not in song_ids, "Song 999 should not be in results"


class TestGetAll:
    def test_returns_all_tags_sorted_by_name(self, populated_db):
        """Should return all 6 tags, sorted case-insensitively."""
        repo = TagRepository(populated_db)
        result = repo.get_all()

        assert len(result) == 7, f"Expected 7 tags, got {len(result)}"

        # Verify sorted order (case-insensitive)
        names = [t.name for t in result]
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
        tag = result[0]
        assert tag.id == 3, f"Expected id=3, got {tag.id}"
        assert tag.name == "90s", f"Expected '90s', got '{tag.name}'"
        assert tag.category == "Era", f"Expected 'Era', got '{tag.category}'"
        assert (
            tag.is_primary is False
        ), f"Expected is_primary=False (not in row), got {tag.is_primary}"

    def test_empty_db_returns_empty_list(self, empty_db):
        """Empty database should return empty list."""
        repo = TagRepository(empty_db)
        result = repo.get_all()

        assert len(result) == 0, f"Expected 0 tags in empty db, got {len(result)}"


class TestSearch:
    def test_exact_match_returns_single_result(self, populated_db):
        """Search 'Grunge' should return exactly that tag."""
        repo = TagRepository(populated_db)
        result = repo.search("Grunge")

        assert len(result) == 1, f"Expected 1 result for 'Grunge', got {len(result)}"

        tag = result[0]
        assert tag.id == 1, f"Expected id=1, got {tag.id}"
        assert tag.name == "Grunge", f"Expected 'Grunge', got '{tag.name}'"
        assert tag.category == "Genre", f"Expected 'Genre', got '{tag.category}'"
        assert (
            tag.is_primary is False
        ), f"Expected is_primary=False, got {tag.is_primary}"

        # Verify Alt Rock is NOT included
        names = [t.name for t in result]
        assert "Alt Rock" not in names, "'Alt Rock' should not match 'Grunge' search"

    def test_partial_match_returns_matching_tags(self, populated_db):
        """Search 'e' should return tags containing 'e'."""
        repo = TagRepository(populated_db)
        result = repo.search("e")

        # Should match: Grunge, Energetic, Electronic, English (4 tags)
        assert (
            len(result) >= 4
        ), f"Expected at least 4 matches for 'e', got {len(result)}"

        names = [t.name for t in result]
        assert "Grunge" in names, "Expected 'Grunge' to match 'e' (contains e)"
        assert "Energetic" in names, "Expected 'Energetic' to match 'e'"
        assert "Electronic" in names, "Expected 'Electronic' to match 'e'"
        assert "English" in names, "Expected 'English' to match 'e'"

    def test_case_insensitive_search(self, populated_db):
        """Search 'GRUNGE' should match 'Grunge'."""
        repo = TagRepository(populated_db)
        result = repo.search("GRUNGE")

        assert (
            len(result) == 1
        ), f"Expected 1 result (case-insensitive), got {len(result)}"
        assert result[0].name == "Grunge", f"Expected 'Grunge', got '{result[0].name}'"

    def test_no_matches_returns_empty_list(self, populated_db):
        """Search for nonexistent term returns empty."""
        repo = TagRepository(populated_db)
        result = repo.search("xyz_does_not_exist")

        assert (
            len(result) == 0
        ), f"Expected 0 results for nonexistent term, got {len(result)}"

    def test_results_sorted_by_name(self, populated_db):
        """Results should be sorted alphabetically."""
        repo = TagRepository(populated_db)
        result = repo.search("e")

        names = [t.name for t in result]
        sorted_names = sorted(names, key=str.lower)
        assert (
            names == sorted_names
        ), f"Expected sorted names {sorted_names}, got {names}"


class TestGetById:
    def test_existing_tag_returns_complete_object(self, populated_db):
        """Tag 1 (Grunge) should return with all fields."""
        repo = TagRepository(populated_db)
        tag = repo.get_by_id(1)

        assert tag is not None, "Expected tag object, got None"
        assert tag.id == 1, f"Expected id=1, got {tag.id}"
        assert tag.name == "Grunge", f"Expected 'Grunge', got '{tag.name}'"
        assert tag.category == "Genre", f"Expected 'Genre', got '{tag.category}'"
        assert (
            tag.is_primary is False
        ), f"Expected is_primary=False (not in row keys), got {tag.is_primary}"

    def test_nonexistent_id_returns_none(self, populated_db):
        """Tag 999 doesn't exist, should return None."""
        repo = TagRepository(populated_db)
        tag = repo.get_by_id(999)

        assert tag is None, f"Expected None for nonexistent ID, got {tag}"

    def test_multiple_tags_independently(self, populated_db):
        """Verify multiple tags can be fetched with correct data."""
        repo = TagRepository(populated_db)

        # Tag 2: Energetic/Mood
        tag2 = repo.get_by_id(2)
        assert tag2 is not None, "Expected tag 2 to exist"
        assert tag2.id == 2, f"Expected id=2, got {tag2.id}"
        assert tag2.name == "Energetic", f"Expected 'Energetic', got '{tag2.name}'"
        assert tag2.category == "Mood", f"Expected 'Mood', got '{tag2.category}'"

        # Tag 6: Alt Rock/Genre
        tag6 = repo.get_by_id(6)
        assert tag6 is not None, "Expected tag 6 to exist"
        assert tag6.id == 6, f"Expected id=6, got {tag6.id}"
        assert tag6.name == "Alt Rock", f"Expected 'Alt Rock', got '{tag6.name}'"
        assert tag6.category == "Genre", f"Expected 'Genre', got '{tag6.category}'"


class TestGetSongIdsByTag:
    def test_tag_with_single_song_returns_one_id(self, populated_db):
        """Tag 3 (90s) is only on Song 2."""
        repo = TagRepository(populated_db)
        song_ids = repo.get_song_ids_by_tag(3)

        assert len(song_ids) == 1, f"Expected 1 song for Tag 3, got {len(song_ids)}"
        assert song_ids[0] == 2, f"Expected song_id=2, got {song_ids[0]}"

    def test_tag_with_multiple_songs_returns_all(self, populated_db):
        """Tag 1 (Grunge) is on Song 1 and Song 9."""
        repo = TagRepository(populated_db)
        song_ids = repo.get_song_ids_by_tag(1)

        assert (
            len(song_ids) == 2
        ), f"Expected 2 songs for Tag 1 (Grunge), got {len(song_ids)}"
        assert 1 in song_ids, "Expected Song 1 in results"
        assert 9 in song_ids, "Expected Song 9 in results"

        # Verify other songs are NOT included
        assert 2 not in song_ids, "Song 2 should not have Grunge tag"
        assert 3 not in song_ids, "Song 3 should not have Grunge tag"

    def test_tag_with_no_songs_returns_empty(self, populated_db):
        """Create a tag with no song links, should return empty."""
        repo = TagRepository(populated_db)

        # Insert a tag directly without any MediaSourceTags link
        with repo._get_connection() as conn:
            conn.execute(
                "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (100, 'Orphan Tag', 'Test')"
            )
            conn.commit()

        song_ids = repo.get_song_ids_by_tag(100)
        assert (
            len(song_ids) == 0
        ), f"Expected 0 songs for orphan tag, got {len(song_ids)}"

    def test_nonexistent_tag_id_returns_empty(self, populated_db):
        """Tag 999 doesn't exist, should return empty."""
        repo = TagRepository(populated_db)
        song_ids = repo.get_song_ids_by_tag(999)

        assert (
            len(song_ids) == 0
        ), f"Expected 0 songs for nonexistent tag, got {len(song_ids)}"


class TestRowToTag:
    def test_all_fields_present(self, populated_db):
        """Map a complete row with IsPrimary=1."""
        repo = TagRepository(populated_db)
        mock_row = {
            "TagID": 42,
            "TagName": "Test Tag",
            "TagCategory": "Test Category",
            "IsPrimary": 1,
        }

        tag = repo._row_to_tag(mock_row)

        assert tag.id == 42, f"Expected id=42, got {tag.id}"
        assert tag.name == "Test Tag", f"Expected 'Test Tag', got '{tag.name}'"
        assert (
            tag.category == "Test Category"
        ), f"Expected 'Test Category', got '{tag.category}'"
        assert (
            tag.is_primary is True
        ), f"Expected is_primary=True (1→True), got {tag.is_primary}"

    def test_is_primary_false(self, populated_db):
        """Map row with IsPrimary=0."""
        repo = TagRepository(populated_db)
        mock_row = {
            "TagID": 43,
            "TagName": "Secondary Tag",
            "TagCategory": "Mood",
            "IsPrimary": 0,
        }

        tag = repo._row_to_tag(mock_row)

        assert tag.id == 43, f"Expected id=43, got {tag.id}"
        assert (
            tag.is_primary is False
        ), f"Expected is_primary=False (0→False), got {tag.is_primary}"

    def test_is_primary_missing_defaults_false(self, populated_db):
        """If IsPrimary not in row keys, default to False."""
        repo = TagRepository(populated_db)
        mock_row = {
            "TagID": 44,
            "TagName": "No Primary Field",
            "TagCategory": "Genre",
        }

        tag = repo._row_to_tag(mock_row)

        assert tag.id == 44, f"Expected id=44, got {tag.id}"
        assert (
            tag.is_primary is False
        ), f"Expected is_primary=False (missing key), got {tag.is_primary}"

    def test_category_can_be_none(self, populated_db):
        """TagCategory is nullable in schema."""
        repo = TagRepository(populated_db)
        mock_row = {
            "TagID": 45,
            "TagName": "No Category",
            "TagCategory": None,
            "IsPrimary": 0,
        }

        tag = repo._row_to_tag(mock_row)

        assert tag.id == 45, f"Expected id=45, got {tag.id}"
        assert tag.category is None, f"Expected None for category, got {tag.category}"
