"""
API tests for song update endpoints (PATCH/POST/DELETE).
Uses populated_db fixture — see conftest.py for exact data map.
"""
import pytest
from fastapi.testclient import TestClient
from src.engine_server import app


@pytest.fixture
def api(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Scalar Updates  PATCH /api/v1/songs/{song_id}
# ---------------------------------------------------------------------------

class TestUpdateSongScalars:
    def test_update_title(self, api):
        resp = api.patch("/api/v1/songs/1", json={"media_name": "Renamed Title"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["media_name"] == "Renamed Title"

    def test_update_year(self, api):
        resp = api.patch("/api/v1/songs/1", json={"year": 2000})
        assert resp.status_code == 200
        assert resp.json()["year"] == 2000

    def test_update_bpm(self, api):
        resp = api.patch("/api/v1/songs/7", json={"bpm": 140})
        assert resp.status_code == 200
        assert resp.json()["bpm"] == 140

    def test_update_isrc(self, api):
        resp = api.patch("/api/v1/songs/1", json={"isrc": "USRC12345678"})
        assert resp.status_code == 200
        assert resp.json()["isrc"] == "USRC12345678"

    def test_422_no_fields(self, api):
        resp = api.patch("/api/v1/songs/1", json={})
        assert resp.status_code == 422

    def test_404_unknown_song(self, api):
        resp = api.patch("/api/v1/songs/9999", json={"media_name": "X"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Credits  POST/DELETE/PATCH /api/v1/songs/{song_id}/credits
# ---------------------------------------------------------------------------

class TestSongCredits:
    def test_add_credit_success(self, api):
        resp = api.post("/api/v1/songs/7/credits", json={"display_name": "Dave Grohl", "role_name": "Performer"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Dave Grohl"
        assert data["role_name"] == "Performer"
        assert data["credit_id"] is not None

    def test_add_credit_returns_song_credit_shape(self, api):
        resp = api.post("/api/v1/songs/7/credits", json={"display_name": "Taylor Hawkins", "role_name": "Composer"})
        assert resp.status_code == 200
        data = resp.json()
        # Required SongCredit fields
        assert "credit_id" in data
        assert "display_name" in data
        assert "role_name" in data

    def test_add_credit_404_unknown_song(self, api):
        resp = api.post("/api/v1/songs/9999/credits", json={"display_name": "X", "role_name": "Performer"})
        assert resp.status_code == 404

    def test_remove_credit_success(self, api):
        # Song 1 has credit: Nirvana (NameID=20) Performer — get credit_id first
        add = api.post("/api/v1/songs/7/credits", json={"display_name": "Dave Grohl", "role_name": "Performer"})
        credit_id = add.json()["credit_id"]
        resp = api.delete(f"/api/v1/songs/7/credits/{credit_id}")
        assert resp.status_code == 204

    def test_remove_credit_404_bad_credit(self, api):
        resp = api.delete("/api/v1/songs/1/credits/99999")
        assert resp.status_code == 404

    def test_update_credit_name_success(self, api):
        # name_id=11 is "Grohlton" (alias for Dave Grohl)
        resp = api.patch("/api/v1/songs/4/credits/11", json={"display_name": "GrohltonX"})
        assert resp.status_code == 204

    def test_update_credit_name_unknown_name_is_noop(self, api):
        # name_id is global — updating a nonexistent name is a silent no-op
        resp = api.patch("/api/v1/songs/1/credits/99999", json={"display_name": "X"})
        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Albums  POST/DELETE/PATCH /api/v1/songs/{song_id}/albums
# ---------------------------------------------------------------------------

class TestSongAlbums:
    def test_link_existing_album(self, api):
        # Song 3 has no album; link to album 100 (Nevermind)
        resp = api.post("/api/v1/songs/3/albums", json={"album_id": 100, "track_number": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["album_id"] == 100
        assert data["track_number"] == 5
        assert data["album_title"] == "Nevermind"

    def test_link_existing_album_shape(self, api):
        resp = api.post("/api/v1/songs/4/albums", json={"album_id": 200})
        assert resp.status_code == 200
        data = resp.json()
        assert "album_id" in data
        assert "album_title" in data
        assert "source_id" in data

    def test_create_and_link_album(self, api):
        resp = api.post("/api/v1/songs/5/albums", json={"title": "Brand New Album", "release_year": 2024})
        assert resp.status_code == 200
        data = resp.json()
        assert data["album_title"] == "Brand New Album"
        assert data["album_id"] is not None

    def test_add_album_422_no_id_or_title(self, api):
        resp = api.post("/api/v1/songs/1/albums", json={"track_number": 1})
        assert resp.status_code == 422

    def test_add_album_404_unknown_song(self, api):
        resp = api.post("/api/v1/songs/9999/albums", json={"album_id": 100})
        assert resp.status_code == 404

    def test_remove_album_link_success(self, api):
        # Song 1 is linked to album 100
        resp = api.delete("/api/v1/songs/1/albums/100")
        assert resp.status_code == 204

    def test_remove_album_link_404(self, api):
        resp = api.delete("/api/v1/songs/1/albums/9999")
        assert resp.status_code == 404

    def test_update_album_link(self, api):
        # Song 2 is on album 200 track 11
        resp = api.patch("/api/v1/songs/2/albums/200", json={"track_number": 3, "disc_number": 2})
        assert resp.status_code == 204

    def test_update_album_link_404_bad_link(self, api):
        resp = api.patch("/api/v1/songs/1/albums/9999", json={"track_number": 1})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Album global updates  PATCH /api/v1/albums/{album_id}
# ---------------------------------------------------------------------------

class TestAlbumUpdates:
    def test_update_album_title(self, api):
        resp = api.patch("/api/v1/albums/100", json={"title": "Nevermind (Remaster)"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Nevermind (Remaster)"
        assert data["id"] == 100

    def test_update_album_year(self, api):
        resp = api.patch("/api/v1/albums/200", json={"release_year": 1998})
        assert resp.status_code == 200
        assert resp.json()["release_year"] == 1998

    def test_update_album_422_no_fields(self, api):
        resp = api.patch("/api/v1/albums/100", json={})
        assert resp.status_code == 422

    def test_update_album_404(self, api):
        resp = api.patch("/api/v1/albums/9999", json={"title": "X"})
        assert resp.status_code == 404

    def test_add_album_credit(self, api):
        # Add Taylor Hawkins as credit on Nevermind (album 100)
        resp = api.post("/api/v1/albums/100/credits", json={"artist_name": "Taylor Hawkins"})
        assert resp.status_code == 204

    def test_add_album_credit_404(self, api):
        resp = api.post("/api/v1/albums/9999/credits", json={"artist_name": "X"})
        assert resp.status_code == 404

    def test_remove_album_credit(self, api):
        # Nirvana (name_id=20) is credited on album 100
        resp = api.delete("/api/v1/albums/100/credits/20")
        assert resp.status_code == 204

    def test_remove_album_credit_404(self, api):
        resp = api.delete("/api/v1/albums/100/credits/9999")
        assert resp.status_code == 404

    def test_set_album_publisher(self, api):
        resp = api.patch("/api/v1/albums/100/publisher", json={"publisher_name": "Island Records"})
        assert resp.status_code == 204

    def test_set_album_publisher_404(self, api):
        resp = api.patch("/api/v1/albums/9999/publisher", json={"publisher_name": "X"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tags  POST/DELETE /api/v1/songs/{song_id}/tags  PATCH /api/v1/tags/{tag_id}
# ---------------------------------------------------------------------------

class TestSongTags:
    def test_add_tag_success(self, api):
        # Song 3 has no tags
        resp = api.post("/api/v1/songs/3/tags", json={"tag_name": "Grunge", "category": "Genre"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Grunge"
        assert data["category"] == "Genre"
        assert data["id"] is not None

    def test_add_tag_returns_tag_shape(self, api):
        resp = api.post("/api/v1/songs/4/tags", json={"tag_name": "NewMood", "category": "Mood"})
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "name" in data
        assert "category" in data

    def test_add_tag_404_unknown_song(self, api):
        resp = api.post("/api/v1/songs/9999/tags", json={"tag_name": "X", "category": "Y"})
        assert resp.status_code == 404

    def test_remove_tag_success(self, api):
        # Song 1 has tag_id=1 (Grunge)
        resp = api.delete("/api/v1/songs/1/tags/1")
        assert resp.status_code == 204

    def test_remove_tag_404(self, api):
        resp = api.delete("/api/v1/songs/1/tags/9999")
        assert resp.status_code == 404

    def test_update_tag_success(self, api):
        # tag_id=3 is "90s" / Era
        resp = api.patch("/api/v1/tags/3", json={"tag_name": "Nineties", "category": "Era"})
        assert resp.status_code == 204

    def test_update_tag_404(self, api):
        resp = api.patch("/api/v1/tags/9999", json={"tag_name": "X", "category": "Y"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Publishers  POST/DELETE /api/v1/songs/{song_id}/publishers  PATCH /api/v1/publishers/{id}
# ---------------------------------------------------------------------------

class TestSongPublishers:
    def test_add_publisher_success(self, api):
        # Song 2 has no recording publisher
        resp = api.post("/api/v1/songs/2/publishers", json={"publisher_name": "Sub Pop"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Sub Pop"
        assert data["id"] is not None

    def test_add_publisher_returns_publisher_shape(self, api):
        resp = api.post("/api/v1/songs/3/publishers", json={"publisher_name": "Island Records"})
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "name" in data

    def test_add_publisher_404_unknown_song(self, api):
        resp = api.post("/api/v1/songs/9999/publishers", json={"publisher_name": "X"})
        assert resp.status_code == 404

    def test_remove_publisher_success(self, api):
        # Song 1 -> DGC Records (publisher_id=10)
        resp = api.delete("/api/v1/songs/1/publishers/10")
        assert resp.status_code == 204

    def test_remove_publisher_404(self, api):
        resp = api.delete("/api/v1/songs/1/publishers/9999")
        assert resp.status_code == 404

    def test_update_publisher_success(self, api):
        # publisher_id=5 is "Sub Pop"
        resp = api.patch("/api/v1/publishers/5", json={"publisher_name": "Sub Pop Records"})
        assert resp.status_code == 204

    def test_update_publisher_404(self, api):
        resp = api.patch("/api/v1/publishers/9999", json={"publisher_name": "X"})
        assert resp.status_code == 404
