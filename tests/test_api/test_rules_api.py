"""HTTP-layer tests for the filing rules router.

GET serves the current routing rules read fresh from json/rules.json plus any
load warnings. POST validates the whole ordered rule list -> persists it.
FilingService reads its own copy per LibraryService construction, so there is
no live in-memory instance to keep in sync here (unlike settings).
"""

import json

import pytest
from fastapi.testclient import TestClient

from src.engine import config


@pytest.fixture
def api(populated_db, tmp_path, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    monkeypatch.setattr(config, "RENAME_RULES_PATH", tmp_path / "rules.json")
    from src.engine_server import app

    return TestClient(app)


def _rules_path():
    return config.RENAME_RULES_PATH


def test_get_missing_file_returns_empty_rules_no_warnings(api):
    resp = api.get("/api/v1/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rules"] == {"routing_rules": [], "default_rule": None}
    assert body["warnings"] == []


def test_get_reflects_file(api):
    _rules_path().write_text(
        json.dumps(
            {
                "routing_rules": [
                    {
                        "match_genres": ["pop"],
                        "target_path": "{year}/{artist} - {title}",
                    }
                ],
                "default_rule": "{genre}/{artist} - {title}",
            }
        ),
        encoding="utf-8",
    )
    resp = api.get("/api/v1/rules")
    assert resp.status_code == 200
    body = resp.json()["rules"]
    assert body["routing_rules"] == [
        {"match_genres": ["pop"], "target_path": "{year}/{artist} - {title}"}
    ]
    assert body["default_rule"] == "{genre}/{artist} - {title}"


def test_get_corrupt_file_returns_empty_rules_with_warning(api):
    _rules_path().write_text("{ broken", encoding="utf-8")
    resp = api.get("/api/v1/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rules"]["routing_rules"] == []
    assert len(body["warnings"]) == 1
    assert body["warnings"][0]["kind"] == "rules_load"


def test_post_persists_full_rule_list(api):
    payload = {
        "routing_rules": [
            {"match_genres": ["pop"], "target_path": "{year}/{artist} - {title}"},
            {
                "match_genres": ["rock", "metal"],
                "target_path": "{genre}/{artist} - {title}",
            },
        ],
        "default_rule": "{genre}/{artist} - {title}",
    }
    resp = api.post("/api/v1/rules", json=payload)
    assert resp.status_code == 200
    assert resp.json()["rules"] == payload

    on_disk = json.loads(_rules_path().read_text())
    assert on_disk == payload


def test_post_reorders_and_replaces_previous_content(api):
    api.post(
        "/api/v1/rules",
        json={
            "routing_rules": [
                {"match_genres": ["pop"], "target_path": "{year}/{artist} - {title}"}
            ],
            "default_rule": None,
        },
    )
    replacement = {
        "routing_rules": [
            {"match_genres": ["rock"], "target_path": "{genre}/{artist} - {title}"}
        ],
        "default_rule": None,
    }
    resp = api.post("/api/v1/rules", json=replacement)
    assert resp.status_code == 200
    on_disk = json.loads(_rules_path().read_text())
    assert on_disk == replacement


def test_post_empty_match_genres_is_400_and_writes_nothing(api):
    resp = api.post(
        "/api/v1/rules",
        json={
            "routing_rules": [{"match_genres": [], "target_path": "{artist}"}],
            "default_rule": None,
        },
    )
    assert resp.status_code == 400
    assert not _rules_path().exists()


def test_post_unknown_token_is_400_and_writes_nothing(api):
    resp = api.post(
        "/api/v1/rules",
        json={
            "routing_rules": [
                {"match_genres": ["pop"], "target_path": "{bogus}/{artist}"}
            ],
            "default_rule": None,
        },
    )
    assert resp.status_code == 400
    assert not _rules_path().exists()


def test_post_unknown_token_in_default_rule_is_400(api):
    resp = api.post(
        "/api/v1/rules",
        json={"routing_rules": [], "default_rule": "{nope}"},
    )
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "target_path",
    [
        "C:\\Windows\\System32\\{artist}",
        "C:/Windows/{artist}",
        "/etc/{artist}",
        "\\etc\\{artist}",
        "../{genre}/{artist}",
        "{genre}/../{artist}",
    ],
)
def test_post_unsafe_target_path_is_400_and_writes_nothing(api, target_path):
    resp = api.post(
        "/api/v1/rules",
        json={
            "routing_rules": [{"match_genres": ["pop"], "target_path": target_path}],
            "default_rule": None,
        },
    )
    assert resp.status_code == 400
    assert not _rules_path().exists()


@pytest.mark.parametrize(
    "default_rule",
    [
        "Z:\\{genre}/{artist} - {title}",
        "/{genre}/{artist} - {title}",
        "../{genre}/{artist} - {title}",
    ],
)
def test_post_unsafe_default_rule_is_400(api, default_rule):
    resp = api.post(
        "/api/v1/rules",
        json={"routing_rules": [], "default_rule": default_rule},
    )
    assert resp.status_code == 400
    assert not _rules_path().exists()


def test_post_relative_path_with_dotted_folder_name_is_still_allowed(api):
    resp = api.post(
        "/api/v1/rules",
        json={
            "routing_rules": [
                {"match_genres": ["pop"], "target_path": "Va.rious/{artist} - {title}"}
            ],
            "default_rule": None,
        },
    )
    assert resp.status_code == 200


def _seed_rules():
    _rules_path().write_text(
        json.dumps(
            {
                "routing_rules": [
                    {
                        "match_genres": ["samba"],
                        "target_path": "latin/{artist} - {title}",
                    },
                    {
                        "match_genres": ["Pop", "Rock"],
                        "target_path": "{genre}/{artist} - {title}",
                    },
                ],
                "default_rule": "{genre}/{year}/{artist} - {title}",
            }
        ),
        encoding="utf-8",
    )


def test_resolve_returns_matching_rule(api):
    _seed_rules()
    resp = api.get("/api/v1/rules/resolve", params={"genre": "samba"})
    assert resp.status_code == 200
    assert resp.json() == {
        "target_path": "latin/{artist} - {title}",
        "rule_index": 0,
        "source": "rule",
    }


def test_resolve_is_case_insensitive_and_matches_by_index(api):
    _seed_rules()
    resp = api.get("/api/v1/rules/resolve", params={"genre": "rock"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["rule_index"] == 1
    assert body["source"] == "rule"
    assert body["target_path"] == "{genre}/{artist} - {title}"


def test_resolve_falls_back_to_default_rule(api):
    _seed_rules()
    resp = api.get("/api/v1/rules/resolve", params={"genre": "jazz"})
    assert resp.status_code == 200
    assert resp.json() == {
        "target_path": "{genre}/{year}/{artist} - {title}",
        "rule_index": None,
        "source": "default",
    }


def test_resolve_with_no_rules_and_no_default_returns_none(api):
    resp = api.get("/api/v1/rules/resolve", params={"genre": "anything"})
    assert resp.status_code == 200
    assert resp.json() == {"target_path": None, "rule_index": None, "source": "none"}
