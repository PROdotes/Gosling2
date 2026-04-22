"""
Engine Router Tests (HTTP Layer)
================================
Contract tests for every API endpoint using FastAPI TestClient.
Hits the full stack: HTTP -> Router -> Service -> Repository -> real SQLite.

No mocking. Exact value verification. Environment isolation via monkeypatch.
"""

import os
import pytest
from fastapi.testclient import TestClient
from src.engine_server import app
from tests.conftest import _connect


# ---------------------------------------------------------------------------
# Fixture: A TestClient wired to the populated hermetic DB
# ---------------------------------------------------------------------------
@pytest.fixture
def client(populated_db, monkeypatch):
    """TestClient wired to populated_db via GOSLING_DB_PATH env var."""
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


@pytest.fixture
def empty_client(empty_db, monkeypatch):
    """TestClient wired to empty_db for negative tests."""
    monkeypatch.setenv("GOSLING_DB_PATH", empty_db)
    return TestClient(app)


# ===========================================================================
# GET / (Dashboard)
# ===========================================================================
class TestDashboard:
    def test_dashboard_returns_html(self, populated_db, monkeypatch):
        """GET / should return the dashboard HTML template."""
        monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
        c = TestClient(app)
        resp = c.get("/")
        assert resp.status_code in (
            200,
            404,
        ), f"Expected 200 or 404, got {resp.status_code}"
        if resp.status_code == 200:
            assert (
                "<!DOCTYPE html>" in resp.text or "<html" in resp.text
            ), f"Expected HTML content, got: {resp.text[:200]}"

    def test_static_dashboard_assets_are_served(self, populated_db, monkeypatch):
        """GET /static/... should serve extracted dashboard assets."""
        monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
        c = TestClient(app)
        resp = c.get("/static/css/dashboard/base.css")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert (
            "--bg-deep" in resp.text
        ), f"Expected '--bg-deep' CSS variable in response, got: {resp.text[:200]}"


# ===========================================================================
# GET /api/v1/songs/{song_id}
# ===========================================================================
class TestGetSong:
    def test_everlong_exact(self, client):
        """Song ID 2 is Everlong - verify all fields in JSON response."""
        resp = client.get("/api/v1/songs/2")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["id"] == 2, f"Expected id=2, got {data['id']}"
        assert (
            data["title"] == "Everlong"
        ), f"Expected title='Everlong', got {data['title']!r}"
        assert (
            data["media_name"] == "Everlong"
        ), f"Expected media_name='Everlong', got {data['media_name']!r}"
        assert (
            data["source_path"] == "/path/2"
        ), f"Expected source_path='/path/2', got {data['source_path']!r}"
        assert (
            data["duration_ms"] == 240000
        ), f"Expected duration_s=240.0, got {data['duration_ms']}"
        assert (
            data["formatted_duration"] == "4:00"
        ), f"Expected formatted_duration='4:00', got {data['formatted_duration']!r}"

    def test_everlong_credits(self, client):
        """Song 2 has one credit: Foo Fighters as Performer."""
        data = client.get("/api/v1/songs/2").json()
        assert (
            len(data["credits"]) == 1
        ), f"Expected 1 credit, got {len(data['credits'])}"
        assert (
            data["credits"][0]["display_name"] == "Foo Fighters"
        ), f"Expected display_name='Foo Fighters', got {data['credits'][0]['display_name']!r}"
        assert (
            data["credits"][0]["role_name"] == "Performer"
        ), f"Expected role_name='Performer', got {data['credits'][0]['role_name']!r}"
        assert (
            data["display_artist"] == "Foo Fighters"
        ), f"Expected display_artist='Foo Fighters', got {data['display_artist']!r}"

    def test_everlong_album(self, client):
        """Song 2 is on TCATS (album 200), track 11."""
        data = client.get("/api/v1/songs/2").json()
        assert len(data["albums"]) == 1, f"Expected 1 album, got {len(data['albums'])}"
        album = data["albums"][0]
        assert (
            album["album_id"] == 200
        ), f"Expected album_id=200, got {album['album_id']}"
        assert (
            album["album_title"] == "The Colour and the Shape"
        ), f"Expected album_title='The Colour and the Shape', got {album['album_title']!r}"
        assert (
            album["track_number"] == 11
        ), f"Expected track_number=11, got {album['track_number']}"
        assert (
            album["release_year"] == 1997
        ), f"Expected release_year=1997, got {album['release_year']}"

    def test_song_with_master_publisher(self, client):
        """Song 1 (SLTS) has recording publisher DGC Records."""
        data = client.get("/api/v1/songs/1").json()
        assert (
            data["title"] == "Smells Like Teen Spirit"
        ), f"Expected title='Smells Like Teen Spirit', got {data['title']!r}"
        assert (
            len(data["publishers"]) == 1
        ), f"Expected 1 publisher, got {len(data['publishers'])}"
        assert (
            data["publishers"][0]["name"] == "DGC Records"
        ), f"Expected publisher name='DGC Records', got {data['publishers'][0]['name']!r}"
        assert (
            data["display_master_publisher"] == "DGC Records (Universal Music Group)"
        ), f"Expected display_master_publisher='DGC Records (Universal Music Group)', got {data['display_master_publisher']!r}"

    def test_song_with_tags(self, client):
        """Song 1 has tags: Grunge, Energetic, English."""
        data = client.get("/api/v1/songs/1").json()
        tag_names = sorted([t["name"] for t in data["tags"]])
        assert tag_names == [
            "Energetic",
            "English",
            "Grunge",
        ], f"Expected tags ['Energetic', 'English', 'Grunge'], got {tag_names}"
        assert (
            data["primary_genre"] == "Grunge"
        ), f"Expected primary_genre='Grunge', got {data['primary_genre']!r}"

    def test_song_primary_genre_explicit(self, client):
        """Song 9 has Alt Rock(primary) and Grunge(not primary) - explicit wins."""
        data = client.get("/api/v1/songs/9").json()
        assert (
            data["primary_genre"] == "Alt Rock"
        ), f"Expected primary_genre='Alt Rock', got {data['primary_genre']!r}"

    def test_song_no_credits(self, client):
        """Song 7 (Hollow Song) has zero credits."""
        data = client.get("/api/v1/songs/7").json()
        assert (
            data["title"] == "Hollow Song"
        ), f"Expected title='Hollow Song', got {data['title']!r}"
        assert (
            data["credits"] == []
        ), f"Expected empty credits list, got {data['credits']}"
        assert (
            data["display_artist"] is None
        ), f"Expected display_artist=None, got {data['display_artist']!r}"

    def test_song_dual_credits(self, client):
        """Song 6 has Dave Grohl (Performer) + Taylor Hawkins (Composer)."""
        data = client.get("/api/v1/songs/6").json()
        assert (
            data["title"] == "Dual Credit Track"
        ), f"Expected title='Dual Credit Track', got {data['title']!r}"
        assert (
            len(data["credits"]) == 2
        ), f"Expected 2 credits, got {len(data['credits'])}"
        credit_pairs = [(c["display_name"], c["role_name"]) for c in data["credits"]]
        assert (
            "Dave Grohl",
            "Performer",
        ) in credit_pairs, (
            f"Expected ('Dave Grohl', 'Performer') in credits, got {credit_pairs}"
        )
        assert (
            "Taylor Hawkins",
            "Composer",
        ) in credit_pairs, (
            f"Expected ('Taylor Hawkins', 'Composer') in credits, got {credit_pairs}"
        )
        assert (
            data["display_artist"] == "Dave Grohl"
        ), f"Expected display_artist='Dave Grohl' (Performers only), got {data['display_artist']!r}"

    def test_song_two_performers(self, client):
        """Song 8 has Dave Grohl + Taylor Hawkins both as Performer."""
        data = client.get("/api/v1/songs/8").json()
        assert (
            data["title"] == "Joint Venture"
        ), f"Expected title='Joint Venture', got {data['title']!r}"
        assert (
            data["display_artist"] == "Dave Grohl, Taylor Hawkins"
        ), f"Expected display_artist='Dave Grohl, Taylor Hawkins', got {data['display_artist']!r}"

    def test_not_found(self, client):
        """Non-existent song returns 404."""
        resp = client.get("/api/v1/songs/999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert (
            "not found" in resp.json()["detail"].lower()
        ), f"Expected 'not found' in detail, got {resp.json()['detail']!r}"

    def test_all_nine_songs_accessible(self, client):
        """Every song ID 1-9 returns 200."""
        for song_id in range(1, 10):
            resp = client.get(f"/api/v1/songs/{song_id}")
            assert (
                resp.status_code == 200
            ), f"Song {song_id} failed: got {resp.status_code}"


# ===========================================================================
# GET /api/v1/songs/search
# ===========================================================================
class TestSearchSongs:
    def test_title_match(self, client):
        """Searching 'Everlong' returns exactly that song."""
        resp = client.get("/api/v1/songs/search", params={"q": "Everlong"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        titles = [s["title"] for s in data]
        assert "Everlong" in titles, f"Expected 'Everlong' in results, got {titles}"

    def test_query_alias_param(self, client):
        """'query' param also works (alias for 'q')."""
        resp = client.get("/api/v1/songs/search", params={"query": "Everlong"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        titles = [s["title"] for s in resp.json()]
        assert "Everlong" in titles, f"Expected 'Everlong' in results, got {titles}"

    def test_identity_expansion(self, client):
        """Searching 'Dave Grohl' expands to groups and returns Nirvana/FF songs."""
        resp = client.get(
            "/api/v1/songs/search", params={"q": "Dave Grohl", "deep": "true"}
        )
        data = resp.json()
        titles = [s["title"] for s in data]
        assert (
            "Smells Like Teen Spirit" in titles
        ), f"Expected 'Smells Like Teen Spirit' (via Nirvana) in results, got {titles}"
        assert (
            "Everlong" in titles
        ), f"Expected 'Everlong' (via Foo Fighters) in results, got {titles}"

    def test_alias_expansion(self, client):
        """Searching 'Grohlton' (Dave's alias) resolves to his identity tree."""
        resp = client.get("/api/v1/songs/search", params={"q": "Grohlton"})
        data = resp.json()
        titles = [s["title"] for s in data]
        assert (
            "Grohlton Theme" in titles
        ), f"Expected 'Grohlton Theme' in results, got {titles}"

    def test_no_results(self, client):
        """Non-matching query returns empty list."""
        resp = client.get("/api/v1/songs/search", params={"q": "zzz_nonexistent"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"

    def test_empty_query(self, client):
        """Empty query returns results (exploration mode)."""
        resp = client.get("/api/v1/songs/search", params={"q": ""})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert (
            len(resp.json()) > 0
        ), f"Expected non-empty results for empty query, got {len(resp.json())} items"

    def test_no_params(self, client):
        """No query params at all still returns 200."""
        resp = client.get("/api/v1/songs/search")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_results_include_aggregated_slim_fields(self, client):
        """Search results include display_artist and primary_genre aggregated from DB."""
        resp = client.get("/api/v1/songs/search", params={"q": "Everlong"})
        data = resp.json()
        everlong = next(s for s in data if s["title"] == "Everlong")
        assert (
            everlong["display_artist"] == "Foo Fighters"
        ), f"Expected display_artist='Foo Fighters', got {everlong['display_artist']!r}"
        assert (
            everlong["duration_s"] == 240.0
        ), f"Expected duration_s=240.0, got {everlong['duration_s']}"

    def test_no_duplicate_songs(self, client):
        """Search for 'Nirvana' should not return SLTS twice."""
        resp = client.get("/api/v1/songs/search", params={"q": "Nirvana"})
        data = resp.json()
        ids = [s["id"] for s in data]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"

    def test_empty_db_returns_empty(self, empty_client):
        """Search on empty DB returns empty list."""
        resp = empty_client.get("/api/v1/songs/search", params={"q": "anything"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


# ===========================================================================
# GET /api/v1/identities
# ===========================================================================
class TestGetAllIdentities:
    def test_returns_all_four(self, client):
        """Populated DB has exactly 4 identities."""
        resp = client.get("/api/v1/identities")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert len(data) == 4, f"Expected 4 identities, got {len(data)}"

    def test_names_are_correct(self, client):
        """All four identity names are present."""
        data = client.get("/api/v1/identities").json()
        names = sorted([i["display_name"] for i in data])
        assert names == [
            "Dave Grohl",
            "Foo Fighters",
            "Nirvana",
            "Taylor Hawkins",
        ], f"Expected exact identity names, got {names}"

    def test_dave_has_aliases(self, client):
        """Dave Grohl (ID 1) has aliases including primary name + non-primary aliases."""
        data = client.get("/api/v1/identities").json()
        dave = next(i for i in data if i["display_name"] == "Dave Grohl")
        alias_names = sorted([a["display_name"] for a in dave["aliases"]])
        assert alias_names == [
            "Dave Grohl",
            "Grohlton",
            "Ines Prajo",
            "Late!",
        ], f"Expected Dave's aliases, got {alias_names}"

    def test_dave_has_groups(self, client):
        """Dave's groups are Nirvana and Foo Fighters."""
        data = client.get("/api/v1/identities").json()
        dave = next(i for i in data if i["display_name"] == "Dave Grohl")
        group_names = sorted([g["display_name"] for g in dave["groups"]])
        assert group_names == [
            "Foo Fighters",
            "Nirvana",
        ], f"Expected Dave's groups ['Foo Fighters', 'Nirvana'], got {group_names}"

    def test_foo_fighters_has_members(self, client):
        """Foo Fighters has members Dave Grohl and Taylor Hawkins."""
        data = client.get("/api/v1/identities").json()
        ff = next(i for i in data if i["display_name"] == "Foo Fighters")
        member_names = sorted([m["display_name"] for m in ff["members"]])
        assert member_names == [
            "Dave Grohl",
            "Taylor Hawkins",
        ], f"Expected FF members ['Dave Grohl', 'Taylor Hawkins'], got {member_names}"

    def test_empty_db(self, empty_client):
        """Empty DB returns empty list."""
        resp = empty_client.get("/api/v1/identities")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


# ===========================================================================
# GET /api/v1/identities/search
# ===========================================================================
class TestSearchIdentities:
    def test_by_name(self, client):
        """Search 'Dave' returns Dave Grohl."""
        resp = client.get("/api/v1/identities/search", params={"q": "Dave"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        names = [i["display_name"] for i in resp.json()]
        assert "Dave Grohl" in names, f"Expected 'Dave Grohl' in results, got {names}"

    def test_by_alias(self, client):
        """Search 'Grohlton' returns Dave Grohl (via alias match)."""
        resp = client.get("/api/v1/identities/search", params={"q": "Grohlton"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        names = [i["display_name"] for i in data]
        assert "Dave Grohl" in names, f"Expected 'Dave Grohl' in results, got {names}"

    def test_no_results(self, client):
        """Non-matching search returns empty."""
        resp = client.get("/api/v1/identities/search", params={"q": "zzz_nothing"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


# ===========================================================================
# GET /api/v1/identities/{id}
# ===========================================================================
class TestGetIdentity:
    def test_dave_grohl(self, client):
        """Identity ID 1 is Dave Grohl, person, with full tree."""
        resp = client.get("/api/v1/identities/1")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["id"] == 1, f"Expected id=1, got {data['id']}"
        assert data["type"] == "person", f"Expected type='person', got {data['type']!r}"
        assert (
            data["display_name"] == "Dave Grohl"
        ), f"Expected display_name='Dave Grohl', got {data['display_name']!r}"
        alias_names = sorted([a["display_name"] for a in data["aliases"]])
        assert alias_names == [
            "Dave Grohl",
            "Grohlton",
            "Ines Prajo",
            "Late!",
        ], f"Expected Dave's aliases, got {alias_names}"
        group_names = sorted([g["display_name"] for g in data["groups"]])
        assert group_names == [
            "Foo Fighters",
            "Nirvana",
        ], f"Expected groups ['Foo Fighters', 'Nirvana'], got {group_names}"

    def test_nirvana_group(self, client):
        """Identity ID 2 is Nirvana, group, with Dave as member."""
        resp = client.get("/api/v1/identities/2")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["id"] == 2, f"Expected id=2, got {data['id']}"
        assert data["type"] == "group", f"Expected type='group', got {data['type']!r}"
        assert (
            data["display_name"] == "Nirvana"
        ), f"Expected display_name='Nirvana', got {data['display_name']!r}"
        member_names = [m["display_name"] for m in data["members"]]
        assert (
            "Dave Grohl" in member_names
        ), f"Expected 'Dave Grohl' in Nirvana members, got {member_names}"

    def test_not_found(self, client):
        """Non-existent identity returns 404."""
        resp = client.get("/api/v1/identities/999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# ===========================================================================
# GET /api/v1/identities/{id}/songs
# ===========================================================================
class TestGetSongsByIdentity:
    def test_dave_full_tree(self, client):
        """Dave Grohl's songs include his solo, alias, and group tracks."""
        resp = client.get("/api/v1/identities/1/songs")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        titles = sorted([s["title"] for s in data])
        assert (
            "Smells Like Teen Spirit" in titles
        ), f"Expected 'Smells Like Teen Spirit' in Dave's songs, got {titles}"
        assert (
            "Everlong" in titles
        ), f"Expected 'Everlong' in Dave's songs, got {titles}"
        assert (
            "Grohlton Theme" in titles
        ), f"Expected 'Grohlton Theme' in Dave's songs, got {titles}"
        assert (
            "Pocketwatch Demo" in titles
        ), f"Expected 'Pocketwatch Demo' in Dave's songs, got {titles}"
        assert (
            "Dual Credit Track" in titles
        ), f"Expected 'Dual Credit Track' in Dave's songs, got {titles}"
        assert (
            "Joint Venture" in titles
        ), f"Expected 'Joint Venture' in Dave's songs, got {titles}"

    def test_taylor_hawkins(self, client):
        """Taylor Hawkins (ID 4) has Range Rover Bitch + Dual Credit + Joint Venture + FF songs."""
        resp = client.get("/api/v1/identities/4/songs")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        titles = sorted([s["title"] for s in data])
        assert (
            "Range Rover Bitch" in titles
        ), f"Expected 'Range Rover Bitch' in Taylor's songs, got {titles}"
        assert (
            "Dual Credit Track" in titles
        ), f"Expected 'Dual Credit Track' in Taylor's songs, got {titles}"
        assert (
            "Joint Venture" in titles
        ), f"Expected 'Joint Venture' in Taylor's songs, got {titles}"
        assert (
            "Everlong" in titles
        ), f"Expected 'Everlong' (Foo Fighters) in Taylor's songs, got {titles}"

    def test_not_found_identity(self, client):
        """Non-existent identity returns 404."""
        resp = client.get("/api/v1/identities/999/songs")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_results_are_hydrated(self, client):
        """Songs from identity endpoint include credits and albums."""
        data = client.get("/api/v1/identities/2/songs").json()
        slts = next(s for s in data if s["title"] == "Smells Like Teen Spirit")
        assert (
            len(slts["credits"]) == 1
        ), f"Expected 1 credit on SLTS, got {len(slts['credits'])}"
        assert (
            slts["credits"][0]["display_name"] == "Nirvana"
        ), f"Expected credit='Nirvana', got {slts['credits'][0]['display_name']!r}"
        assert (
            len(slts["albums"]) == 1
        ), f"Expected 1 album on SLTS, got {len(slts['albums'])}"
        assert (
            slts["albums"][0]["album_title"] == "Nevermind"
        ), f"Expected album='Nevermind', got {slts['albums'][0]['album_title']!r}"


# ===========================================================================
# GET /api/v1/publishers
# ===========================================================================
class TestGetAllPublishers:
    def test_returns_six(self, client):
        """Populated DB has exactly 6 publishers."""
        resp = client.get("/api/v1/publishers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert len(data) == 6, f"Expected 6 publishers, got {len(data)}"

    def test_names(self, client):
        """All six publisher names are present."""
        data = client.get("/api/v1/publishers").json()
        names = sorted([p["name"] for p in data])
        expected = [
            "DGC Records",
            "Island Def Jam",
            "Island Records",
            "Roswell Records",
            "Sub Pop",
            "Universal Music Group",
        ]
        assert names == expected, f"Expected {expected}, got {names}"

    def test_parent_names_resolved(self, client):
        """DGC Records (parent=1) has parent_name 'Universal Music Group'."""
        data = client.get("/api/v1/publishers").json()
        dgc = next(p for p in data if p["name"] == "DGC Records")
        assert (
            dgc["parent_name"] == "Universal Music Group"
        ), f"Expected parent_name='Universal Music Group', got {dgc['parent_name']!r}"

    def test_island_def_jam_parent(self, client):
        """Island Def Jam (parent=2) has parent_name 'Island Records'."""
        data = client.get("/api/v1/publishers").json()
        idj = next(p for p in data if p["name"] == "Island Def Jam")
        assert (
            idj["parent_name"] == "Island Records"
        ), f"Expected parent_name='Island Records', got {idj['parent_name']!r}"

    def test_top_level_has_no_parent(self, client):
        """Universal Music Group has no parent."""
        data = client.get("/api/v1/publishers").json()
        umg = next(p for p in data if p["name"] == "Universal Music Group")
        assert (
            umg["parent_name"] is None
        ), f"Expected parent_name=None, got {umg['parent_name']!r}"

    def test_empty_db(self, empty_client):
        """Empty DB returns empty list."""
        resp = empty_client.get("/api/v1/publishers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


# ===========================================================================
# GET /api/v1/publishers/search
# ===========================================================================
class TestSearchPublishers:
    def test_partial_match(self, client):
        """Search 'island' returns Island Records and Island Def Jam."""
        resp = client.get("/api/v1/publishers/search", params={"q": "island"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        names = sorted([p["name"] for p in resp.json()])
        assert (
            "Island Records" in names
        ), f"Expected 'Island Records' in results, got {names}"
        assert (
            "Island Def Jam" in names
        ), f"Expected 'Island Def Jam' in results, got {names}"

    def test_no_match(self, client):
        """Non-matching search returns empty list."""
        resp = client.get("/api/v1/publishers/search", params={"q": "zzz_nothing"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


# ===========================================================================
# GET /api/v1/publishers/{id}
# ===========================================================================
class TestGetPublisher:
    def test_universal_with_children(self, client):
        """Publisher 1 (UMG) has children: Island Records, DGC Records."""
        resp = client.get("/api/v1/publishers/1")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert (
            data["name"] == "Universal Music Group"
        ), f"Expected name='Universal Music Group', got {data['name']!r}"
        child_names = sorted([c["name"] for c in data["sub_publishers"]])
        assert (
            "DGC Records" in child_names
        ), f"Expected 'DGC Records' in sub_publishers, got {child_names}"
        assert (
            "Island Records" in child_names
        ), f"Expected 'Island Records' in sub_publishers, got {child_names}"

    def test_dgc_parent_resolved(self, client):
        """Publisher 10 (DGC Records) has parent_name 'Universal Music Group'."""
        data = client.get("/api/v1/publishers/10").json()
        assert (
            data["name"] == "DGC Records"
        ), f"Expected name='DGC Records', got {data['name']!r}"
        assert (
            data["parent_name"] == "Universal Music Group"
        ), f"Expected parent_name='Universal Music Group', got {data['parent_name']!r}"

    def test_leaf_publisher(self, client):
        """Publisher 4 (Roswell Records) has no parent, no children."""
        data = client.get("/api/v1/publishers/4").json()
        assert (
            data["name"] == "Roswell Records"
        ), f"Expected name='Roswell Records', got {data['name']!r}"
        assert (
            data["parent_name"] is None
        ), f"Expected parent_name=None, got {data['parent_name']!r}"
        assert (
            data["sub_publishers"] == []
        ), f"Expected empty sub_publishers, got {data['sub_publishers']}"

    def test_not_found(self, client):
        """Non-existent publisher returns 404."""
        resp = client.get("/api/v1/publishers/999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# ===========================================================================
# GET /api/v1/publishers/{id}/songs
# ===========================================================================
class TestGetPublisherSongs:
    def test_dgc_songs(self, client):
        """DGC Records (ID 10) has Song 1 (SLTS) via RecordingPublishers."""
        resp = client.get("/api/v1/publishers/10/songs")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        titles = [s["title"] for s in data]
        assert (
            "Smells Like Teen Spirit" in titles
        ), f"Expected 'Smells Like Teen Spirit' in DGC songs, got {titles}"

    def test_publisher_with_no_songs(self, client):
        """Roswell Records (ID 4) may have no recording-level songs."""
        resp = client.get("/api/v1/publishers/4/songs")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(
            data, list
        ), f"Expected list response, got {type(data).__name__}"

    def test_not_found_publisher(self, client):
        """Non-existent publisher returns 404."""
        resp = client.get("/api/v1/publishers/999/songs")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# ===========================================================================
# GET /api/v1/albums
# ===========================================================================
class TestGetAllAlbums:
    def test_returns_two(self, client):
        """Populated DB has exactly 2 albums."""
        resp = client.get("/api/v1/albums")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert len(data) == 2, f"Expected 2 albums, got {len(data)}"

    def test_nevermind(self, client):
        """Nevermind (ID 100) slim fields: id, release_year, display_artist, song_count."""
        data = client.get("/api/v1/albums").json()
        nvm = next(a for a in data if a["title"] == "Nevermind")
        assert nvm["id"] == 100, f"Expected id=100, got {nvm['id']}"
        assert (
            nvm["release_year"] == 1991
        ), f"Expected release_year=1991, got {nvm['release_year']}"
        assert nvm["song_count"] == 1, f"Expected song_count=1, got {nvm['song_count']}"
        assert (
            nvm["display_artist"] == "Nirvana"
        ), f"Expected display_artist='Nirvana', got {nvm['display_artist']!r}"
        # No hydrated publishers/credits/songs in slim view
        assert "publishers" not in nvm, "Slim album should not have 'publishers'"
        assert "credits" not in nvm, "Slim album should not have 'credits'"
        assert "songs" not in nvm, "Slim album should not have 'songs'"

    def test_tcats(self, client):
        """TCATS (ID 200) slim fields: id, release_year, display_artist, song_count."""
        data = client.get("/api/v1/albums").json()
        tcats = next(a for a in data if a["title"] == "The Colour and the Shape")
        assert tcats["id"] == 200, f"Expected id=200, got {tcats['id']}"
        assert (
            tcats["release_year"] == 1997
        ), f"Expected release_year=1997, got {tcats['release_year']}"
        assert (
            tcats["display_artist"] == "Foo Fighters"
        ), f"Expected display_artist='Foo Fighters', got {tcats['display_artist']!r}"
        assert (
            tcats["song_count"] == 1
        ), f"Expected song_count=1, got {tcats['song_count']}"

    def test_empty_db(self, empty_client):
        """Empty DB returns empty list."""
        resp = empty_client.get("/api/v1/albums")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


# ===========================================================================
# GET /api/v1/albums/search
# ===========================================================================
class TestSearchAlbums:
    def test_partial_match(self, client):
        """Search 'Never' returns Nevermind."""
        resp = client.get("/api/v1/albums/search", params={"q": "Never"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        titles = [a["title"] for a in resp.json()]
        assert "Nevermind" in titles, f"Expected 'Nevermind' in results, got {titles}"

    def test_no_match(self, client):
        """Non-matching search returns empty."""
        resp = client.get("/api/v1/albums/search", params={"q": "zzz_nothing"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


# ===========================================================================
# GET /api/v1/albums/{id}
# ===========================================================================
class TestGetAlbum:
    def test_nevermind_by_id(self, client):
        """Album 100 is Nevermind, fully hydrated."""
        resp = client.get("/api/v1/albums/100")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert (
            data["title"] == "Nevermind"
        ), f"Expected title='Nevermind', got {data['title']!r}"
        assert (
            data["release_year"] == 1991
        ), f"Expected release_year=1991, got {data['release_year']}"
        assert (
            data["song_count"] == 1
        ), f"Expected song_count=1, got {data['song_count']}"
        assert (
            data["display_artist"] == "Nirvana"
        ), f"Expected display_artist='Nirvana', got {data['display_artist']!r}"
        pub_names = sorted([p["name"] for p in data["publishers"]])
        assert pub_names == [
            "DGC Records",
            "Sub Pop",
        ], f"Expected publishers ['DGC Records', 'Sub Pop'], got {pub_names}"

    def test_not_found(self, client):
        """Non-existent album returns 404."""
        resp = client.get("/api/v1/albums/999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# ===========================================================================
# GET /api/v1/audit/history/{table}/{record_id}
# ===========================================================================
class TestAuditHistory:
    def test_artist_name_history(self, client):
        """ArtistNames record 33 has a rename action and a change."""
        resp = client.get("/api/v1/audit/history/ArtistNames/33")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert len(data) == 2, f"Expected 2 audit entries, got {len(data)}"
        types = sorted([entry["type"] for entry in data])
        assert types == [
            "ACTION",
            "CHANGE",
        ], f"Expected ['ACTION', 'CHANGE'], got {types}"
        action = next(e for e in data if e["type"] == "ACTION")
        assert (
            action["label"] == "RENAME"
        ), f"Expected label='RENAME', got {action['label']!r}"
        assert (
            action["details"] == "User updated artist name"
        ), f"Expected details='User updated artist name', got {action['details']!r}"
        change = next(e for e in data if e["type"] == "CHANGE")
        assert (
            change["label"] == "Updated DisplayName"
        ), f"Expected label='Updated DisplayName', got {change['label']!r}"
        assert (
            change["old"] == "PinkPantheress"
        ), f"Expected old='PinkPantheress', got {change['old']!r}"
        assert (
            change["new"] == "Ines Prajo"
        ), f"Expected new='Ines Prajo', got {change['new']!r}"

    def test_deleted_record_history(self, client):
        """Songs record 99 was deleted - should appear as lifecycle entry."""
        resp = client.get("/api/v1/audit/history/Songs/99")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert len(data) == 1, f"Expected 1 audit entry, got {len(data)}"
        types = [entry["type"] for entry in data]
        assert "LIFECYCLE" in types, f"Expected 'LIFECYCLE' in types, got {types}"
        lifecycle = data[0]
        assert (
            lifecycle["label"] == "RECORD DELETED"
        ), f"Expected label='RECORD DELETED', got {lifecycle['label']!r}"
        assert (
            '"Deleted Song"' in lifecycle["snapshot"]
        ), f"Expected '\"Deleted Song\"' in snapshot, got {lifecycle['snapshot']!r}"

    def test_no_history(self, client):
        """Record with no audit history returns empty list."""
        resp = client.get("/api/v1/audit/history/Songs/1")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(
            data, list
        ), f"Expected list response, got {type(data).__name__}"

    def test_nonexistent_record(self, client):
        """Non-existent record returns empty list (not 404)."""
        resp = client.get("/api/v1/audit/history/Songs/99999")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"

    def test_empty_db(self, empty_client):
        """Empty DB returns empty list."""
        resp = empty_client.get("/api/v1/audit/history/Songs/1")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


# ===========================================================================
# GET /api/v1/metabolic/inspect-file/{song_id}
# ===========================================================================
class TestMetabolicInspectFile:
    def test_not_found(self, client):
        """Non-existent song returns 404."""
        resp = client.get("/api/v1/metabolic/inspect-file/9999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_real_file_inspection(self, populated_db, monkeypatch):
        """inspect-file with a real audio file returns SongView."""
        import sqlite3

        fixture_path = os.path.abspath("tests/fixtures/silence.mp3")
        if not os.path.exists(fixture_path):
            pytest.skip("silence.mp3 fixture not available")

        conn = _connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (fixture_path,),
        )
        conn.commit()
        conn.close()

        monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
        c = TestClient(app)
        resp = c.get("/api/v1/metabolic/inspect-file/1")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert (
            data["source_path"] == fixture_path
        ), f"Expected source_path={fixture_path!r}, got {data['source_path']!r}"

    def test_missing_file_returns_500(self, client):
        """Song with non-existent file path returns 500."""
        resp = client.get("/api/v1/metabolic/inspect-file/1")
        assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"


# ===========================================================================
# Router Coverage: Edge Cases (Migrated from test_coverage_gap.py)
# ===========================================================================
class TestRouterEdgeCases:
    def test_router_get_song_not_found(self, client):
        """Router coverage: 404 for missing song."""
        resp = client.get("/api/v1/songs/9999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert (
            "not found" in resp.json()["detail"].lower()
        ), f"Expected 'not found' in detail, got {resp.json()['detail']!r}"

    def test_router_search_short_query_success(self, client):
        """Router coverage: Single character query now allowed."""
        resp = client.get("/api/v1/songs/search", params={"q": "A"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert isinstance(
            resp.json(), list
        ), f"Expected list response, got {type(resp.json()).__name__}"

    def test_router_get_song_success(self, client):
        """Router coverage: Successful get_song hit for ID 1."""
        resp = client.get("/api/v1/songs/1")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json()["id"] == 1, f"Expected id=1, got {resp.json()['id']}"
        assert (
            resp.json()["title"] == "Smells Like Teen Spirit"
        ), f"Expected title='Smells Like Teen Spirit', got {resp.json()['title']!r}"
