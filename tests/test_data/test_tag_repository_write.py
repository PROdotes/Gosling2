"""
Tests for TagRepository.insert_tags (RED phase)
================================================
Verifies get-or-create logic for Tags table and link insertion into MediaSourceTags.
Uses populated_db which already has:
    Tags: 1=Grunge/Genre, 2=Energetic/Mood, 3=90s/Era, 4=Electronic/Style, 5=English/Jezik, 6=Alt Rock/Genre
    Songs: 1-9 (various)
    MediaSourceTags: Song 1 -> Grunge,Energetic,English; Song 2 -> 90s; Song 4 -> Electronic; Song 9 -> Grunge,Alt Rock
"""

import sqlite3
from src.data.tag_repository import TagRepository
from src.models.domain import Tag


class TestInsertTags:
    def test_insert_two_new_tags_creates_tag_rows_and_links(self, populated_db):
        """Insert 2 brand-new tags onto Song 7 (Hollow Song, currently has no tags)."""
        repo = TagRepository(populated_db)

        tags = [
            Tag(name="Ambient", category="Genre"),
            Tag(name="Chill", category="Mood"),
        ]

        with repo._get_connection() as conn:
            repo.insert_tags(7, tags, conn)
            conn.commit()

        # Verify Tags table has the new entries
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row_ambient = conn.execute(
                "SELECT TagID, TagName, TagCategory FROM Tags WHERE TagName = 'Ambient'"
            ).fetchone()
            assert row_ambient is not None, "Expected 'Ambient' tag row to exist"
            assert (
                row_ambient["TagName"] == "Ambient"
            ), f"Expected 'Ambient', got '{row_ambient['TagName']}'"
            assert (
                row_ambient["TagCategory"] == "Genre"
            ), f"Expected 'Genre', got '{row_ambient['TagCategory']}'"

            row_chill = conn.execute(
                "SELECT TagID, TagName, TagCategory FROM Tags WHERE TagName = 'Chill'"
            ).fetchone()
            assert row_chill is not None, "Expected 'Chill' tag row to exist"
            assert (
                row_chill["TagName"] == "Chill"
            ), f"Expected 'Chill', got '{row_chill['TagName']}'"
            assert (
                row_chill["TagCategory"] == "Mood"
            ), f"Expected 'Mood', got '{row_chill['TagCategory']}'"

        # Verify MediaSourceTags links
        result = repo.get_tags_for_songs([7])
        assert len(result) == 2, f"Expected 2 tags on Song 7, got {len(result)}"

        tag_names = sorted([t.name for _, t in result])
        assert tag_names == [
            "Ambient",
            "Chill",
        ], f"Expected ['Ambient', 'Chill'], got {tag_names}"

    def test_insert_existing_tag_reuses_tag_id(self, populated_db):
        """Insert 'Grunge' (already TagID=1) onto Song 3 — should reuse, not duplicate."""
        repo = TagRepository(populated_db)

        tags = [Tag(name="Grunge", category="Genre")]

        with repo._get_connection() as conn:
            repo.insert_tags(3, tags, conn)
            conn.commit()

        # Verify no duplicate Tag row
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT TagID FROM Tags WHERE TagName = 'Grunge'"
            ).fetchall()
            assert (
                len(rows) == 1
            ), f"Expected 1 'Grunge' tag row (reused), got {len(rows)}"
            assert (
                rows[0]["TagID"] == 1
            ), f"Expected TagID=1 (original), got {rows[0]['TagID']}"

        # Verify link was created
        result = repo.get_tags_for_songs([3])
        assert len(result) == 1, f"Expected 1 tag on Song 3, got {len(result)}"
        assert (
            result[0][1].name == "Grunge"
        ), f"Expected 'Grunge', got '{result[0][1].name}'"

    def test_insert_empty_list_is_noop(self, populated_db):
        """Passing empty list should not crash or create any rows."""
        repo = TagRepository(populated_db)

        # Song 7 has no tags before
        before = repo.get_tags_for_songs([7])
        assert len(before) == 0, f"Expected 0 tags on Song 7 before, got {len(before)}"

        with repo._get_connection() as conn:
            repo.insert_tags(7, [], conn)
            conn.commit()

        after = repo.get_tags_for_songs([7])
        assert (
            len(after) == 0
        ), f"Expected 0 tags on Song 7 after empty insert, got {len(after)}"

    def test_insert_preserves_is_primary_flag(self, populated_db):
        """Tags with is_primary=True should persist that flag in MediaSourceTags."""
        repo = TagRepository(populated_db)

        tags = [
            Tag(name="Rock", category="Genre", is_primary=True),
            Tag(name="Live", category="Style", is_primary=False),
        ]

        with repo._get_connection() as conn:
            repo.insert_tags(7, tags, conn)
            conn.commit()

        result = repo.get_tags_for_songs([7])
        assert len(result) == 2, f"Expected 2 tags on Song 7, got {len(result)}"

        tag_map = {t.name: t for _, t in result}
        assert (
            tag_map["Rock"].is_primary is True
        ), f"Expected Rock.is_primary=True, got {tag_map['Rock'].is_primary}"
        assert (
            tag_map["Live"].is_primary is False
        ), f"Expected Live.is_primary=False, got {tag_map['Live'].is_primary}"

    def test_insert_case_insensitive_reuse(self, populated_db):
        """'grunge' (lowercase) should reuse existing 'Grunge' tag (TagID=1)."""
        repo = TagRepository(populated_db)

        tags = [Tag(name="grunge", category="Genre")]

        with repo._get_connection() as conn:
            repo.insert_tags(3, tags, conn)
            conn.commit()

        # Should still be only 1 Grunge row
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT TagID FROM Tags WHERE TagName = 'Grunge' COLLATE UTF8_NOCASE"
            ).fetchall()
            assert (
                len(rows) == 1
            ), f"Expected 1 tag row for Grunge (case-insensitive reuse), got {len(rows)}"

    def test_same_name_different_category_creates_separate_tags(self, populated_db):
        """'Jazz' as Genre and 'Jazz' as Mood should be two different tag rows."""
        repo = TagRepository(populated_db)

        tags_song3 = [Tag(name="Jazz", category="Genre")]
        tags_song4 = [Tag(name="Jazz", category="Mood")]

        with repo._get_connection() as conn:
            repo.insert_tags(3, tags_song3, conn)
            repo.insert_tags(4, tags_song4, conn)
            conn.commit()

        # Should be 2 separate tag rows
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT TagID, TagCategory FROM Tags WHERE TagName = 'Jazz'"
            ).fetchall()
            assert (
                len(rows) == 2
            ), f"Expected 2 'Jazz' tag rows (different categories), got {len(rows)}"
            categories = sorted([r["TagCategory"] for r in rows])
            assert categories == [
                "Genre",
                "Mood",
            ], f"Expected ['Genre', 'Mood'], got {categories}"
