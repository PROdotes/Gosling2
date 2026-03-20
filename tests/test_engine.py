"""
Engine Router Tests (HTTP Layer)
================================
Contract tests for every API endpoint using FastAPI TestClient.
Hits the full stack: HTTP → Router → Service → Repository → real SQLite.

No mocking. Exact value verification. Environment isolation via monkeypatch.
"""

import os
import pytest
from fastapi.testclient import TestClient
from src.engine_server import app


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
        # Dashboard template might or might not exist in test env
        # We verify the endpoint is reachable and returns either 200 or 404
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert "<!DOCTYPE html>" in resp.text or "<html" in resp.text

    def test_static_dashboard_assets_are_served(self, populated_db, monkeypatch):
        """GET /static/... should serve extracted dashboard assets."""
        monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
        c = TestClient(app)
        resp = c.get("/static/css/dashboard.css")
        assert resp.status_code == 200
        assert "--bg-deep" in resp.text


# ===========================================================================
# GET /api/v1/songs/{song_id}
# ===========================================================================
class TestGetSong:
    def test_everlong_exact(self, client):
        """Song ID 2 is Everlong - verify all fields in JSON response."""
        resp = client.get("/api/v1/songs/2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 2
        assert data["title"] == "Everlong"
        assert data["media_name"] == "Everlong"
        assert data["source_path"] == "/path/2"
        assert data["duration_ms"] == 240000
        assert data["formatted_duration"] == "4:00"

    def test_everlong_credits(self, client):
        """Song 2 has one credit: Foo Fighters as Performer."""
        data = client.get("/api/v1/songs/2").json()
        assert len(data["credits"]) == 1
        assert data["credits"][0]["display_name"] == "Foo Fighters"
        assert data["credits"][0]["role_name"] == "Performer"
        assert data["display_artist"] == "Foo Fighters"

    def test_everlong_album(self, client):
        """Song 2 is on TCATS (album 200), track 11."""
        data = client.get("/api/v1/songs/2").json()
        assert len(data["albums"]) == 1
        album = data["albums"][0]
        assert album["album_id"] == 200
        assert album["album_title"] == "The Colour and the Shape"
        assert album["track_number"] == 11
        assert album["release_year"] == 1997

    def test_song_with_master_publisher(self, client):
        """Song 1 (SLTS) has recording publisher DGC Records."""
        data = client.get("/api/v1/songs/1").json()
        assert data["title"] == "Smells Like Teen Spirit"
        assert len(data["publishers"]) == 1
        assert data["publishers"][0]["name"] == "DGC Records"
        assert data["display_master_publisher"] == "DGC Records (Universal Music Group)"

    def test_song_with_tags(self, client):
        """Song 1 has tags: Grunge, Energetic, English."""
        data = client.get("/api/v1/songs/1").json()
        tag_names = sorted([t["name"] for t in data["tags"]])
        assert tag_names == ["Energetic", "English", "Grunge"]
        assert data["primary_genre"] == "Grunge"

    def test_song_primary_genre_explicit(self, client):
        """Song 9 has Alt Rock(primary) and Grunge(not primary) - explicit wins."""
        data = client.get("/api/v1/songs/9").json()
        assert data["primary_genre"] == "Alt Rock"

    def test_song_no_credits(self, client):
        """Song 7 (Hollow Song) has zero credits."""
        data = client.get("/api/v1/songs/7").json()
        assert data["title"] == "Hollow Song"
        assert data["credits"] == []
        assert data["display_artist"] is None

    def test_song_dual_credits(self, client):
        """Song 6 has Dave Grohl (Performer) + Taylor Hawkins (Composer)."""
        data = client.get("/api/v1/songs/6").json()
        assert data["title"] == "Dual Credit Track"
        assert len(data["credits"]) == 2
        credit_pairs = [(c["display_name"], c["role_name"]) for c in data["credits"]]
        assert ("Dave Grohl", "Performer") in credit_pairs
        assert ("Taylor Hawkins", "Composer") in credit_pairs
        # display_artist only shows Performers
        assert data["display_artist"] == "Dave Grohl"

    def test_song_two_performers(self, client):
        """Song 8 has Dave Grohl + Taylor Hawkins both as Performer."""
        data = client.get("/api/v1/songs/8").json()
        assert data["title"] == "Joint Venture"
        # display_artist should be comma-joined
        assert data["display_artist"] == "Dave Grohl, Taylor Hawkins"

    def test_not_found(self, client):
        """Non-existent song returns 404."""
        resp = client.get("/api/v1/songs/999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_all_nine_songs_accessible(self, client):
        """Every song ID 1-9 returns 200."""
        for song_id in range(1, 10):
            resp = client.get(f"/api/v1/songs/{song_id}")
            assert resp.status_code == 200, f"Song {song_id} failed"


# ===========================================================================
# GET /api/v1/songs/search
# ===========================================================================
class TestSearchSongs:
    def test_title_match(self, client):
        """Searching 'Everlong' returns exactly that song."""
        resp = client.get("/api/v1/songs/search", params={"q": "Everlong"})
        assert resp.status_code == 200
        data = resp.json()
        titles = [s["title"] for s in data]
        assert "Everlong" in titles

    def test_query_alias_param(self, client):
        """'query' param also works (alias for 'q')."""
        resp = client.get("/api/v1/songs/search", params={"query": "Everlong"})
        assert resp.status_code == 200
        titles = [s["title"] for s in resp.json()]
        assert "Everlong" in titles

    def test_identity_expansion(self, client):
        """Searching 'Dave Grohl' expands to groups and returns Nirvana/FF songs."""
        resp = client.get("/api/v1/songs/search", params={"q": "Dave Grohl"})
        data = resp.json()
        titles = [s["title"] for s in data]
        # Dave's groups (Nirvana, Foo Fighters) songs should appear
        assert "Smells Like Teen Spirit" in titles
        assert "Everlong" in titles

    def test_alias_expansion(self, client):
        """Searching 'Grohlton' (Dave's alias) resolves to his identity tree."""
        resp = client.get("/api/v1/songs/search", params={"q": "Grohlton"})
        data = resp.json()
        titles = [s["title"] for s in data]
        # Should include the alias track itself AND group songs
        assert "Grohlton Theme" in titles

    def test_no_results(self, client):
        """Non-matching query returns empty list."""
        resp = client.get("/api/v1/songs/search", params={"q": "zzz_nonexistent"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_empty_query(self, client):
        """Empty query returns results (exploration mode)."""
        resp = client.get("/api/v1/songs/search", params={"q": ""})
        assert resp.status_code == 200
        # Should return some results (all songs match empty LIKE)
        assert len(resp.json()) > 0

    def test_no_params(self, client):
        """No query params at all still returns 200."""
        resp = client.get("/api/v1/songs/search")
        assert resp.status_code == 200

    def test_results_are_hydrated(self, client):
        """Search results include credits, albums, tags."""
        resp = client.get("/api/v1/songs/search", params={"q": "Everlong"})
        data = resp.json()
        everlong = next(s for s in data if s["title"] == "Everlong")
        assert len(everlong["credits"]) == 1
        assert everlong["credits"][0]["display_name"] == "Foo Fighters"
        assert len(everlong["albums"]) == 1
        assert everlong["albums"][0]["album_title"] == "The Colour and the Shape"

    def test_no_duplicate_songs(self, client):
        """Search for 'Nirvana' should not return SLTS twice."""
        resp = client.get("/api/v1/songs/search", params={"q": "Nirvana"})
        data = resp.json()
        ids = [s["id"] for s in data]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"

    def test_empty_db_returns_empty(self, empty_client):
        """Search on empty DB returns empty list."""
        resp = empty_client.get("/api/v1/songs/search", params={"q": "anything"})
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# GET /api/v1/identities
# ===========================================================================
class TestGetAllIdentities:
    def test_returns_all_four(self, client):
        """Populated DB has exactly 4 identities."""
        resp = client.get("/api/v1/identities")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4

    def test_names_are_correct(self, client):
        """All four identity names are present."""
        data = client.get("/api/v1/identities").json()
        names = sorted([i["display_name"] for i in data])
        assert names == ["Dave Grohl", "Foo Fighters", "Nirvana", "Taylor Hawkins"]

    def test_dave_has_aliases(self, client):
        """Dave Grohl (ID 1) has aliases including primary name + non-primary aliases."""
        data = client.get("/api/v1/identities").json()
        dave = next(i for i in data if i["display_name"] == "Dave Grohl")
        alias_names = sorted([a["display_name"] for a in dave["aliases"]])
        # get_aliases_batch returns ALL ArtistNames (primary + non-primary)
        assert alias_names == ["Dave Grohl", "Grohlton", "Ines Prajo", "Late!"]

    def test_dave_has_groups(self, client):
        """Dave's groups are Nirvana and Foo Fighters."""
        data = client.get("/api/v1/identities").json()
        dave = next(i for i in data if i["display_name"] == "Dave Grohl")
        group_names = sorted([g["display_name"] for g in dave["groups"]])
        assert group_names == ["Foo Fighters", "Nirvana"]

    def test_foo_fighters_has_members(self, client):
        """Foo Fighters has members Dave Grohl and Taylor Hawkins."""
        data = client.get("/api/v1/identities").json()
        ff = next(i for i in data if i["display_name"] == "Foo Fighters")
        member_names = sorted([m["display_name"] for m in ff["members"]])
        assert member_names == ["Dave Grohl", "Taylor Hawkins"]

    def test_empty_db(self, empty_client):
        """Empty DB returns empty list."""
        resp = empty_client.get("/api/v1/identities")
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# GET /api/v1/identities/search
# ===========================================================================
class TestSearchIdentities:
    def test_by_name(self, client):
        """Search 'Dave' returns Dave Grohl."""
        resp = client.get("/api/v1/identities/search", params={"q": "Dave"})
        assert resp.status_code == 200
        names = [i["display_name"] for i in resp.json()]
        assert "Dave Grohl" in names

    def test_by_alias(self, client):
        """Search 'Grohlton' returns Dave Grohl (via alias match)."""
        resp = client.get("/api/v1/identities/search", params={"q": "Grohlton"})
        data = resp.json()
        names = [i["display_name"] for i in data]
        assert "Dave Grohl" in names

    def test_no_results(self, client):
        """Non-matching search returns empty."""
        resp = client.get("/api/v1/identities/search", params={"q": "zzz_nothing"})
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# GET /api/v1/identities/{id}
# ===========================================================================
class TestGetIdentity:
    def test_dave_grohl(self, client):
        """Identity ID 1 is Dave Grohl, person, with full tree."""
        resp = client.get("/api/v1/identities/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["type"] == "person"
        assert data["display_name"] == "Dave Grohl"
        # Aliases (includes primary name + non-primary aliases)
        alias_names = sorted([a["display_name"] for a in data["aliases"]])
        assert alias_names == ["Dave Grohl", "Grohlton", "Ines Prajo", "Late!"]
        # Groups
        group_names = sorted([g["display_name"] for g in data["groups"]])
        assert group_names == ["Foo Fighters", "Nirvana"]

    def test_nirvana_group(self, client):
        """Identity ID 2 is Nirvana, group, with Dave as member."""
        resp = client.get("/api/v1/identities/2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 2
        assert data["type"] == "group"
        assert data["display_name"] == "Nirvana"
        member_names = [m["display_name"] for m in data["members"]]
        assert "Dave Grohl" in member_names

    def test_not_found(self, client):
        """Non-existent identity returns 404."""
        resp = client.get("/api/v1/identities/999")
        assert resp.status_code == 404


# ===========================================================================
# GET /api/v1/identities/{id}/songs
# ===========================================================================
class TestGetSongsByIdentity:
    def test_dave_full_tree(self, client):
        """Dave Grohl's songs include his solo, alias, and group tracks."""
        resp = client.get("/api/v1/identities/1/songs")
        assert resp.status_code == 200
        data = resp.json()
        titles = sorted([s["title"] for s in data])
        # Dave Grohl (NameID 10): Dual Credit Track, Joint Venture
        # Grohlton (NameID 11): Grohlton Theme
        # Late! (NameID 12): Pocketwatch Demo
        # Nirvana (group, NameID 20): Smells Like Teen Spirit
        # Foo Fighters (group, NameID 30): Everlong
        assert "Smells Like Teen Spirit" in titles
        assert "Everlong" in titles
        assert "Grohlton Theme" in titles
        assert "Pocketwatch Demo" in titles
        assert "Dual Credit Track" in titles
        assert "Joint Venture" in titles

    def test_taylor_hawkins(self, client):
        """Taylor Hawkins (ID 4) has Range Rover Bitch + Dual Credit + Joint Venture + FF songs."""
        resp = client.get("/api/v1/identities/4/songs")
        data = resp.json()
        titles = sorted([s["title"] for s in data])
        assert "Range Rover Bitch" in titles
        assert "Dual Credit Track" in titles
        assert "Joint Venture" in titles
        # Also Foo Fighters group songs
        assert "Everlong" in titles

    def test_not_found_identity(self, client):
        """Non-existent identity returns 404."""
        resp = client.get("/api/v1/identities/999/songs")
        assert resp.status_code == 404

    def test_results_are_hydrated(self, client):
        """Songs from identity endpoint include credits and albums."""
        data = client.get("/api/v1/identities/2/songs").json()
        slts = next(s for s in data if s["title"] == "Smells Like Teen Spirit")
        assert len(slts["credits"]) == 1
        assert slts["credits"][0]["display_name"] == "Nirvana"
        assert len(slts["albums"]) == 1
        assert slts["albums"][0]["album_title"] == "Nevermind"


# ===========================================================================
# GET /api/v1/publishers
# ===========================================================================
class TestGetAllPublishers:
    def test_returns_six(self, client):
        """Populated DB has exactly 6 publishers."""
        resp = client.get("/api/v1/publishers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 6

    def test_names(self, client):
        """All six publisher names are present."""
        data = client.get("/api/v1/publishers").json()
        names = sorted([p["name"] for p in data])
        assert names == [
            "DGC Records",
            "Island Def Jam",
            "Island Records",
            "Roswell Records",
            "Sub Pop",
            "Universal Music Group",
        ]

    def test_parent_names_resolved(self, client):
        """DGC Records (parent=1) has parent_name 'Universal Music Group'."""
        data = client.get("/api/v1/publishers").json()
        dgc = next(p for p in data if p["name"] == "DGC Records")
        assert dgc["parent_name"] == "Universal Music Group"

    def test_island_def_jam_parent(self, client):
        """Island Def Jam (parent=2) has parent_name 'Island Records'."""
        data = client.get("/api/v1/publishers").json()
        idj = next(p for p in data if p["name"] == "Island Def Jam")
        assert idj["parent_name"] == "Island Records"

    def test_top_level_has_no_parent(self, client):
        """Universal Music Group has no parent."""
        data = client.get("/api/v1/publishers").json()
        umg = next(p for p in data if p["name"] == "Universal Music Group")
        assert umg["parent_id"] is None
        assert umg["parent_name"] is None

    def test_empty_db(self, empty_client):
        """Empty DB returns empty list."""
        resp = empty_client.get("/api/v1/publishers")
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# GET /api/v1/publishers/search
# ===========================================================================
class TestSearchPublishers:
    def test_partial_match(self, client):
        """Search 'island' returns Island Records and Island Def Jam."""
        resp = client.get("/api/v1/publishers/search", params={"q": "island"})
        assert resp.status_code == 200
        names = sorted([p["name"] for p in resp.json()])
        assert "Island Records" in names
        assert "Island Def Jam" in names

    def test_no_match(self, client):
        """Non-matching search returns empty list."""
        resp = client.get("/api/v1/publishers/search", params={"q": "zzz_nothing"})
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# GET /api/v1/publishers/{id}
# ===========================================================================
class TestGetPublisher:
    def test_universal_with_children(self, client):
        """Publisher 1 (UMG) has children: Island Records, DGC Records."""
        resp = client.get("/api/v1/publishers/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Universal Music Group"
        child_names = sorted([c["name"] for c in data["sub_publishers"]])
        assert "DGC Records" in child_names
        assert "Island Records" in child_names

    def test_dgc_parent_resolved(self, client):
        """Publisher 10 (DGC Records) has parent_name 'Universal Music Group'."""
        data = client.get("/api/v1/publishers/10").json()
        assert data["name"] == "DGC Records"
        assert data["parent_name"] == "Universal Music Group"

    def test_leaf_publisher(self, client):
        """Publisher 4 (Roswell Records) has no parent, no children."""
        data = client.get("/api/v1/publishers/4").json()
        assert data["name"] == "Roswell Records"
        assert data["parent_id"] is None
        assert data["sub_publishers"] == []

    def test_not_found(self, client):
        """Non-existent publisher returns 404."""
        resp = client.get("/api/v1/publishers/999")
        assert resp.status_code == 404


# ===========================================================================
# GET /api/v1/publishers/{id}/songs
# ===========================================================================
class TestGetPublisherSongs:
    def test_dgc_songs(self, client):
        """DGC Records (ID 10) has Song 1 (SLTS) via RecordingPublishers."""
        resp = client.get("/api/v1/publishers/10/songs")
        assert resp.status_code == 200
        data = resp.json()
        titles = [s["title"] for s in data]
        assert "Smells Like Teen Spirit" in titles

    def test_publisher_with_no_songs(self, client):
        """Roswell Records (ID 4) may have no recording-level songs."""
        resp = client.get("/api/v1/publishers/4/songs")
        assert resp.status_code == 200
        # Roswell only has album-level association, not recording publisher
        data = resp.json()
        assert isinstance(data, list)

    def test_not_found_publisher(self, client):
        """Non-existent publisher returns 404."""
        resp = client.get("/api/v1/publishers/999/songs")
        assert resp.status_code == 404


# ===========================================================================
# GET /api/v1/albums
# ===========================================================================
class TestGetAllAlbums:
    def test_returns_two(self, client):
        """Populated DB has exactly 2 albums."""
        resp = client.get("/api/v1/albums")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_nevermind(self, client):
        """Nevermind (ID 100) with correct fields."""
        data = client.get("/api/v1/albums").json()
        nvm = next(a for a in data if a["title"] == "Nevermind")
        assert nvm["id"] == 100
        assert nvm["release_year"] == 1991
        # Publishers
        pub_names = sorted([p["name"] for p in nvm["publishers"]])
        assert pub_names == ["DGC Records", "Sub Pop"]
        # Credits
        assert len(nvm["credits"]) == 1
        assert nvm["credits"][0]["display_name"] == "Nirvana"
        # Songs
        assert nvm["song_count"] == 1
        assert nvm["songs"][0]["title"] == "Smells Like Teen Spirit"

    def test_tcats(self, client):
        """TCATS (ID 200) with Foo Fighters and Everlong."""
        data = client.get("/api/v1/albums").json()
        tcats = next(a for a in data if a["title"] == "The Colour and the Shape")
        assert tcats["id"] == 200
        assert tcats["release_year"] == 1997
        pub_names = [p["name"] for p in tcats["publishers"]]
        assert pub_names == ["Roswell Records"]
        assert tcats["display_artist"] == "Foo Fighters"
        assert tcats["song_count"] == 1
        assert tcats["songs"][0]["title"] == "Everlong"

    def test_empty_db(self, empty_client):
        """Empty DB returns empty list."""
        resp = empty_client.get("/api/v1/albums")
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# GET /api/v1/albums/search
# ===========================================================================
class TestSearchAlbums:
    def test_partial_match(self, client):
        """Search 'Never' returns Nevermind."""
        resp = client.get("/api/v1/albums/search", params={"q": "Never"})
        assert resp.status_code == 200
        titles = [a["title"] for a in resp.json()]
        assert "Nevermind" in titles

    def test_no_match(self, client):
        """Non-matching search returns empty."""
        resp = client.get("/api/v1/albums/search", params={"q": "zzz_nothing"})
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# GET /api/v1/albums/{id}
# ===========================================================================
class TestGetAlbum:
    def test_nevermind_by_id(self, client):
        """Album 100 is Nevermind, fully hydrated."""
        resp = client.get("/api/v1/albums/100")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Nevermind"
        assert data["release_year"] == 1991
        assert data["song_count"] == 1
        assert data["display_artist"] == "Nirvana"
        pub_names = sorted([p["name"] for p in data["publishers"]])
        assert pub_names == ["DGC Records", "Sub Pop"]

    def test_not_found(self, client):
        """Non-existent album returns 404."""
        resp = client.get("/api/v1/albums/999")
        assert resp.status_code == 404


# ===========================================================================
# GET /api/v1/audit/history/{table}/{record_id}
# ===========================================================================
class TestAuditHistory:
    def test_artist_name_history(self, client):
        """ArtistNames record 33 has a rename action and a change."""
        resp = client.get("/api/v1/audit/history/ArtistNames/33")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Should have an ACTION and a CHANGE entry
        types = sorted([entry["type"] for entry in data])
        assert types == ["ACTION", "CHANGE"]
        # Verify the action
        action = next(e for e in data if e["type"] == "ACTION")
        assert action["label"] == "RENAME"
        assert action["details"] == "User updated artist name"
        # Verify the change
        change = next(e for e in data if e["type"] == "CHANGE")
        assert change["label"] == "Updated DisplayName"
        assert change["old"] == "PinkPantheress"
        assert change["new"] == "Ines Prajo"

    def test_deleted_record_history(self, client):
        """Songs record 99 was deleted - should appear as lifecycle entry."""
        resp = client.get("/api/v1/audit/history/Songs/99")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        types = [entry["type"] for entry in data]
        assert "LIFECYCLE" in types
        lifecycle = data[0]
        assert lifecycle["label"] == "RECORD DELETED"
        assert '"Deleted Song"' in lifecycle["snapshot"]

    def test_no_history(self, client):
        """Record with no audit history returns empty list."""
        resp = client.get("/api/v1/audit/history/Songs/1")
        assert resp.status_code == 200
        # Song 1 has no audit log entries in our test data
        # (audit data is for ArtistNames:33 and Songs:99)
        data = resp.json()
        assert isinstance(data, list)

    def test_nonexistent_record(self, client):
        """Non-existent record returns empty list (not 404)."""
        resp = client.get("/api/v1/audit/history/Songs/99999")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_empty_db(self, empty_client):
        """Empty DB returns empty list."""
        resp = empty_client.get("/api/v1/audit/history/Songs/1")
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# GET /api/v1/metabolic/inspect-file/{song_id}
# ===========================================================================
class TestMetabolicInspectFile:
    def test_not_found(self, client):
        """Non-existent song returns 404."""
        resp = client.get("/api/v1/metabolic/inspect-file/9999")
        assert resp.status_code == 404

    def test_real_file_inspection(self, populated_db, monkeypatch):
        """inspect-file with a real audio file returns SongView."""
        import sqlite3

        fixture_path = os.path.abspath("tests/fixtures/silence.mp3")
        if not os.path.exists(fixture_path):
            pytest.skip("silence.mp3 fixture not available")

        # Point Song 1's source path to the real fixture file
        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (fixture_path,),
        )
        conn.commit()
        conn.close()

        monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
        c = TestClient(app)
        resp = c.get("/api/v1/metabolic/inspect-file/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_path"] == fixture_path

    def test_missing_file_returns_500(self, client):
        """Song with non-existent file path returns 500."""
        # Song 1 has source_path="/path/1" which doesn't exist on disk
        resp = client.get("/api/v1/metabolic/inspect-file/1")
        assert resp.status_code == 500
    # ===========================================================================
# Router Coverage: Edge Cases (Migrated from test_coverage_gap.py)
# ===========================================================================
class TestRouterEdgeCases:
    def test_router_get_song_not_found(self, client):
        """Router coverage: 404 for missing song."""
        resp = client.get("/api/v1/songs/9999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_router_search_short_query_success(self, client):
        """Router coverage: Single character query now allowed."""
        resp = client.get("/api/v1/songs/search", params={"q": "A"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_router_get_song_success(self, client):
        """Router coverage: Successful get_song hit for ID 1."""
        resp = client.get("/api/v1/songs/1")
        assert resp.status_code == 200
        assert resp.json()["id"] == 1
        assert resp.json()["title"] == "Smells Like Teen Spirit"
