"""
Contract tests for CatalogService.search_songs() deep resolution.

Verifies that search_songs() correctly discovers songs through:
- Title surface match
- Album surface match
- Identity alias resolution
- Identity primary-name resolution
- Group membership expansion
"""

import pytest
from src.models.domain import Song


def _assert_song_fields(song: Song, expected: dict, context: str = ""):
    """Assert every field of a Song against expected values.

    Skips None-allowed fields when the expected value is None,
    but still checks they are None. Verifies all non-optional fields explicitly.
    """
    for field, expected_val in expected.items():
        actual = getattr(song, field, None)
        assert (
            actual == expected_val
        ), f"[{context}] Field '{field}': expected {expected_val!r}, got {actual!r}"


def _get_song_by_title(songs: list[Song], title: str, context: str = "") -> Song:
    """Retrieve a single song by title from a result set, failing with a clear message."""
    for s in songs:
        if s.title == title:
            return s
    titles = [s.title for s in songs]
    pytest.fail(f"[{context}] Song '{title}' not found in results: {titles}")


# --------------------------------------------------------------------------
# SLTS baseline expectations (Song 1)
# --------------------------------------------------------------------------
SLTS_EXPECTED = {
    "id": 1,
    "type_id": 1,
    "media_name": "Smells Like Teen Spirit",
    "source_path": "/path/1",
    "duration_ms": 200000,
    "audio_hash": "hash_1",
    "processing_status": None,
    "is_active": True,
    "notes": None,
    "bpm": None,
    "year": 1991,
    "isrc": None,
}

# --------------------------------------------------------------------------
# Everlong baseline expectations (Song 2)
# --------------------------------------------------------------------------
EVERLONG_EXPECTED = {
    "id": 2,
    "type_id": 1,
    "media_name": "Everlong",
    "source_path": "/path/2",
    "duration_ms": 240000,
    "audio_hash": None,
    "processing_status": None,
    "is_active": True,
    "notes": None,
    "bpm": None,
    "year": 1997,
    "isrc": None,
}

# --------------------------------------------------------------------------
# Grohlton Theme baseline expectations (Song 4)
# --------------------------------------------------------------------------
GROHLTON_THEME_EXPECTED = {
    "id": 4,
    "type_id": 1,
    "media_name": "Grohlton Theme",
    "source_path": "/path/4",
    "duration_ms": 120000,
    "audio_hash": None,
    "processing_status": None,
    "is_active": True,
    "notes": None,
    "bpm": None,
    "year": None,
    "isrc": None,
}

# --------------------------------------------------------------------------
# Dual Credit Track baseline expectations (Song 6)
# --------------------------------------------------------------------------
DUAL_CREDIT_EXPECTED = {
    "id": 6,
    "type_id": 1,
    "media_name": "Dual Credit Track",
    "source_path": "/path/6",
    "duration_ms": 300000,
    "audio_hash": None,
    "processing_status": None,
    "is_active": True,
    "notes": None,
    "bpm": None,
    "year": None,
    "isrc": None,
}


class TestSearchSongsDeepSearch:
    """Contract tests for CatalogService.search_songs_deep() deep resolution."""

    def test_search_by_title_returns_correct_song(self, catalog_service):
        """Surface match on title must return the song with all fields intact."""
        results = catalog_service.search_songs_deep("Spirit")
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"

        song = results[0]
        _assert_song_fields(song, SLTS_EXPECTED, context="search_by_title")

    def test_search_by_album_returns_correct_song(self, catalog_service):
        """Surface match on album title 'Nevermind' must return the song on that album."""
        results = catalog_service.search_songs_deep("Nevermind")
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"

        song = results[0]
        _assert_song_fields(song, SLTS_EXPECTED, context="search_by_album")

    def test_search_by_alias_finds_own_songs_and_group_songs(self, catalog_service):
        """Searching for alias 'Grohlton' must find Grohlton's own songs plus
        songs from groups the parent identity belongs to (Nirvana, Foo Fighters)."""
        results = catalog_service.search_songs_deep("Grohlton")
        titles = {s.title for s in results}

        assert (
            "Grohlton Theme" in titles
        ), f"Expected 'Grohlton Theme' in results, got {titles}"
        assert (
            "Smells Like Teen Spirit" in titles
        ), f"Expected 'Smells Like Teen Spirit' in results, got {titles}"
        assert "Everlong" in titles, f"Expected 'Everlong' in results, got {titles}"

        _assert_song_fields(
            _get_song_by_title(results, "Grohlton Theme", "alias_search"),
            GROHLTON_THEME_EXPECTED,
            context="alias_search",
        )
        _assert_song_fields(
            _get_song_by_title(results, "Smells Like Teen Spirit", "alias_search"),
            SLTS_EXPECTED,
            context="alias_search",
        )
        _assert_song_fields(
            _get_song_by_title(results, "Everlong", "alias_search"),
            EVERLONG_EXPECTED,
            context="alias_search",
        )

    def test_search_by_primary_name_resolves_groups(self, catalog_service):
        """Searching for 'Dave Grohl' must find songs from all his groups
        (Nirvana, Foo Fighters) plus direct-credit songs."""
        results = catalog_service.search_songs_deep("Dave Grohl")
        titles = {s.title for s in results}

        expected_titles = {
            "Smells Like Teen Spirit",
            "Everlong",
            "Dual Credit Track",
            "Joint Venture",
        }
        for t in expected_titles:
            assert (
                t in titles
            ), f"Expected '{t}' in results for 'Dave Grohl' search, got {titles}"

        _assert_song_fields(
            _get_song_by_title(results, "Smells Like Teen Spirit", "primary_name"),
            SLTS_EXPECTED,
            context="primary_name",
        )
        _assert_song_fields(
            _get_song_by_title(results, "Everlong", "primary_name"),
            EVERLONG_EXPECTED,
            context="primary_name",
        )
        _assert_song_fields(
            _get_song_by_title(results, "Dual Credit Track", "primary_name"),
            DUAL_CREDIT_EXPECTED,
            context="primary_name",
        )

    def test_search_no_results_returns_empty_list(self, catalog_service):
        """A query matching nothing must return an empty list, not None or a partial."""
        results = catalog_service.search_songs_deep("NonexistentArtist")
        assert isinstance(results, list), f"Expected list, got {type(results).__name__}"
        assert (
            len(results) == 0
        ), f"Expected 0 results for unknown query, got {len(results)}"

    def test_search_returns_hydrated_credits(self, catalog_service):
        """Returned songs must have hydrated credits with correct display names."""
        results = catalog_service.search_songs_deep("Spirit")
        song = results[0]

        assert (
            len(song.credits) == 1
        ), f"Expected 1 credit for SLTS, got {len(song.credits)}"
        credit = song.credits[0]
        assert (
            credit.display_name == "Nirvana"
        ), f"Expected credit display_name 'Nirvana', got {credit.display_name!r}"
        assert (
            credit.role_name == "Performer"
        ), f"Expected credit role_name 'Performer', got {credit.role_name!r}"

    def test_search_returns_hydrated_albums(self, catalog_service):
        """Returned songs must have hydrated album associations."""
        results = catalog_service.search_songs_deep("Spirit")
        song = results[0]

        assert (
            len(song.albums) == 1
        ), f"Expected 1 album for SLTS, got {len(song.albums)}"
        album = song.albums[0]
        assert (
            album.album_title == "Nevermind"
        ), f"Expected album_title 'Nevermind', got {album.album_title!r}"
        assert (
            album.track_number == 1
        ), f"Expected track_number 1, got {album.track_number}"

    def test_search_returns_hydrated_tags(self, catalog_service):
        """Returned songs must have hydrated tags."""
        results = catalog_service.search_songs_deep("Spirit")
        song = results[0]

        tag_names = {t.name for t in song.tags}
        assert "Grunge" in tag_names, f"Expected tag 'Grunge' for SLTS, got {tag_names}"
        assert (
            "Energetic" in tag_names
        ), f"Expected tag 'Energetic' for SLTS, got {tag_names}"
        assert (
            "English" in tag_names
        ), f"Expected tag 'English' for SLTS, got {tag_names}"
        assert len(song.tags) == 3, f"Expected 3 tags for SLTS, got {len(song.tags)}"

    def test_search_returns_hydrated_publishers(self, catalog_service):
        """Returned songs must have hydrated recording publishers."""
        results = catalog_service.search_songs_deep("Spirit")
        song = results[0]

        pub_names = {p.name for p in song.publishers}
        assert (
            "DGC Records" in pub_names
        ), f"Expected publisher 'DGC Records' for SLTS, got {pub_names}"

    def test_search_by_alias_expands_to_all_group_songs(self, catalog_service):
        """Searching for alias 'Grohlton' must expand to songs from all parent
        identity's groups, not just a subset."""
        results = catalog_service.search_songs_deep("Grohlton")
        titles = {s.title for s in results}

        assert "Everlong" in titles, (
            "Expected 'Everlong' (Foo Fighters group) via Grohlton alias expansion, "
            f"got {titles}"
        )
        assert "Smells Like Teen Spirit" in titles, (
            "Expected 'Smells Like Teen Spirit' (Nirvana group) via Grohlton alias expansion, "
            f"got {titles}"
        )

    def test_search_excludes_duplicates(self, catalog_service):
        """Search must not return duplicate songs even when matched by
        both surface and deep paths."""
        results = catalog_service.search_songs_deep("Grohlton")
        song_ids = [s.id for s in results]
        assert len(song_ids) == len(
            set(song_ids)
        ), f"Duplicate song IDs in results: {song_ids}"
