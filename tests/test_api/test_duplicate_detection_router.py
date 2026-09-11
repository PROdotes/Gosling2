import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.data.audio_fingerprint_repository import AudioFingerprintRepository
from src.engine_server import app


@pytest.fixture
def api(populated_db, monkeypatch):
    """Hermetic API client with isolated populated DB."""
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


def _seed_fingerprint(db_path, source_id, blob, duration_s):
    repo = AudioFingerprintRepository(db_path)
    with repo._get_connection() as conn:
        repo.set_fingerprint(source_id, blob, duration_s, 180, conn)
        conn.commit()


def _blob(seed, length=300):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2**32, size=length, dtype=np.uint64).astype("<u4").tobytes()


class TestFindDuplicatesRouter:
    def test_unknown_song_returns_404(self, api):
        response = api.post("/api/v1/songs/999999/find-duplicates")
        assert response.status_code == 404

    def test_song_without_fingerprint_is_not_comparable(self, api):
        # Song 1 exists in populated_db but has no AudioFingerprints row.
        response = api.post("/api/v1/songs/1/find-duplicates")
        assert response.status_code == 200
        data = response.json()
        assert data["comparable"] is False
        assert data["matches"] == []

    def test_matching_fingerprints_are_returned(self, api, populated_db):
        # Songs 1 and 2 given the identical fingerprint at close durations -
        # a duplicate pair. Song 3 gets an unrelated fingerprint.
        same_blob = _blob(seed=1)
        _seed_fingerprint(populated_db, 1, same_blob, 200.0)
        _seed_fingerprint(populated_db, 2, same_blob, 205.0)
        _seed_fingerprint(populated_db, 3, _blob(seed=2), 200.0)

        response = api.post("/api/v1/songs/1/find-duplicates")
        assert response.status_code == 200
        data = response.json()
        assert data["comparable"] is True

        matched_ids = [m["song_id"] for m in data["matches"]]
        assert matched_ids == [2]
        match = data["matches"][0]
        assert match["score"] == pytest.approx(1.0)
        assert match["title"] == "Everlong"

    def test_threshold_query_param_narrows_results(self, api, populated_db):
        same_blob = _blob(seed=1)
        _seed_fingerprint(populated_db, 1, same_blob, 200.0)
        _seed_fingerprint(populated_db, 2, same_blob, 205.0)

        response = api.post("/api/v1/songs/1/find-duplicates?threshold=1.1")
        assert response.status_code == 200
        assert response.json()["matches"] == []

    def test_no_writes_to_the_database(self, api, populated_db):
        # Sanity check on the "read-only" contract: calling the endpoint
        # must not create ChangeLog rows or otherwise mutate the DB.
        import sqlite3

        same_blob = _blob(seed=1)
        _seed_fingerprint(populated_db, 1, same_blob, 200.0)
        _seed_fingerprint(populated_db, 2, same_blob, 205.0)

        conn = sqlite3.connect(populated_db)
        try:
            before = conn.execute("SELECT COUNT(*) FROM ChangeLog").fetchone()[0]
        except sqlite3.OperationalError:
            before = 0
        conn.close()

        api.post("/api/v1/songs/1/find-duplicates")

        conn = sqlite3.connect(populated_db)
        try:
            after = conn.execute("SELECT COUNT(*) FROM ChangeLog").fetchone()[0]
        except sqlite3.OperationalError:
            after = 0
        conn.close()

        assert after == before
