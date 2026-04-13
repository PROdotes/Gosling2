"""
Tests for CatalogService orphan deletion — Tags (Step 1)
=========================================================
delete_unlinked_tags(tag_ids: List[int]) -> int

populated_db tags:
  TagID=1: Grunge/Genre    -> Song 1 (primary), Song 9 (not primary)
  TagID=2: Energetic/Mood  -> Song 1
  TagID=3: 90s/Era         -> Song 2
  TagID=4: Electronic/Style -> Song 4
  TagID=5: English/Jezik   -> Song 1
  TagID=6: Alt Rock/Genre  -> Song 9 (primary)
  Song 7: no tags

Orphan tags (zero active song links): none in populated_db by default.
Tests that need an orphan insert one directly via SQL.
"""

from src.services.catalog_service import CatalogService


def _insert_orphan_tag(db_path: str, tag_id: int, name: str, category: str) -> None:
    """Insert a tag with no MediaSourceTags links."""
    from src.data.tag_repository import TagRepository
    repo = TagRepository(db_path)
    with repo._get_connection() as conn:
        conn.execute(
            "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (?, ?, ?)",
            (tag_id, name, category),
        )
        conn.commit()


class TestDeleteUnlinkedTagsSingle:
    """Single-delete behaviour: pass [tag_id]."""

    def test_unlinked_tag_is_deleted(self, populated_db):
        """An orphan tag passed as a single-item list is soft-deleted. Returns 1."""
        _insert_orphan_tag(populated_db, 100, "Orphan", "Test")
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([100])

        assert result == 1, f"Expected 1 deleted, got {result}"

    def test_deleted_tag_is_hidden_from_get_tag(self, populated_db):
        """After deletion, get_tag returns None for the deleted tag."""
        _insert_orphan_tag(populated_db, 100, "Orphan", "Test")
        service = CatalogService(populated_db)

        service.delete_unlinked_tags([100])

        assert service.get_tag(100) is None, "Expected get_tag to return None after deletion"

    def test_linked_tag_is_not_deleted(self, populated_db):
        """A tag with active song links returns 0 — not deleted."""
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([1])  # Grunge -> Song 1, Song 9

        assert result == 0, f"Expected 0 (linked tag rejected), got {result}"

    def test_linked_tag_remains_in_db(self, populated_db):
        """A linked tag must still exist after a failed delete attempt."""
        service = CatalogService(populated_db)

        service.delete_unlinked_tags([1])

        tag = service.get_tag(1)
        assert tag is not None, "Expected linked tag to remain after rejected delete"
        assert tag.name == "Grunge", f"Expected 'Grunge', got '{tag.name}'"

    def test_nonexistent_tag_returns_zero(self, populated_db):
        """A tag ID that doesn't exist returns 0."""
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([9999])

        assert result == 0, f"Expected 0 for nonexistent tag, got {result}"

    def test_tag_linked_only_to_deleted_song_is_deletable(self, populated_db):
        """A tag whose only song is soft-deleted counts as unlinked — delete succeeds."""
        service = CatalogService(populated_db)

        # Tag 3 (90s) is only on Song 2 — soft-delete Song 2 first
        service.delete_song(2)

        result = service.delete_unlinked_tags([3])

        assert result == 1, f"Expected 1 (tag unlinked after song deleted), got {result}"


class TestDeleteUnlinkedTagsBulk:
    """Bulk behaviour: pass multiple IDs."""

    def test_bulk_deletes_all_orphans_in_list(self, populated_db):
        """All orphan IDs in the list are deleted. Returns count."""
        _insert_orphan_tag(populated_db, 100, "Orphan A", "Test")
        _insert_orphan_tag(populated_db, 101, "Orphan B", "Test")
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([100, 101])

        assert result == 2, f"Expected 2 deleted, got {result}"
        assert service.get_tag(100) is None, "Expected tag 100 to be deleted"
        assert service.get_tag(101) is None, "Expected tag 101 to be deleted"

    def test_bulk_skips_linked_tags_in_list(self, populated_db):
        """Mixed list: orphans deleted, linked tags skipped. Returns only orphan count."""
        _insert_orphan_tag(populated_db, 100, "Orphan", "Test")
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([100, 1])  # 100=orphan, 1=Grunge (linked)

        assert result == 1, f"Expected 1 deleted (orphan only), got {result}"
        assert service.get_tag(1) is not None, "Expected linked tag 1 to survive"
        assert service.get_tag(100) is None, "Expected orphan tag 100 to be deleted"

    def test_bulk_empty_list_returns_zero(self, populated_db):
        """Empty list is a no-op. Returns 0."""
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([])

        assert result == 0, f"Expected 0 for empty list, got {result}"

    def test_bulk_all_linked_returns_zero(self, populated_db):
        """All tags in list are linked — nothing deleted."""
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([1, 2, 3])

        assert result == 0, f"Expected 0 (all linked), got {result}"
