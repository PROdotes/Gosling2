"""HTTP-layer tests for the settings router.

GET serves the current values (read fresh from json/settings.json), the JSON
schema the editor form is generated from, and any load warnings. POST validates
-> persists the full settings -> pushes onto the live settings instance. The
model logic itself is covered in test_config_service.py.
"""

import json

import pytest
from fastapi.testclient import TestClient

from src.engine import config
from src.services.config_service import Settings, settings

FIELD_NAMES = set(Settings.model_fields)


@pytest.fixture
def api(populated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "settings.json")
    # POST mutates the live settings instance; snapshot and restore so a write
    # test never leaks into the next test's defaults.
    saved = settings.model_dump()
    from src.engine_server import app

    yield TestClient(app)
    for name, value in saved.items():
        setattr(settings, name, value)


def _settings_path():
    return config.SETTINGS_PATH


def test_get_returns_all_keys_no_warnings(api):
    resp = api.get("/api/v1/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["settings"].keys()) == FIELD_NAMES
    assert body["warnings"] == []


def test_get_returns_schema_for_form_generation(api):
    resp = api.get("/api/v1/settings")
    assert resp.status_code == 200
    schema = resp.json()["schema"]
    assert set(schema["properties"].keys()) == FIELD_NAMES
    # The select field's options come from the SearchEngine enum in $defs.
    assert "SearchEngine" in schema["$defs"]
    assert set(schema["$defs"]["SearchEngine"]["enum"]) == {
        "spotify",
        "google",
        "youtube",
        "musicbrainz",
    }


def test_get_reflects_file(api):
    target = not Settings().auto_save_id3
    _settings_path().write_text(json.dumps({"auto_save_id3": target}), encoding="utf-8")
    resp = api.get("/api/v1/settings")
    assert resp.status_code == 200
    assert resp.json()["settings"]["auto_save_id3"] == target


def test_get_corrupt_file_returns_defaults_with_warning(api):
    _settings_path().write_text("{ broken", encoding="utf-8")
    resp = api.get("/api/v1/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["settings"]["auto_save_id3"] == Settings().auto_save_id3
    assert len(body["warnings"]) == 1
    assert body["warnings"][0]["kind"] == "settings_load"


def test_post_persists_full_file_and_updates_live(api):
    target = not settings.auto_save_id3
    resp = api.post("/api/v1/settings", json={"auto_save_id3": target})
    assert resp.status_code == 200
    body = resp.json()
    assert body["settings"]["auto_save_id3"] == target
    # Full settings persisted (JSON is the source of truth)...
    on_disk = json.loads(_settings_path().read_text())
    assert set(on_disk) == FIELD_NAMES
    assert on_disk["auto_save_id3"] == target
    # ...and pushed onto the live instance.
    assert settings.auto_save_id3 == target


def test_post_unknown_key_is_400_and_writes_nothing(api):
    resp = api.post("/api/v1/settings", json={"totally_made_up_key": True})
    assert resp.status_code == 400
    assert not _settings_path().exists()


def test_post_bad_type_is_400(api):
    resp = api.post("/api/v1/settings", json={"auto_save_id3": [1, 2]})
    assert resp.status_code == 400


def test_post_unknown_search_engine_is_400(api):
    resp = api.post("/api/v1/settings", json={"default_search_engine": "bogus"})
    assert resp.status_code == 400
