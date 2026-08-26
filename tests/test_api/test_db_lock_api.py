"""The audit tripwire must surface to the write path as a structured 409.

A locked DB fails the mutate outright (get_connection raises before anything is
written), so it is an error response, not a 200-with-warning like filing failures.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.engine_server import app


@pytest.fixture
def api_client(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


def _lock_db(path):
    """Leave an unstamped ChangeLog row, exactly what a bypassed write_connection()
    commits. Written directly rather than via triggers so the test does not depend
    on trigger installation."""
    conn = sqlite3.connect(path)
    conn.execute(
        "INSERT INTO ChangeLog (batch_id, table_name, entity_id, field_name, "
        "old_value, new_value) VALUES (NULL, 'Songs', 1, 'TempoBPM', '100', '99')"
    )
    conn.commit()
    conn.close()


def test_mutate_on_locked_db_returns_structured_409(api_client, populated_db):
    _lock_db(populated_db)

    resp = api_client.post(
        "/api/v1/mutate",
        json={"update": [{"type": "song", "id": 1, "title": "Anything"}]},
    )

    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["code"] == "DB_LOCKED"
    assert detail["null_batch_rows"] > 0
    assert "NULL batch_id" in detail["message"]


def test_multi_mutate_on_locked_db_returns_structured_409(api_client, populated_db):
    _lock_db(populated_db)

    resp = api_client.post(
        "/api/v1/songs/multi-mutate",
        json={"song_ids": [1, 2], "update": {"year": 2020}},
    )

    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "DB_LOCKED"


def test_mutate_on_clean_db_is_not_locked(api_client):
    resp = api_client.post(
        "/api/v1/mutate",
        json={"update": [{"type": "song", "id": 1, "title": "Clean Write"}]},
    )

    assert resp.status_code == 200, resp.text
