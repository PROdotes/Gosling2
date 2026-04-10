"""
API tests for identity type conversion and group membership endpoints.

PATCH  /api/v1/identities/{id}/type
POST   /api/v1/identities/{id}/members
DELETE /api/v1/identities/{id}/members/{member_id}

populated_db fixtures:
  ID=1: person  "Dave Grohl"    aliases: Grohlton(11), Late!(12), Ines Prajo(33)
  ID=2: group   "Nirvana"       members: Dave(1)
  ID=3: group   "Foo Fighters"  members: Dave(1), Taylor(4)
  ID=4: person  "Taylor Hawkins"
"""

import pytest
from fastapi.testclient import TestClient
from src.engine_server import app


@pytest.fixture
def api(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


# ---------------------------------------------------------------------------
# PATCH /api/v1/identities/{id}/type
# ---------------------------------------------------------------------------


class TestSetIdentityTypeApi:

    def test_person_to_group_returns_204(self, api):
        resp = api.patch("/api/v1/identities/4/type", json={"type": "group"})
        assert resp.status_code == 204, resp.text

    def test_group_to_person_no_members_returns_204(self, api):
        # Remove Dave from Nirvana first
        api.delete("/api/v1/identities/2/members/1")
        resp = api.patch("/api/v1/identities/2/type", json={"type": "person"})
        assert resp.status_code == 204, resp.text

    def test_group_to_person_with_members_returns_400(self, api):
        resp = api.patch("/api/v1/identities/2/type", json={"type": "person"})
        assert resp.status_code == 400, resp.text

    def test_invalid_type_returns_400(self, api):
        resp = api.patch("/api/v1/identities/1/type", json={"type": "band"})
        assert resp.status_code == 400, resp.text

    def test_not_found_returns_404(self, api):
        resp = api.patch("/api/v1/identities/9999/type", json={"type": "group"})
        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# POST /api/v1/identities/{id}/members
# ---------------------------------------------------------------------------


class TestAddIdentityMemberApi:

    def test_add_member_returns_204(self, api):
        resp = api.post("/api/v1/identities/2/members", json={"member_id": 4})
        assert resp.status_code == 204, resp.text

    def test_add_self_returns_400(self, api):
        resp = api.post("/api/v1/identities/2/members", json={"member_id": 2})
        assert resp.status_code == 400, resp.text

    def test_add_group_as_member_returns_400(self, api):
        resp = api.post("/api/v1/identities/2/members", json={"member_id": 3})
        assert resp.status_code == 400, resp.text

    def test_group_not_found_returns_404(self, api):
        resp = api.post("/api/v1/identities/9999/members", json={"member_id": 1})
        assert resp.status_code == 404, resp.text

    def test_member_not_found_returns_404(self, api):
        resp = api.post("/api/v1/identities/2/members", json={"member_id": 9999})
        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# DELETE /api/v1/identities/{id}/members/{member_id}
# ---------------------------------------------------------------------------


class TestRemoveIdentityMemberApi:

    def test_remove_member_returns_204(self, api):
        resp = api.delete("/api/v1/identities/2/members/1")
        assert resp.status_code == 204, resp.text

    def test_remove_nonexistent_member_returns_204(self, api):
        resp = api.delete("/api/v1/identities/2/members/4")  # Taylor not in Nirvana
        assert resp.status_code == 204, resp.text
