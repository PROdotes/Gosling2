"""
API tests for the splitter endpoints.

POST /api/v1/tools/splitter/tokenize
  - Stateless, no DB needed.
  - Tokenizer logic is tested in test_tokenizer.py — here we only verify
    the endpoint wires through and returns the correct shape.

POST /api/v1/tools/splitter/preview
  - Identity lookup per name. Uses populated_db.
  - populated_db identities:
      1: Dave Grohl (person)
      2: Nirvana (group)
      3: Foo Fighters (group)
      4: Taylor Hawkins (person)

POST /api/v1/tools/splitter/confirm
  - Splits a credit string into individual credits or publishers.
  - Deletes the original credit/publisher after splitting.
  - populated_db songs: 1=SLTS, 2=Everlong, 3=Range Rover Bitch, ...
  - populated_db publishers: 10=DGC Records (linked to song 1)
"""

import pytest
from fastapi.testclient import TestClient
from src.engine_server import app


@pytest.fixture
def api():
    return TestClient(app)


@pytest.fixture
def api_db(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/v1/tools/splitter/tokenize
# ---------------------------------------------------------------------------


class TestTokenize:
    def test_returns_tokens(self, api):
        r = api.post(
            "/api/v1/tools/splitter/tokenize",
            json={"text": "John & Paul", "separators": [" & "]},
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        tokens = r.json()
        assert tokens == [
            {"type": "name", "text": "John"},
            {"type": "sep", "text": " & "},
            {"type": "name", "text": "Paul"},
        ], f"Unexpected tokens: {tokens}"

    def test_missing_text_returns_422(self, api):
        r = api.post("/api/v1/tools/splitter/tokenize", json={"separators": [" & "]})
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"

    def test_missing_separators_returns_422(self, api):
        r = api.post("/api/v1/tools/splitter/tokenize", json={"text": "John & Paul"})
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"


# ---------------------------------------------------------------------------
# POST /api/v1/tools/splitter/preview
# ---------------------------------------------------------------------------


class TestPreview:
    def test_known_name_returns_exists_true(self, api_db):
        r = api_db.post(
            "/api/v1/tools/splitter/preview",
            json={"names": ["Dave Grohl"], "target": "credits"},
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        results = r.json()
        assert results[0]["name"] == "Dave Grohl"
        assert results[0]["exists"] is True

    def test_known_name_returns_identity_id(self, api_db):
        """Truth-First: Splitter preview should return the identity ID for known artists."""
        r = api_db.post(
            "/api/v1/tools/splitter/preview",
            json={"names": ["Dave Grohl"], "target": "credits"},
        )
        assert r.status_code == 200
        results = r.json()
        assert results[0]["exists"] is True
        assert results[0]["identity_id"] == 1, (
            f"Expected identity_id 1, got {results[0].get('identity_id')}"
        )

    def test_unknown_name_returns_exists_false(self, api_db):
        r = api_db.post(
            "/api/v1/tools/splitter/preview",
            json={"names": ["Nobody Famous"], "target": "credits"},
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        results = r.json()
        assert results[0]["exists"] is False

    def test_multiple_names_returned_in_order(self, api_db):
        r = api_db.post(
            "/api/v1/tools/splitter/preview",
            json={"names": ["Dave Grohl", "Nobody Famous"], "target": "credits"},
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        results = r.json()
        assert len(results) == 2
        assert results[0]["name"] == "Dave Grohl"
        assert results[1]["name"] == "Nobody Famous"

    def test_empty_names_returns_empty_list(self, api_db):
        r = api_db.post(
            "/api/v1/tools/splitter/preview", json={"names": [], "target": "credits"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert r.json() == []

    def test_missing_fields_returns_422(self, api_db):
        r = api_db.post("/api/v1/tools/splitter/preview", json={})
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"


# ---------------------------------------------------------------------------
# POST /api/v1/tools/splitter/confirm
# ---------------------------------------------------------------------------


class TestConfirm:
    def test_split_credits(self, api_db):
        add = api_db.post(
            "/api/v1/songs/2/credits",
            json={
                "display_name": "Dave Grohl & Taylor Hawkins",
                "role_name": "Composer",
            },
        )
        assert add.status_code == 200, f"Setup failed: {add.status_code} {add.text}"
        credit_id = add.json()["credit_id"]

        r = api_db.post(
            "/api/v1/tools/splitter/confirm",
            json={
                "song_id": 2,
                "tokens": [
                    {"type": "name", "text": "Dave Grohl"},
                    {"type": "sep", "text": " & "},
                    {"type": "name", "text": "Taylor Hawkins"},
                ],
                "target": "credits",
                "classification": "Composer",
                "remove": {"type": "credit", "id": credit_id},
            },
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"

        song = api_db.get("/api/v1/songs/2").json()
        credit_names = [c["display_name"] for c in song["credits"]]
        assert "Dave Grohl & Taylor Hawkins" not in credit_names
        assert "Dave Grohl" in credit_names
        assert "Taylor Hawkins" in credit_names

    def test_split_credits_with_ignored_sep(self, api_db):
        add = api_db.post(
            "/api/v1/songs/2/credits",
            json={"display_name": "Earth, Wind & Fire & ABBA", "role_name": "Composer"},
        )
        assert add.status_code == 200, f"Setup failed: {add.status_code} {add.text}"
        credit_id = add.json()["credit_id"]

        r = api_db.post(
            "/api/v1/tools/splitter/confirm",
            json={
                "song_id": 2,
                "tokens": [
                    {"type": "name", "text": "Earth"},
                    {"type": "sep", "text": ", ", "ignore": True},
                    {"type": "name", "text": "Wind"},
                    {"type": "sep", "text": " & ", "ignore": True},
                    {"type": "name", "text": "Fire"},
                    {"type": "sep", "text": " & "},
                    {"type": "name", "text": "ABBA"},
                ],
                "target": "credits",
                "classification": "Composer",
                "remove": {"type": "credit", "id": credit_id},
            },
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"

        song = api_db.get("/api/v1/songs/2").json()
        credit_names = [c["display_name"] for c in song["credits"]]
        assert "Earth, Wind & Fire" in credit_names
        assert "ABBA" in credit_names
        assert "Earth, Wind & Fire & ABBA" not in credit_names

    def test_split_publishers(self, api_db):
        add = api_db.post(
            "/api/v1/songs/2/publishers", json={"publisher_name": "Universal & Sub Pop"}
        )
        assert add.status_code == 200, f"Setup failed: {add.status_code} {add.text}"
        publisher_id = add.json()["id"]

        r = api_db.post(
            "/api/v1/tools/splitter/confirm",
            json={
                "song_id": 2,
                "tokens": [
                    {"type": "name", "text": "Universal Music Group"},
                    {"type": "sep", "text": " & "},
                    {"type": "name", "text": "Sub Pop"},
                ],
                "target": "publishers",
                "classification": None,
                "remove": {"type": "publisher", "id": publisher_id},
            },
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"

        song = api_db.get("/api/v1/songs/2").json()
        pub_names = [p["name"] for p in song["publishers"]]
        assert "Universal & Sub Pop" not in pub_names
        assert "Universal Music Group" in pub_names
        assert "Sub Pop" in pub_names

    def test_unknown_target_returns_422(self, api_db):
        r = api_db.post(
            "/api/v1/tools/splitter/confirm",
            json={
                "song_id": 1,
                "tokens": [{"type": "name", "text": "Dave Grohl"}],
                "target": "bananas",
                "classification": None,
                "remove": {"type": "credit", "id": 1},
            },
        )
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"

    def test_missing_fields_returns_422(self, api_db):
        r = api_db.post("/api/v1/tools/splitter/confirm", json={"song_id": 1})
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"
