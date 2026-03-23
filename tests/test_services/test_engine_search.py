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
    """Exhaustive contract for 'Smells Like Teen Spirit' SongView."""
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
        song["duration_ms"] == 200000
    ), f"Expected duration_s=200.0, got {song['duration_ms']}"
    assert (
        song["audio_hash"] == "hash_1"
    ), f"Expected audio_hash='hash_1', got {song['audio_hash']}"
    assert (
        song["processing_status"] is None
    ), f"Expected processing_status=None, got {song['processing_status']}"
    assert (
        song["is_active"] is True
    ), f"Expected is_active=True, got {song['is_active']}"
    assert song["notes"] is None, f"Expected notes=None, got {song['notes']}"
    assert song["bpm"] is None, f"Expected bpm=None, got {song['bpm']}"
    assert song["year"] == 1991, f"Expected year=1991, got {song['year']}"
    assert song["isrc"] is None, f"Expected isrc=None, got {song['isrc']}"
    assert song["raw_tags"] == {}, f"Expected raw_tags={{}}, got {song['raw_tags']}"

    # Credits: Nirvana Performer
    assert len(song["credits"]) == 1, f"Expected 1 credit, got {len(song['credits'])}"
    credit = song["credits"][0]
    assert (
        credit["display_name"] == "Nirvana"
    ), f"Expected display_name='Nirvana', got {credit['display_name']}"
    assert (
        credit["role_name"] == "Performer"
    ), f"Expected role_name='Performer', got {credit['role_name']}"
    assert (
        credit["is_primary"] is True
    ), f"Expected is_primary=True, got {credit['is_primary']}"

    # Albums: Nevermind track 1
    assert len(song["albums"]) == 1, f"Expected 1 album, got {len(song['albums'])}"
    album = song["albums"][0]
    assert (
        album["album_title"] == "Nevermind"
    ), f"Expected album_title='Nevermind', got {album['album_title']}"
    assert (
        album["track_number"] == 1
    ), f"Expected track_number=1, got {album['track_number']}"

    # Publishers: DGC Records (parent: Universal Music Group)
    assert (
        len(song["publishers"]) == 1
    ), f"Expected 1 publisher, got {len(song['publishers'])}"
    pub = song["publishers"][0]
    assert (
        pub["name"] == "DGC Records"
    ), f"Expected publisher name='DGC Records', got {pub['name']}"
    assert (
        pub["parent_name"] == "Universal Music Group"
    ), f"Expected parent_name='Universal Music Group', got {pub['parent_name']}"

    # Tags: Energetic, English, Grunge (order may vary)
    tag_names = sorted([t["name"] for t in song["tags"]])
    assert tag_names == [
        "Energetic",
        "English",
        "Grunge",
    ], f"Expected tags=['Energetic','English','Grunge'], got {tag_names}"
    tag_by_name = {t["name"]: t for t in song["tags"]}
    assert (
        tag_by_name["Grunge"]["category"] == "Genre"
    ), f"Expected Grunge category='Genre', got {tag_by_name['Grunge']['category']}"
    assert (
        tag_by_name["Grunge"]["is_primary"] is False
    ), f"Expected Grunge is_primary=False, got {tag_by_name['Grunge']['is_primary']}"
    assert (
        tag_by_name["Energetic"]["category"] == "Mood"
    ), f"Expected Energetic category='Mood', got {tag_by_name['Energetic']['category']}"
    assert (
        tag_by_name["English"]["category"] == "Jezik"
    ), f"Expected English category='Jezik', got {tag_by_name['English']['category']}"

    # Computed fields
    assert (
        song["formatted_duration"] == "3:20"
    ), f"Expected formatted_duration='3:20', got {song['formatted_duration']}"
    assert (
        song["display_artist"] == "Nirvana"
    ), f"Expected display_artist='Nirvana', got {song['display_artist']}"
    assert (
        song["primary_genre"] == "Grunge"
    ), f"Expected primary_genre='Grunge', got {song['primary_genre']}"
    assert (
        song["display_master_publisher"] == "DGC Records (Universal Music Group)"
    ), f"Expected display_master_publisher='DGC Records (Universal Music Group)', got {song['display_master_publisher']}"


def _assert_everlong(song):
    """Exhaustive contract for 'Everlong' SongView."""
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
        song["duration_ms"] == 240000
    ), f"Expected duration_s=240.0, got {song['duration_ms']}"
    assert (
        song["audio_hash"] is None
    ), f"Expected audio_hash=None, got {song['audio_hash']}"
    assert (
        song["processing_status"] is None
    ), f"Expected processing_status=None, got {song['processing_status']}"
    assert (
        song["is_active"] is True
    ), f"Expected is_active=True, got {song['is_active']}"
    assert song["year"] == 1997, f"Expected year=1997, got {song['year']}"
    assert song["isrc"] is None, f"Expected isrc=None, got {song['isrc']}"

    # Credits: Foo Fighters Performer
    assert len(song["credits"]) == 1, f"Expected 1 credit, got {len(song['credits'])}"
    credit = song["credits"][0]
    assert (
        credit["display_name"] == "Foo Fighters"
    ), f"Expected display_name='Foo Fighters', got {credit['display_name']}"
    assert (
        credit["role_name"] == "Performer"
    ), f"Expected role_name='Performer', got {credit['role_name']}"

    # Albums: The Colour and the Shape track 11
    assert len(song["albums"]) == 1, f"Expected 1 album, got {len(song['albums'])}"
    album = song["albums"][0]
    assert (
        album["album_title"] == "The Colour and the Shape"
    ), f"Expected album_title='The Colour and the Shape', got {album['album_title']}"
    assert (
        album["track_number"] == 11
    ), f"Expected track_number=11, got {album['track_number']}"

    # No recording publishers
    assert song["publishers"] == [], f"Expected publishers=[], got {song['publishers']}"

    # Computed fields
    assert (
        song["formatted_duration"] == "4:00"
    ), f"Expected formatted_duration='4:00', got {song['formatted_duration']}"
    assert (
        song["display_artist"] == "Foo Fighters"
    ), f"Expected display_artist='Foo Fighters', got {song['display_artist']}"


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
        data = client.get("/api/v1/songs/search", params={"q": "Dave Grohl"}).json()
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
        """'Late!' (Dave's alias) resolves through Dave's identity tree and returns hydrated Pocketwatch Demo."""
        data = client.get("/api/v1/songs/search", params={"q": "Late!"}).json()
        song = _find_song(data, "Pocketwatch Demo")
        assert song["id"] == 5, f"Expected id=5, got {song['id']}"
        assert (
            song["media_name"] == "Pocketwatch Demo"
        ), f"Expected media_name='Pocketwatch Demo', got {song['media_name']}"
        assert (
            song["source_path"] == "/path/5"
        ), f"Expected source_path='/path/5', got {song['source_path']}"
        assert (
            song["duration_ms"] == 180000
        ), f"Expected duration_s=180.0, got {song['duration_ms']}"
        assert (
            song["is_active"] is True
        ), f"Expected is_active=True, got {song['is_active']}"
        assert song["year"] == 1992, f"Expected year=1992, got {song['year']}"
        assert (
            len(song["credits"]) == 1
        ), f"Expected 1 credit, got {len(song['credits'])}"
        assert (
            song["credits"][0]["display_name"] == "Late!"
        ), f"Expected display_name='Late!', got {song['credits'][0]['display_name']}"
        assert (
            song["credits"][0]["role_name"] == "Performer"
        ), f"Expected role_name='Performer', got {song['credits'][0]['role_name']}"
        assert song["albums"] == [], f"Expected albums=[], got {song['albums']}"
        assert (
            song["publishers"] == []
        ), f"Expected publishers=[], got {song['publishers']}"

    def test_group_name_returns_group_songs(self, client):
        """'Foo Fighters' returns Everlong with full hydration."""
        data = client.get("/api/v1/songs/search", params={"q": "Foo Fighters"}).json()
        song = _find_song(data, "Everlong")
        _assert_everlong(song)

    def test_taylor_hawkins_expansion(self, client):
        """'Taylor Hawkins' returns his solo + group (FF) songs with correct fields."""
        data = client.get("/api/v1/songs/search", params={"q": "Taylor Hawkins"}).json()
        titles = sorted([s["title"] for s in data])
        assert (
            "Range Rover Bitch" in titles
        ), f"Expected 'Range Rover Bitch' in {titles}"
        assert "Everlong" in titles, f"Expected 'Everlong' in {titles}"

        # Exhaustive check on Taylor's solo track
        rrb = _find_song(data, "Range Rover Bitch")
        assert rrb["id"] == 3, f"Expected id=3, got {rrb['id']}"
        assert (
            rrb["media_name"] == "Range Rover Bitch"
        ), f"Expected media_name='Range Rover Bitch', got {rrb['media_name']}"
        assert (
            rrb["duration_ms"] == 180000
        ), f"Expected duration_s=180.0, got {rrb['duration_ms']}"
        assert (
            rrb["is_active"] is True
        ), f"Expected is_active=True, got {rrb['is_active']}"
        assert rrb["year"] == 2016, f"Expected year=2016, got {rrb['year']}"
        assert len(rrb["credits"]) == 1, f"Expected 1 credit, got {len(rrb['credits'])}"
        assert (
            rrb["credits"][0]["display_name"] == "Taylor Hawkins"
        ), f"Expected display_name='Taylor Hawkins', got {rrb['credits'][0]['display_name']}"
        assert (
            rrb["credits"][0]["role_name"] == "Performer"
        ), f"Expected role_name='Performer', got {rrb['credits'][0]['role_name']}"
        assert rrb["albums"] == [], f"Expected albums=[], got {rrb['albums']}"
        assert (
            rrb["publishers"] == []
        ), f"Expected publishers=[], got {rrb['publishers']}"
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


class TestSongSearchHydration:
    """Search results must be fully hydrated SongViews."""

    def test_credits_present(self, client):
        """Search result for SLTS has Nirvana credit with all fields."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = _find_song(data, "Smells Like Teen Spirit")
        assert (
            len(slts["credits"]) == 1
        ), f"Expected 1 credit, got {len(slts['credits'])}"
        credit = slts["credits"][0]
        assert (
            credit["display_name"] == "Nirvana"
        ), f"Expected display_name='Nirvana', got {credit['display_name']}"
        assert (
            credit["role_name"] == "Performer"
        ), f"Expected role_name='Performer', got {credit['role_name']}"
        assert (
            credit["is_primary"] is True
        ), f"Expected is_primary=True, got {credit['is_primary']}"

    def test_album_present(self, client):
        """Search result for SLTS has Nevermind album with track number."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = _find_song(data, "Smells Like Teen Spirit")
        assert len(slts["albums"]) == 1, f"Expected 1 album, got {len(slts['albums'])}"
        album = slts["albums"][0]
        assert (
            album["album_title"] == "Nevermind"
        ), f"Expected album_title='Nevermind', got {album['album_title']}"
        assert (
            album["track_number"] == 1
        ), f"Expected track_number=1, got {album['track_number']}"

    def test_tags_present(self, client):
        """Search result for SLTS has tags: Grunge, Energetic, English with correct categories."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = _find_song(data, "Smells Like Teen Spirit")
        tag_names = sorted([t["name"] for t in slts["tags"]])
        assert tag_names == [
            "Energetic",
            "English",
            "Grunge",
        ], f"Expected tags=['Energetic','English','Grunge'], got {tag_names}"
        tag_by_name = {t["name"]: t for t in slts["tags"]}
        assert (
            tag_by_name["Grunge"]["category"] == "Genre"
        ), f"Expected Grunge category='Genre', got {tag_by_name['Grunge']['category']}"
        assert (
            tag_by_name["Grunge"]["is_primary"] is False
        ), f"Expected Grunge is_primary=False, got {tag_by_name['Grunge']['is_primary']}"
        assert (
            tag_by_name["Energetic"]["category"] == "Mood"
        ), f"Expected Energetic category='Mood', got {tag_by_name['Energetic']['category']}"
        assert (
            tag_by_name["English"]["category"] == "Jezik"
        ), f"Expected English category='Jezik', got {tag_by_name['English']['category']}"

    def test_publishers_present(self, client):
        """Search result for SLTS has DGC Records publisher with parent hierarchy."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = _find_song(data, "Smells Like Teen Spirit")
        assert (
            len(slts["publishers"]) == 1
        ), f"Expected 1 publisher, got {len(slts['publishers'])}"
        pub = slts["publishers"][0]
        assert (
            pub["name"] == "DGC Records"
        ), f"Expected publisher name='DGC Records', got {pub['name']}"
        assert (
            pub["parent_name"] == "Universal Music Group"
        ), f"Expected parent_name='Universal Music Group', got {pub['parent_name']}"

    def test_computed_fields(self, client):
        """Search results include computed fields with exact values."""
        data = client.get("/api/v1/songs/search", params={"q": "Teen Spirit"}).json()
        slts = _find_song(data, "Smells Like Teen Spirit")
        assert (
            slts["formatted_duration"] == "3:20"
        ), f"Expected formatted_duration='3:20', got {slts['formatted_duration']}"
        assert (
            slts["display_artist"] == "Nirvana"
        ), f"Expected display_artist='Nirvana', got {slts['display_artist']}"
        assert (
            slts["primary_genre"] == "Grunge"
        ), f"Expected primary_genre='Grunge', got {slts['primary_genre']}"
        assert (
            slts["display_master_publisher"] == "DGC Records (Universal Music Group)"
        ), f"Expected display_master_publisher='DGC Records (Universal Music Group)', got {slts['display_master_publisher']}"

    def test_full_slts_contract(self, client):
        """Complete exhaustive contract assertion for SLTS search result."""
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
