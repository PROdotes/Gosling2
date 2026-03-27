"""
CatalogService.search_songs_deep_slim contracts.

Returns List[dict] (slim rows). No hydration — credits/publishers are NOT in the result.
Covers identity expansion (member → group) and publisher expansion (parent → child labels).
"""



class TestSearchSongsDeepSlim:
    """CatalogService.search_songs_deep_slim contracts."""

    def test_search_parent_publisher_finds_child_songs(self, catalog_service):
        """'Universal' should find 'Smells Like Teen Spirit' because DGC is a child of Universal."""
        # Universal (1) -> DGC (10) -> SLTS (Song 1)
        rows = catalog_service.search_songs_deep_slim("Universal")

        media_names = {r["MediaName"] for r in rows}
        assert (
            "Smells Like Teen Spirit" in media_names
        ), "Expected 'Universal' deep search to discover DGC's songs via publisher expansion."

        slts = next(r for r in rows if r["SourceID"] == 1)
        assert slts["SourceID"] == 1, f"Expected SourceID=1, got {slts['SourceID']}"
        assert (
            slts["MediaName"] == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{slts['MediaName']}'"

    def test_search_child_publisher_finds_own_songs_only(self, catalog_service):
        """'DGC' finds only SLTS (Song 1) — the sole DGC-published song."""
        rows = catalog_service.search_songs_deep_slim("DGC")

        media_names = {r["MediaName"] for r in rows}
        assert "Smells Like Teen Spirit" in media_names, "Expected 'DGC' to find SLTS."
        assert len(rows) == 1, f"Expected 1 match for 'DGC', got {len(rows)}"

        # Negative isolation
        returned_ids = {r["SourceID"] for r in rows}
        assert 2 not in returned_ids, "Everlong should not match 'DGC'"

    def test_search_identity_expansion_finds_group_songs(self, catalog_service):
        """'Dave Grohl' (member of Nirvana) should discover Nirvana songs via group expansion."""
        # Dave Grohl (Identity 2) -> Nirvana group (Identity 1) -> SLTS (Song 1)
        rows = catalog_service.search_songs_deep_slim("Dave Grohl")

        media_names = {r["MediaName"] for r in rows}
        assert (
            "Smells Like Teen Spirit" in media_names
        ), "Dave Grohl's group membership should discover Nirvana songs."

    def test_no_match_returns_empty(self, catalog_service):
        """Non-existent query returns empty list."""
        rows = catalog_service.search_songs_deep_slim("ZZZZZZ_NO_MATCH")
        assert rows == [], f"Expected [], got {rows}"

    def test_returns_slim_dict_shape(self, catalog_service):
        """Each result row must contain the expected slim fields."""
        rows = catalog_service.search_songs_deep_slim("Nirvana")
        assert len(rows) >= 1, "Expected at least one result for 'Nirvana'"
        row = rows[0]
        assert "SourceID" in row, "Row missing 'SourceID'"
        assert "MediaName" in row, "Row missing 'MediaName'"
        assert "SourcePath" in row, "Row missing 'SourcePath'"
        assert "SourceDuration" in row, "Row missing 'SourceDuration'"
        assert "IsActive" in row, "Row missing 'IsActive'"
        assert "DisplayArtist" in row, "Row missing 'DisplayArtist'"
        assert "PrimaryGenre" in row, "Row missing 'PrimaryGenre'"

    def test_no_duplicates_across_expansion_legs(self, catalog_service):
        """Songs found via multiple expansion legs should not appear twice."""
        # "Dave Grohl" direct credit AND group expansion could both find the same song
        rows = catalog_service.search_songs_deep_slim("Dave Grohl")
        ids = [r["SourceID"] for r in rows]
        assert len(ids) == len(
            set(ids)
        ), f"Duplicate SourceIDs in deep search results: {ids}"
