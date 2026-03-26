import pytest

class TestSearchSongsDiscovery:
    """CatalogService verification of Flat (Direct) vs Recursive (Expansion) discovery legs."""

    # --- LEVEL 1: DIRECT (FLAT) MATCHES ---
    
    def test_direct_metadata_match_year(self, catalog_service):
        """Direct match on RecordingYear is now part of the unified discovery path."""
        # Song 1 (SLTS) is 1991. 
        # Both Normal and Deep should find it by year
        assert "Smells Like Teen Spirit" in {s.title for s in catalog_service.search_songs("1991")}
        assert "Smells Like Teen Spirit" in {s.title for s in catalog_service.search_songs_deep("1991")}

    def test_direct_credit_match(self, catalog_service):
        """Direct string match on a credited name (Identity independent)."""
        # Dave Grohl (NameID=10) is credited on Songs 6 & 8.
        # Nirvana (NameID=20) is credited on Song 1.
        results = catalog_service.search_songs("Dave Grohl")
        titles = {s.title for s in results}
        assert "Dual Credit Track" in titles
        assert "Joint Venture" in titles
        assert "Smells Like Teen Spirit" not in titles, "Normal search should not resolve members to groups."

    # --- LEVEL 2: RECURSIVE (RESOLUTION) MATCHES ---

    def test_recursive_identity_resolution_only_in_deep(self, catalog_service):
        """Dave Grohl (Identity) finds Nirvana songs ONLY in Deep mode."""
        # 1. Normal (Surface) - Should NOT find Nirvana via Dave
        results_norm = catalog_service.search_songs("Dave Grohl")
        assert "Smells Like Teen Spirit" not in {s.title for s in results_norm}

        # 2. Deep - SHOULD find Nirvana via Dave resolve
        results_deep = catalog_service.search_songs_deep("Dave Grohl")
        assert "Smells Like Teen Spirit" in {s.title for s in results_deep}

    def test_recursive_publisher_resolution_only_in_deep(self, catalog_service):
        """Universal (Parent) finds DGC songs ONLY in Deep mode."""
        # 1. Normal (Surface) - Should NOT find DGC via Universal
        results_norm = catalog_service.search_songs("Universal")
        assert "Smells Like Teen Spirit" not in {s.title for s in results_norm}

        # 2. Deep - SHOULD find DGC via Universal umbrella
        results_deep = catalog_service.search_songs_deep("Universal")
        assert "Smells Like Teen Spirit" in {s.title for s in results_deep}
