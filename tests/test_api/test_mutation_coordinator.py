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
from pathlib import Path

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
            original,
            "apply_within",
            lambda action, item, conn, *args: (calls.append((action, item.type)), [])[
                1
            ],
        )
        coordinator.apply(MutationRequest.model_validate(req_dict))
        return calls

    def test_song_update_routes_to_song_mutator(self, coordinator, monkeypatch):
        calls = self._calls(
            monkeypatch,
            coordinator,
            "_song_mutator",
            {"update": [{"type": "song", "id": 1}]},
        )
        assert calls == [("update", "song")]

    def test_credit_add_routes_to_credit_mutator(self, coordinator, monkeypatch):
        calls = self._calls(
            monkeypatch,
            coordinator,
            "_credit_mutator",
            {
                "add": [
                    {
                        "type": "credit",
                        "song_id": 1,
                        "name": "Dave",
                        "role": "Performer",
                    }
                ]
            },
        )
        assert calls == [("add", "credit")]

    def test_credit_remove_routes_to_credit_mutator(self, coordinator, monkeypatch):
        calls = self._calls(
            monkeypatch,
            coordinator,
            "_credit_mutator",
            {"remove": [{"type": "credit", "song_id": 1, "id": 99}]},
        )
        assert calls == [("remove", "credit")]

    def test_tag_entity_update_routes_to_tag_mutator(self, coordinator, monkeypatch):
        calls = self._calls(
            monkeypatch,
            coordinator,
            "_tag_mutator",
            {"update": [{"type": "tag", "id": 6, "name": "Rock"}]},
        )
        assert calls == [("update", "tag")]

    def test_song_tag_update_routes_to_tag_mutator(self, coordinator, monkeypatch):
        calls = self._calls(
            monkeypatch,
            coordinator,
            "_tag_mutator",
            {
                "update": [
                    {"type": "song_tag", "song_id": 1, "tag_id": 6, "is_primary": True}
                ]
            },
        )
        assert calls == [("update", "song_tag")]

    def test_publisher_add_routes_to_publisher_mutator(self, coordinator, monkeypatch):
        calls = self._calls(
            monkeypatch,
            coordinator,
            "_publisher_mutator",
            {"add": [{"type": "publisher", "song_id": 1, "name": "EMI"}]},
        )
        assert calls == [("add", "publisher")]

    def test_album_add_routes_to_album_mutator(self, coordinator, monkeypatch):
        calls = self._calls(
            monkeypatch,
            coordinator,
            "_album_mutator",
            {"add": [{"type": "album", "song_id": 1, "name": "Nevermind"}]},
        )
        assert calls == [("add", "album")]

    def test_song_album_update_routes_to_album_mutator(self, coordinator, monkeypatch):
        calls = self._calls(
            monkeypatch,
            coordinator,
            "_album_mutator",
            {
                "update": [
                    {
                        "type": "song_album",
                        "song_id": 1,
                        "album_id": 100,
                        "track_number": 2,
                    }
                ]
            },
        )
        assert calls == [("update", "song_album")]

    def test_album_entity_update_routes_to_album_mutator(
        self, coordinator, monkeypatch
    ):
        calls = self._calls(
            monkeypatch,
            coordinator,
            "_album_mutator",
            {"update": [{"type": "album", "id": 100, "title": "Nevermind"}]},
        )
        assert calls == [("update", "album")]

    def test_delete_song_routes_to_delete_mutator(self, coordinator, monkeypatch):
        calls = []
        monkeypatch.setattr(
            coordinator._delete_mutator,
            "apply_within",
            lambda action, item, conn, *args: (calls.append((action, item.type)), [])[
                1
            ],
        )
        coordinator.apply(
            MutationRequest.model_validate({"delete": [{"type": "song", "id": 1}]})
        )
        assert calls == [("delete", "song")]

    def test_delete_tag_routes_to_delete_mutator(self, coordinator, monkeypatch):
        calls = []
        monkeypatch.setattr(
            coordinator._delete_mutator,
            "apply_within",
            lambda action, item, conn, *args: (calls.append((action, item.type)), [])[
                1
            ],
        )
        coordinator.apply(
            MutationRequest.model_validate({"delete": [{"type": "tag", "id": 6}]})
        )
        assert calls == [("delete", "tag")]

    def test_delete_publisher_routes_to_delete_mutator(self, coordinator, monkeypatch):
        calls = []
        monkeypatch.setattr(
            coordinator._delete_mutator,
            "apply_within",
            lambda action, item, conn, *args: (calls.append((action, item.type)), [])[
                1
            ],
        )
        coordinator.apply(
            MutationRequest.model_validate({"delete": [{"type": "publisher", "id": 1}]})
        )
        assert calls == [("delete", "publisher")]

    def test_delete_album_routes_to_delete_mutator(self, coordinator, monkeypatch):
        calls = []
        monkeypatch.setattr(
            coordinator._delete_mutator,
            "apply_within",
            lambda action, item, conn, *args: (calls.append((action, item.type)), [])[
                1
            ],
        )
        coordinator.apply(
            MutationRequest.model_validate({"delete": [{"type": "album", "id": 100}]})
        )
        assert calls == [("delete", "album")]

    def test_delete_identity_routes_to_delete_mutator(self, coordinator, monkeypatch):
        calls = []
        monkeypatch.setattr(
            coordinator._delete_mutator,
            "apply_within",
            lambda action, item, conn, *args: (calls.append((action, item.type)), [])[
                1
            ],
        )
        coordinator.apply(
            MutationRequest.model_validate({"delete": [{"type": "identity", "id": 1}]})
        )
        assert calls == [("delete", "identity")]

    def test_delete_fires_before_remove(self, coordinator, monkeypatch):
        order = []
        monkeypatch.setattr(
            coordinator._delete_mutator,
            "apply_within",
            lambda action, item, conn, *args: (order.append("delete"), [])[1],
        )
        monkeypatch.setattr(
            coordinator._tag_mutator,
            "apply_within",
            lambda action, item, conn, *args: (order.append("remove"), [])[1],
        )
        coordinator.apply(
            MutationRequest.model_validate(
                {
                    "delete": [{"type": "tag", "id": 6}],
                    "remove": [{"type": "tag", "song_id": 1, "id": 99}],
                }
            )
        )
        assert order == ["delete", "remove"]

    def test_mixed_request_all_mutators_called(self, coordinator, monkeypatch):
        received = {
            name: [] for name in ("song", "credit", "tag", "publisher", "album")
        }

        for attr, key in [
            ("_song_mutator", "song"),
            ("_credit_mutator", "credit"),
            ("_tag_mutator", "tag"),
            ("_publisher_mutator", "publisher"),
            ("_album_mutator", "album"),
        ]:
            k = key
            monkeypatch.setattr(
                getattr(coordinator, attr),
                "apply_within",
                lambda action, item, conn, *args, k=k: (
                    received[k].append((action, item.type)),
                    [],
                )[1],
            )

        coordinator.apply(
            MutationRequest.model_validate(
                {
                    "add": [
                        {
                            "type": "credit",
                            "song_id": 1,
                            "name": "Dave",
                            "role": "Performer",
                        },
                        {
                            "type": "tag",
                            "song_id": 1,
                            "name": "Rock",
                            "category": "Genre",
                        },
                        {"type": "publisher", "song_id": 1, "name": "EMI"},
                        {"type": "album", "song_id": 1, "name": "Nevermind"},
                    ],
                    "update": [
                        {"type": "song", "id": 1, "bpm": 120},
                        {
                            "type": "song_tag",
                            "song_id": 1,
                            "tag_id": 6,
                            "is_primary": True,
                        },
                        {
                            "type": "song_album",
                            "song_id": 1,
                            "album_id": 100,
                            "track_number": 2,
                        },
                    ],
                    "remove": [
                        {"type": "credit", "song_id": 1, "id": 99},
                        {"type": "tag", "song_id": 1, "id": 99},
                        {"type": "publisher", "song_id": 1, "id": 99},
                        {"type": "album", "song_id": 1, "id": 99},
                    ],
                }
            )
        )

        assert received["song"] == [("update", "song")]
        assert received["credit"] == [("remove", "credit"), ("add", "credit")]
        assert received["tag"] == [
            ("remove", "tag"),
            ("add", "tag"),
            ("update", "song_tag"),
        ]
        assert received["publisher"] == [("remove", "publisher"), ("add", "publisher")]
        assert received["album"] == [
            ("remove", "album"),
            ("add", "album"),
            ("update", "song_album"),
        ]

    def test_mixed_request_touched_songs_correct(self, coordinator, monkeypatch):
        for attr in (
            "_credit_mutator",
            "_tag_mutator",
            "_publisher_mutator",
            "_album_mutator",
            "_song_mutator",
        ):
            monkeypatch.setattr(
                getattr(coordinator, attr),
                "apply_within",
                lambda action, item, conn, *args: [],
            )
        monkeypatch.setattr(
            coordinator._delete_mutator,
            "apply_within",
            lambda action, item, conn, *args: [],
        )
        result = coordinator.apply(
            MutationRequest.model_validate(
                {
                    "add": [
                        {
                            "type": "credit",
                            "song_id": 1,
                            "name": "Dave",
                            "role": "Performer",
                        },
                        {"type": "publisher", "song_id": 2, "name": "EMI"},
                    ],
                    "update": [
                        {"type": "song", "id": 3, "bpm": 90},
                        {
                            "type": "song_tag",
                            "song_id": 4,
                            "tag_id": 6,
                            "is_primary": True,
                        },
                        {"type": "tag", "id": 6, "name": "Rock"},
                    ],
                    "remove": [
                        {"type": "album", "song_id": 5, "id": 99},
                    ],
                }
            )
        )
        ids = {s["id"] for s in result["songs"]}
        assert ids == {1, 2, 3, 4, 5}


# ---------------------------------------------------------------------------
# touched_song_ids: every item type with song_id must be tracked
# ---------------------------------------------------------------------------


class TestTouchedSongIds:
    def _song_ids(self, coordinator, req_dict):
        result = coordinator.apply(MutationRequest.model_validate(req_dict))
        return {s["id"] for s in result["songs"]}

    def _song_ids_with_spies(self, coordinator, monkeypatch, req_dict):
        for attr in (
            "_credit_mutator",
            "_tag_mutator",
            "_publisher_mutator",
            "_album_mutator",
            "_song_mutator",
            "_delete_mutator",
        ):
            monkeypatch.setattr(
                getattr(coordinator, attr),
                "apply_within",
                lambda action, item, conn, *args: [],
            )
        result = coordinator.apply(MutationRequest.model_validate(req_dict))
        return {s["id"] for s in result["songs"]}

    def test_update_song_id_field(self, coordinator):
        assert 1 in self._song_ids(coordinator, {"update": [{"type": "song", "id": 1}]})

    def test_add_credit_song_id(self, coordinator):
        assert 1 in self._song_ids(
            coordinator,
            {
                "add": [
                    {
                        "type": "credit",
                        "song_id": 1,
                        "name": "Dave",
                        "role": "Performer",
                    }
                ]
            },
        )

    def test_add_tag_song_id(self, coordinator):
        assert 1 in self._song_ids(
            coordinator,
            {
                "add": [
                    {"type": "tag", "song_id": 1, "name": "Rock", "category": "Genre"}
                ]
            },
        )

    def test_add_publisher_song_id(self, coordinator):
        assert 1 in self._song_ids(
            coordinator, {"add": [{"type": "publisher", "song_id": 1, "name": "EMI"}]}
        )

    def test_add_album_song_id(self, coordinator):
        assert 1 in self._song_ids(
            coordinator, {"add": [{"type": "album", "song_id": 1, "name": "Nevermind"}]}
        )

    def test_remove_credit_song_id(self, coordinator, monkeypatch):
        assert 1 in self._song_ids_with_spies(
            coordinator,
            monkeypatch,
            {"remove": [{"type": "credit", "song_id": 1, "id": 99}]},
        )

    def test_remove_tag_song_id(self, coordinator, monkeypatch):
        assert 1 in self._song_ids_with_spies(
            coordinator,
            monkeypatch,
            {"remove": [{"type": "tag", "song_id": 1, "id": 99}]},
        )

    def test_remove_publisher_song_id(self, coordinator, monkeypatch):
        assert 1 in self._song_ids_with_spies(
            coordinator,
            monkeypatch,
            {"remove": [{"type": "publisher", "song_id": 1, "id": 99}]},
        )

    def test_remove_album_song_id(self, coordinator, monkeypatch):
        assert 1 in self._song_ids_with_spies(
            coordinator,
            monkeypatch,
            {"remove": [{"type": "album", "song_id": 1, "id": 99}]},
        )

    def test_song_tag_update_song_id(self, coordinator, monkeypatch):
        assert 1 in self._song_ids_with_spies(
            coordinator,
            monkeypatch,
            {
                "update": [
                    {"type": "song_tag", "song_id": 1, "tag_id": 1, "is_primary": True}
                ]
            },
        )

    def test_song_album_update_song_id(self, coordinator):
        assert 1 in self._song_ids(
            coordinator,
            {
                "update": [
                    {
                        "type": "song_album",
                        "song_id": 1,
                        "album_id": 100,
                        "track_number": 2,
                    }
                ]
            },
        )

    def test_entity_only_update_no_song_id(self, coordinator, monkeypatch):
        ids = self._song_ids_with_spies(
            coordinator,
            monkeypatch,
            {
                "update": [
                    {"type": "tag", "id": 6, "name": "Alt Rock Renamed"},
                    {"type": "album", "id": 100, "title": "Nevermind"},
                    {"type": "credit", "id": 1, "display_name": "Dave G"},
                    {"type": "publisher", "id": 10, "name": "DGC"},
                ]
            },
        )
        assert ids == set()


# ---------------------------------------------------------------------------
# Dedup and response shape
# ---------------------------------------------------------------------------


class TestResponseShape:
    def test_same_song_from_multiple_items_appears_once(self, coordinator, monkeypatch):
        for attr in ("_tag_mutator", "_credit_mutator"):
            monkeypatch.setattr(
                getattr(coordinator, attr),
                "apply_within",
                lambda action, item, conn, *args: [],
            )
        result = coordinator.apply(
            MutationRequest.model_validate(
                {
                    "add": [
                        {
                            "type": "credit",
                            "song_id": 1,
                            "name": "Dave",
                            "role": "Performer",
                        }
                    ],
                    "update": [{"type": "song", "id": 1, "bpm": 120}],
                    "remove": [{"type": "tag", "song_id": 1, "id": 99}],
                }
            )
        )
        song_ids = [s["id"] for s in result["songs"]]
        assert song_ids.count(1) == 1

    def test_multiple_distinct_songs_all_returned(self, coordinator):
        result = coordinator.apply(
            MutationRequest.model_validate(
                {
                    "update": [
                        {"type": "song", "id": 1},
                        {"type": "song", "id": 2},
                        {"type": "song", "id": 3},
                    ]
                }
            )
        )
        ids = {s["id"] for s in result["songs"]}
        assert ids == {1, 2, 3}

    def test_missing_song_id_silently_dropped(self, coordinator):
        result = coordinator.apply(
            MutationRequest.model_validate({"update": [{"type": "song", "id": 9999}]})
        )
        assert result["songs"] == []

    def test_response_always_has_songs_key(self, coordinator, monkeypatch):
        for attr in ("_tag_mutator",):
            monkeypatch.setattr(
                getattr(coordinator, attr),
                "apply_within",
                lambda action, item, conn, *args: [],
            )
        result = coordinator.apply(
            MutationRequest.model_validate(
                {"update": [{"type": "tag", "id": 6, "name": "Alt Rock Renamed"}]}
            )
        )
        assert "songs" in result


# ---------------------------------------------------------------------------
# Ordering: remove -> add -> update
# ---------------------------------------------------------------------------


class TestOperationOrder:
    def test_remove_fires_before_add_fires_before_update(
        self, coordinator, monkeypatch
    ):
        order = []

        def make_spy(label):
            return lambda action, item, conn, *args: (order.append(label), [])[1]

        monkeypatch.setattr(
            coordinator._song_mutator, "apply_within", make_spy("update:song")
        )
        monkeypatch.setattr(
            coordinator._credit_mutator, "apply_within", make_spy("add:credit")
        )
        monkeypatch.setattr(
            coordinator._tag_mutator, "apply_within", make_spy("remove:tag")
        )

        coordinator.apply(
            MutationRequest.model_validate(
                {
                    "add": [
                        {
                            "type": "credit",
                            "song_id": 1,
                            "name": "Dave",
                            "role": "Performer",
                        }
                    ],
                    "update": [{"type": "song", "id": 1}],
                    "remove": [{"type": "tag", "song_id": 1, "id": 99}],
                }
            )
        )

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
            coordinator.apply(
                MutationRequest.model_validate(
                    {
                        "remove": [{"type": "tag", "song_id": 1, "id": 99}],
                        "update": [{"type": "song", "id": 1}],
                    }
                )
            )

    def test_exception_in_add_phase_prevents_update_phase(
        self, coordinator, monkeypatch
    ):
        update_called = []

        def boom_add(*_):
            raise RuntimeError("boom in add")

        def track_update(*_):
            update_called.append(True)

        monkeypatch.setattr(coordinator._credit_mutator, "apply_within", boom_add)
        monkeypatch.setattr(coordinator._song_mutator, "apply_within", track_update)

        with pytest.raises(RuntimeError):
            coordinator.apply(
                MutationRequest.model_validate(
                    {
                        "add": [
                            {
                                "type": "credit",
                                "song_id": 1,
                                "name": "Dave",
                                "role": "Performer",
                            }
                        ],
                        "update": [{"type": "song", "id": 1}],
                    }
                )
            )

        assert update_called == []

    def test_lookup_error_propagates_without_commit(self, coordinator, monkeypatch):
        monkeypatch.setattr(
            coordinator._credit_mutator,
            "apply_within",
            lambda action, item, conn, *args: (_ for _ in ()).throw(
                LookupError("gone")
            ),
        )
        with pytest.raises(LookupError):
            coordinator.apply(
                MutationRequest.model_validate(
                    {"remove": [{"type": "credit", "song_id": 1, "id": 99}]}
                )
            )


# ---------------------------------------------------------------------------
# HTTP layer: error mapping
# ---------------------------------------------------------------------------


class TestHttpErrorMapping:
    def test_well_formed_returns_200_with_shape(self, api):
        resp = api.post("/api/v1/mutate", json={"update": [{"type": "song", "id": 1}]})
        assert resp.status_code == 200
        body = resp.json()
        assert "songs" in body

    def test_empty_request_returns_422(self, api):
        resp = api.post("/api/v1/mutate", json={})
        assert resp.status_code == 422

    def test_empty_string_field_returns_422(self, api):
        resp = api.post(
            "/api/v1/mutate",
            json={"update": [{"type": "song", "id": 1, "media_name": ""}]},
        )
        assert resp.status_code == 422

    def test_unknown_item_type_returns_422(self, api):
        resp = api.post(
            "/api/v1/mutate", json={"add": [{"type": "spaceship", "song_id": 1}]}
        )
        assert resp.status_code == 422

    def test_lookup_error_returns_404(self, api, monkeypatch):
        monkeypatch.setattr(
            "src.engine.routers.mutations._get_coordinator",
            lambda: type(
                "C",
                (),
                {
                    "apply": staticmethod(
                        lambda b: (_ for _ in ()).throw(LookupError("gone"))
                    )
                },
            )(),
        )
        resp = api.post("/api/v1/mutate", json={"update": [{"type": "song", "id": 1}]})
        assert resp.status_code == 404

    def test_value_error_returns_400(self, api, monkeypatch):
        monkeypatch.setattr(
            "src.engine.routers.mutations._get_coordinator",
            lambda: type(
                "C",
                (),
                {
                    "apply": staticmethod(
                        lambda b: (_ for _ in ()).throw(ValueError("bad"))
                    )
                },
            )(),
        )
        resp = api.post("/api/v1/mutate", json={"update": [{"type": "song", "id": 1}]})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Staging file cleanup on song delete
# ---------------------------------------------------------------------------


class TestStagingFileCleanup:
    def test_staged_song_delete_removes_file(self, populated_db, monkeypatch, tmp_path):
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod

        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        monkeypatch.setattr(config_mod, "STAGING_DIR", staging)
        monkeypatch.setattr(coord_mod, "STAGING_DIR", staging)

        staged_file = staging / "test_song.mp3"
        staged_file.write_bytes(b"fake audio")

        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (str(staged_file),),
        )
        conn.commit()
        conn.close()

        coordinator = MutationCoordinator(populated_db)
        coordinator.apply(
            MutationRequest.model_validate({"delete": [{"type": "song", "id": 1}]})
        )

        assert not staged_file.exists()

    def test_staged_song_delete_missing_file_does_not_error(
        self, populated_db, monkeypatch, tmp_path
    ):
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod

        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        monkeypatch.setattr(config_mod, "STAGING_DIR", staging)
        monkeypatch.setattr(coord_mod, "STAGING_DIR", staging)

        missing_file = staging / "already_gone.mp3"

        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (str(missing_file),),
        )
        conn.commit()
        conn.close()

        coordinator = MutationCoordinator(populated_db)
        coordinator.apply(
            MutationRequest.model_validate({"delete": [{"type": "song", "id": 1}]})
        )

    def test_library_song_delete_does_not_remove_file(
        self, populated_db, monkeypatch, tmp_path
    ):
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod

        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        monkeypatch.setattr(config_mod, "STAGING_DIR", staging)
        monkeypatch.setattr(coord_mod, "STAGING_DIR", staging)

        library_file = tmp_path / "library" / "song.mp3"
        library_file.parent.mkdir()
        library_file.write_bytes(b"fake audio")

        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (str(library_file),),
        )
        conn.commit()
        conn.close()

        coordinator = MutationCoordinator(populated_db)
        coordinator.apply(
            MutationRequest.model_validate({"delete": [{"type": "song", "id": 1}]})
        )

        assert library_file.exists()

    def test_no_source_path_does_not_error(self, populated_db, monkeypatch, tmp_path):
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod

        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        monkeypatch.setattr(config_mod, "STAGING_DIR", staging)
        monkeypatch.setattr(coord_mod, "STAGING_DIR", staging)

        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute("UPDATE MediaSources SET SourcePath = '' WHERE SourceID = 1")
        conn.commit()
        conn.close()

        coordinator = MutationCoordinator(populated_db)
        coordinator.apply(
            MutationRequest.model_validate({"delete": [{"type": "song", "id": 1}]})
        )

    def test_unrelated_directory_file_not_deleted(
        self, populated_db, monkeypatch, tmp_path
    ):
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod

        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        monkeypatch.setattr(config_mod, "STAGING_DIR", staging)
        monkeypatch.setattr(coord_mod, "STAGING_DIR", staging)

        other_dir = tmp_path / "other"
        other_dir.mkdir()
        other_file = other_dir / "song.mp3"
        other_file.write_bytes(b"fake audio")

        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (str(other_file),),
        )
        conn.commit()
        conn.close()

        coordinator = MutationCoordinator(populated_db)
        coordinator.apply(
            MutationRequest.model_validate({"delete": [{"type": "song", "id": 1}]})
        )

        assert other_file.exists()

    def test_batch_delete_only_removes_staged_files(
        self, populated_db, monkeypatch, tmp_path
    ):
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod

        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        monkeypatch.setattr(config_mod, "STAGING_DIR", staging)
        monkeypatch.setattr(coord_mod, "STAGING_DIR", staging)

        staged_file = staging / "staged.mp3"
        staged_file.write_bytes(b"fake audio")

        library_file = tmp_path / "library" / "library.mp3"
        library_file.parent.mkdir()
        library_file.write_bytes(b"fake audio")

        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (str(staged_file),),
        )
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 2",
            (str(library_file),),
        )
        conn.commit()
        conn.close()

        coordinator = MutationCoordinator(populated_db)
        coordinator.apply(
            MutationRequest.model_validate(
                {"delete": [{"type": "song", "id": 1}, {"type": "song", "id": 2}]}
            )
        )

        assert not staged_file.exists()
        assert library_file.exists()

    def test_multiple_staged_files_all_deleted(
        self, populated_db, monkeypatch, tmp_path
    ):
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod

        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        monkeypatch.setattr(config_mod, "STAGING_DIR", staging)
        monkeypatch.setattr(coord_mod, "STAGING_DIR", staging)

        staged_1 = staging / "staged_1.mp3"
        staged_2 = staging / "staged_2.mp3"
        staged_1.write_bytes(b"fake audio")
        staged_2.write_bytes(b"fake audio")

        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (str(staged_1),),
        )
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 2",
            (str(staged_2),),
        )
        conn.commit()
        conn.close()

        coordinator = MutationCoordinator(populated_db)
        coordinator.apply(
            MutationRequest.model_validate(
                {"delete": [{"type": "song", "id": 1}, {"type": "song", "id": 2}]}
            )
        )

        assert not staged_1.exists()
        assert not staged_2.exists()

    def test_reviewed_song_still_in_staging_delete_file_true_only_removes_staging(
        self, populated_db, monkeypatch, tmp_path
    ):
        """
        Quantum state: song was marked done (status=REVIEWED) but the auto-move
        failed (e.g. target already existed), so source_path still points into
        staging. A pre-existing library file lives at the projected target path
        but is NOT referenced by this song's source_path.

        Delete with delete_file=True must:
          - unlink the staging file (via delete_physical_file on source_path)
          - leave the unrelated pre-existing library file untouched
          - not raise (no double-delete: coordinator uses if/else, so
            delete_staging_file does not also run)
        """
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod

        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        monkeypatch.setattr(config_mod, "STAGING_DIR", staging)
        monkeypatch.setattr(coord_mod, "STAGING_DIR", staging)

        staged_file = staging / "quantum_song.mp3"
        staged_file.write_bytes(b"fake staged audio")

        library_file = tmp_path / "library" / "preexisting.mp3"
        library_file.parent.mkdir()
        library_file.write_bytes(b"fake library audio")
        library_bytes_before = library_file.read_bytes()

        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ?, ProcessingStatus = 0 WHERE SourceID = 1",
            (str(staged_file),),
        )
        conn.commit()
        conn.close()

        coordinator = MutationCoordinator(populated_db)
        coordinator.apply(
            MutationRequest.model_validate(
                {"delete": [{"type": "song", "id": 1, "delete_file": True}]}
            )
        )

        assert not staged_file.exists()
        assert library_file.exists()
        assert library_file.read_bytes() == library_bytes_before


# ---------------------------------------------------------------------------
# File move on approve: copy before commit, source_path updated, original deleted
# ---------------------------------------------------------------------------


class TestFileMoveOnApprove:
    """
    Song 1 (SLTS): status=0 (REVIEWED), performer=Nirvana, year=1991, genre=Grunge.
    These tests monkeypatch AUTO_MOVE_ON_APPROVE=True and LIBRARY_ROOT to a tmp dir.
    """

    def _setup(self, populated_db, monkeypatch, tmp_path):
        import sqlite3
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod
        from src.services.filing_service import FilingService

        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        library = tmp_path / "library"
        library.mkdir(exist_ok=True)

        source_file = staging / "song1.mp3"
        source_file.write_bytes(b"audio data")

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (str(source_file),),
        )
        conn.commit()
        conn.close()

        rules_file = tmp_path / "rules.json"
        rules_file.write_text(
            '{"routing_rules": [], "default_rule": "{year}/{artist} - {title}"}'
        )

        monkeypatch.setattr(config_mod, "AUTO_MOVE_ON_APPROVE", True)
        monkeypatch.setattr(coord_mod, "LIBRARY_ROOT", library)
        monkeypatch.setattr(coord_mod, "STAGING_DIR", str(staging))

        coordinator = MutationCoordinator(populated_db)
        coordinator._filing = FilingService(rules_path=rules_file)
        return coordinator, source_file, library

    def test_reviewed_song_file_is_copied_to_library(
        self, populated_db, monkeypatch, tmp_path
    ):
        coordinator, source_file, library = self._setup(
            populated_db, monkeypatch, tmp_path
        )
        coordinator.apply(
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1}]})
        )
        copied = list(library.rglob("*.mp3"))
        assert len(copied) == 1
        assert copied[0].read_bytes() == b"audio data"

    def test_reviewed_song_original_deleted_after_commit(
        self, populated_db, monkeypatch, tmp_path
    ):
        coordinator, source_file, library = self._setup(
            populated_db, monkeypatch, tmp_path
        )
        coordinator.apply(
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1}]})
        )
        assert not source_file.exists()

    def test_reviewed_song_source_path_updated_in_db(
        self, populated_db, monkeypatch, tmp_path
    ):
        import sqlite3

        coordinator, source_file, library = self._setup(
            populated_db, monkeypatch, tmp_path
        )
        coordinator.apply(
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1}]})
        )
        conn = sqlite3.connect(populated_db)
        row = conn.execute(
            "SELECT SourcePath FROM MediaSources WHERE SourceID = 1"
        ).fetchone()
        conn.close()
        new_path = Path(row[0])
        assert new_path.is_relative_to(library)
        assert new_path.exists()

    def test_copy_failure_does_not_delete_original(
        self, populated_db, monkeypatch, tmp_path
    ):
        coordinator, source_file, library = self._setup(
            populated_db, monkeypatch, tmp_path
        )
        monkeypatch.setattr(
            coordinator._filing,
            "copy_to_library",
            lambda *a, **kw: (_ for _ in ()).throw(OSError("disk full")),
        )
        coordinator.apply(
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1}]})
        )
        assert source_file.exists()

    def test_original_unlink_failure_keeps_destination_and_db_commit(
        self, populated_db, monkeypatch, tmp_path
    ):
        """Regression: if the post-commit unlink of the original (staging) file fails,
        the destination copy and the DB commit must survive. Half-rollback would leave
        the DB pointing at a path with no file (the bug we just fixed).
        """
        import sqlite3

        coordinator, source_file, library = self._setup(
            populated_db, monkeypatch, tmp_path
        )

        original_unlink = Path.unlink

        def selective_unlink(self, *args, **kwargs):
            if self.resolve() == source_file.resolve():
                raise OSError(
                    32,
                    "The process cannot access the file because it is being used by another process",
                )
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", selective_unlink)

        result = coordinator.apply(
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1}]})
        )

        copied = list(library.rglob("*.mp3"))
        assert (
            len(copied) == 1
        ), "Destination copy must survive when original unlink fails"
        assert copied[0].read_bytes() == b"audio data"

        conn = sqlite3.connect(populated_db)
        row = conn.execute(
            "SELECT SourcePath FROM MediaSources WHERE SourceID = 1"
        ).fetchone()
        conn.close()
        assert (
            Path(row[0]).resolve() == copied[0].resolve()
        ), "DB source_path must point at the surviving destination"

        assert "songs" in result, "Mutation must report success, not raise"

    def test_rollback_deletes_copy(self, populated_db, monkeypatch, tmp_path):
        coordinator, source_file, library = self._setup(
            populated_db, monkeypatch, tmp_path
        )

        original_apply_within = coordinator._song_mutator.apply_within
        call_count = [0]

        def fail_on_second(action, item, conn):
            call_count[0] += 1
            if call_count[0] > 1:
                raise RuntimeError("db write failed")
            return original_apply_within(action, item, conn)

        monkeypatch.setattr(coordinator._song_mutator, "apply_within", fail_on_second)

        with pytest.raises(RuntimeError):
            coordinator.apply(
                MutationRequest.model_validate({"update": [{"type": "song", "id": 1}]})
            )

        copied = list(library.rglob("*.mp3"))
        assert copied == [], "Copy should have been cleaned up on rollback"
        assert source_file.exists(), "Original must survive a failed transaction"

    def test_file_exists_at_destination_returns_warning_and_leaves_original(
        self, populated_db, monkeypatch, tmp_path
    ):
        coordinator, source_file, library = self._setup(
            populated_db, monkeypatch, tmp_path
        )

        # Pre-create a different file at the destination path
        dest_dir = library / "1991"
        dest_dir.mkdir(parents=True, exist_ok=True)
        conflict_file = dest_dir / "Nirvana - Smells Like Teen Spirit.mp3"
        conflict_file.write_bytes(b"different content")

        result = coordinator.apply(
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1}]})
        )

        assert (
            source_file.exists()
        ), "Original must not be deleted when destination conflict exists"
        assert (
            conflict_file.read_bytes() == b"different content"
        ), "Existing destination file must not be overwritten"
        assert any(
            w.get("kind") == "file_move" for w in result["warnings"]
        ), "Warning must be returned for file conflict"

    def test_missing_filing_rule_returns_warning_and_commits_db(
        self, populated_db, monkeypatch, tmp_path
    ):
        """A missing filing rule must not abort the mutation: DB commits, warning surfaced, no file copied."""
        import sqlite3
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod
        from src.services.filing_service import FilingService

        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        library = tmp_path / "library"
        library.mkdir(exist_ok=True)

        source_file = staging / "song1.mp3"
        source_file.write_bytes(b"audio data")

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (str(source_file),),
        )
        conn.commit()
        conn.close()

        rules_file = tmp_path / "rules.json"
        rules_file.write_text('{"routing_rules": []}')

        monkeypatch.setattr(config_mod, "AUTO_MOVE_ON_APPROVE", True)
        monkeypatch.setattr(coord_mod, "LIBRARY_ROOT", library)
        monkeypatch.setattr(coord_mod, "STAGING_DIR", str(staging))

        coordinator = MutationCoordinator(populated_db)
        coordinator._filing = FilingService(rules_path=rules_file)

        result = coordinator.apply(
            MutationRequest.model_validate(
                {
                    "update": [
                        {
                            "type": "song",
                            "id": 1,
                            "notes": "approved despite missing rule",
                        }
                    ]
                }
            )
        )

        assert any(
            w.get("kind") == "file_move" for w in result["warnings"]
        ), "Warning must be returned when no filing rule matches"
        assert source_file.exists(), "Original must remain when filing was skipped"
        assert (
            list(library.rglob("*.mp3")) == []
        ), "No file should be copied when routing fails"

        conn = sqlite3.connect(populated_db)
        row = conn.execute(
            "SELECT SourceNotes, SourcePath FROM MediaSources WHERE SourceID = 1"
        ).fetchone()
        conn.close()
        assert (
            row[0] == "approved despite missing rule"
        ), "DB scalar update must persist even when filing fails"
        assert row[1] == str(
            source_file
        ), "source_path must remain pointing at staging when no copy happened"

    def test_source_already_in_library_at_correct_path_not_deleted(
        self, populated_db, monkeypatch, tmp_path
    ):
        """Regression: when source_path is already the correct library target, coordinator must not delete it.
        The FilingService bypasses the physical copy but the coordinator cleanup must not treat it as a move.
        """
        import sqlite3
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod
        from src.services.filing_service import FilingService

        library = tmp_path / "library"
        library.mkdir(exist_ok=True)

        # Place the file at the exact path the routing rule will produce:
        # default_rule = "{year}/{artist} - {title}" -> 1991/Nirvana - Smells Like Teen Spirit.mp3
        dest_dir = library / "1991"
        dest_dir.mkdir(parents=True, exist_ok=True)
        library_file = dest_dir / "Nirvana - Smells Like Teen Spirit.mp3"
        library_file.write_bytes(b"original audio do not delete")

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
            (str(library_file),),
        )
        conn.commit()
        conn.close()

        rules_file = tmp_path / "rules.json"
        rules_file.write_text(
            '{"routing_rules": [], "default_rule": "{year}/{artist} - {title}"}'
        )

        monkeypatch.setattr(config_mod, "AUTO_MOVE_ON_APPROVE", True)
        monkeypatch.setattr(coord_mod, "LIBRARY_ROOT", library)

        coordinator = MutationCoordinator(populated_db)
        coordinator._filing = FilingService(rules_path=rules_file)

        coordinator.apply(
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1}]})
        )

        assert (
            library_file.exists()
        ), "File was deleted by coordinator cleanup — source == target case not handled"
        assert (
            library_file.read_bytes() == b"original audio do not delete"
        ), "File contents were modified"

    def test_non_reviewed_song_not_moved(self, populated_db, monkeypatch, tmp_path):
        import src.engine.config as config_mod
        import src.services.mutation_coordinator as coord_mod

        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        library = tmp_path / "library"
        library.mkdir(exist_ok=True)

        source_file = staging / "song7.mp3"
        source_file.write_bytes(b"audio data")

        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 7",
            (str(source_file),),
        )
        conn.commit()
        conn.close()

        monkeypatch.setattr(config_mod, "AUTO_MOVE_ON_APPROVE", True)
        monkeypatch.setattr(coord_mod, "LIBRARY_ROOT", library)

        coordinator = MutationCoordinator(populated_db)
        coordinator.apply(
            MutationRequest.model_validate({"update": [{"type": "song", "id": 7}]})
        )

        assert source_file.exists()
        assert list(library.rglob("*.mp3")) == []
