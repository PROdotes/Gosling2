"""
Engine Search Tests (HTTP Layer - Search-Specific)
===================================================
Deep contract tests for the search endpoints via FastAPI TestClient.
Tests the full pipeline: HTTP -> Router -> CatalogService (two-phase search) -> SQLite.

Also covers the dashboard endpoint.

No mocking. Exact value verification. Environment isolation via monkeypatch.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.engine_server import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client(populated_db, monkeypatch):
    """TestClient wired to populated_db."""
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


@pytest.fixture
def empty_client(empty_db, monkeypatch):
    """TestClient wired to empty_db."""
    monkeypatch.setenv("GOSLING_DB_PATH", empty_db)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _find_song(data, title):
    """Find a song by exact title in a list of song dicts, fail if missing."""
    matches = [s for s in data if s["title"] == title]
    assert (
        len(matches) > 0
    ), f"Song '{title}' not found in results: {[s['title'] for s in data]}"
    return matches[0]


def _assert_slts(song):
    """Exhaustive contract for 'Smells Like Teen Spirit' SongSlimView (search result)."""
    assert song["id"] == 1, f"Expected id=1, got {song['id']}"
    assert (
        song["media_name"] == "Smells Like Teen Spirit"
    ), f"Expected media_name='Smells Like Teen Spirit', got {song['media_name']}"
    assert (
        song["title"] == "Smells Like Teen Spirit"
    ), f"Expected title='Smells Like Teen Spirit', got {song['title']}"
    assert (
        song["source_path"] == "/path/1"
    ), f"Expected source_path='/path/1', got {song['source_path']}"
    assert (
        song["duration_s"] == 200.0
    ), f"Expected duration_s=200.0, got {song['duration_s']}"
    assert (
        song["is_active"] is True
    ), f"Expected is_active=True, got {song['is_active']}"
    assert song["bpm"] is None, f"Expected bpm=None, got {song['bpm']}"
    assert song["year"] == 1991, f"Expected year=1991, got {song['year']}"
    assert song["isrc"] is None, f"Expected isrc=None, got {song['isrc']}"
    assert (
        song["display_artist"] == "Nirvana"
    ), f"Expected display_artist='Nirvana', got {song['display_artist']}"
    assert (
        song["primary_genre"] == "Grunge"
    ), f"Expected primary_genre='Grunge', got {song['primary_genre']}"
    assert (
        song["formatted_duration"] == "3:20"
    ), f"Expected formatted_duration='3:20', got {song['formatted_duration']}"


def _assert_everlong(song):
    """Exhaustive contract for 'Everlong' SongSlimView (search result)."""
    assert song["id"] == 2, f"Expected id=2, got {song['id']}"
    assert (
        song["media_name"] == "Everlong"
    ), f"Expected media_name='Everlong', got {song['media_name']}"
    assert (
        song["title"] == "Everlong"
    ), f"Expected title='Everlong', got {song['title']}"
    assert (
        song["source_path"] == "/path/2"
    ), f"Expected source_path='/path/2', got {song['source_path']}"
    assert (
        song["duration_s"] == 240.0
    ), f"Expected duration_s=240.0, got {song['duration_s']}"
    assert (
        song["is_active"] is True
    ), f"Expected is_active=True, got {song['is_active']}"
    assert song["year"] == 1997, f"Expected year=1997, got {song['year']}"
    assert song["isrc"] is None, f"Expected isrc=None, got {song['isrc']}"
    assert (
        song["display_artist"] == "Foo Fighters"
    ), f"Expected display_artist='Foo Fighters', got {song['display_artist']}"
    assert (
        song["formatted_duration"] == "4:00"
    ), f"Expected formatted_duration='4:00', got {song['formatted_duration']}"


# ===========================================================================
# Song Search: Two-Phase Discovery Contracts
# ===========================================================================
class TestSongSearchPhaseOne:
    """Phase 1: Surface discovery - title and album LIKE matching."""

    def test_exact_title_match(self, client):
        """'Everlong' matches song title directly and returns fully hydrated SongView."""
        data = client.get("/api/v1/songs/search", params={"q": "Everlong"}).json()
        song = _find_song(data, "Everlong")
        _assert_everlong(song)

    def test_partial_title_match(self, client):
        """'Ever' matches 'Everlong' via LIKE %Ever% with full hydration."""
        data = client.get("/api/v1/songs/search", params={"q": "Ever"}).json()
        song = _find_song(data, "Everlong")
        _assert_everlong(song)

    def test_case_insensitive(self, client):
        """'everlong' (lowercase) still matches with full hydration."""
        data = client.get("/api/v1/songs/search", params={"q": "everlong"}).json()
        song = _find_song(data, "Everlong")
        _assert_everlong(song)

    def test_album_title_match(self, client):
        """Searching 'Nevermind' (album name) returns SLTS with full hydration."""
        data = client.get("/api/v1/songs/search", params={"q": "Nevermind"}).json()
        song = _find_song(data, "Smells Like Teen Spirit")
        _assert_slts(song)

    def test_single_char_query(self, client):
        """Single character 'E' should work (exploration mode) and return hydrated Everlong."""
        resp = client.get("/api/v1/songs/search", params={"q": "E"})
        assert resp.status_code == 200, f"Expected status 200, got {resp.status_code}"
        data = resp.json()
        song = _find_song(data, "Everlong")
        _assert_everlong(song)


class TestSongSearchPhaseTwo:
    """Phase 2: Deep resolution - identity/alias/group expansion."""

    def test_identity_name_expands_to_group_songs(self, client):
        """'Dave Grohl' identity search expands to Nirvana + FF songs with full hydration."""
        data = client.get(
            "/api/v1/songs/search", params={"q": "Dave Grohl", "deep": "true"}
        ).json()
        titles = sorted([s["title"] for s in data])
        assert (
            "Smells Like Teen Spirit" in titles
        ), f"Expected 'Smells Like Teen Spirit' in {titles}"
        assert "Everlong" in titles, f"Expected 'Everlong' in {titles}"
        slts = _find_song(data, "Smells Like Teen Spirit")
        _assert_slts(slts)
        everlong = _find_song(data, "Everlong")
        _assert_everlong(everlong)

    def test_alias_expands_to_identity_tree(self, client):
        """'Late!' (Dave's alias) resolves through Dave's identity tree and returns Pocketwatch Demo."""
        data = client.get(
            "/api/v1/songs/search", params={"q": "Late!", "deep": "true"}
        ).json()
        song = _find_song(data, "Pocketwatch Demo")
        assert song["id"] == 5, f"Expected id=5, got {song['id']}"
        assert (
            song["media_name"] == "Pocketwatch Demo"
        ), f"Expected media_name='Pocketwatch Demo', got {song['media_name']}"
        assert (
            song["source_path"] == "/path/5"
        ), f"Expected source_path='/path/5', got {song['source_path']}"
        assert (
            song["duration_s"] == 180.0
        ), f"Expected duration_s=180.0, got {song['duration_s']}"
        assert (
            song["is_active"] is True
        ), f"Expected is_active=True, got {song['is_active']}"
        assert song["year"] == 1992, f"Expected year=1992, got {song['year']}"
        assert (
            song["display_artist"] == "Late!"
        ), f"Expected display_artist='Late!', got '{song['display_artist']}'"

    def test_group_name_returns_group_songs(self, client):
        """'Foo Fighters' returns Everlong with full hydration."""
        data = client.get(
            "/api/v1/songs/search", params={"q": "Foo Fighters", "deep": "true"}
        ).json()
        song = _find_song(data, "Everlong")
        _assert_everlong(song)

    def test_taylor_hawkins_expansion(self, client):
        """'Taylor Hawkins' returns his solo + group (FF) songs with correct fields."""
        data = client.get(
            "/api/v1/songs/search", params={"q": "Taylor Hawkins", "deep": "true"}
        ).json()
        titles = sorted([s["title"] for s in data])
        assert (
            "Range Rover Bitch" in titles
        ), f"Expected 'Range Rover Bitch' in {titles}"
        assert "Everlong" in titles, f"Expected 'Everlong' in {titles}"

        # Exhaustive slim check on Taylor's solo track
        rrb = _find_song(data, "Range Rover Bitch")
        assert rrb["id"] == 3, f"Expected id=3, got {rrb['id']}"
        assert (
            rrb["media_name"] == "Range Rover Bitch"
        ), f"Expected media_name='Range Rover Bitch', got {rrb['media_name']}"
        assert (
            rrb["duration_s"] == 180.0
        ), f"Expected duration_s=180.0, got {rrb['duration_s']}"
        assert (
            rrb["is_active"] is True
        ), f"Expected is_active=True, got {rrb['is_active']}"
        assert rrb["year"] == 2016, f"Expected year=2016, got {rrb['year']}"
        assert (
            rrb["formatted_duration"] == "3:00"
        ), f"Expected formatted_duration='3:00', got {rrb['formatted_duration']}"
        assert (
            rrb["display_artist"] == "Taylor Hawkins"
        ), f"Expected display_artist='Taylor Hawkins', got {rrb['display_artist']}"

        # Exhaustive check on FF group song
        everlong = _find_song(data, "Everlong")
        _assert_everlong(everlong)

    def test_nirvana_returns_slts(self, client):
        """'Nirvana' returns SLTS with full hydration."""
        data = client.get("/api/v1/songs/search", params={"q": "Nirvana"}).json()
        song = _find_song(data, "Smells Like Teen Spirit")
        _assert_slts(song)


class TestSongSearchDeduplication:
    """Ensure no duplicates in combined phase 1 + phase 2 results."""

    def test_no_duplicates_on_overlap(self, client):
        """Searching 'Nirvana' shouldn't return SLTS twice (title match + identity match)."""
        data = client.get("/api/v1/songs/search", params={"q": "Nirvana"}).json()
        ids = [s["id"] for s in data]
        assert len(ids) == len(set(ids)), f"Duplicate song IDs found: {ids}"

    def test_no_duplicates_empty_query(self, client):
        """Empty query returning all songs has no duplicates."""
        data = client.get("/api/v1/songs/search", params={"q": ""}).json()
        ids = [s["id"] for s in data]
        assert len(ids) == len(set(ids)), f"Duplicate song IDs found: {ids}"


class TestSongSearchSlimShape:
    """Search endpoint returns SongSlimView — verify slim field contract.
    No credits/albums/tags/publishers. Computed fields come from the slim aggregation.
    """

    def test_slim_fields_present_for_slts(self, client):
        """SLTS search result has all slim fields with correct values."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = _find_song(data, "Smells Like Teen Spirit")
        _assert_slts(slts)

    def test_display_artist_aggregated_from_credits(self, client):
        """display_artist is the Performer credit aggregated by the SQL query."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = _find_song(data, "Smells Like Teen Spirit")
        assert (
            slts["display_artist"] == "Nirvana"
        ), f"Expected 'Nirvana', got '{slts['display_artist']}'"

    def test_primary_genre_aggregated_from_tags(self, client):
        """primary_genre is the primary Genre tag aggregated by the SQL query."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = _find_song(data, "Smells Like Teen Spirit")
        assert (
            slts["primary_genre"] == "Grunge"
        ), f"Expected 'Grunge', got '{slts['primary_genre']}'"

    def test_no_hydrated_fields_in_slim_response(self, client):
        """Slim response must NOT contain hydrated fields (credits, albums, tags, publishers)."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = _find_song(data, "Smells Like Teen Spirit")
        assert "credits" not in slts, "Slim view should not have 'credits' field"
        assert "albums" not in slts, "Slim view should not have 'albums' field"
        assert "tags" not in slts, "Slim view should not have 'tags' field"
        assert "publishers" not in slts, "Slim view should not have 'publishers' field"

    def test_formatted_duration_computed(self, client):
        """formatted_duration is computed from duration_s."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = _find_song(data, "Smells Like Teen Spirit")
        assert (
            slts["formatted_duration"] == "3:20"
        ), f"Expected '3:20', got '{slts['formatted_duration']}'"

    def test_full_slts_slim_contract(self, client):
        """Complete exhaustive slim contract for SLTS."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = _find_song(data, "Smells Like Teen Spirit")
        _assert_slts(slts)


class TestSongSearchEdgeCases:
    """Edge cases for the search endpoint."""

    def test_empty_query_returns_all(self, client):
        """Empty string returns all 9 songs."""
        data = client.get("/api/v1/songs/search", params={"q": ""}).json()
        assert len(data) == 9, f"Expected 9 songs, got {len(data)}"

    def test_no_params(self, client):
        """No query params at all (both q and query missing) returns all songs."""
        resp = client.get("/api/v1/songs/search")
        assert resp.status_code == 200, f"Expected status 200, got {resp.status_code}"
        data = resp.json()
        assert len(data) == 9, f"Expected 9 songs, got {len(data)}"

    def test_empty_db_search(self, empty_client):
        """Search on empty DB returns empty list with status 200."""
        resp = empty_client.get("/api/v1/songs/search", params={"q": "anything"})
        assert resp.status_code == 200, f"Expected status 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


# ===========================================================================
# Dashboard
# ===========================================================================
class TestDashboardServing:
    """Tests for the dashboard HTML serving endpoint."""

    def test_dashboard_returns_html_or_404(self, client):
        """GET / serves the dashboard HTML if template exists, or 404."""
        resp = client.get("/")
        assert resp.status_code in (
            200,
            404,
        ), f"Expected status 200 or 404, got {resp.status_code}"
        if resp.status_code == 200:
            assert "GOSLING" in resp.text, "Expected 'GOSLING' in response body"

    def test_dashboard_missing_template(self, populated_db, monkeypatch):
        """GET / returns 404 when dashboard template is missing."""
        monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
        c = TestClient(app)
        with patch("src.engine_server.os.path.exists", return_value=False):
            resp = c.get("/")
            assert (
                resp.status_code == 404
            ), f"Expected status 404, got {resp.status_code}"
            body = resp.json()
            assert (
                "detail" in body
            ), f"Expected 'detail' key in response, got {body.keys()}"
            assert (
                "Dashboard UI template not found" in body["detail"]
            ), f"Expected error message in detail, got {body['detail']}"
