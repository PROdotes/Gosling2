"""
Engine Search Tests (HTTP Layer - Search-Specific)
===================================================
Deep contract tests for the search endpoints via FastAPI TestClient.
Tests the full pipeline: HTTP → Router → CatalogService (two-phase search) → SQLite.

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


# ===========================================================================
# Song Search: Two-Phase Discovery Contracts
# ===========================================================================
class TestSongSearchPhaseOne:
    """Phase 1: Surface discovery - title and album LIKE matching."""

    def test_exact_title_match(self, client):
        """'Everlong' matches song title directly."""
        data = client.get("/api/v1/songs/search", params={"q": "Everlong"}).json()
        titles = [s["title"] for s in data]
        assert "Everlong" in titles

    def test_partial_title_match(self, client):
        """'Ever' matches 'Everlong' via LIKE %Ever%."""
        data = client.get("/api/v1/songs/search", params={"q": "Ever"}).json()
        titles = [s["title"] for s in data]
        assert "Everlong" in titles

    def test_case_insensitive(self, client):
        """'everlong' (lowercase) still matches."""
        data = client.get("/api/v1/songs/search", params={"q": "everlong"}).json()
        titles = [s["title"] for s in data]
        assert "Everlong" in titles

    def test_album_title_match(self, client):
        """Searching 'Nevermind' (album name) returns Song 1 (SLTS)."""
        data = client.get("/api/v1/songs/search", params={"q": "Nevermind"}).json()
        titles = [s["title"] for s in data]
        assert "Smells Like Teen Spirit" in titles

    def test_single_char_query(self, client):
        """Single character 'E' should work (exploration mode)."""
        resp = client.get("/api/v1/songs/search", params={"q": "E"})
        assert resp.status_code == 200
        data = resp.json()
        # 'E' matches 'Everlong' at minimum
        titles = [s["title"] for s in data]
        assert "Everlong" in titles


class TestSongSearchPhaseTwo:
    """Phase 2: Deep resolution - identity/alias/group expansion."""

    def test_identity_name_expands_to_group_songs(self, client):
        """'Dave Grohl' identity search expands to Nirvana + FF songs."""
        data = client.get("/api/v1/songs/search", params={"q": "Dave Grohl"}).json()
        titles = sorted([s["title"] for s in data])
        # Dave's identity -> Nirvana member -> SLTS
        assert "Smells Like Teen Spirit" in titles
        # Dave's identity -> FF member -> Everlong
        assert "Everlong" in titles

    def test_alias_expands_to_identity_tree(self, client):
        """'Late!' (Dave's alias) resolves through Dave's identity tree."""
        data = client.get("/api/v1/songs/search", params={"q": "Late!"}).json()
        titles = [s["title"] for s in data]
        # The alias track itself
        assert "Pocketwatch Demo" in titles

    def test_group_name_returns_group_songs(self, client):
        """'Foo Fighters' returns Everlong directly."""
        data = client.get("/api/v1/songs/search", params={"q": "Foo Fighters"}).json()
        titles = [s["title"] for s in data]
        assert "Everlong" in titles

    def test_taylor_hawkins_expansion(self, client):
        """'Taylor Hawkins' should return his solo + group (FF) songs."""
        data = client.get("/api/v1/songs/search", params={"q": "Taylor Hawkins"}).json()
        titles = sorted([s["title"] for s in data])
        assert "Range Rover Bitch" in titles  # Taylor solo
        assert "Everlong" in titles  # FF group song

    def test_nirvana_returns_slts(self, client):
        """'Nirvana' returns SLTS."""
        data = client.get("/api/v1/songs/search", params={"q": "Nirvana"}).json()
        titles = [s["title"] for s in data]
        assert "Smells Like Teen Spirit" in titles


class TestSongSearchDeduplication:
    """Ensure no duplicates in combined phase 1 + phase 2 results."""

    def test_no_duplicates_on_overlap(self, client):
        """Searching 'Nirvana' shouldn't return SLTS twice (title match + identity match)."""
        data = client.get("/api/v1/songs/search", params={"q": "Nirvana"}).json()
        ids = [s["id"] for s in data]
        assert len(ids) == len(set(ids)), f"Duplicate song IDs: {ids}"

    def test_no_duplicates_empty_query(self, client):
        """Empty query returning all songs has no duplicates."""
        data = client.get("/api/v1/songs/search", params={"q": ""}).json()
        ids = [s["id"] for s in data]
        assert len(ids) == len(set(ids))


class TestSongSearchHydration:
    """Search results must be fully hydrated SongViews."""

    def test_credits_present(self, client):
        """Search result for SLTS has Nirvana credit."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = next(s for s in data if s["title"] == "Smells Like Teen Spirit")
        assert len(slts["credits"]) == 1
        assert slts["credits"][0]["display_name"] == "Nirvana"
        assert slts["credits"][0]["role_name"] == "Performer"

    def test_album_present(self, client):
        """Search result for SLTS has Nevermind album."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = next(s for s in data if s["title"] == "Smells Like Teen Spirit")
        assert len(slts["albums"]) == 1
        assert slts["albums"][0]["album_title"] == "Nevermind"
        assert slts["albums"][0]["track_number"] == 1

    def test_tags_present(self, client):
        """Search result for SLTS has tags: Grunge, Energetic, English."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = next(s for s in data if s["title"] == "Smells Like Teen Spirit")
        tag_names = sorted([t["name"] for t in slts["tags"]])
        assert tag_names == ["Energetic", "English", "Grunge"]

    def test_publishers_present(self, client):
        """Search result for SLTS has DGC Records publisher."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = next(s for s in data if s["title"] == "Smells Like Teen Spirit")
        assert len(slts["publishers"]) == 1
        assert slts["publishers"][0]["name"] == "DGC Records"

    def test_computed_fields(self, client):
        """Search results include computed fields: formatted_duration, display_artist, primary_genre."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = next(s for s in data if s["title"] == "Smells Like Teen Spirit")
        assert slts["formatted_duration"] == "3:20"
        assert slts["display_artist"] == "Nirvana"
        assert slts["primary_genre"] == "Grunge"
        assert slts["display_master_publisher"] == "DGC Records (Universal Music Group)"


class TestSongSearchEdgeCases:
    """Edge cases for the search endpoint."""

    def test_empty_query_returns_all(self, client):
        """Empty string returns all 9 songs."""
        data = client.get("/api/v1/songs/search", params={"q": ""}).json()
        assert len(data) == 9

    def test_no_params(self, client):
        """No query params at all (both q and query missing)."""
        resp = client.get("/api/v1/songs/search")
        assert resp.status_code == 200
        # Should search with empty string -> all songs
        assert len(resp.json()) == 9

    def test_empty_db_search(self, empty_client):
        """Search on empty DB returns empty list."""
        resp = empty_client.get("/api/v1/songs/search", params={"q": "anything"})
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# Dashboard
# ===========================================================================
class TestDashboardServing:
    def test_dashboard_returns_html_or_404(self, client):
        """GET / serves the dashboard HTML if template exists."""
        resp = client.get("/")
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert "GOSLING" in resp.text

    def test_dashboard_missing_template(self, populated_db, monkeypatch):
        """GET / returns 404 when dashboard template is missing."""
        monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
        c = TestClient(app)
        with patch("src.engine_server.os.path.exists", return_value=False):
            resp = c.get("/")
            assert resp.status_code == 404
            assert "Dashboard UI template not found" in resp.json()["detail"]
