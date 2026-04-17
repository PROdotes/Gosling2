"""
PublisherRepository.search_deep tests — recursive CTE expansion.
Additional coverage beyond the TestSearchDeep class in test_publisher_repository.py.
"""

from src.data.publisher_repository import PublisherRepository


class TestSearchDeep:
    """PublisherRepository.search_deep contracts for recursive discovery."""

    def test_search_parent_finds_all_descendants(self, populated_db):
        """'Universal' should match itself, its children (Island, DGC), and grandchildren (Def Jam)."""
        repo = PublisherRepository(populated_db)
        results = repo.search_deep("Universal")

        # Expecting: 1 (UMG), 2 (Island), 3 (Def Jam), 10 (DGC)
        assert len(results) == 4, (
            f"Expected 4 publishers for 'Universal', got {len(results)}"
        )
        ids = {p.id for p in results}
        assert ids == {1, 2, 3, 10}, f"Expected IDs {{1, 2, 3, 10}}, got {ids}"

    def test_search_mid_tier_finds_children(self, populated_db):
        """'Island' should match 'Island Records' and 'Island Def Jam' (child)."""
        repo = PublisherRepository(populated_db)
        results = repo.search_deep("Island")

        # Expecting: 2 (Island Records), 3 (Island Def Jam)
        assert len(results) == 2, (
            f"Expected 2 publishers for 'Island', got {len(results)}"
        )
        ids = {p.id for p in results}
        assert ids == {2, 3}, f"Expected IDs {{2, 3}}, got {ids}"

    def test_search_leaf_finds_only_itself(self, populated_db):
        """'Def Jam' should match only itself as it has no children."""
        repo = PublisherRepository(populated_db)
        results = repo.search_deep("Def Jam")

        assert len(results) == 1, (
            f"Expected 1 publisher for 'Def Jam', got {len(results)}"
        )
        assert results[0].id == 3, f"Expected ID 3, got {results[0].id}"
