"""
Contract tests for CatalogService.search_songs_deep_slim() deep resolution.

Verifies that search_songs_deep_slim() correctly discovers songs through:
- Title surface match
- Album surface match
- Identity alias resolution
- Identity primary-name resolution
- Group membership expansion

Returns List[dict] (slim rows). No hydration.
"""

import pytest


def _get_row_by_media_name(rows: list[dict], media_name: str, context: str = "") -> dict:
    """Retrieve a single row by MediaName, failing with a clear message."""
    for r in rows:
        if r["MediaName"] == media_name:
            return r
    names = [r["MediaName"] for r in rows]
    pytest.fail(f"[{context}] '{media_name}' not found in results: {names}")


# --------------------------------------------------------------------------
# Slim field expectations (subset — not all fields, just key identifiers)
# --------------------------------------------------------------------------
SLTS_ROW = {"SourceID": 1, "MediaName": "Smells Like Teen Spirit", "SourceDuration": 200}
EVERLONG_ROW = {"SourceID": 2, "MediaName": "Everlong", "SourceDuration": 240}
GROHLTON_THEME_ROW = {"SourceID": 4, "MediaName": "Grohlton Theme"}
DUAL_CREDIT_ROW = {"SourceID": 6, "MediaName": "Dual Credit Track"}


def _assert_slim_row(row: dict, expected: dict, context: str = ""):
    for key, val in expected.items():
        assert row[key] == val, f"[{context}] '{key}': expected {val!r}, got {row[key]!r}"


class TestSearchSongsDeepSlimSearch:
    """Contract tests for CatalogService.search_songs_deep_slim()."""

    def test_search_by_title_returns_correct_song(self, catalog_service):
        """Surface title match returns the correct slim row."""
        rows = catalog_service.search_songs_deep_slim("Spirit")
        assert len(rows) == 1, f"Expected 1 result, got {len(rows)}"
        _assert_slim_row(rows[0], SLTS_ROW, context="search_by_title")

    def test_search_by_album_returns_correct_song(self, catalog_service):
        """Album title match 'Nevermind' returns the song on that album."""
        rows = catalog_service.search_songs_deep_slim("Nevermind")
        assert len(rows) == 1, f"Expected 1 result, got {len(rows)}"
        _assert_slim_row(rows[0], SLTS_ROW, context="search_by_album")

    def test_search_by_alias_finds_own_songs_and_group_songs(self, catalog_service):
        """Alias 'Grohlton' finds Grohlton's songs + all parent identity group songs."""
        rows = catalog_service.search_songs_deep_slim("Grohlton")
        media_names = {r["MediaName"] for r in rows}

        assert "Grohlton Theme" in media_names, \
            f"Expected 'Grohlton Theme', got {media_names}"
        assert "Smells Like Teen Spirit" in media_names, \
            f"Expected 'Smells Like Teen Spirit' via Nirvana group, got {media_names}"
        assert "Everlong" in media_names, \
            f"Expected 'Everlong' via Foo Fighters group, got {media_names}"

        _assert_slim_row(
            _get_row_by_media_name(rows, "Grohlton Theme", "alias_search"),
            GROHLTON_THEME_ROW, context="alias_search",
        )
        _assert_slim_row(
            _get_row_by_media_name(rows, "Smells Like Teen Spirit", "alias_search"),
            SLTS_ROW, context="alias_search",
        )
        _assert_slim_row(
            _get_row_by_media_name(rows, "Everlong", "alias_search"),
            EVERLONG_ROW, context="alias_search",
        )

    def test_search_by_primary_name_resolves_groups(self, catalog_service):
        """'Dave Grohl' finds direct credits + group songs (Nirvana, Foo Fighters)."""
        rows = catalog_service.search_songs_deep_slim("Dave Grohl")
        media_names = {r["MediaName"] for r in rows}

        expected = {
            "Smells Like Teen Spirit",
            "Everlong",
            "Dual Credit Track",
            "Joint Venture",
        }
        for title in expected:
            assert title in media_names, \
                f"Expected '{title}' in deep_slim results for 'Dave Grohl', got {media_names}"

        _assert_slim_row(
            _get_row_by_media_name(rows, "Smells Like Teen Spirit", "primary_name"),
            SLTS_ROW, context="primary_name",
        )
        _assert_slim_row(
            _get_row_by_media_name(rows, "Everlong", "primary_name"),
            EVERLONG_ROW, context="primary_name",
        )
        _assert_slim_row(
            _get_row_by_media_name(rows, "Dual Credit Track", "primary_name"),
            DUAL_CREDIT_ROW, context="primary_name",
        )

    def test_search_no_results_returns_empty_list(self, catalog_service):
        """A query matching nothing returns an empty list."""
        rows = catalog_service.search_songs_deep_slim("NonexistentArtist")
        assert isinstance(rows, list), f"Expected list, got {type(rows).__name__}"
        assert len(rows) == 0, f"Expected 0 results, got {len(rows)}"

    def test_search_by_alias_expands_to_all_group_songs(self, catalog_service):
        """'Grohlton' expands to all parent groups, not a subset."""
        rows = catalog_service.search_songs_deep_slim("Grohlton")
        media_names = {r["MediaName"] for r in rows}

        assert "Everlong" in media_names, \
            f"Expected 'Everlong' via Foo Fighters group, got {media_names}"
        assert "Smells Like Teen Spirit" in media_names, \
            f"Expected 'Smells Like Teen Spirit' via Nirvana group, got {media_names}"

    def test_search_excludes_duplicates(self, catalog_service):
        """No duplicate SourceIDs even when matched via multiple expansion paths."""
        rows = catalog_service.search_songs_deep_slim("Grohlton")
        source_ids = [r["SourceID"] for r in rows]
        assert len(source_ids) == len(set(source_ids)), \
            f"Duplicate SourceIDs in results: {source_ids}"

    def test_result_rows_have_required_slim_fields(self, catalog_service):
        """Every result row must contain the required slim dict keys."""
        rows = catalog_service.search_songs_deep_slim("Spirit")
        assert len(rows) >= 1, "Expected at least 1 result"
        row = rows[0]
        for key in ("SourceID", "MediaName", "SourcePath", "SourceDuration", "IsActive",
                    "DisplayArtist", "PrimaryGenre"):
            assert key in row, f"Result row missing required field '{key}'"
