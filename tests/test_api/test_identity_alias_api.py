"""
API tests for identity alias endpoints.
POST /api/v1/identities/{id}/aliases
DELETE /api/v1/identities/{id}/aliases/{name_id}

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
# POST /api/v1/identities/{identity_id}/aliases
# ---------------------------------------------------------------------------


class TestAddIdentityAliasApi:
    def test_add_new_alias_returns_200_and_body(self, api):
        resp = api.post(
            "/api/v1/identities/1/aliases", json={"display_name": "D. Grohl"}
        )
        assert (
            resp.status_code == 200
        ), f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "name_id" in data, f"Expected 'name_id' in response, got {data}"
        assert (
            data["display_name"] == "D. Grohl"
        ), f"Expected 'D. Grohl', got {data['display_name']}"
        assert data["name_id"] > 0, f"Expected positive name_id, got {data['name_id']}"

    def test_add_alias_with_name_id_relinks(self, api):
        """Re-link Grohlton (NameID=11) from identity 1 to identity 2."""
        resp = api.post(
            "/api/v1/identities/2/aliases",
            json={"display_name": "Grohlton", "name_id": 11},
        )
        assert (
            resp.status_code == 200
        ), f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["name_id"] == 11, f"Expected name_id=11, got {data['name_id']}"
        assert (
            data["display_name"] == "Grohlton"
        ), f"Expected 'Grohlton', got {data['display_name']}"

    def test_add_alias_invalid_identity_returns_404(self, api):
        resp = api.post(
            "/api/v1/identities/9999/aliases", json={"display_name": "Ghost"}
        )
        assert (
            resp.status_code == 404
        ), f"Expected 404, got {resp.status_code}: {resp.text}"

    def test_add_alias_steal_primary_with_siblings_returns_409(self, api):
        """Stealing Dave Grohl (primary, has other aliases) should be 409."""
        resp = api.post(
            "/api/v1/identities/2/aliases",
            json={"display_name": "Dave Grohl", "name_id": 10},
        )
        assert (
            resp.status_code == 409
        ), f"Expected 409, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# DELETE /api/v1/identities/{identity_id}/aliases/{name_id}
# ---------------------------------------------------------------------------


class TestRemoveIdentityAliasApi:
    def test_remove_alias_returns_204(self, api):
        resp = api.delete("/api/v1/identities/1/aliases/11")
        assert (
            resp.status_code == 204
        ), f"Expected 204, got {resp.status_code}: {resp.text}"

    def test_remove_primary_name_returns_400(self, api):
        resp = api.delete("/api/v1/identities/1/aliases/10")
        assert (
            resp.status_code == 400
        ), f"Expected 400, got {resp.status_code}: {resp.text}"

    def test_remove_nonexistent_name_id_returns_204(self, api):
        """Nonexistent name_id is a noop — should not error."""
        resp = api.delete("/api/v1/identities/1/aliases/9999")
        assert (
            resp.status_code == 204
        ), f"Expected 204 (noop), got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# PATCH /api/v1/identities/{identity_id}/legal-name
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# PATCH /api/v1/songs/{song_id}/credits/{name_id} — rename collision
# ---------------------------------------------------------------------------


class TestUpdateCreditNameApi:
    def test_clean_rename_returns_204(self, api):
        resp = api.patch(
            "/api/v1/songs/0/credits/11", json={"display_name": "Grohlton Reloaded"}
        )
        assert resp.status_code == 204, resp.text

    def test_collision_with_orphan_returns_409_merge_required(self, api):
        """Renaming Grohlton (11) to Taylor Hawkins (solo identity) → 409 MERGE_REQUIRED."""
        resp = api.patch(
            "/api/v1/songs/0/credits/11", json={"display_name": "Taylor Hawkins"}
        )
        assert resp.status_code == 409, resp.text
        body = resp.json()["detail"]
        assert body["code"] == "MERGE_REQUIRED"
        assert "collision_name_id" in body
        assert "source_identity_id" in body

    def test_collision_with_parent_returns_409_unsafe_merge(self, api):
        """Renaming Taylor (40) to Dave Grohl (multi-alias identity) → 409 UNSAFE_MERGE."""
        resp = api.patch(
            "/api/v1/songs/0/credits/40", json={"display_name": "Dave Grohl"}
        )
        assert resp.status_code == 409, resp.text
        body = resp.json()["detail"]
        assert body["code"] == "UNSAFE_MERGE"

    def test_rename_nonexistent_name_returns_404(self, api):
        resp = api.patch("/api/v1/songs/0/credits/9999", json={"display_name": "Ghost"})
        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# POST /api/v1/identities/merge
# ---------------------------------------------------------------------------


class TestMergeIdentityApi:
    def test_merge_returns_204(self, api):
        """Merging Taylor (NameID=40) into Dave (NameID=10) should succeed."""
        resp = api.post("/api/v1/identities/merge?source_name_id=40&target_name_id=10")
        assert resp.status_code == 204, resp.text

    def test_merge_source_not_found_returns_404(self, api):
        resp = api.post(
            "/api/v1/identities/merge?source_name_id=9999&target_name_id=10"
        )
        assert resp.status_code == 404, resp.text

    def test_merge_non_orphan_source_returns_400(self, api):
        """Dave Grohl (NameID=10) has multiple aliases — merge should be blocked."""
        resp = api.post("/api/v1/identities/merge?source_name_id=10&target_name_id=40")
        assert resp.status_code == 400, resp.text


class TestUpdateLegalNameApi:
    def test_update_legal_name_returns_204(self, api):
        resp = api.patch(
            "/api/v1/identities/1/legal-name",
            json={"legal_name": "David Eric Grohl Jr."},
        )
        assert (
            resp.status_code == 204
        ), f"Expected 204, got {resp.status_code}: {resp.text}"

    def test_update_legal_name_invalid_identity_returns_404(self, api):
        resp = api.patch(
            "/api/v1/identities/9999/legal-name", json={"legal_name": "Ghost"}
        )
        assert (
            resp.status_code == 404
        ), f"Expected 404, got {resp.status_code}: {resp.text}"

    def test_update_legal_name_to_null_returns_204(self, api):
        resp = api.patch("/api/v1/identities/1/legal-name", json={"legal_name": None})
        assert (
            resp.status_code == 204
        ), f"Expected 204, got {resp.status_code}: {resp.text}"
