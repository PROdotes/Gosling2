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

from src.services.catalog_service import CatalogService


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


class TestGetTagSongs:
    def test_tag_with_single_song_returns_hydrated_song(self, populated_db):
        """Tag 3 (90s) is only on Song 2."""
        service = CatalogService(populated_db)
        songs = service.get_songs_by_tag(3)

        assert len(songs) == 1, f"Expected 1 song for Tag 3 (90s), got {len(songs)}"

        song = songs[0]
        assert song.id == 2, f"Expected song_id=2, got {song.id}"
        assert (
            song.media_name == "Everlong"
        ), f"Expected 'Everlong', got '{song.media_name}'"
        assert (
            song.duration_ms == 240000
        ), f"Expected 240000ms (240s), got {song.duration_ms}"
        assert (
            song.source_path == "/path/2"
        ), f"Expected '/path/2', got '{song.source_path}'"
        assert (
            song.audio_hash is None
        ), f"Expected None (Song 2 has no hash), got '{song.audio_hash}'"
        assert song.year == 1997, f"Expected 1997, got {song.year}"
        assert song.is_active is True, f"Expected True, got {song.is_active}"
        assert song.processing_status == 0, f"Expected 0, got {song.processing_status}"

        # Verify tags are hydrated (Song 2 has only "90s" tag)
        assert len(song.tags) == 2, f"Expected 2 tags on Song 2 (90s, Rock), got {len(song.tags)}"
        assert (
            song.tags[0].name == "90s"
        ), f"Expected '90s' tag, got '{song.tags[0].name}'"

    def test_tag_with_multiple_songs_returns_all_hydrated(self, populated_db):
        """Tag 1 (Grunge) is on Song 1 and Song 9."""
        service = CatalogService(populated_db)
        songs = service.get_songs_by_tag(1)

        assert len(songs) == 2, f"Expected 2 songs for Tag 1 (Grunge), got {len(songs)}"

        # Sort by ID for consistent assertion (using or 0 to satisfy Pyright)
        songs_sorted = sorted(songs, key=lambda s: s.id or 0)

        # Song 1: Smells Like Teen Spirit
        song1 = songs_sorted[0]
        assert song1.id == 1, f"Expected song_id=1, got {song1.id}"
        assert (
            song1.media_name == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{song1.media_name}'"
        assert (
            song1.duration_ms == 200000
        ), f"Expected 200000ms (200s), got {song1.duration_ms}"
        assert (
            song1.source_path == "/path/1"
        ), f"Expected '/path/1', got '{song1.source_path}'"
        assert (
            song1.audio_hash == "hash_1"
        ), f"Expected 'hash_1', got '{song1.audio_hash}'"
        assert song1.year == 1991, f"Expected 1991, got {song1.year}"
        assert song1.is_active is True, f"Expected True, got {song1.is_active}"
        assert (
            song1.processing_status == 0
        ), f"Expected 0, got {song1.processing_status}"

        # Verify Song 1 has 3 tags: Grunge, Energetic, English
        assert len(song1.tags) == 3, f"Expected 3 tags on Song 1, got {len(song1.tags)}"
        song1_tag_names = sorted([t.name for t in song1.tags])
        assert song1_tag_names == [
            "Energetic",
            "English",
            "Grunge",
        ], f"Expected ['Energetic', 'English', 'Grunge'], got {song1_tag_names}"

        # Song 9: Priority Test
        song9 = songs_sorted[1]
        assert song9.id == 9, f"Expected song_id=9, got {song9.id}"
        assert (
            song9.media_name == "Priority Test"
        ), f"Expected 'Priority Test', got '{song9.media_name}'"
        assert (
            song9.duration_ms == 100000
        ), f"Expected 100000ms (100s), got {song9.duration_ms}"
        assert (
            song9.source_path == "/path/9"
        ), f"Expected '/path/9', got '{song9.source_path}'"
        assert (
            song9.audio_hash is None
        ), f"Expected None (Song 9 has no hash), got '{song9.audio_hash}'"
        assert (
            song9.year is None
        ), f"Expected None (Song 9 has no year), got {song9.year}"
        assert song9.is_active is True, f"Expected True, got {song9.is_active}"
        assert (
            song9.processing_status == 1
        ), f"Expected 1, got {song9.processing_status}"

        # Verify Song 9 has 2 tags: Grunge, Alt Rock
        assert len(song9.tags) == 2, f"Expected 2 tags on Song 9, got {len(song9.tags)}"
        song9_tag_names = sorted([t.name for t in song9.tags])
        assert song9_tag_names == [
            "Alt Rock",
            "Grunge",
        ], f"Expected ['Alt Rock', 'Grunge'], got {song9_tag_names}"

        # Verify other songs are NOT included
        returned_ids = [s.id for s in songs]
        assert 2 not in returned_ids, "Song 2 should not have Grunge tag"
        assert 3 not in returned_ids, "Song 3 should not have Grunge tag"
        assert 4 not in returned_ids, "Song 4 should not have Grunge tag"

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

        songs = service.get_songs_by_tag(100)
        assert len(songs) == 0, f"Expected 0 songs for orphan tag, got {len(songs)}"

    def test_nonexistent_tag_returns_empty(self, populated_db):
        """Tag 999 doesn't exist, should return empty."""
        service = CatalogService(populated_db)
        songs = service.get_songs_by_tag(999)

        assert (
            len(songs) == 0
        ), f"Expected 0 songs for nonexistent tag, got {len(songs)}"

    def test_songs_include_credits_and_albums(self, populated_db):
        """Verify songs returned have credits and albums hydrated."""
        service = CatalogService(populated_db)
        songs = service.get_songs_by_tag(1)  # Tag 1 (Grunge) -> Song 1, 9

        # Song 1 should have credits and albums
        song1 = next((s for s in songs if s.id == 1), None)
        assert song1 is not None, "Expected Song 1 in results"

        # Credits check (Song 1 has Nirvana as Performer)
        assert (
            len(song1.credits) >= 1
        ), f"Expected at least 1 credit on Song 1, got {len(song1.credits)}"
        nirvana_credit = next(
            (c for c in song1.credits if c.display_name == "Nirvana"), None
        )
        assert nirvana_credit is not None, "Expected Nirvana credit on Song 1"
        assert (
            nirvana_credit.role_name == "Performer"
        ), f"Expected role_name='Performer', got '{nirvana_credit.role_name}'"

        # Albums check (Song 1 is on "Nevermind")
        assert (
            len(song1.albums) >= 1
        ), f"Expected at least 1 album on Song 1, got {len(song1.albums)}"
        nevermind = next(
            (a for a in song1.albums if a.album_title == "Nevermind"), None
        )
        assert nevermind is not None, "Expected 'Nevermind' album on Song 1"


class TestUpdateTag:
    def test_update_tag_success(self, populated_db):
        """Should update tag name and category globally."""
        service = CatalogService(populated_db)
        # Tag 1: Grunge / Genre
        service.update_tag(1, "Post-Grunge", "Style")

        updated = service.get_tag(1)
        assert updated.name == "Post-Grunge"
        assert updated.category == "Style"

        # Verify it updated on linked songs
        song1 = service.get_song(1)
        tag1_on_song = next(t for t in song1.tags if t.id == 1)
        assert tag1_on_song.name == "Post-Grunge"
        assert tag1_on_song.category == "Style"

    def test_update_tag_nonexistent_raises_lookup_error(self, populated_db):
        """Should raise LookupError when updating nonexistent tag."""
        service = CatalogService(populated_db)
        try:
            service.update_tag(999, "New Name", "New Category")
            assert False, "Expected LookupError"
        except LookupError:
            pass

    def test_add_tag_normalizes_whitespace_but_retains_case(self, populated_db):
        """Should merge '  NormalizationTest  ' and 'NORMALIZATIONtest' while retaining original record casing."""
        service = CatalogService(populated_db)
        song_id = 1

        # 1. Add with specific case
        t1 = service.add_song_tag(song_id, "NormalizationTest", "Category")
        assert t1.name == "NormalizationTest", "Expected original casing to be retained"

        # 2. Add with different case: should merge to same ID
        t2 = service.add_song_tag(song_id, "  NORMALIZATIONtest  ", "  category  ")
        assert (
            t1.id == t2.id
        ), f"Expected same ID (NOCASE match), got {t1.id} and {t2.id}"
