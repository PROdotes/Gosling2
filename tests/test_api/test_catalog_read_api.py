"""
API tests for catalog read endpoints (GET).
Verifies response shapes match TagView and PublisherView contracts.

populated_db reference:
  Tags:
    1: Grunge / Genre
    2: Energetic / Mood
    3: 90s / Era
    4: Electronic / Style
    5: English / Jezik
    6: Alt Rock / Genre

  Publishers:
    1:  Universal Music Group  parent=NULL
    2:  Island Records         parent=1
    3:  Island Def Jam         parent=2
    4:  Roswell Records        parent=NULL
    5:  Sub Pop                parent=NULL
    10: DGC Records            parent=1
"""

import pytest
from fastapi.testclient import TestClient
from src.engine_server import app


@pytest.fixture
def api(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tags  GET /api/v1/tags  GET /api/v1/tags/search  GET /api/v1/tags/{id}
# ---------------------------------------------------------------------------


class TestGetAllTags:
    def test_returns_200_with_list(self, api):
        resp = api.get("/api/v1/tags")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) == 6, f"Expected 6 tags, got {len(data)}"

    def test_response_shape_matches_tag_view(self, api):
        resp = api.get("/api/v1/tags")
        data = resp.json()
        tag = next(t for t in data if t["id"] == 1)
        assert tag["id"] == 1, f"Expected id=1, got {tag['id']}"
        assert tag["name"] == "Grunge", f"Expected name='Grunge', got {tag['name']}"
        assert tag["category"] == "Genre", (
            f"Expected category='Genre', got {tag['category']}"
        )
        # Verify no domain-only fields leak through
        assert "is_primary" not in tag, "TagView must not expose is_primary on list"

    def test_all_tags_present(self, api):
        resp = api.get("/api/v1/tags")
        data = resp.json()
        ids = [t["id"] for t in data]
        for expected_id in [1, 2, 3, 4, 5, 6]:
            assert expected_id in ids, (
                f"Expected tag_id={expected_id} in list, got {ids}"
            )

    def test_empty_db_returns_empty_list(self, empty_db, monkeypatch):
        monkeypatch.setenv("GOSLING_DB_PATH", empty_db)
        client = TestClient(app)
        resp = client.get("/api/v1/tags")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


class TestSearchTags:
    def test_search_returns_matching_tags(self, api):
        resp = api.get("/api/v1/tags/search?q=Grunge")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert len(data) == 1, f"Expected 1 result, got {len(data)}"
        assert data[0]["id"] == 1, f"Expected id=1, got {data[0]['id']}"
        assert data[0]["name"] == "Grunge", f"Expected 'Grunge', got {data[0]['name']}"
        assert data[0]["category"] == "Genre", (
            f"Expected 'Genre', got {data[0]['category']}"
        )

    def test_search_excludes_non_matching(self, api):
        resp = api.get("/api/v1/tags/search?q=Grunge")
        data = resp.json()
        ids = [t["id"] for t in data]
        for excluded in [2, 3, 4, 5, 6]:
            assert excluded not in ids, (
                f"Tag {excluded} should not match 'Grunge', got {ids}"
            )

    def test_search_no_results_returns_empty_list(self, api):
        resp = api.get("/api/v1/tags/search?q=ZZZNoMatch")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


class TestGetTagById:
    def test_existing_tag_returns_200_with_full_shape(self, api):
        resp = api.get("/api/v1/tags/1")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["id"] == 1, f"Expected id=1, got {data['id']}"
        assert data["name"] == "Grunge", f"Expected name='Grunge', got {data['name']}"
        assert data["category"] == "Genre", (
            f"Expected category='Genre', got {data['category']}"
        )

    def test_tag_with_null_category_returns_none(self, api):
        # Tag 2 has category "Mood" — test a tag with a real category
        # and verify no extra fields appear
        resp = api.get("/api/v1/tags/2")
        data = resp.json()
        assert data["id"] == 2, f"Expected id=2, got {data['id']}"
        assert data["name"] == "Energetic", f"Expected 'Energetic', got {data['name']}"
        assert data["category"] == "Mood", f"Expected 'Mood', got {data['category']}"
        assert "is_primary" not in data, "TagView must not expose is_primary on detail"

    def test_nonexistent_tag_returns_404(self, api):
        resp = api.get("/api/v1/tags/9999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_invalid_id_returns_405(self, api):
        # `:int` path constraint causes FastAPI to return 405 (no matching route) for non-int IDs
        resp = api.get("/api/v1/tags/not_an_int")
        assert resp.status_code == 405, f"Expected 405, got {resp.status_code}"


class TestGetTagCategories:
    def test_returns_distinct_categories(self, api):
        resp = api.get("/api/v1/tags/categories")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        for expected in ["Genre", "Mood", "Era", "Style", "Jezik"]:
            assert expected in data, (
                f"Expected category '{expected}' in list, got {data}"
            )

    def test_no_duplicates_in_categories(self, api):
        resp = api.get("/api/v1/tags/categories")
        data = resp.json()
        assert len(data) == len(set(data)), f"Duplicate categories found: {data}"


# ---------------------------------------------------------------------------
# Publishers  GET /api/v1/publishers  GET /api/v1/publishers/search  GET /api/v1/publishers/{id}
# ---------------------------------------------------------------------------


class TestGetAllPublishers:
    def test_returns_200_with_list(self, api):
        resp = api.get("/api/v1/publishers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) == 6, f"Expected 6 publishers, got {len(data)}"

    def test_response_shape_matches_publisher_view(self, api):
        resp = api.get("/api/v1/publishers")
        data = resp.json()
        pub = next(p for p in data if p["id"] == 10)
        assert pub["id"] == 10, f"Expected id=10, got {pub['id']}"
        assert pub["name"] == "DGC Records", (
            f"Expected name='DGC Records', got {pub['name']}"
        )
        assert pub["parent_name"] == "Universal Music Group", (
            f"Expected parent_name='Universal Music Group', got {pub['parent_name']}"
        )
        assert "sub_publishers" in pub, "PublisherView must include sub_publishers"
        # Verify no domain-only fields leak through
        assert "parent_id" not in pub, "PublisherView must not expose parent_id"

    def test_top_level_publisher_has_null_parent(self, api):
        resp = api.get("/api/v1/publishers")
        data = resp.json()
        umg = next(p for p in data if p["id"] == 1)
        assert umg["parent_name"] is None, (
            f"Expected parent_name=None for UMG, got {umg['parent_name']}"
        )

    def test_all_publishers_present(self, api):
        resp = api.get("/api/v1/publishers")
        data = resp.json()
        ids = [p["id"] for p in data]
        for expected_id in [1, 2, 3, 4, 5, 10]:
            assert expected_id in ids, (
                f"Expected pub_id={expected_id} in list, got {ids}"
            )

    def test_empty_db_returns_empty_list(self, empty_db, monkeypatch):
        monkeypatch.setenv("GOSLING_DB_PATH", empty_db)
        client = TestClient(app)
        resp = client.get("/api/v1/publishers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


class TestSearchPublishers:
    def test_search_returns_matching_publishers(self, api):
        resp = api.get("/api/v1/publishers/search?q=Sub Pop")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert len(data) == 1, f"Expected 1 result, got {len(data)}"
        assert data[0]["id"] == 5, f"Expected id=5, got {data[0]['id']}"
        assert data[0]["name"] == "Sub Pop", (
            f"Expected 'Sub Pop', got {data[0]['name']}"
        )

    def test_search_excludes_non_matching(self, api):
        resp = api.get("/api/v1/publishers/search?q=Sub Pop")
        data = resp.json()
        ids = [p["id"] for p in data]
        for excluded in [1, 2, 3, 4, 10]:
            assert excluded not in ids, (
                f"Publisher {excluded} should not match 'Sub Pop', got {ids}"
            )

    def test_search_no_results_returns_empty_list(self, api):
        resp = api.get("/api/v1/publishers/search?q=ZZZNoMatch")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"


class TestGetPublisherById:
    def test_existing_publisher_returns_200_with_full_shape(self, api):
        resp = api.get("/api/v1/publishers/10")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["id"] == 10, f"Expected id=10, got {data['id']}"
        assert data["name"] == "DGC Records", (
            f"Expected name='DGC Records', got {data['name']}"
        )
        assert data["parent_name"] == "Universal Music Group", (
            f"Expected parent_name='Universal Music Group', got {data['parent_name']}"
        )
        assert isinstance(data["sub_publishers"], list), (
            f"Expected sub_publishers list, got {type(data['sub_publishers'])}"
        )

    def test_publisher_with_sub_publishers_includes_them(self, api):
        # Universal Music Group (id=1) has children: Island Records(2), DGC Records(10)
        resp = api.get("/api/v1/publishers/1")
        data = resp.json()
        assert data["id"] == 1, f"Expected id=1, got {data['id']}"
        assert data["name"] == "Universal Music Group", (
            f"Expected 'Universal Music Group', got {data['name']}"
        )
        assert data["parent_name"] is None, (
            f"Expected parent_name=None, got {data['parent_name']}"
        )
        sub_ids = [s["id"] for s in data["sub_publishers"]]
        assert 2 in sub_ids, (
            f"Expected Island Records (id=2) in sub_publishers, got {sub_ids}"
        )
        assert 10 in sub_ids, (
            f"Expected DGC Records (id=10) in sub_publishers, got {sub_ids}"
        )

    def test_publisher_no_sub_publishers_returns_empty_list(self, api):
        # Sub Pop (id=5) has no children
        resp = api.get("/api/v1/publishers/5")
        data = resp.json()
        assert data["sub_publishers"] == [], (
            f"Expected empty sub_publishers for Sub Pop, got {data['sub_publishers']}"
        )

    def test_domain_fields_not_exposed(self, api):
        resp = api.get("/api/v1/publishers/10")
        data = resp.json()
        assert "parent_id" not in data, "PublisherView must not expose parent_id"

    def test_nonexistent_publisher_returns_404(self, api):
        resp = api.get("/api/v1/publishers/9999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        assert "detail" in resp.json(), "Error response missing 'detail'"

    def test_invalid_id_returns_405(self, api):
        # `:int` path constraint causes FastAPI to return 405 (no matching route) for non-int IDs
        resp = api.get("/api/v1/publishers/not_an_int")
        assert resp.status_code == 405, f"Expected 405, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Songs  GET /api/v1/songs/{id}/web-search
# ---------------------------------------------------------------------------


class TestGetSongWebSearch:
    def test_returns_spotify_url_by_default(self, api):
        # Using a song ID from populated_db (e.g. 1)
        resp = api.get("/api/v1/songs/1/web-search")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "url" in data
        assert "spotify.com/search/" in data["url"]

    def test_returns_google_url_when_requested(self, api):
        resp = api.get("/api/v1/songs/1/web-search?engine=google")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "url" in data
        assert "google.com/search?q=" in data["url"]

    def test_returns_youtube_url_when_requested(self, api):
        resp = api.get("/api/v1/songs/1/web-search?engine=youtube")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "url" in data
        assert "youtube.com/results?search_query=" in data["url"]

    def test_nonexistent_song_returns_404(self, api):
        resp = api.get("/api/v1/songs/9999/web-search")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
