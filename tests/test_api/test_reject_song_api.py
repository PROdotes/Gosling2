"""
End-to-end coverage for the reject/change-reason mutate payloads sent by
src/static/js/dashboard/api.js (rejectSong, changeRejectReason).

These hit POST /api/v1/mutate against a real populated_db and assert real
DB state, not just that fetch was called with a given body.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    from src.engine_server import app

    return TestClient(app)


def _media_row(populated_db, song_id):
    conn = sqlite3.connect(populated_db)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT IsDeleted, SourceNotes FROM MediaSources WHERE SourceID = ?",
        (song_id,),
    ).fetchone()
    conn.close()
    return row


def _artist_name_deleted(populated_db, name_id):
    conn = sqlite3.connect(populated_db)
    row = conn.execute(
        "SELECT IsDeleted FROM ArtistNames WHERE NameID = ?", (name_id,)
    ).fetchone()
    conn.close()
    return bool(row[0])


def _credit_exists(populated_db, source_id, name_id):
    conn = sqlite3.connect(populated_db)
    row = conn.execute(
        "SELECT 1 FROM SongCredits WHERE SourceID = ? AND CreditedNameID = ?",
        (source_id, name_id),
    ).fetchone()
    conn.close()
    return row is not None


class TestRejectSong:
    def test_reject_does_not_touch_shared_identity_or_other_songs(
        self, api, populated_db
    ):
        # Song 8 (Joint Venture) and song 3 (Range Rover Bitch) both credit
        # identity 40 (Taylor Hawkins, NameID 40). Rejecting song 8 must only
        # hard-delete song 8's own SongCredits row, not the shared identity's
        # ArtistNames row or song 3's own credit link.
        resp = api.post(
            "/api/v1/mutate",
            json={
                "update": [{"type": "song", "id": 8, "notes": "REJECTED: BAD SONG"}],
                "delete": [{"type": "song", "id": 8}],
            },
        )
        assert resp.status_code == 200, resp.text

        assert not _credit_exists(populated_db, source_id=8, name_id=40)
        assert _credit_exists(populated_db, source_id=3, name_id=40)
        assert _artist_name_deleted(populated_db, 40) is False

        song_3 = _media_row(populated_db, 3)
        assert bool(song_3["IsDeleted"]) is False

    def test_reject_soft_deletes_and_sets_notes(self, api, populated_db):
        resp = api.post(
            "/api/v1/mutate",
            json={
                "update": [{"type": "song", "id": 1, "notes": "REJECTED: BAD SONG"}],
                "delete": [{"type": "song", "id": 1}],
            },
        )
        assert resp.status_code == 200, resp.text

        row = _media_row(populated_db, 1)
        assert bool(row["IsDeleted"]) is True
        assert row["SourceNotes"] == "REJECTED: BAD SONG"


class TestChangeRejectReason:
    def test_updates_reason_on_already_rejected_song_without_deleting_again(
        self, api, populated_db
    ):
        # First reject the song (mirrors rejectSong()).
        reject_resp = api.post(
            "/api/v1/mutate",
            json={
                "update": [{"type": "song", "id": 1, "notes": "REJECTED: BAD SONG"}],
                "delete": [{"type": "song", "id": 1}],
            },
        )
        assert reject_resp.status_code == 200, reject_resp.text

        # Now change the reason (mirrors changeRejectReason()) - update only,
        # no delete. This must succeed even though the row is already
        # soft-deleted.
        change_resp = api.post(
            "/api/v1/mutate",
            json={
                "update": [
                    {
                        "type": "song",
                        "id": 1,
                        "notes": "REJECTED: WRONG METADATA",
                    }
                ]
            },
        )
        assert change_resp.status_code == 200, change_resp.text

        row = _media_row(populated_db, 1)
        assert bool(row["IsDeleted"]) is True
        assert row["SourceNotes"] == "REJECTED: WRONG METADATA"

    def test_change_reason_on_nonexistent_song_returns_404_and_writes_nothing(
        self, api, populated_db
    ):
        change_resp = api.post(
            "/api/v1/mutate",
            json={
                "update": [{"type": "song", "id": 99999, "notes": "REJECTED: WHATEVER"}]
            },
        )
        assert change_resp.status_code == 404, change_resp.text
        assert _media_row(populated_db, 99999) is None


class TestDeletedStatusFilter:
    def test_filter_by_deleted_status_does_not_500_on_null_source_path(self, api):
        # delete_file=True nulls SourcePath (see MediaSourceRepository.soft_delete)
        # - a plain "delete this bad ingest" flow, not a reject.
        del_resp = api.post(
            "/api/v1/mutate",
            json={"delete": [{"type": "song", "id": 2, "delete_file": True}]},
        )
        assert del_resp.status_code == 200, del_resp.text

        # Also reject a different song (notes set, SourcePath left alone).
        reject_resp = api.post(
            "/api/v1/mutate",
            json={
                "update": [{"type": "song", "id": 1, "notes": "REJECTED: BAD SONG"}],
                "delete": [{"type": "song", "id": 1}],
            },
        )
        assert reject_resp.status_code == 200, reject_resp.text

        filter_resp = api.get("/api/v1/songs/filter?mode=ALL&statuses=deleted")
        assert filter_resp.status_code == 200, filter_resp.text

        returned_ids = {song["id"] for song in filter_resp.json()}
        assert {1, 2} <= returned_ids

        by_id = {song["id"]: song for song in filter_resp.json()}
        assert by_id[2]["source_path"] is None
        assert by_id[1]["source_path"] is not None


class TestGetDeletedSongEndpoint:
    def test_returns_bare_row_with_reject_reason(self, api):
        reject_resp = api.post(
            "/api/v1/mutate",
            json={
                "update": [{"type": "song", "id": 1, "notes": "REJECTED: BAD SONG"}],
                "delete": [{"type": "song", "id": 1}],
            },
        )
        assert reject_resp.status_code == 200, reject_resp.text

        resp = api.get("/api/v1/songs/1/deleted")
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["id"] == 1
        assert body["reject_reason"] == "BAD SONG"

    def test_returns_bare_row_with_no_reason_for_plain_delete(self, api):
        del_resp = api.post(
            "/api/v1/mutate",
            json={"delete": [{"type": "song", "id": 2, "delete_file": True}]},
        )
        assert del_resp.status_code == 200, del_resp.text

        resp = api.get("/api/v1/songs/2/deleted")
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["id"] == 2
        assert body["source_path"] is None
        assert body["reject_reason"] is None

    def test_404_for_a_live_song(self, api):
        resp = api.get("/api/v1/songs/1/deleted")
        assert resp.status_code == 404, resp.text

    def test_404_for_a_nonexistent_song(self, api):
        resp = api.get("/api/v1/songs/99999/deleted")
        assert resp.status_code == 404, resp.text
