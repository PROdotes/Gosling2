import pytest

class TestSearchSongsDeep:
    """CatalogService.search_songs_deep contracts (Universal 6 checks)."""

    def test_search_parent_publisher_finds_child_songs(self, catalog_service):
        """'Universal' should find 'Smells Like Teen Spirit' because DGC is a child of Universal."""
        # Universal (1) -> DGC (10) -> SLTS (Song 1)
        results = catalog_service.search_songs_deep("Universal")
        
        titles = {s.title for s in results}
        assert "Smells Like Teen Spirit" in titles, "Expected 'Universal' search to discover DGC's songs."
        
        # Verify fully hydrated
        slts = next(s for s in results if s.id == 1)
        assert len(slts.credits) > 0, "Credits should be hydrated"
        assert len(slts.publishers) > 0, "Publishers should be hydrated"
        assert slts.publishers[0].name == "DGC Records"
        assert slts.publishers[0].parent_name == "Universal Music Group"

    def test_search_child_publisher_finds_own_songs_only(self, catalog_service):
        """'DGC' finds SLTS, but not other Universal songs."""
        results = catalog_service.search_songs_deep("DGC")
        
        titles = {s.title for s in results}
        assert "Smells Like Teen Spirit" in titles
        # In conftest, are there other Universal songs? 
        # Song 6 (Taylor Hawkins) has no publisher.
        # Song 7 (Hollow Song) has no publisher.
        # Song 8 (Taylor) has no publisher.
        # Song 9 (Taylor) has no publisher.
        # So it's a weak test for 'only own', but it establishes intent.
        assert len(results) == 1, f"Expected 1 match for 'DGC', got {len(results)}"

    def test_search_identity_expansion_still_works(self, catalog_service):
        """'Dave Grohl' (Member) should still find 'Nirvana' (Group) songs."""
        # Dave Grohl (2) -> Nirvana (1) -> SLTS (Song 1)
        results = catalog_service.search_songs_deep("Dave Grohl")
        
        titles = {s.title for s in results}
        assert "Smells Like Teen Spirit" in titles, "Dave Grohl should discover Nirvana songs."
