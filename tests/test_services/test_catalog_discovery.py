"""
CatalogService: Flat (surface) vs Recursive (deep) discovery leg verification.
Both search_songs_slim and search_songs_deep_slim return List[dict].
"""
import pytest


class TestSearchSongsDiscovery:
    """CatalogService verification of surface vs deep discovery modes."""

    # --- LEVEL 1: DIRECT (FLAT/SLIM) MATCHES ---

    def test_direct_metadata_match_year(self, catalog_service):
        """RecordingYear match is covered by both slim and deep_slim."""
        slim_names = {r["MediaName"] for r in catalog_service.search_songs_slim("1991")}
        deep_names = {r["MediaName"] for r in catalog_service.search_songs_deep_slim("1991")}
        assert "Smells Like Teen Spirit" in slim_names, \
            "Slim search should find SLTS by year '1991'"
        assert "Smells Like Teen Spirit" in deep_names, \
            "Deep slim search should also find SLTS by year '1991'"

    def test_direct_credit_match(self, catalog_service):
        """Surface slim finds songs directly credited to 'Dave Grohl'."""
        rows = catalog_service.search_songs_slim("Dave Grohl")
        media_names = {r["MediaName"] for r in rows}
        assert "Dual Credit Track" in media_names, \
            "Expected 'Dual Credit Track' — Dave is directly credited"
        assert "Joint Venture" in media_names, \
            "Expected 'Joint Venture' — Dave is directly credited"
        assert "Smells Like Teen Spirit" not in media_names, \
            "Surface slim should not resolve Dave to Nirvana"

    # --- LEVEL 2: RECURSIVE (DEEP SLIM) MATCHES ---

    def test_recursive_identity_resolution_only_in_deep(self, catalog_service):
        """Dave Grohl finds Nirvana songs ONLY via deep_slim, not surface slim."""
        slim_names = {r["MediaName"] for r in catalog_service.search_songs_slim("Dave Grohl")}
        assert "Smells Like Teen Spirit" not in slim_names, \
            "Surface slim should NOT expand Dave→Nirvana"

        deep_names = {r["MediaName"] for r in catalog_service.search_songs_deep_slim("Dave Grohl")}
        assert "Smells Like Teen Spirit" in deep_names, \
            "Deep slim SHOULD expand Dave→Nirvana"

    def test_recursive_publisher_resolution_only_in_deep(self, catalog_service):
        """Universal (parent) finds DGC songs ONLY via deep_slim, not surface slim."""
        slim_names = {r["MediaName"] for r in catalog_service.search_songs_slim("Universal")}
        assert "Smells Like Teen Spirit" not in slim_names, \
            "Surface slim should NOT expand Universal→DGC songs"

        deep_names = {r["MediaName"] for r in catalog_service.search_songs_deep_slim("Universal")}
        assert "Smells Like Teen Spirit" in deep_names, \
            "Deep slim SHOULD find DGC songs via Universal umbrella"
