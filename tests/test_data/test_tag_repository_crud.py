"""
Tests for TagRepository CRUD methods
======================================
add_tag, remove_tag, update_tag

populated_db tags:
  TagID=1: Grunge/Genre    -> Song 1 (primary), Song 9 (not primary)
  TagID=2: Energetic/Mood  -> Song 1
  TagID=3: 90s/Era         -> Song 2
  TagID=4: Electronic/Style -> Song 4
  TagID=5: English/Jezik   -> Song 1
  TagID=6: Alt Rock/Genre  -> Song 9 (primary)
  Song 7: no tags
"""

from src.data.tag_repository import TagRepository


class TestAddTag:
    def test_add_existing_tag_to_song(self, populated_db):
        """Add an existing tag to Song 7 — should create link, not duplicate Tag row."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            result = repo.add_tag(7, "Grunge", "Genre", conn)
            conn.commit()

        assert result.id == 1, f"Expected TagID=1 (existing Grunge), got {result.id}"
        assert result.name == "Grunge", f"Expected name='Grunge', got '{result.name}'"
        assert (
            result.category == "Genre"
        ), f"Expected category='Genre', got '{result.category}'"

        # Verify no duplicate Tag row
        with repo._get_connection() as conn:
            rows = conn.execute(
                "SELECT TagID FROM Tags WHERE TagName = 'Grunge'"
            ).fetchall()
            assert (
                len(rows) == 1
            ), f"Expected 1 Grunge row (no duplicate), got {len(rows)}"

        # Verify link created
        song_tags = repo.get_tags_for_songs([7])
        assert len(song_tags) == 1, f"Expected 1 tag on Song 7, got {len(song_tags)}"
        assert song_tags[0][1].id == 1, f"Expected TagID=1, got {song_tags[0][1].id}"

    def test_add_new_tag_creates_tag_row(self, populated_db):
        """Add a brand-new tag to Song 7 — should create Tag row and link."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            result = repo.add_tag(7, "Shoegaze", "Genre", conn)
            conn.commit()

        assert (
            result.name == "Shoegaze"
        ), f"Expected name='Shoegaze', got '{result.name}'"
        assert (
            result.category == "Genre"
        ), f"Expected category='Genre', got '{result.category}'"
        assert result.id is not None, "Expected id to be set, got None"

        song_tags = repo.get_tags_for_songs([7])
        assert len(song_tags) == 1, f"Expected 1 tag on Song 7, got {len(song_tags)}"
        assert (
            song_tags[0][1].name == "Shoegaze"
        ), f"Expected 'Shoegaze', got '{song_tags[0][1].name}'"

    def test_add_tag_idempotent_on_duplicate(self, populated_db):
        """Adding the same tag twice should not create duplicate MediaSourceTags rows."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_tag(7, "Grunge", "Genre", conn)
            repo.add_tag(7, "Grunge", "Genre", conn)
            conn.commit()

        song_tags = repo.get_tags_for_songs([7])
        grunge_tags = [t for _, t in song_tags if t.name == "Grunge"]
        assert (
            len(grunge_tags) == 1
        ), f"Expected 1 Grunge link (idempotent), got {len(grunge_tags)}"

    def test_add_tag_does_not_affect_other_songs(self, populated_db):
        """Adding a tag to Song 7 should not affect Song 1's tags."""
        repo = TagRepository(populated_db)
        before = repo.get_tags_for_songs([1])

        with repo._get_connection() as conn:
            repo.add_tag(7, "Shoegaze", "Genre", conn)
            conn.commit()

        after = repo.get_tags_for_songs([1])
        assert len(after) == len(
            before
        ), f"Song 1 tag count should not change: expected {len(before)}, got {len(after)}"


class TestRemoveTag:
    def test_remove_tag_deletes_link(self, populated_db):
        """Remove a tag from Song 1 — link should be gone, Tag record should remain."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            repo.remove_tag(1, 1, conn)  # Remove Grunge (TagID=1) from Song 1
            conn.commit()

        song_tags = repo.get_tags_for_songs([1])
        tag_ids = [t.id for _, t in song_tags]
        assert (
            1 not in tag_ids
        ), f"Expected Grunge (TagID=1) to be removed from Song 1, got {tag_ids}"

        # Tag record persists
        tag = repo.get_by_id(1)
        assert (
            tag is not None
        ), "Expected Tag record (TagID=1) to persist after link removal"
        assert tag.name == "Grunge", f"Expected tag name 'Grunge', got '{tag.name}'"

    def test_remove_tag_leaves_other_tags_on_same_song(self, populated_db):
        """Removing Grunge from Song 1 should leave Energetic and English intact."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            repo.remove_tag(1, 1, conn)  # Remove Grunge
            conn.commit()

        song_tags = repo.get_tags_for_songs([1])
        tag_ids = [t.id for _, t in song_tags]
        assert 2 in tag_ids, f"Expected Energetic (TagID=2) to remain, got {tag_ids}"
        assert 5 in tag_ids, f"Expected English (TagID=5) to remain, got {tag_ids}"
        assert (
            len(song_tags) == 2
        ), f"Expected 2 remaining tags on Song 1, got {len(song_tags)}"

    def test_remove_tag_does_not_affect_other_songs(self, populated_db):
        """Removing Grunge from Song 1 should not affect Song 9 which also has Grunge."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            repo.remove_tag(1, 1, conn)
            conn.commit()

        song9_tags = repo.get_tags_for_songs([9])
        tag_ids = [t.id for _, t in song9_tags]
        assert (
            1 in tag_ids
        ), f"Expected Grunge (TagID=1) to remain on Song 9, got {tag_ids}"


class TestUpdateTag:
    def test_update_tag_name(self, populated_db):
        """Update a tag's name — should change TagName in Tags table."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_tag(1, "Grunge Rock", "Genre", conn)
            conn.commit()

        tag = repo.get_by_id(1)
        assert (
            tag.name == "Grunge Rock"
        ), f"Expected name='Grunge Rock', got '{tag.name}'"
        assert (
            tag.category == "Genre"
        ), f"Expected category='Genre', got '{tag.category}'"

    def test_update_tag_category(self, populated_db):
        """Update a tag's category."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_tag(2, "Energetic", "Style", conn)  # Energetic: Mood -> Style
            conn.commit()

        tag = repo.get_by_id(2)
        assert tag.name == "Energetic", f"Expected name='Energetic', got '{tag.name}'"
        assert (
            tag.category == "Style"
        ), f"Expected category='Style', got '{tag.category}'"

    def test_update_tag_is_global(self, populated_db):
        """Updating Grunge (TagID=1) should reflect on all songs that have it."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_tag(1, "Grunge Renamed", "Genre", conn)
            conn.commit()

        # Song 1 has Grunge
        song1_tags = repo.get_tags_for_songs([1])
        grunge = next(t for _, t in song1_tags if t.id == 1)
        assert (
            grunge.name == "Grunge Renamed"
        ), f"Expected 'Grunge Renamed' on Song 1, got '{grunge.name}'"

        # Song 9 also has Grunge
        song9_tags = repo.get_tags_for_songs([9])
        grunge9 = next(t for _, t in song9_tags if t.id == 1)
        assert (
            grunge9.name == "Grunge Renamed"
        ), f"Expected 'Grunge Renamed' on Song 9, got '{grunge9.name}'"

    def test_update_tag_does_not_affect_other_tags(self, populated_db):
        """Updating Grunge should not affect Energetic."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_tag(1, "Grunge Renamed", "Genre", conn)
            conn.commit()

        tag2 = repo.get_by_id(2)
        assert (
            tag2.name == "Energetic"
        ), f"Expected 'Energetic' unchanged, got '{tag2.name}'"
        assert (
            tag2.category == "Mood"
        ), f"Expected category='Mood' unchanged, got '{tag2.category}'"
