"""
API tests for identity type conversion and group membership via the mutate endpoint.

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
# identity type via POST /api/v1/mutate
# ---------------------------------------------------------------------------


class TestSetIdentityTypeApi:
    def test_person_to_group_returns_200(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={"update": [{"type": "identity", "id": 4, "identity_type": "group"}]},
        )
        assert resp.status_code == 200, resp.text

    def test_group_to_person_no_members_returns_200(self, api):
        api.post(
            "/api/v1/mutate",
            json={
                "remove": [{"type": "identity_member", "group_id": 2, "member_id": 1}]
            },
        )
        resp = api.post(
            "/api/v1/mutate",
            json={"update": [{"type": "identity", "id": 2, "identity_type": "person"}]},
        )
        assert resp.status_code == 200, resp.text

    def test_group_to_person_with_members_returns_400(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={"update": [{"type": "identity", "id": 2, "identity_type": "person"}]},
        )
        assert resp.status_code == 400, resp.text

    def test_invalid_type_returns_422(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={"update": [{"type": "identity", "id": 1, "identity_type": "band"}]},
        )
        assert resp.status_code == 422, resp.text

    def test_not_found_returns_404(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={
                "update": [{"type": "identity", "id": 9999, "identity_type": "group"}]
            },
        )
        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# identity members via POST /api/v1/mutate
# ---------------------------------------------------------------------------


class TestAddIdentityMemberApi:
    def test_add_member_returns_200(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={"add": [{"type": "identity_member", "group_id": 2, "member_id": 4}]},
        )
        assert resp.status_code == 200, resp.text

    def test_add_self_returns_400(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={"add": [{"type": "identity_member", "group_id": 2, "member_id": 2}]},
        )
        assert resp.status_code == 400, resp.text

    def test_add_group_as_member_returns_400(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={"add": [{"type": "identity_member", "group_id": 2, "member_id": 3}]},
        )
        assert resp.status_code == 400, resp.text

    def test_group_not_found_returns_404(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={
                "add": [{"type": "identity_member", "group_id": 9999, "member_id": 1}]
            },
        )
        assert resp.status_code == 404, resp.text

    def test_member_not_found_returns_404(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={
                "add": [{"type": "identity_member", "group_id": 2, "member_id": 9999}]
            },
        )
        assert resp.status_code == 404, resp.text


class TestRemoveIdentityMemberApi:
    def test_remove_member_returns_200(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={
                "remove": [{"type": "identity_member", "group_id": 2, "member_id": 1}]
            },
        )
        assert resp.status_code == 200, resp.text

    def test_remove_nonexistent_member_returns_200(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={
                "remove": [{"type": "identity_member", "group_id": 2, "member_id": 4}]
            },
        )
        assert resp.status_code == 200, resp.text
