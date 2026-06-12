"""
HTTP-layer tests for the multi-edit router (request validation + error
mapping). Packer expansion logic is covered in test_multi_edit_service.py.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    from src.engine_server import app

    return TestClient(app)


def test_multi_view_returns_collapsed_song(api):
    resp = api.post("/api/v1/songs/multi-view", json={"song_ids": [1, 2]})
    assert resp.status_code == 200
    assert resp.json()["id"] is None


def test_multi_mutate_requires_at_least_one_op(api):
    resp = api.post("/api/v1/songs/multi-mutate", json={"song_ids": [1, 2]})
    assert resp.status_code == 422


def test_multi_mutate_requires_two_songs(api):
    resp = api.post(
        "/api/v1/songs/multi-mutate",
        json={"song_ids": [1], "update": {"year": 2000}},
    )
    assert resp.status_code == 422


def test_multi_mutate_rejects_unknown_update_field(api):
    # extra="forbid" on MultiUpdateOp: non-multi-editable fields must not
    # be silently dropped into a 200 no-op.
    resp = api.post(
        "/api/v1/songs/multi-mutate",
        json={"song_ids": [1, 2], "update": {"processing_status": 2}},
    )
    assert resp.status_code == 422


def test_multi_mutate_missing_song_is_404(api):
    resp = api.post(
        "/api/v1/songs/multi-mutate",
        json={"song_ids": [1, 999999], "update": {"year": 2000}},
    )
    assert resp.status_code == 404


def test_multi_mutate_absent_remove_target_is_404(api):
    resp = api.post(
        "/api/v1/songs/multi-mutate",
        json={"song_ids": [1, 2], "remove": [{"type": "tag", "id": 999999}]},
    )
    assert resp.status_code == 404


def test_multi_mutate_partial_remove_target_is_400(api):
    # Energetic(2) is on song 1 only -> not universal across [1, 9]
    resp = api.post(
        "/api/v1/songs/multi-mutate",
        json={"song_ids": [1, 9], "remove": [{"type": "tag", "id": 2}]},
    )
    assert resp.status_code == 400
