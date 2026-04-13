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

EXPECTED_INGESTION_FIELDS = {
    "status",
    "match_type",
    "message",
    "song",
    "ghost_id",
    "title",
    "duration_s",
    "year",
    "isrc",
    "staged_path",
}


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


# ========================================
# BATCH UPLOAD TESTS
# ========================================

EXPECTED_BATCH_REPORT_FIELDS = {
    "total_files",
    "ingested",
    "duplicates",
    "conflicts",
    "errors",
    "results",
    "pending_conversion",
}


class TestBatchUploadApi:
    """Tests for POST /api/v1/ingest/upload with multiple files."""

    def test_no_files_uploaded_returns_422(self, client):
        """Uploading zero files returns 422 validation error."""
        resp = client.post("/api/v1/ingest/upload", files=[])
        assert (
            resp.status_code == 422
        ), f"Expected 422 for no files, got {resp.status_code}"

        body = resp.json()
        assert (
            "detail" in body
        ), f"Expected 'detail' in error response, got {list(body.keys())}"

    def test_invalid_extension_files_returns_400(self, client, tmp_path):
        """Uploading only non-.mp3 files returns 400."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not audio")

        with open(txt_file, "rb") as f:
            resp = client.post(
                "/api/v1/ingest/upload",
                files=[("files", ("test.txt", f, "text/plain"))],
            )

        assert (
            resp.status_code == 400
        ), f"Expected 400 for invalid extension, got {resp.status_code}"
        body = resp.json()
        assert "detail" in body, "Expected 'detail' in error response"
        assert (
            "No valid audio files" in body["detail"]
        ), f"Expected rejection message, got '{body['detail']}'"

    def test_batch_report_structure(self, client, tmp_path):
        """Valid batch upload returns BatchIngestReport with all required fields."""
        # Create mock mp3 file
        mp3_file = tmp_path / "test.mp3"
        mp3_file.write_bytes(b"mock mp3 data")

        with open(mp3_file, "rb") as f:
            resp = client.post(
                "/api/v1/ingest/upload",
                files=[("files", ("test.mp3", f, "audio/mpeg"))],
            )

        # Should get 200 even if ingestion logic fails (batch report still returned)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        data = resp.json()
        assert (
            set(data.keys()) == EXPECTED_BATCH_REPORT_FIELDS
        ), f"Expected keys {EXPECTED_BATCH_REPORT_FIELDS}, got {set(data.keys())}"

        # Verify all fields have correct types
        assert isinstance(
            data["total_files"], int
        ), f"Expected total_files to be int, got {type(data['total_files'])}"
        assert isinstance(
            data["ingested"], int
        ), f"Expected ingested to be int, got {type(data['ingested'])}"
        assert isinstance(
            data["duplicates"], int
        ), f"Expected duplicates to be int, got {type(data['duplicates'])}"
        assert isinstance(
            data["errors"], int
        ), f"Expected errors to be int, got {type(data['errors'])}"
        assert isinstance(
            data["results"], list
        ), f"Expected results to be list, got {type(data['results'])}"

        # Total should be at least 1 (the file we uploaded)
        assert (
            data["total_files"] >= 1
        ), f"Expected at least 1 total_file, got {data['total_files']}"

    def test_mixed_valid_invalid_files_filters_correctly(self, client, tmp_path):
        """Mix of .mp3 and .txt files only processes .mp3 files."""
        mp3_1 = tmp_path / "song1.mp3"
        mp3_1.write_bytes(b"mock mp3 1")

        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("not audio")

        mp3_2 = tmp_path / "song2.mp3"
        mp3_2.write_bytes(b"mock mp3 2")

        with open(mp3_1, "rb") as f1, open(txt_file, "rb") as f2, open(
            mp3_2, "rb"
        ) as f3:
            resp = client.post(
                "/api/v1/ingest/upload",
                files=[
                    ("files", ("song1.mp3", f1, "audio/mpeg")),
                    ("files", ("readme.txt", f2, "text/plain")),
                    ("files", ("song2.mp3", f3, "audio/mpeg")),
                ],
            )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        data = resp.json()
        # Should process 2 mp3 files (txt skipped)
        assert (
            data["total_files"] == 2
        ), f"Expected 2 files processed, got {data['total_files']}"


class TestScanFolderApi:
    """Tests for POST /api/v1/ingest/scan-folder endpoint."""

    def test_nonexistent_folder_returns_404(self, client):
        """Scanning nonexistent folder returns 404."""
        resp = client.post(
            "/api/v1/ingest/scan-folder",
            json={"folder_path": "/absolutely/does/not/exist", "recursive": True},
        )

        assert (
            resp.status_code == 404
        ), f"Expected 404 for nonexistent folder, got {resp.status_code}"
        body = resp.json()
        assert "detail" in body, "Expected 'detail' in error response"
        assert (
            "No audio files found" in body["detail"]
        ), f"Expected rejection message, got '{body['detail']}'"

    def test_empty_folder_returns_404(self, client, tmp_path):
        """Scanning empty folder returns 404."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        resp = client.post(
            "/api/v1/ingest/scan-folder",
            json={"folder_path": str(empty_dir), "recursive": True},
        )

        assert (
            resp.status_code == 404
        ), f"Expected 404 for empty folder, got {resp.status_code}"
        body = resp.json()
        assert "detail" in body, "Expected 'detail' in error response"

    def test_missing_folder_path_returns_422(self, client):
        """Missing folder_path field returns 422 validation error."""
        resp = client.post("/api/v1/ingest/scan-folder", json={"recursive": True})

        assert (
            resp.status_code == 422
        ), f"Expected 422 for missing field, got {resp.status_code}"
        body = resp.json()
        assert "detail" in body, "Expected 'detail' in validation error"

    def test_scan_folder_returns_batch_report(self, client, tmp_path):
        """Valid folder scan returns BatchIngestReport structure."""
        # Create folder with mock mp3 files
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        (audio_dir / "song1.mp3").write_bytes(b"mock mp3 1")
        (audio_dir / "song2.mp3").write_bytes(b"mock mp3 2")

        resp = client.post(
            "/api/v1/ingest/scan-folder",
            json={"folder_path": str(audio_dir), "recursive": False},
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        data = resp.json()
        assert (
            set(data.keys()) == EXPECTED_BATCH_REPORT_FIELDS
        ), f"Expected keys {EXPECTED_BATCH_REPORT_FIELDS}, got {set(data.keys())}"

        # Should have found 2 files
        assert (
            data["total_files"] == 2
        ), f"Expected 2 total_files, got {data['total_files']}"

    def test_recursive_false_only_scans_top_level(self, client, tmp_path):
        """recursive=false only processes top-level files."""
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        (audio_dir / "top.mp3").write_bytes(b"top level")

        subdir = audio_dir / "subfolder"
        subdir.mkdir()
        (subdir / "nested.mp3").write_bytes(b"nested")

        resp = client.post(
            "/api/v1/ingest/scan-folder",
            json={"folder_path": str(audio_dir), "recursive": False},
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()

        # Should only find top.mp3 (not nested.mp3)
        assert (
            data["total_files"] == 1
        ), f"Expected 1 file (non-recursive), got {data['total_files']}"

    def test_recursive_true_scans_subdirectories(self, client, tmp_path):
        """recursive=true processes all subdirectories."""
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        (audio_dir / "top.mp3").write_bytes(b"top level")

        subdir = audio_dir / "subfolder"
        subdir.mkdir()
        (subdir / "nested.mp3").write_bytes(b"nested")

        resp = client.post(
            "/api/v1/ingest/scan-folder",
            json={"folder_path": str(audio_dir), "recursive": True},
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()

        # Should find both files
        assert (
            data["total_files"] == 2
        ), f"Expected 2 files (recursive), got {data['total_files']}"


# ========================================
# PENDING CONVERT TESTS
# ========================================


class TestPendingConvertApi:
    """Group 4: GET /api/v1/ingest/pending-convert."""

    def test_empty_db_returns_empty_list(self, client):
        """No status=3 songs → 200 with empty list."""
        resp = client.get("/api/v1/ingest/pending-convert")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        # populated_db has no status=3 songs by default
        wav_items = [item for item in data if item.get("status") == "PENDING_CONVERT"]
        assert wav_items == [], f"Expected no PENDING_CONVERT items, got {wav_items}"

    def test_status3_song_appears_in_results(self, client, populated_db):
        """A song manually set to status=3 must appear in the results."""
        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute("UPDATE MediaSources SET ProcessingStatus = 3 WHERE SourceID = 1")
        conn.commit()
        conn.close()

        resp = client.get("/api/v1/ingest/pending-convert")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert (
            len(data) >= 1
        ), f"Expected at least one item for status=3 song, got {data}"

    def test_each_item_has_pending_convert_status(self, client, populated_db):
        """Every item returned must have status='PENDING_CONVERT'."""
        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute("UPDATE MediaSources SET ProcessingStatus = 3 WHERE SourceID = 1")
        conn.commit()
        conn.close()

        resp = client.get("/api/v1/ingest/pending-convert")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        for item in data:
            assert (
                item.get("status") == "PENDING_CONVERT"
            ), f"Expected status='PENDING_CONVERT', got '{item.get('status')}'"

    def test_each_item_has_required_shape(self, client, populated_db):
        """Each result item must have status, staged_path, and song keys."""
        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute("UPDATE MediaSources SET ProcessingStatus = 3 WHERE SourceID = 1")
        conn.commit()
        conn.close()

        resp = client.get("/api/v1/ingest/pending-convert")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert len(data) >= 1, "Need at least one item to check shape"
        for item in data:
            assert "status" in item, f"Missing 'status' key in item: {item}"
            assert "staged_path" in item, f"Missing 'staged_path' key in item: {item}"
            assert "song" in item, f"Missing 'song' key in item: {item}"

    def test_soft_deleted_status3_song_excluded(self, client, populated_db):
        """A soft-deleted song with status=3 must NOT appear in pending-convert results."""
        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET ProcessingStatus = 3, IsDeleted = 1 WHERE SourceID = 1"
        )
        conn.commit()
        conn.close()

        resp = client.get("/api/v1/ingest/pending-convert")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        song_ids = [item["song"]["id"] for item in data if item.get("song")]
        assert (
            1 not in song_ids
        ), f"Soft-deleted song 1 should not appear in pending-convert, got ids={song_ids}"


# ========================================
# CONVERT WAV TESTS
# ========================================


class TestConvertWavApi:
    """Group 5: POST /api/v1/ingest/convert-wav — no-DB-record error case."""

    def test_staged_path_not_in_db_returns_error(self, client, tmp_path):
        """A staged_path with no DB record must return status=ERROR with a clear message."""
        # Create a real WAV file so the router doesn't fail on file I/O before the DB check
        import wave

        wav_path = tmp_path / "phantom.wav"
        with wave.open(str(wav_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(44100)
            f.writeframes(b"\x00\x00" * 4410)

        resp = client.post(f"/api/v1/ingest/convert-wav?staged_path={wav_path}")
        assert resp.status_code == 200, f"Expected 200 envelope, got {resp.status_code}"
        data = resp.json()
        assert (
            data.get("status") == "ERROR"
        ), f"Expected status='ERROR' for unknown path, got '{data.get('status')}'"
        assert (
            "message" in data
        ), f"Expected 'message' key in error response, got {data}"
        assert (
            "No DB record" in data["message"]
        ), f"Expected 'No DB record' in message, got '{data['message']}'"
