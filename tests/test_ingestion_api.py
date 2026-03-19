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


@pytest.fixture
def client(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


class TestIngestionApi:

    def test_check_ingestion_file_not_found(self, client):
        """Non-existent path returns 400."""
        resp = client.post(
            "/api/v1/catalog/ingest/check",
            json={"file_path": "/absolutely/does/not/exist.mp3"},
        )
        assert resp.status_code == 400
        assert "File not found" in resp.json()["detail"]

    def test_check_ingestion_path_collision(self, client, populated_db, tmp_path):
        """Path that exists in DB returns ALREADY_EXISTS with PATH match.
        We write a real empty file and update the DB to point to it."""
        import sqlite3
        temp_file = tmp_path / "song1.mp3"
        temp_file.write_bytes(b"")
        target_path = str(temp_file)

        # Update DB to point to this real path
        conn = sqlite3.connect(populated_db)
        conn.execute("UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1", (target_path,))
        conn.commit()
        conn.close()

        resp = client.post(
            "/api/v1/catalog/ingest/check", json={"file_path": target_path}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ALREADY_EXISTS"
        assert data["match_type"] == "PATH"
        assert data["song"]["source_path"] == target_path

    def test_check_ingestion_missing_field(self, client):
        """Missing file_path field returns 422."""
        resp = client.post("/api/v1/catalog/ingest/check", json={})
        assert resp.status_code == 422

    def test_check_ingestion_empty_path(self, client):
        """Empty string path returns 400 (file not found)."""
        resp = client.post(
            "/api/v1/catalog/ingest/check", json={"file_path": ""}
        )
        # Empty path won't exist on disk
        assert resp.status_code == 400
