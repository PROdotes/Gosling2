import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from src.engine_server import app
from src.engine.config import SONG_DEFAULT_YEAR


@pytest.fixture
def api_client(populated_db, monkeypatch, tmp_path):
    """Client wired to populated_db with isolated staging."""
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    # Isolate staging to tmp_path
    staging = tmp_path / "staging_api"
    staging.mkdir(parents=True, exist_ok=True)
    # Ensure both router and service use the SAME isolated staging
    monkeypatch.setattr("src.engine.routers.ingest.STAGING_DIR", str(staging))
    monkeypatch.setattr("src.services.catalog_service.STAGING_DIR", str(staging))

    return TestClient(app)


@pytest.fixture
def sample_mp3():
    """Returns path to a valid fixture MP3."""
    return Path("tests/fixtures/silence.mp3")


class TestCatalogWriteApi:
    """End-to-end API tests for Ingestion Write Path following TDD_TESTING_STANDARD."""

    def test_upload_and_ingest_success(self, api_client, sample_mp3):
        """POST /upload: Binary file upload triggers full ingestion and returns exhaustive SongView."""
        # silence.mp3 title: "Mayor of Crazy Town (Radio Edit)"
        with open(sample_mp3, "rb") as f:
            resp = api_client.post(
                "/api/v1/ingest/upload",
                files=[("files", (sample_mp3.name, f, "audio/mpeg"))],
            )

        assert (
            resp.status_code == 200
        ), f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        # 1. Batch Report Structure (now returns BatchIngestReport)
        assert data["total_files"] == 1, f"Expected 1 file, got {data['total_files']}"
        assert data["ingested"] == 1, f"Expected 1 ingested, got {data['ingested']}"
        assert (
            data["duplicates"] == 0
        ), f"Expected 0 duplicates, got {data['duplicates']}"
        assert data["errors"] == 0, f"Expected 0 errors, got {data['errors']}"
        assert (
            len(data["results"]) == 1
        ), f"Expected 1 result, got {len(data['results'])}"

        # 2. Individual Result
        result = data["results"][0]
        assert (
            result["status"] == "INGESTED"
        ), f"Expected 'INGESTED', got '{result['status']}'"
        assert (
            result["match_type"] is None
        ), f"Expected None match_type for new ingest, got {result['match_type']}"

        # 3. EXHAUSTIVE SONGVIEW ASSERTIONS
        song = result["song"]
        assert song["id"] is not None, "Expected DB-assigned ID"
        assert (
            song["title"] == "Mayor of Crazy Town (Radio Edit)"
        ), f"Expected 'Mayor of Crazy Town (Radio Edit)', got '{song['title']}'"
        assert (
            song["media_name"] == "Mayor of Crazy Town (Radio Edit)"
        ), f"Expected 'Mayor of Crazy Town (Radio Edit)', got '{song['media_name']}'"
        # duration in silence.mp3 is ~2.27s
        assert (
            2.0 < song["duration_s"] < 3.0
        ), f"Expected ~2.27s, got {song['duration_s']}"
        assert song["duration_ms"] == int(song["duration_s"] * 1000)
        assert song["audio_hash"] is not None, "Expected hash calculation"
        assert (
            song["is_active"] is False
        ), f"Expected default False, got {song['is_active']}"
        assert (
            song["processing_status"] == 1
        ), f"Expected processing_status=1 after enrichment, got {song['processing_status']}"
        assert (
            song["year"] == SONG_DEFAULT_YEAR
        ), f"Expected year {SONG_DEFAULT_YEAR}, got {song['year']}"
        assert song["bpm"] is None, f"Expected bpm None, got {song['bpm']}"
        assert (
            song["isrc"] == "USCGJ2326543"
        ), f"Expected ISRC USCGJ2326543, got {song['isrc']}"
        assert song["notes"] is None, f"Expected notes None, got {song['notes']}"
        # raw_tags may contain unrecognized frames (e.g. UFID from promo services) — that's expected
        assert isinstance(song["raw_tags"], dict), f"Expected raw_tags to be a dict, got {type(song['raw_tags'])}"

        # Verification of relations
        assert (
            len(song["credits"]) >= 2
        ), f"Expected at least 2 credits, got {len(song['credits'])}"
        # Performer
        performer = next(
            (c for c in song["credits"] if c["role_name"] == "Performer"), None
        )
        assert performer is not None, "Expected a Performer credit"
        assert performer["display_name"] == "Atwater Collective feat. Jesse Ulma"
        # Composers - stored as separate credits due to COMMA_SPLIT_FIELDS
        composers = [c for c in song["credits"] if c["role_name"] == "Composer"]
        assert len(composers) == 4, f"Expected 4 Composer credits, got {len(composers)}"
        composer_names = {c["display_name"] for c in composers}
        expected_composers = {
            "Will Kimbrough",
            "Vince Green",
            "Sam Wade",
            "Linda Corelli",
        }
        assert (
            composer_names == expected_composers
        ), f"Expected {expected_composers}, got {composer_names}"

        assert len(song["albums"]) == 1, f"Expected 1 album, got {len(song['albums'])}"
        assert song["albums"][0]["album_title"] == "Mayor of Crazy Town"

        # Tags (Genre: Folk only — UFID:iPluggers is unrecognized and goes to raw_tags)
        assert len(song["tags"]) == 1, f"Expected 1 tag, got {len(song['tags'])}"
        assert song["tags"][0]["name"] == "Folk"
        assert song["tags"][0]["category"] == "Genre"

    def test_upload_rejected_extension(self, api_client, tmp_path):
        """POST /upload: Reject non-MP3 files with 400."""
        bad_file = tmp_path / "report.pdf"
        bad_file.write_bytes(b"%PDF-1.4")

        with open(bad_file, "rb") as f:
            resp = api_client.post(
                "/api/v1/ingest/upload",
                files=[("files", (bad_file.name, f, "application/pdf"))],
            )

        assert (
            resp.status_code == 400
        ), f"Expected 400 for bad extension, got {resp.status_code}"
        assert "no valid audio files" in resp.json()["detail"].lower()

    def test_upload_missing_file_returns_422(self, api_client):
        """POST /upload: Missing 'file' field returns 422."""
        resp = api_client.post("/api/v1/ingest/upload", files={})
        assert (
            resp.status_code == 422
        ), f"Expected 422 for missing file, got {resp.status_code}"

    def test_delete_song_success_removes_from_library_and_staging(
        self, api_client, sample_mp3, tmp_path
    ):
        """DELETE /songs/{id}: Atomic removal with negative isolation (doesn't kill others)."""
        # 1. Setup: Ingest a song
        with open(sample_mp3, "rb") as f:
            up_resp = api_client.post(
                "/api/v1/ingest/upload",
                files=[("files", (sample_mp3.name, f, "audio/mpeg"))],
            )
        batch_result = up_resp.json()
        song_id = batch_result["results"][0]["song"]["id"]
        source_path = batch_result["results"][0]["song"]["source_path"]

        assert os.path.exists(source_path), "File should exist in staging before delete"

        # 2. Verify Haystack: Song 1 (SLTS) exists in populated_db
        haystack_resp = api_client.get("/api/v1/songs/1")
        assert haystack_resp.status_code == 200, "Song 1 must exist for negative check"

        # 3. Action: Delete the new song
        del_resp = api_client.delete(f"/api/v1/ingest/songs/{song_id}")
        assert (
            del_resp.status_code == 200
        ), f"Expected 200 DELETE, got {del_resp.status_code}"
        assert del_resp.json()["status"] == "DELETED"
        assert del_resp.json()["id"] == song_id

        # 4. Verify Positive: It's gone
        check_resp = api_client.get(f"/api/v1/songs/{song_id}")
        assert (
            check_resp.status_code == 404
        ), f"Expected 404 after delete, got {check_resp.status_code}"
        assert not os.path.exists(
            source_path
        ), "Physical file should be purged from staging"

        # 5. Verify Negative Isolation: Song 1 still exists
        haystack_check = api_client.get("/api/v1/songs/1")
        assert (
            haystack_check.status_code == 200
        ), "Deletion leaked! Song 1 was accidentally removed"
        assert haystack_check.json()["title"] == "Smells Like Teen Spirit"

    def test_delete_nonexistent_song_returns_404(self, api_client):
        """DELETE /songs/{id}: 404 for unknown IDs."""
        resp = api_client.delete("/api/v1/ingest/songs/99999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "not found" in resp.json()["detail"].lower()
