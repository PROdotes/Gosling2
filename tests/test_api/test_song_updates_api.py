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
    def test_update_title_returns_full_song(self, api):
        resp = api.patch("/api/v1/songs/1", json={"media_name": "Renamed Title"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["id"] == 1, f"Expected id=1, got {data['id']}"
        assert (
            data["media_name"] == "Renamed Title"
        ), f"Expected 'Renamed Title', got {data['media_name']}"
        assert (
            data["title"] == "Renamed Title"
        ), f"Expected title='Renamed Title', got {data['title']}"
        assert (
            data["source_path"] == "/path/1"
        ), f"Expected '/path/1', got {data['source_path']}"
        assert data["duration_s"] == 200.0, f"Expected 200.0, got {data['duration_s']}"
        assert (
            data["audio_hash"] == "hash_1"
        ), f"Expected 'hash_1', got {data['audio_hash']}"
        assert (
            data["is_active"] is True
        ), f"Expected is_active=True, got {data['is_active']}"
        assert data["year"] == 1991, f"Expected year=1991, got {data['year']}"
        assert data["bpm"] is None, f"Expected bpm=None, got {data['bpm']}"
        assert data["isrc"] is None, f"Expected isrc=None, got {data['isrc']}"
        assert data["notes"] is None, f"Expected notes=None, got {data['notes']}"

    def test_update_year_does_not_wipe_other_fields(self, api):
        resp = api.patch("/api/v1/songs/7", json={"year": 2000})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["id"] == 7, f"Expected id=7, got {data['id']}"
        assert data["year"] == 2000, f"Expected year=2000, got {data['year']}"
        assert (
            data["media_name"] == "Hollow Song"
        ), f"Expected 'Hollow Song', got {data['media_name']}"
        assert data["bpm"] == 128, f"Expected bpm=128 (unchanged), got {data['bpm']}"
        assert (
            data["isrc"] == "ISRC123"
        ), f"Expected isrc='ISRC123' (unchanged), got {data['isrc']}"
        assert (
            data["source_path"] == "/path/7"
        ), f"Expected '/path/7', got {data['source_path']}"
        assert data["duration_s"] == 10.0, f"Expected 10.0, got {data['duration_s']}"
        assert (
            data["is_active"] is True
        ), f"Expected is_active=True, got {data['is_active']}"

    def test_update_bpm_does_not_wipe_other_fields(self, api):
        resp = api.patch("/api/v1/songs/7", json={"bpm": 140})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["bpm"] == 140, f"Expected bpm=140, got {data['bpm']}"
        assert (
            data["isrc"] == "ISRC123"
        ), f"Expected isrc='ISRC123' (unchanged), got {data['isrc']}"
        assert (
            data["media_name"] == "Hollow Song"
        ), f"Expected 'Hollow Song' (unchanged), got {data['media_name']}"

    def test_update_isrc_does_not_wipe_other_fields(self, api):
        resp = api.patch("/api/v1/songs/1", json={"isrc": "USRC12345678"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert (
            data["isrc"] == "USRC12345678"
        ), f"Expected 'USRC12345678', got {data['isrc']}"
        assert (
            data["media_name"] == "Smells Like Teen Spirit"
        ), f"Expected title unchanged, got {data['media_name']}"
        assert (
            data["year"] == 1991
        ), f"Expected year=1991 (unchanged), got {data['year']}"
        assert (
            data["audio_hash"] == "hash_1"
        ), f"Expected hash unchanged, got {data['audio_hash']}"

    def test_422_no_fields(self, api):
        resp = api.patch("/api/v1/songs/1", json={})
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"

    def test_404_unknown_song(self, api):
        resp = api.patch("/api/v1/songs/9999", json={"media_name": "X"})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail' field"

    def test_partial_update_persistence_exhaustive(self, api):
        # Setup: give song 7 a known year
        api.patch("/api/v1/songs/7", json={"year": 2024})

        # Update ONLY bpm
        resp = api.patch("/api/v1/songs/7", json={"bpm": 140})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["bpm"] == 140, f"Expected bpm=140, got {data['bpm']}"
        assert (
            data["year"] == 2024
        ), f"Expected year=2024 (unchanged), got {data['year']}"
        assert (
            data["media_name"] == "Hollow Song"
        ), f"Expected title unchanged, got {data['media_name']}"
        assert data["isrc"] == "ISRC123", f"Expected isrc unchanged, got {data['isrc']}"


# ---------------------------------------------------------------------------
# Credits  POST/DELETE/PATCH /api/v1/songs/{song_id}/credits
# ---------------------------------------------------------------------------


class TestSongCredits:
    def test_add_credit_returns_full_song_credit(self, api):
        resp = api.post(
            "/api/v1/songs/7/credits",
            json={"display_name": "Dave Grohl", "role_name": "Performer"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert (
            data["display_name"] == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got {data['display_name']}"
        assert (
            data["role_name"] == "Performer"
        ), f"Expected 'Performer', got {data['role_name']}"
        assert data["credit_id"] is not None, "Expected credit_id to be set"
        assert "source_id" in data, "Response missing 'source_id'"
        assert "name_id" in data, "Response missing 'name_id'"
        assert "identity_id" in data, "Response missing 'identity_id'"
        assert "role_id" in data, "Response missing 'role_id'"
        assert "is_primary" in data, "Response missing 'is_primary'"

    def test_add_credit_404_unknown_song(self, api):
        resp = api.post(
            "/api/v1/songs/9999/credits",
            json={"display_name": "X", "role_name": "Performer"},
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_remove_credit_success(self, api):
        add = api.post(
            "/api/v1/songs/7/credits",
            json={"display_name": "Dave Grohl", "role_name": "Performer"},
        )
        assert add.status_code == 200, f"Add credit failed: {add.status_code}"
        credit_id = add.json()["credit_id"]

        resp = api.delete(f"/api/v1/songs/7/credits/{credit_id}")
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        # Verify removed: song 7 should have no credits
        song = api.get("/api/v1/songs/7").json()
        assert not any(
            c["credit_id"] == credit_id for c in song["credits"]
        ), f"Credit {credit_id} should be removed but still present"

    def test_remove_credit_404_bad_credit(self, api):
        resp = api.delete("/api/v1/songs/1/credits/99999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_remove_credit_404_wrong_song(self, api):
        # credit_id=1 belongs to song 1 (Nirvana on SLTS), not song 2
        resp = api.delete("/api/v1/songs/2/credits/1")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_update_credit_name_success(self, api):
        # name_id=11 is "Grohlton" (alias for Dave Grohl on song 4)
        resp = api.patch(
            "/api/v1/songs/4/credits/11", json={"display_name": "GrohltonX"}
        )
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        # Verify the rename is reflected
        song = api.get("/api/v1/songs/4").json()
        assert any(
            c["display_name"] == "GrohltonX" for c in song["credits"]
        ), "Renamed credit 'GrohltonX' not found on song 4"
        assert not any(
            c["display_name"] == "Grohlton" for c in song["credits"]
        ), "Old name 'Grohlton' should no longer appear on song 4"

    def test_update_credit_name_404(self, api):
        resp = api.patch("/api/v1/songs/1/credits/99999", json={"display_name": "X"})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"


# ---------------------------------------------------------------------------
# Albums  POST/DELETE/PATCH /api/v1/songs/{song_id}/albums
# ---------------------------------------------------------------------------


class TestSongAlbums:
    def test_link_existing_album_returns_full_song_album(self, api):
        # Song 3 has no album; link to album 100 (Nevermind, 1991)
        resp = api.post(
            "/api/v1/songs/3/albums", json={"album_id": 100, "track_number": 5}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["album_id"] == 100, f"Expected album_id=100, got {data['album_id']}"
        assert (
            data["album_title"] == "Nevermind"
        ), f"Expected 'Nevermind', got {data['album_title']}"
        assert (
            data["track_number"] == 5
        ), f"Expected track_number=5, got {data['track_number']}"
        assert (
            data["release_year"] == 1991
        ), f"Expected release_year=1991, got {data['release_year']}"
        assert data["source_id"] == 3, f"Expected source_id=3, got {data['source_id']}"
        assert "disc_number" in data, "Response missing 'disc_number'"
        assert "is_primary" in data, "Response missing 'is_primary'"

    def test_create_and_link_album_returns_full_song_album(self, api):
        resp = api.post(
            "/api/v1/songs/5/albums",
            json={"title": "Brand New Album", "release_year": 2024},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert (
            data["album_title"] == "Brand New Album"
        ), f"Expected 'Brand New Album', got {data['album_title']}"
        assert (
            data["release_year"] == 2024
        ), f"Expected 2024, got {data['release_year']}"
        assert data["album_id"] is not None, "Expected album_id to be set"
        assert data["source_id"] == 5, f"Expected source_id=5, got {data['source_id']}"

    def test_add_album_422_no_id_or_title(self, api):
        resp = api.post("/api/v1/songs/1/albums", json={"track_number": 1})
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"

    def test_add_album_404_unknown_song(self, api):
        resp = api.post("/api/v1/songs/9999/albums", json={"album_id": 100})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_remove_album_link_success(self, api):
        # Song 1 is linked to album 100
        resp = api.delete("/api/v1/songs/1/albums/100")
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        # Verify link is gone
        song = api.get("/api/v1/songs/1").json()
        assert not any(
            a["album_id"] == 100 for a in song["albums"]
        ), "Album link 100 should be removed but still present on song 1"

    def test_remove_album_link_404_unknown_album(self, api):
        resp = api.delete("/api/v1/songs/1/albums/9999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_remove_album_link_404_wrong_song(self, api):
        # Album 200 is linked to song 2, not song 1
        resp = api.delete("/api/v1/songs/1/albums/200")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_update_album_link_success(self, api):
        # Song 2 is on album 200 track 11
        resp = api.patch(
            "/api/v1/songs/2/albums/200", json={"track_number": 3, "disc_number": 2}
        )
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        # Verify both fields persisted
        song = api.get("/api/v1/songs/2").json()
        link = next((a for a in song["albums"] if a["album_id"] == 200), None)
        assert link is not None, "Album link 200 not found on song 2"
        assert (
            link["track_number"] == 3
        ), f"Expected track_number=3, got {link['track_number']}"
        assert (
            link["disc_number"] == 2
        ), f"Expected disc_number=2, got {link['disc_number']}"

    def test_update_album_link_partial_preserves_other_field(self, api):
        # Setup: multi-disc state
        api.patch(
            "/api/v1/songs/2/albums/200", json={"track_number": 4, "disc_number": 2}
        )

        # Update ONLY track_number
        resp = api.patch("/api/v1/songs/2/albums/200", json={"track_number": 5})
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        song = api.get("/api/v1/songs/2").json()
        link = next((a for a in song["albums"] if a["album_id"] == 200), None)
        assert link is not None, "Album link 200 not found on song 2"
        assert (
            link["track_number"] == 5
        ), f"Expected track_number=5, got {link['track_number']}"
        assert (
            link["disc_number"] == 2
        ), f"Expected disc_number=2 (unchanged), got {link['disc_number']}"

    def test_update_album_link_404_bad_link(self, api):
        resp = api.patch("/api/v1/songs/1/albums/9999", json={"track_number": 1})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"


# ---------------------------------------------------------------------------
# Album global updates  PATCH /api/v1/albums/{album_id}
# ---------------------------------------------------------------------------


class TestAlbumUpdates:
    def test_update_album_title_returns_full_album(self, api):
        resp = api.patch("/api/v1/albums/100", json={"title": "Nevermind (Remaster)"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["id"] == 100, f"Expected id=100, got {data['id']}"
        assert (
            data["title"] == "Nevermind (Remaster)"
        ), f"Expected 'Nevermind (Remaster)', got {data['title']}"
        assert (
            data["release_year"] == 1991
        ), f"Expected release_year=1991 (unchanged), got {data['release_year']}"
        assert "credits" in data, "Response missing 'credits'"
        assert "publishers" in data, "Response missing 'publishers'"

    def test_update_album_year_does_not_wipe_title(self, api):
        resp = api.patch("/api/v1/albums/200", json={"release_year": 1998})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert (
            data["release_year"] == 1998
        ), f"Expected 1998, got {data['release_year']}"
        assert (
            data["title"] == "The Colour and the Shape"
        ), f"Expected title unchanged, got {data['title']}"
        assert data["id"] == 200, f"Expected id=200, got {data['id']}"

    def test_update_album_422_no_fields(self, api):
        resp = api.patch("/api/v1/albums/100", json={})
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"

    def test_update_album_404(self, api):
        resp = api.patch("/api/v1/albums/9999", json={"title": "X"})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_add_album_credit_success_and_visible(self, api):
        resp = api.post(
            "/api/v1/albums/100/credits", json={"artist_name": "Taylor Hawkins"}
        )
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        alb = api.get("/api/v1/albums/100")
        assert (
            alb.status_code == 200
        ), f"Expected 200 on GET album, got {alb.status_code}"
        data = alb.json()
        names = [c["display_name"] for c in data["credits"]]
        assert (
            "Taylor Hawkins" in names
        ), f"Expected 'Taylor Hawkins' in credits, got {names}"
        # Existing credit (Nirvana) must still be present
        assert (
            "Nirvana" in names
        ), f"Expected existing 'Nirvana' credit to remain, got {names}"

    def test_add_album_credit_404_unknown_album(self, api):
        resp = api.post("/api/v1/albums/9999/credits", json={"artist_name": "X"})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_remove_album_credit_success(self, api):
        # Nirvana (name_id=20) is credited on album 100
        resp = api.delete("/api/v1/albums/100/credits/20")
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        # Verify removed
        alb = api.get("/api/v1/albums/100").json()
        names = [c["display_name"] for c in alb["credits"]]
        assert (
            "Nirvana" not in names
        ), f"Expected 'Nirvana' to be removed but still present: {names}"

    def test_remove_album_credit_404_unknown_credit(self, api):
        resp = api.delete("/api/v1/albums/100/credits/9999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_remove_album_credit_404_wrong_album(self, api):
        # name_id=30 (Foo Fighters) is on album 200, not 100
        resp = api.delete("/api/v1/albums/100/credits/30")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_set_album_publisher_success(self, api):
        resp = api.patch(
            "/api/v1/albums/100/publisher", json={"publisher_name": "Island Records"}
        )
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        # Verify reflected on album
        alb = api.get("/api/v1/albums/100").json()
        pub_names = [p["name"] for p in alb["publishers"]]
        assert (
            "Island Records" in pub_names
        ), f"Expected 'Island Records' in publishers, got {pub_names}"

    def test_set_album_publisher_404_unknown_album(self, api):
        resp = api.patch("/api/v1/albums/9999/publisher", json={"publisher_name": "X"})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"


# ---------------------------------------------------------------------------
# Tags  POST/DELETE /api/v1/songs/{song_id}/tags  PATCH /api/v1/tags/{tag_id}
# ---------------------------------------------------------------------------


class TestSongTags:
    def test_add_tag_returns_full_tag(self, api):
        # Song 3 has no tags
        resp = api.post(
            "/api/v1/songs/3/tags", json={"tag_name": "Grunge", "category": "Genre"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["name"] == "Grunge", f"Expected name='Grunge', got {data['name']}"
        assert (
            data["category"] == "Genre"
        ), f"Expected category='Genre', got {data['category']}"
        assert data["id"] is not None, "Expected id to be set"
        assert "is_primary" in data, "Response missing 'is_primary'"

    def test_add_tag_does_not_wipe_existing_song_data(self, api):
        resp = api.post(
            "/api/v1/songs/7/tags", json={"tag_name": "Ambient", "category": "Genre"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        song = api.get("/api/v1/songs/7").json()
        assert song["bpm"] == 128, f"Expected bpm=128 (unchanged), got {song['bpm']}"
        assert (
            song["isrc"] == "ISRC123"
        ), f"Expected isrc='ISRC123' (unchanged), got {song['isrc']}"
        assert (
            song["media_name"] == "Hollow Song"
        ), f"Expected title unchanged, got {song['media_name']}"

    def test_add_tag_404_unknown_song(self, api):
        resp = api.post(
            "/api/v1/songs/9999/tags", json={"tag_name": "X", "category": "Y"}
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_remove_tag_success(self, api):
        # Song 1 has tag_id=1 (Grunge/Genre)
        resp = api.delete("/api/v1/songs/1/tags/1")
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        # Verify removed; song 1 still has tags 2 and 5
        song = api.get("/api/v1/songs/1").json()
        tag_ids = [t["id"] for t in song["tags"]]
        assert (
            1 not in tag_ids
        ), f"Tag 1 (Grunge) should be removed but still present: {tag_ids}"
        assert 2 in tag_ids, f"Tag 2 (Energetic) should still be present: {tag_ids}"
        assert 5 in tag_ids, f"Tag 5 (English) should still be present: {tag_ids}"

    def test_remove_tag_404_unknown_tag(self, api):
        resp = api.delete("/api/v1/songs/1/tags/9999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_remove_tag_404_wrong_song(self, api):
        # tag_id=3 (90s/Era) belongs to song 2, not song 1
        resp = api.delete("/api/v1/songs/1/tags/3")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_update_tag_success_and_reflected_on_song(self, api):
        # tag_id=3 is "90s" / Era, linked to Everlong (Song 2)
        resp = api.patch(
            "/api/v1/tags/3", json={"tag_name": "Nineties", "category": "Era"}
        )
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        song = api.get("/api/v1/songs/2").json()
        tag_names = [t["name"] for t in song["tags"]]
        assert (
            "Nineties" in tag_names
        ), f"Expected 'Nineties' in song 2 tags after rename, got {tag_names}"
        assert (
            "90s" not in tag_names
        ), f"Old name '90s' should be gone from song 2, got {tag_names}"

    def test_update_tag_does_not_affect_unrelated_song(self, api):
        # tag_id=3 (90s) is on song 2 only — verify song 1 tags unchanged
        api.patch("/api/v1/tags/3", json={"tag_name": "Nineties", "category": "Era"})
        song1 = api.get("/api/v1/songs/1").json()
        tag_names = [t["name"] for t in song1["tags"]]
        assert (
            "Nineties" not in tag_names
        ), f"Song 1 should not have 'Nineties' tag: {tag_names}"

    def test_update_tag_404(self, api):
        resp = api.patch("/api/v1/tags/9999", json={"tag_name": "X", "category": "Y"})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_add_tag_by_id_links_existing(self, api):
        # Song 2 has no tags — link Grunge (tag_id=1) by ID only
        resp = api.post("/api/v1/songs/2/tags", json={"tag_id": 1})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["id"] == 1, f"Expected id=1, got {data['id']}"
        assert data["name"] == "Grunge", f"Expected name='Grunge', got {data['name']}"
        assert data["category"] == "Genre", f"Expected category='Genre', got {data['category']}"

    def test_add_tag_by_id_not_found_returns_500(self, api):
        resp = api.post("/api/v1/songs/2/tags", json={"tag_id": 9999})
        assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"

    def test_add_tag_missing_both_id_and_name_returns_500(self, api):
        # Neither tag_id nor tag_name provided — service raises ValueError
        resp = api.post("/api/v1/songs/2/tags", json={})
        assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Publishers  POST/DELETE /api/v1/songs/{song_id}/publishers  PATCH /api/v1/publishers/{id}
# ---------------------------------------------------------------------------


class TestSongPublishers:
    def test_add_publisher_returns_full_publisher(self, api):
        # Song 2 has no recording publisher
        resp = api.post(
            "/api/v1/songs/2/publishers", json={"publisher_name": "Sub Pop"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["name"] == "Sub Pop", f"Expected name='Sub Pop', got {data['name']}"
        assert data["id"] is not None, "Expected id to be set"
        assert "parent_name" in data, "Response missing 'parent_name'"
        assert "sub_publishers" in data, "Response missing 'sub_publishers'"

    def test_add_publisher_404_unknown_song(self, api):
        resp = api.post("/api/v1/songs/9999/publishers", json={"publisher_name": "X"})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_remove_publisher_success(self, api):
        # Song 1 -> DGC Records (publisher_id=10)
        resp = api.delete("/api/v1/songs/1/publishers/10")
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        # Verify removed
        song = api.get("/api/v1/songs/1").json()
        pub_ids = [p["id"] for p in song["publishers"]]
        assert (
            10 not in pub_ids
        ), f"Publisher 10 (DGC Records) should be removed but still present: {pub_ids}"

    def test_remove_publisher_404_unknown_publisher(self, api):
        resp = api.delete("/api/v1/songs/1/publishers/9999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_remove_publisher_404_wrong_song(self, api):
        # publisher_id=4 (Roswell Records) is on album 200, not on song 1 directly
        resp = api.delete("/api/v1/songs/2/publishers/4")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_update_publisher_success_and_reflected_on_song(self, api):
        # publisher_id=10 is "DGC Records", linked to Song 1
        resp = api.patch(
            "/api/v1/publishers/10", json={"publisher_name": "DGC (Universal)"}
        )
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

        song = api.get("/api/v1/songs/1").json()
        pub_names = [p["name"] for p in song["publishers"]]
        assert (
            "DGC (Universal)" in pub_names
        ), f"Expected 'DGC (Universal)' in song 1 publishers, got {pub_names}"
        assert (
            "DGC Records" not in pub_names
        ), f"Old name 'DGC Records' should be gone, got {pub_names}"

    def test_update_publisher_does_not_affect_unrelated_song(self, api):
        # publisher_id=10 is on song 1 only — verify song 2 publishers unchanged
        api.patch("/api/v1/publishers/10", json={"publisher_name": "DGC (Universal)"})
        song2 = api.get("/api/v1/songs/2").json()
        pub_names = [p["name"] for p in song2["publishers"]]
        assert (
            "DGC (Universal)" not in pub_names
        ), f"Song 2 should not have 'DGC (Universal)': {pub_names}"

    def test_update_publisher_404(self, api):
        resp = api.patch("/api/v1/publishers/9999", json={"publisher_name": "X"})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_add_publisher_by_id_links_existing(self, api):
        # Song 2 has no publisher — link Sub Pop (pub_id=5) by ID only
        resp = api.post("/api/v1/songs/2/publishers", json={"publisher_id": 5})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["id"] == 5, f"Expected id=5, got {data['id']}"
        assert data["name"] == "Sub Pop", f"Expected name='Sub Pop', got {data['name']}"

    def test_add_publisher_by_id_not_found_returns_500(self, api):
        resp = api.post("/api/v1/songs/2/publishers", json={"publisher_id": 9999})
        assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"

    def test_add_publisher_missing_both_id_and_name_returns_500(self, api):
        # Neither publisher_id nor publisher_name provided — service raises ValueError
        resp = api.post("/api/v1/songs/2/publishers", json={})
        assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"


class TestSetPublisherParent:
    def test_set_parent_returns_204(self, api):
        # Sub Pop (5, parent=NULL) → parent=1 (Universal Music Group)
        resp = api.patch("/api/v1/publishers/5/parent", json={"parent_id": 1})
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

    def test_set_parent_persisted(self, api):
        # Sub Pop (5) → parent=1 (Universal Music Group)
        api.patch("/api/v1/publishers/5/parent", json={"parent_id": 1})
        publisher = api.get("/api/v1/publishers/5").json()
        assert (
            publisher["parent_name"] == "Universal Music Group"
        ), f"Expected parent_name='Universal Music Group', got {publisher['parent_name']}"
        assert (
            publisher["name"] == "Sub Pop"
        ), f"Expected name='Sub Pop', got '{publisher['name']}'"

    def test_clear_parent_returns_204(self, api):
        # DGC Records (10, parent=1) → clear parent
        resp = api.patch("/api/v1/publishers/10/parent", json={"parent_id": None})
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"

    def test_clear_parent_persisted(self, api):
        api.patch("/api/v1/publishers/10/parent", json={"parent_id": None})
        publisher = api.get("/api/v1/publishers/10").json()
        assert (
            publisher["parent_name"] is None
        ), f"Expected parent_name=None after clear, got {publisher['parent_name']}"

    def test_set_parent_404_unknown_publisher(self, api):
        resp = api.patch("/api/v1/publishers/9999/parent", json={"parent_id": 1})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_set_parent_404_unknown_parent(self, api):
        resp = api.patch("/api/v1/publishers/5/parent", json={"parent_id": 9999})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"
