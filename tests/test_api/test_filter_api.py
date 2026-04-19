"""
API tests for filter endpoints:
  GET /api/v1/songs/filter-values
  GET /api/v1/songs/filter

populated_db reference (filter-relevant):
  Artists (Performer): Dave Grohl, Foo Fighters, Grohlton, Late!, Nirvana, Taylor Hawkins
  Years: 1991, 1992, 1997, 2016
  Genres: Grunge, Alt Rock
  Albums: Nevermind, The Colour and the Shape
  Publishers (recording): DGC Records  (song 1 only)
  Status=0 (done): 1,2,3,4,5,6,8   Status=1 (not done): 7,9
"""

import pytest
from fastapi.testclient import TestClient
from src.engine_server import app


@pytest.fixture
def api(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/v1/songs/filter-values
# ---------------------------------------------------------------------------


class TestGetFilterValues:
    def test_returns_200(self, api):
        resp = api.get("/api/v1/songs/filter-values")
        assert resp.status_code == 200

    def test_response_has_required_keys(self, api):
        data = api.get("/api/v1/songs/filter-values").json()
        for key in (
            "artists",
            "contributors",
            "years",
            "decades",
            "genres",
            "albums",
            "publishers",
            "tag_categories",
        ):
            assert key in data, f"Missing key: {key}"

    def test_artists_contains_expected_names(self, api):
        data = api.get("/api/v1/songs/filter-values").json()
        artists = set(data["artists"])
        for name in (
            "Nirvana",
            "Foo Fighters",
            "Dave Grohl",
            "Taylor Hawkins",
            "Grohlton",
            "Late!",
        ):
            assert name in artists, f"Expected '{name}' in artists"

    def test_genres_are_genre_category_only(self, api):
        data = api.get("/api/v1/songs/filter-values").json()
        genres = set(data["genres"])
        assert genres == {"Grunge", "Alt Rock"}, f"Unexpected genres: {genres}"
        assert "Energetic" not in genres
        assert "90s" not in genres

    def test_publishers_are_recording_publishers(self, api):
        data = api.get("/api/v1/songs/filter-values").json()
        assert data["publishers"] == ["DGC Records"]

    def test_tag_categories_excludes_genre(self, api):
        data = api.get("/api/v1/songs/filter-values").json()
        cats = data["tag_categories"]
        assert "Genre" not in cats
        assert "Era" in cats and "90s" in cats["Era"]
        assert "Mood" in cats and "Energetic" in cats["Mood"]


# ---------------------------------------------------------------------------
# GET /api/v1/songs/filter — response shape
# ---------------------------------------------------------------------------


class TestFilterSongsShape:
    def test_returns_200_and_list(self, api):
        resp = api.get("/api/v1/songs/filter", params={"artists": "Nirvana"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_slim_view_has_required_fields(self, api):
        resp = api.get("/api/v1/songs/filter", params={"artists": "Nirvana"})
        song = resp.json()[0]
        for field in ("id", "title", "display_artist", "processing_status"):
            assert field in song, f"SongSlimView missing field: {field}"


# ---------------------------------------------------------------------------
# GET /api/v1/songs/filter — artist
# ---------------------------------------------------------------------------


class TestFilterSongsArtist:
    def test_filter_nirvana_returns_song_1(self, api):
        resp = api.get("/api/v1/songs/filter", params={"artists": "Nirvana"})
        ids = {s["id"] for s in resp.json()}
        assert ids == {1}, f"Expected {{1}}, got {ids}"

    def test_filter_foo_fighters_returns_song_2(self, api):
        resp = api.get("/api/v1/songs/filter", params={"artists": "Foo Fighters"})
        ids = {s["id"] for s in resp.json()}
        assert ids == {2}, f"Expected {{2}}, got {ids}"

    def test_filter_unknown_artist_returns_empty(self, api):
        resp = api.get("/api/v1/songs/filter", params={"artists": "Nobody Famous"})
        assert resp.json() == []

    def test_filter_multiple_artists_any_mode(self, api):
        resp = api.get(
            "/api/v1/songs/filter",
            params=[
                ("artists", "Nirvana"),
                ("artists", "Foo Fighters"),
                ("mode", "ANY"),
            ],
        )
        ids = {s["id"] for s in resp.json()}
        assert ids == {1, 2}, f"Expected {{1, 2}}, got {ids}"

    def test_filter_multiple_artists_all_mode_returns_empty(self, api):
        # No song has BOTH Nirvana and Foo Fighters as Performer
        resp = api.get(
            "/api/v1/songs/filter",
            params=[
                ("artists", "Nirvana"),
                ("artists", "Foo Fighters"),
                ("mode", "ALL"),
            ],
        )
        assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/v1/songs/filter — year
# ---------------------------------------------------------------------------


class TestFilterSongsYear:
    def test_filter_year_1991(self, api):
        resp = api.get("/api/v1/songs/filter", params={"years": 1991})
        ids = {s["id"] for s in resp.json()}
        assert ids == {1}

    def test_filter_nonexistent_year_returns_empty(self, api):
        resp = api.get("/api/v1/songs/filter", params={"years": 2000})
        assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/v1/songs/filter — decade
# ---------------------------------------------------------------------------


class TestFilterSongsDecade:
    def test_filter_decade_1990(self, api):
        resp = api.get("/api/v1/songs/filter", params={"decades": 1990})
        ids = {s["id"] for s in resp.json()}
        assert ids == {1, 2, 5}, f"Expected {{1, 2, 5}}, got {ids}"


# ---------------------------------------------------------------------------
# GET /api/v1/songs/filter — genre
# ---------------------------------------------------------------------------


class TestFilterSongsGenre:
    def test_filter_grunge(self, api):
        resp = api.get("/api/v1/songs/filter", params={"genres": "Grunge"})
        ids = {s["id"] for s in resp.json()}
        assert {1, 9}.issubset(ids), f"Expected 1 and 9 in {ids}"


# ---------------------------------------------------------------------------
# GET /api/v1/songs/filter — album
# ---------------------------------------------------------------------------


class TestFilterSongsAlbum:
    def test_filter_nevermind(self, api):
        resp = api.get("/api/v1/songs/filter", params={"albums": "Nevermind"})
        ids = {s["id"] for s in resp.json()}
        assert ids == {1}

    def test_filter_tcats(self, api):
        resp = api.get(
            "/api/v1/songs/filter", params={"albums": "The Colour and the Shape"}
        )
        ids = {s["id"] for s in resp.json()}
        assert ids == {2}


# ---------------------------------------------------------------------------
# GET /api/v1/songs/filter — publisher
# ---------------------------------------------------------------------------


class TestFilterSongsPublisher:
    def test_filter_dgc_records(self, api):
        resp = api.get("/api/v1/songs/filter", params={"publishers": "DGC Records"})
        ids = {s["id"] for s in resp.json()}
        assert ids == {1}


# ---------------------------------------------------------------------------
# GET /api/v1/songs/filter — status
# ---------------------------------------------------------------------------


class TestFilterSongsStatus:
    def test_filter_done(self, api):
        resp = api.get("/api/v1/songs/filter", params={"statuses": "done"})
        ids = {s["id"] for s in resp.json()}
        assert ids == {1, 2, 3, 4, 5, 6, 8}, f"Unexpected done songs: {ids}"

    def test_filter_not_done(self, api):
        resp = api.get("/api/v1/songs/filter", params={"statuses": "not_done"})
        ids = {s["id"] for s in resp.json()}
        assert ids == {7, 9}, f"Expected {{7, 9}}, got {ids}"

    def test_filter_missing_data_includes_hollow_song(self, api):
        resp = api.get("/api/v1/songs/filter", params={"statuses": "missing_data"})
        ids = {s["id"] for s in resp.json()}
        assert (
            7 in ids
        ), f"Song 7 (no credits/publisher/genre) must be in missing_data: {ids}"
        # Done songs must not appear
        assert not ids.intersection(
            {1, 2, 3, 4, 5, 6, 8}
        ), f"Done songs in missing_data: {ids}"


# ---------------------------------------------------------------------------
# GET /api/v1/songs/filter — tag
# ---------------------------------------------------------------------------


class TestFilterSongsTag:
    def test_filter_by_era_tag(self, api):
        resp = api.get("/api/v1/songs/filter", params={"tags": "Era:90s"})
        ids = {s["id"] for s in resp.json()}
        assert ids == {2}

    def test_filter_by_mood_tag(self, api):
        resp = api.get("/api/v1/songs/filter", params={"tags": "Mood:Energetic"})
        ids = {s["id"] for s in resp.json()}
        assert ids == {1}
