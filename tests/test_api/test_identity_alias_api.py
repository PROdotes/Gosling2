"""
API tests for identity alias mutations via POST /api/v1/mutate.

populated_db identity fixtures:
  Identity 1 — Dave Grohl (primary NameID=10), aliases: Grohlton (11), Late! (12)
  Identity 2 — separate identity
"""

import pytest
from fastapi.testclient import TestClient
from src.engine_server import app


@pytest.fixture
def api(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


# ---------------------------------------------------------------------------
# add identity_alias
# ---------------------------------------------------------------------------


class TestAddIdentityAliasApi:
    def test_add_new_alias_returns_200(self, api):
        resp = api.post("/api/v1/mutate", json={"add": [{"type": "identity_alias", "identity_id": 1, "display_name": "D. Grohl"}]})
        assert resp.status_code == 200, resp.text

    def test_add_alias_with_name_id_relinks(self, api):
        resp = api.post("/api/v1/mutate", json={"add": [{"type": "identity_alias", "identity_id": 2, "display_name": "Grohlton", "name_id": 11}]})
        assert resp.status_code == 200, resp.text

    def test_add_alias_invalid_identity_fails(self, api):
        # 9999 is an impossible identity_id — UI only sends real IDs from dropdowns.
        # If it ever arrives, the FK constraint on ArtistNames.OwnerIdentityID is the
        # last line of defense. We pin that the DB rejects it (rather than silently
        # inserting an orphan row).
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            api.post("/api/v1/mutate", json={"add": [{"type": "identity_alias", "identity_id": 9999, "display_name": "Ghost"}]})

    def test_add_alias_steal_primary_with_siblings_returns_400(self, api):
        resp = api.post("/api/v1/mutate", json={"add": [{"type": "identity_alias", "identity_id": 2, "display_name": "Dave Grohl", "name_id": 10}]})
        assert resp.status_code == 400, resp.text


# ---------------------------------------------------------------------------
# remove identity_alias
# ---------------------------------------------------------------------------


class TestRemoveIdentityAliasApi:
    def test_remove_alias_returns_200(self, api):
        resp = api.post("/api/v1/mutate", json={"remove": [{"type": "identity_alias", "identity_id": 1, "name_id": 11}]})
        assert resp.status_code == 200, resp.text

    def test_remove_primary_name_returns_400(self, api):
        resp = api.post("/api/v1/mutate", json={"remove": [{"type": "identity_alias", "identity_id": 1, "name_id": 10}]})
        assert resp.status_code == 400, resp.text

    def test_remove_nonexistent_name_id_returns_200(self, api):
        resp = api.post("/api/v1/mutate", json={"remove": [{"type": "identity_alias", "identity_id": 1, "name_id": 9999}]})
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# PATCH /api/v1/identities/{identity_id}/legal-name  (dedicated endpoint, kept)
# ---------------------------------------------------------------------------


class TestUpdateLegalNameApi:
    def test_update_legal_name_returns_204(self, api):
        resp = api.patch("/api/v1/identities/1/legal-name", json={"legal_name": "David Eric Grohl Jr."})
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}: {resp.text}"

    def test_update_legal_name_invalid_identity_returns_404(self, api):
        resp = api.patch("/api/v1/identities/9999/legal-name", json={"legal_name": "Ghost"})
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"

    def test_update_legal_name_to_null_returns_204(self, api):
        resp = api.patch("/api/v1/identities/1/legal-name", json={"legal_name": None})
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# update credit name and merge — via mutate
# ---------------------------------------------------------------------------


class TestUpdateCreditNameApi:
    def test_clean_rename_returns_200(self, api):
        resp = api.post("/api/v1/mutate", json={"update": [{"type": "credit", "id": 11, "display_name": "Grohlton Reloaded"}]})
        assert resp.status_code == 200, resp.text

    def test_collision_with_existing_name_returns_409_merge_required(self, api):
        resp = api.post("/api/v1/mutate", json={"update": [{"type": "credit", "id": 11, "display_name": "Taylor Hawkins"}]})
        assert resp.status_code == 409, resp.text
        body = resp.json()["detail"]
        assert body["code"] == "MERGE_REQUIRED"
        assert "collision_id" in body

    def test_collision_with_parent_returns_409_merge_required(self, api):
        resp = api.post("/api/v1/mutate", json={"update": [{"type": "credit", "id": 40, "display_name": "Dave Grohl"}]})
        assert resp.status_code == 409, resp.text
        body = resp.json()["detail"]
        assert body["code"] == "MERGE_REQUIRED"

    def test_rename_nonexistent_name_returns_404(self, api):
        resp = api.post("/api/v1/mutate", json={"update": [{"type": "credit", "id": 9999, "display_name": "Ghost"}]})
        assert resp.status_code == 404, resp.text


class TestMergeIdentityApi:
    def test_merge_returns_200(self, api):
        resp = api.post("/api/v1/mutate", json={"merge": [{"type": "identity_merge", "source_name_id": 40, "target_name_id": 10}]})
        assert resp.status_code == 200, resp.text

    def test_merge_source_not_found_returns_404(self, api):
        resp = api.post("/api/v1/mutate", json={"merge": [{"type": "identity_merge", "source_name_id": 9999, "target_name_id": 10}]})
        assert resp.status_code == 404, resp.text

    def test_merge_non_orphan_source_returns_400(self, api):
        resp = api.post("/api/v1/mutate", json={"merge": [{"type": "identity_merge", "source_name_id": 10, "target_name_id": 40}]})
        assert resp.status_code == 400, resp.text
