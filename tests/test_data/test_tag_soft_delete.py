"""
Tests for TagRepository.soft_delete()
======================================
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


class TestSoftDelete:
    def test_soft_delete_returns_true(self, populated_db):
        """Soft-deleting an existing active tag returns True."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            result = repo.soft_delete(1, conn)
            conn.commit()

        assert result is True, f"Expected True, got {result}"

    def test_soft_delete_sets_is_deleted(self, populated_db):
        """After soft_delete, IsDeleted = 1 in the database."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            repo.soft_delete(1, conn)
            conn.commit()

        with repo._get_connection() as conn:
            row = conn.execute(
                "SELECT IsDeleted FROM Tags WHERE TagID = 1"
            ).fetchone()
        assert row[0] == 1, f"Expected IsDeleted=1, got {row[0]}"

    def test_soft_deleted_tag_hidden_from_get_by_id(self, populated_db):
        """get_by_id returns None for a soft-deleted tag."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            repo.soft_delete(1, conn)
            conn.commit()

        result = repo.get_by_id(1)
        assert result is None, f"Expected None for deleted tag, got {result}"

    def test_soft_delete_nonexistent_tag_returns_false(self, populated_db):
        """Soft-deleting a tag ID that doesn't exist returns False."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            result = repo.soft_delete(9999, conn)
            conn.commit()

        assert result is False, f"Expected False for nonexistent tag, got {result}"

    def test_soft_delete_already_deleted_returns_false(self, populated_db):
        """Soft-deleting an already soft-deleted tag returns False."""
        repo = TagRepository(populated_db)

        with repo._get_connection() as conn:
            repo.soft_delete(1, conn)
            conn.commit()

        with repo._get_connection() as conn:
            result = repo.soft_delete(1, conn)
            conn.commit()

        assert result is False, f"Expected False on double-delete, got {result}"
