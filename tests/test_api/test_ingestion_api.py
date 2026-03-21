"""
API-level integration tests for the ingestion check endpoint.
Tests the HTTP contract (status codes, response shapes) against real SQLite.

Only tests cases that don't require real audio files on disk:
- Path collision (DB lookup only, file existence is the only OS call)
- File not found (the path genuinely doesn't exist)

The heavy collision logic (hash, metadata, artist sets, case, year)
is fully covered in tests/test_services/test_ingestion_service.py
against the real repository with zero mocking.
"""

import pytest
from fastapi.testclient import TestClient
from src.engine_server import app

EXPECTED_INGESTION_FIELDS = {"status", "match_type", "message", "song"}


@pytest.fixture
def client(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


class TestIngestionApi:

    def test_check_ingestion_file_not_found(self, client):
        """Non-existent path returns 400 with ERROR status and a descriptive message."""
        resp = client.post(
            "/api/v1/catalog/ingest/check",
            json={"file_path": "/absolutely/does/not/exist.mp3"},
        )
        assert (
            resp.status_code == 400
        ), f"Expected 400 for missing file, got {resp.status_code}"
        body = resp.json()
        assert (
            "detail" in body
        ), f"Expected 'detail' key in error body, got {list(body.keys())}"
        assert (
            "File not found" in body["detail"]
        ), f"Expected 'File not found' in detail, got '{body['detail']}'"

    def test_check_ingestion_path_collision(self, client, populated_db, tmp_path):
        """Path that exists in DB returns ALREADY_EXISTS with PATH match and full song data."""
        import sqlite3

        temp_file = tmp_path / "song1.mp3"
        temp_file.write_bytes(b"")
        target_path = str(temp_file)

        # Update DB to point to this real path
        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1", (target_path,)
        )
        conn.commit()
        conn.close()

        resp = client.post(
            "/api/v1/catalog/ingest/check", json={"file_path": target_path}
        )
        assert (
            resp.status_code == 200
        ), f"Expected 200 for path collision, got {resp.status_code}"

        data = resp.json()

        # Exhaustive field assertions on IngestionReportView
        assert (
            set(data.keys()) == EXPECTED_INGESTION_FIELDS
        ), f"Expected response keys {EXPECTED_INGESTION_FIELDS}, got {set(data.keys())}"
        assert (
            data["status"] == "ALREADY_EXISTS"
        ), f"Expected status 'ALREADY_EXISTS', got '{data['status']}'"
        assert (
            data["match_type"] == "PATH"
        ), f"Expected match_type 'PATH', got '{data['match_type']}'"
        assert (
            data["message"] is not None
        ), "Expected a non-None message for PATH collision"
        assert isinstance(
            data["message"], str
        ), f"Expected message to be str, got {type(data['message'])}"
        assert (
            "collision" in data["message"].lower()
        ), f"Expected 'collision' in message, got '{data['message']}'"

        # Song must be present and have source_path matching the request
        assert (
            data["song"] is not None
        ), "Expected song object in PATH collision response"
        song = data["song"]
        assert (
            "source_path" in song
        ), f"Expected 'source_path' in song, got keys: {list(song.keys())}"
        assert (
            song["source_path"] == target_path
        ), f"Expected song source_path '{target_path}', got '{song['source_path']}'"
        assert "id" in song, f"Expected 'id' in song, got keys: {list(song.keys())}"
        assert song["id"] is not None, "Expected song.id to be non-None"

    def test_check_ingestion_missing_field(self, client):
        """Missing file_path field returns 422 validation error."""
        resp = client.post("/api/v1/catalog/ingest/check", json={})
        assert (
            resp.status_code == 422
        ), f"Expected 422 for missing field, got {resp.status_code}"
        body = resp.json()
        assert (
            "detail" in body
        ), f"Expected 'detail' key in validation error body, got {list(body.keys())}"

    def test_check_ingestion_empty_path(self, client):
        """Empty string path returns 400 because no file exists at empty path."""
        resp = client.post("/api/v1/catalog/ingest/check", json={"file_path": ""})
        assert (
            resp.status_code == 400
        ), f"Expected 400 for empty path, got {resp.status_code}"
        body = resp.json()
        assert (
            "detail" in body
        ), f"Expected 'detail' key in error body, got {list(body.keys())}"
