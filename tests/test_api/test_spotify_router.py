import pytest
from fastapi.testclient import TestClient
from src.engine_server import app


@pytest.fixture
def api(populated_db, monkeypatch):
    """Heremetic API client with isolated populated DB."""
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


class TestSpotifyRouter:
    @pytest.fixture
    def spotify_text(self):
        return "Credits\nTitle\nArtist\n\nGoran Boskovic\nComposer \u2022 Lyricist\n\nSources\nUniversal"

    def test_parse_credits_success(self, api, spotify_text):
        """Rule 156: Verify API response shape for parsing."""
        response = api.post(
            "/api/v1/spotify/parse",
            json={"raw_text": spotify_text, "reference_title": "Title"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["parsed_title"] == "Title", (
            f"Expected 'Title', got {data['parsed_title']}"
        )
        assert data["title_match"] is True, "Expected title_match to be True"
        assert len(data["credits"]) > 0, "Expected credits in response"
        assert "Universal" in data["publishers"], "Expected publisher in response"

    def test_parse_credits_mismatch(self, api, spotify_text):
        response = api.post(
            "/api/v1/spotify/parse",
            json={"raw_text": spotify_text, "reference_title": "Different"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json()["title_match"] is False, (
            "Expected title_match to be False"
        )

    def test_import_credits_success(self, api, spotify_text):
        """Rule 156: Verify bulk import orchestration via API."""
        # We use song_id 2 from populated_db
        payload = {
            "song_id": 2,
            "credits": [{"name": "New Artist", "role": "Vibe Advisor"}],
            "publishers": ["Sony Music"],
        }
        response = api.post("/api/v1/spotify/import", json=payload)
        assert response.status_code == 204, (
            f"Expected 204, got {response.status_code}: {response.text}"
        )

        # Verify persistence via existing GET song endpoint
        get_resp = api.get("/api/v1/songs/2")
        song_data = get_resp.json()

        # Verify credit added
        credit_names = {c["display_name"] for c in song_data["credits"]}
        assert "New Artist" in credit_names, f"Expected 'New Artist' in {credit_names}"

        # Verify publisher added
        pub_names = {p["name"] for p in song_data["publishers"]}
        assert "Sony Music" in pub_names, f"Expected 'Sony Music' in {pub_names}"

    def test_import_credits_song_not_found(self, api):
        """Rule 60/113: Ensure 404 for missing song_id."""
        payload = {"song_id": 9999, "credits": [], "publishers": []}
        response = api.post("/api/v1/spotify/import", json=payload)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    def test_import_credits_invalid_payload(self, api):
        """Rule 156: Pydantic validation should return 422."""
        response = api.post("/api/v1/spotify/import", json={"song_id": "NOT-A-NUMBER"})
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
