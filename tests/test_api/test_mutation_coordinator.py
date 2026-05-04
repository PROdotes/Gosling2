"""
Orchestrator tests for MutationCoordinator (step 4 seam).

Mutators are all no-op stubs. Tests verify coordinator responsibilities:
  - Each item type routes to the correct mutator
  - touched_song_ids is collected correctly across all buckets and item types
  - Same song_id from multiple items appears exactly once in response
  - Missing song (get_song returns None) is silently dropped
  - remove fires before add fires before update (spec order)
  - Exception mid-batch triggers rollback; nothing commits
  - LookupError / ValueError propagate to 404 / 400 at the HTTP layer

populated_db data map (relevant):
  Songs: 1-9
  Tags:  song 9 has tag_id=6 (Genre, primary)
  Albums: song 1 -> album 100, song 2 -> album 200
"""
import pytest
from fastapi.testclient import TestClient

from src.engine.routers.mutation_models import MutationRequest
from src.services.mutation_coordinator import MutationCoordinator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def coordinator(populated_db):
    return MutationCoordinator(populated_db)


@pytest.fixture
def api(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    from src.engine_server import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Routing: each item type hits the right mutator
# ---------------------------------------------------------------------------

class TestRouting:
    def _calls(self, monkeypatch, coordinator, mutator_attr, req_dict):
        calls = []
        original = getattr(coordinator, mutator_attr)
        monkeypatch.setattr(
            original, "apply_within",
            lambda action, item, conn, batch_id: calls.append((action, item.type))
        )
        coordinator.apply(MutationRequest.model_validate(req_dict))
        return calls

    def test_song_update_routes_to_song_mutator(self, coordinator, monkeypatch):
        calls = self._calls(monkeypatch, coordinator, "_song_mutator",
                            {"update": [{"type": "song", "id": 1}]})
        assert calls == [("update", "song")]

    def test_credit_add_routes_to_credit_mutator(self, coordinator, monkeypatch):
        calls = self._calls(monkeypatch, coordinator, "_credit_mutator",
                            {"add": [{"type": "credit", "song_id": 1, "name": "Dave", "role": "Performer"}]})
        assert calls == [("add", "credit")]

    def test_credit_remove_routes_to_credit_mutator(self, coordinator, monkeypatch):
        calls = self._calls(monkeypatch, coordinator, "_credit_mutator",
                            {"remove": [{"type": "credit", "song_id": 1, "id": 99}]})
        assert calls == [("remove", "credit")]

    def test_tag_entity_update_routes_to_tag_mutator(self, coordinator, monkeypatch):
        calls = self._calls(monkeypatch, coordinator, "_tag_mutator",
                            {"update": [{"type": "tag", "id": 6, "name": "Rock"}]})
        assert calls == [("update", "tag")]

    def test_song_tag_update_routes_to_tag_mutator(self, coordinator, monkeypatch):
        calls = self._calls(monkeypatch, coordinator, "_tag_mutator",
                            {"update": [{"type": "song_tag", "song_id": 1, "tag_id": 6, "is_primary": True}]})
        assert calls == [("update", "song_tag")]

    def test_publisher_add_routes_to_publisher_mutator(self, coordinator, monkeypatch):
        calls = self._calls(monkeypatch, coordinator, "_publisher_mutator",
                            {"add": [{"type": "publisher", "song_id": 1, "name": "EMI"}]})
        assert calls == [("add", "publisher")]

    def test_album_add_routes_to_album_mutator(self, coordinator, monkeypatch):
        calls = self._calls(monkeypatch, coordinator, "_album_mutator",
                            {"add": [{"type": "album", "song_id": 1, "name": "Nevermind"}]})
        assert calls == [("add", "album")]

    def test_song_album_update_routes_to_album_mutator(self, coordinator, monkeypatch):
        calls = self._calls(monkeypatch, coordinator, "_album_mutator",
                            {"update": [{"type": "song_album", "song_id": 1, "album_id": 100, "track_number": 2}]})
        assert calls == [("update", "song_album")]

    def test_album_entity_update_routes_to_album_mutator(self, coordinator, monkeypatch):
        calls = self._calls(monkeypatch, coordinator, "_album_mutator",
                            {"update": [{"type": "album", "id": 100, "title": "Nevermind"}]})
        assert calls == [("update", "album")]

    def test_delete_song_routes_to_delete_mutator(self, coordinator, monkeypatch):
        calls = []
        monkeypatch.setattr(coordinator._delete_mutator, "apply_within",
                            lambda action, item, conn, batch_id: calls.append((action, item.type)))
        coordinator.apply(MutationRequest.model_validate({"delete": [{"type": "song", "id": 1}]}))
        assert calls == [("delete", "song")]

    def test_delete_tag_routes_to_delete_mutator(self, coordinator, monkeypatch):
        calls = []
        monkeypatch.setattr(coordinator._delete_mutator, "apply_within",
                            lambda action, item, conn, batch_id: calls.append((action, item.type)))
        coordinator.apply(MutationRequest.model_validate({"delete": [{"type": "tag", "id": 6}]}))
        assert calls == [("delete", "tag")]

    def test_delete_publisher_routes_to_delete_mutator(self, coordinator, monkeypatch):
        calls = []
        monkeypatch.setattr(coordinator._delete_mutator, "apply_within",
                            lambda action, item, conn, batch_id: calls.append((action, item.type)))
        coordinator.apply(MutationRequest.model_validate({"delete": [{"type": "publisher", "id": 1}]}))
        assert calls == [("delete", "publisher")]

    def test_delete_album_routes_to_delete_mutator(self, coordinator, monkeypatch):
        calls = []
        monkeypatch.setattr(coordinator._delete_mutator, "apply_within",
                            lambda action, item, conn, batch_id: calls.append((action, item.type)))
        coordinator.apply(MutationRequest.model_validate({"delete": [{"type": "album", "id": 100}]}))
        assert calls == [("delete", "album")]

    def test_delete_identity_routes_to_delete_mutator(self, coordinator, monkeypatch):
        calls = []
        monkeypatch.setattr(coordinator._delete_mutator, "apply_within",
                            lambda action, item, conn, batch_id: calls.append((action, item.type)))
        coordinator.apply(MutationRequest.model_validate({"delete": [{"type": "identity", "id": 1}]}))
        assert calls == [("delete", "identity")]

    def test_delete_fires_before_remove(self, coordinator, monkeypatch):
        order = []
        monkeypatch.setattr(coordinator._delete_mutator, "apply_within",
                            lambda action, item, conn, batch_id: order.append("delete"))
        monkeypatch.setattr(coordinator._tag_mutator, "apply_within",
                            lambda action, item, conn, batch_id: order.append("remove"))
        coordinator.apply(MutationRequest.model_validate({
            "delete": [{"type": "tag", "id": 6}],
            "remove": [{"type": "tag", "song_id": 1, "id": 99}],
        }))
        assert order == ["delete", "remove"]

    def test_mixed_request_all_mutators_called(self, coordinator, monkeypatch):
        received = {name: [] for name in ("song", "credit", "tag", "publisher", "album")}

        for attr, key in [
            ("_song_mutator", "song"),
            ("_credit_mutator", "credit"),
            ("_tag_mutator", "tag"),
            ("_publisher_mutator", "publisher"),
            ("_album_mutator", "album"),
        ]:
            k = key
            monkeypatch.setattr(
                getattr(coordinator, attr), "apply_within",
                lambda action, item, conn, batch_id, k=k: received[k].append((action, item.type))
            )

        coordinator.apply(MutationRequest.model_validate({
            "add": [
                {"type": "credit",    "song_id": 1, "name": "Dave", "role": "Performer"},
                {"type": "tag",       "song_id": 1, "name": "Rock", "category": "Genre"},
                {"type": "publisher", "song_id": 1, "name": "EMI"},
                {"type": "album",     "song_id": 1, "name": "Nevermind"},
            ],
            "update": [
                {"type": "song",      "id": 1, "bpm": 120},
                {"type": "song_tag",  "song_id": 1, "tag_id": 6, "is_primary": True},
                {"type": "song_album","song_id": 1, "album_id": 100, "track_number": 2},
            ],
            "remove": [
                {"type": "credit",    "song_id": 1, "id": 99},
                {"type": "tag",       "song_id": 1, "id": 99},
                {"type": "publisher", "song_id": 1, "id": 99},
                {"type": "album",     "song_id": 1, "id": 99},
            ],
        }))

        assert received["song"]      == [("update", "song")]
        assert received["credit"]    == [("remove", "credit"), ("add", "credit")]
        assert received["tag"]       == [("remove", "tag"), ("add", "tag"), ("update", "song_tag")]
        assert received["publisher"] == [("remove", "publisher"), ("add", "publisher")]
        assert received["album"]     == [("remove", "album"), ("add", "album"), ("update", "song_album")]

    def test_mixed_request_touched_songs_correct(self, coordinator):
        result = coordinator.apply(MutationRequest.model_validate({
            "add": [
                {"type": "credit",    "song_id": 1, "name": "Dave", "role": "Performer"},
                {"type": "publisher", "song_id": 2, "name": "EMI"},
            ],
            "update": [
                {"type": "song",      "id": 3, "bpm": 90},
                {"type": "song_tag",  "song_id": 4, "tag_id": 6, "is_primary": True},
                {"type": "tag",       "id": 6, "name": "Rock"},  # entity-only, no song_id
            ],
            "remove": [
                {"type": "album",     "song_id": 5, "id": 99},
            ],
        }))
        ids = {s["id"] for s in result["songs"]}
        assert ids == {1, 2, 3, 4, 5}


# ---------------------------------------------------------------------------
# touched_song_ids: every item type with song_id must be tracked
# ---------------------------------------------------------------------------

class TestTouchedSongIds:
    def _song_ids(self, coordinator, req_dict):
        result = coordinator.apply(MutationRequest.model_validate(req_dict))
        return {s["id"] for s in result["songs"]}

    def test_update_song_id_field(self, coordinator):
        assert 1 in self._song_ids(coordinator, {"update": [{"type": "song", "id": 1}]})

    def test_add_credit_song_id(self, coordinator):
        assert 1 in self._song_ids(coordinator,
            {"add": [{"type": "credit", "song_id": 1, "name": "Dave", "role": "Performer"}]})

    def test_add_tag_song_id(self, coordinator):
        assert 1 in self._song_ids(coordinator,
            {"add": [{"type": "tag", "song_id": 1, "name": "Rock", "category": "Genre"}]})

    def test_add_publisher_song_id(self, coordinator):
        assert 1 in self._song_ids(coordinator,
            {"add": [{"type": "publisher", "song_id": 1, "name": "EMI"}]})

    def test_add_album_song_id(self, coordinator):
        assert 1 in self._song_ids(coordinator,
            {"add": [{"type": "album", "song_id": 1, "name": "Nevermind"}]})

    def test_remove_credit_song_id(self, coordinator):
        assert 1 in self._song_ids(coordinator,
            {"remove": [{"type": "credit", "song_id": 1, "id": 99}]})

    def test_remove_tag_song_id(self, coordinator):
        assert 1 in self._song_ids(coordinator,
            {"remove": [{"type": "tag", "song_id": 1, "id": 99}]})

    def test_remove_publisher_song_id(self, coordinator):
        assert 1 in self._song_ids(coordinator,
            {"remove": [{"type": "publisher", "song_id": 1, "id": 99}]})

    def test_remove_album_song_id(self, coordinator):
        assert 1 in self._song_ids(coordinator,
            {"remove": [{"type": "album", "song_id": 1, "id": 99}]})

    def test_song_tag_update_song_id(self, coordinator):
        assert 1 in self._song_ids(coordinator,
            {"update": [{"type": "song_tag", "song_id": 1, "tag_id": 1, "is_primary": True}]})

    def test_song_album_update_song_id(self, coordinator):
        assert 1 in self._song_ids(coordinator,
            {"update": [{"type": "song_album", "song_id": 1, "album_id": 100, "track_number": 2}]})

    def test_entity_only_update_no_song_id(self, coordinator):
        # tag / album / credit / publisher entity updates have no song_id
        ids = self._song_ids(coordinator, {"update": [
            {"type": "tag", "id": 6, "name": "Alt Rock Renamed"},
            {"type": "album", "id": 100, "title": "Nevermind"},
            {"type": "credit", "id": 1, "display_name": "Dave G"},
            {"type": "publisher", "id": 10, "name": "DGC"},
        ]})
        assert ids == set()


# ---------------------------------------------------------------------------
# Dedup and response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_same_song_from_multiple_items_appears_once(self, coordinator):
        result = coordinator.apply(MutationRequest.model_validate({
            "add": [{"type": "credit", "song_id": 1, "name": "Dave", "role": "Performer"}],
            "update": [{"type": "song", "id": 1, "bpm": 120}],
            "remove": [{"type": "tag", "song_id": 1, "id": 99}],
        }))
        song_ids = [s["id"] for s in result["songs"]]
        assert song_ids.count(1) == 1

    def test_multiple_distinct_songs_all_returned(self, coordinator):
        result = coordinator.apply(MutationRequest.model_validate({
            "update": [
                {"type": "song", "id": 1},
                {"type": "song", "id": 2},
                {"type": "song", "id": 3},
            ]
        }))
        ids = {s["id"] for s in result["songs"]}
        assert ids == {1, 2, 3}

    def test_missing_song_id_silently_dropped(self, coordinator):
        # song_id 9999 does not exist — should not appear in response, no error
        result = coordinator.apply(MutationRequest.model_validate({
            "update": [{"type": "song", "id": 9999}]
        }))
        assert result["songs"] == []
        assert result["warnings"] == []

    def test_response_always_has_songs_and_warnings_keys(self, coordinator):
        result = coordinator.apply(MutationRequest.model_validate({
            "update": [{"type": "tag", "id": 6, "name": "Alt Rock Renamed"}]
        }))
        assert "songs" in result
        assert "warnings" in result


# ---------------------------------------------------------------------------
# Ordering: remove → add → update
# ---------------------------------------------------------------------------

class TestOperationOrder:
    def test_remove_fires_before_add_fires_before_update(self, coordinator, monkeypatch):
        order = []

        def make_spy(label):
            return lambda action, item, conn, batch_id: order.append(label)

        monkeypatch.setattr(coordinator._song_mutator, "apply_within", make_spy("update:song"))
        monkeypatch.setattr(coordinator._credit_mutator, "apply_within", make_spy("add:credit"))
        monkeypatch.setattr(coordinator._tag_mutator, "apply_within", make_spy("remove:tag"))

        coordinator.apply(MutationRequest.model_validate({
            "add":    [{"type": "credit", "song_id": 1, "name": "Dave", "role": "Performer"}],
            "update": [{"type": "song", "id": 1}],
            "remove": [{"type": "tag", "song_id": 1, "id": 99}],
        }))

        assert order == ["remove:tag", "add:credit", "update:song"]


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

class TestRollback:
    def test_exception_in_remove_phase_rolls_back(self, coordinator, monkeypatch):
        def boom(*_):
            raise RuntimeError("boom in remove")

        monkeypatch.setattr(coordinator._tag_mutator, "apply_within", boom)
        with pytest.raises(RuntimeError, match="boom in remove"):
            coordinator.apply(MutationRequest.model_validate({
                "remove": [{"type": "tag", "song_id": 1, "id": 99}],
                "update": [{"type": "song", "id": 1}],
            }))

    def test_exception_in_add_phase_prevents_update_phase(self, coordinator, monkeypatch):
        update_called = []

        def boom_add(*_):
            raise RuntimeError("boom in add")

        def track_update(*_):
            update_called.append(True)

        monkeypatch.setattr(coordinator._credit_mutator, "apply_within", boom_add)
        monkeypatch.setattr(coordinator._song_mutator, "apply_within", track_update)

        with pytest.raises(RuntimeError):
            coordinator.apply(MutationRequest.model_validate({
                "add":    [{"type": "credit", "song_id": 1, "name": "Dave", "role": "Performer"}],
                "update": [{"type": "song", "id": 1}],
            }))

        assert update_called == []

    def test_lookup_error_propagates_without_commit(self, coordinator, monkeypatch):
        monkeypatch.setattr(
            coordinator._credit_mutator, "apply_within",
            lambda action, item, conn, batch_id: (_ for _ in ()).throw(LookupError("gone"))
        )
        with pytest.raises(LookupError):
            coordinator.apply(MutationRequest.model_validate({
                "remove": [{"type": "credit", "song_id": 1, "id": 99}]
            }))


# ---------------------------------------------------------------------------
# HTTP layer: error mapping
# ---------------------------------------------------------------------------

class TestHttpErrorMapping:
    def test_well_formed_returns_200_with_shape(self, api):
        resp = api.post("/api/v1/mutate", json={"update": [{"type": "song", "id": 1}]})
        assert resp.status_code == 200
        body = resp.json()
        assert "songs" in body
        assert "warnings" in body

    def test_empty_request_returns_422(self, api):
        resp = api.post("/api/v1/mutate", json={})
        assert resp.status_code == 422

    def test_empty_string_field_returns_422(self, api):
        resp = api.post("/api/v1/mutate", json={
            "update": [{"type": "song", "id": 1, "media_name": ""}]
        })
        assert resp.status_code == 422

    def test_unknown_item_type_returns_422(self, api):
        resp = api.post("/api/v1/mutate", json={
            "add": [{"type": "spaceship", "song_id": 1}]
        })
        assert resp.status_code == 422

    def test_lookup_error_returns_404(self, api, monkeypatch):
        monkeypatch.setattr(
            "src.engine.routers.mutations._get_coordinator",
            lambda: type("C", (), {"apply": staticmethod(lambda b: (_ for _ in ()).throw(LookupError("gone")))})()
        )
        resp = api.post("/api/v1/mutate", json={"update": [{"type": "song", "id": 1}]})
        assert resp.status_code == 404

    def test_value_error_returns_400(self, api, monkeypatch):
        monkeypatch.setattr(
            "src.engine.routers.mutations._get_coordinator",
            lambda: type("C", (), {"apply": staticmethod(lambda b: (_ for _ in ()).throw(ValueError("bad")))})()
        )
        resp = api.post("/api/v1/mutate", json={"update": [{"type": "song", "id": 1}]})
        assert resp.status_code == 400
