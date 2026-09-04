"""
Safety tests for original-file cleanup (the "Delete Original" buttons).

Two live paths reach a physical unlink:
  - MutationCoordinator, DeleteOriginalFileItem -> deletes the recorded StagingOrigin
  - POST /api/v1/ingest/cleanup-original with file_path -> deletes a named duplicate

Both must refuse when the target turns out to be the song's own file, and the
coordinator must not unlink until its transaction has actually committed.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.data.staging_repository import StagingRepository
from src.engine.routers.mutation_models import (
    DeleteOriginalFileItem,
    DeleteSongItem,
    MutationRequest,
)
from src.services.filing_service import is_same_file
from src.utils.audio_hash import calculate_audio_hash
from src.services.mutation_coordinator import MutationCoordinator

SONG_ID = 1


def _set_source_path(db_path, song_id, path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = ?",
        (str(path), song_id),
    )
    conn.commit()
    conn.close()


def _set_audio_hash(db_path, song_id, path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE MediaSources SET AudioHash = ? WHERE SourceID = ?",
        (calculate_audio_hash(str(path)), song_id),
    )
    conn.commit()
    conn.close()


def _soft_delete(db_path, song_id):
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE MediaSources SET IsDeleted = 1 WHERE SourceID = ?", (song_id,))
    conn.commit()
    conn.close()


def _origin_of(db_path, song_id):
    return StagingRepository(db_path).get_origin(song_id)


def _cleanup_request(song_id):
    return MutationRequest(
        delete=[DeleteOriginalFileItem(type="original_file", song_id=song_id)]
    )


@pytest.fixture
def api(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    from src.engine_server import app

    return TestClient(app)


class TestIsSameFile:
    def test_case_difference_is_the_same_file(self, tmp_path):
        f = tmp_path / "Song.mp3"
        f.write_bytes(b"audio")
        assert is_same_file(f, tmp_path / "song.MP3")

    def test_distinct_files_with_identical_bytes_are_not_the_same(self, tmp_path):
        a = tmp_path / "a.mp3"
        b = tmp_path / "b.mp3"
        a.write_bytes(b"audio")
        b.write_bytes(b"audio")
        assert not is_same_file(a, b)

    def test_missing_files_fall_back_to_path_compare(self, tmp_path):
        assert is_same_file(tmp_path / "gone.mp3", tmp_path / "GONE.mp3")
        assert not is_same_file(tmp_path / "gone.mp3", tmp_path / "other.mp3")


class TestCoordinatorCleanup:
    def test_deletes_a_genuine_redundant_original(self, populated_db, tmp_path):
        library = tmp_path / "library.mp3"
        original = tmp_path / "Downloads" / "original.mp3"
        original.parent.mkdir()
        library.write_bytes(b"audio")
        original.write_bytes(b"audio")

        _set_source_path(populated_db, SONG_ID, library)
        StagingRepository(populated_db).set_origin(SONG_ID, str(original))

        MutationCoordinator(populated_db).apply(_cleanup_request(SONG_ID))

        assert not original.exists()
        assert library.exists()
        assert _origin_of(populated_db, SONG_ID) is None

    def test_refuses_when_the_original_is_the_songs_own_file(
        self, populated_db, tmp_path
    ):
        own = tmp_path / "Songs" / "track.mp3"
        own.parent.mkdir()
        own.write_bytes(b"audio")

        _set_source_path(populated_db, SONG_ID, own)
        StagingRepository(populated_db).set_origin(SONG_ID, str(own))

        with pytest.raises(ValueError, match="own file"):
            MutationCoordinator(populated_db).apply(_cleanup_request(SONG_ID))

        assert own.exists()
        assert _origin_of(populated_db, SONG_ID) == str(own)

    def test_refuses_on_case_differing_path_to_the_same_file(
        self, populated_db, tmp_path
    ):
        own = tmp_path / "Songs" / "Track.mp3"
        own.parent.mkdir()
        own.write_bytes(b"audio")

        _set_source_path(populated_db, SONG_ID, own)
        StagingRepository(populated_db).set_origin(
            SONG_ID, str(own).replace("Track.mp3", "track.mp3")
        )

        with pytest.raises(ValueError):
            MutationCoordinator(populated_db).apply(_cleanup_request(SONG_ID))

        assert own.exists()

    def test_guard_still_applies_to_a_rejected_song(self, populated_db, tmp_path):
        """A rejected song is soft-deleted, so get_song() cannot see it."""
        own = tmp_path / "Songs" / "rejected.mp3"
        own.parent.mkdir()
        own.write_bytes(b"audio")

        _set_source_path(populated_db, SONG_ID, own)
        StagingRepository(populated_db).set_origin(SONG_ID, str(own))
        _soft_delete(populated_db, SONG_ID)

        with pytest.raises(ValueError, match="own file"):
            MutationCoordinator(populated_db).apply(_cleanup_request(SONG_ID))

        assert own.exists()

    def test_no_unlink_when_the_transaction_rolls_back(self, populated_db, tmp_path):
        """The file must outlive a mutation that fails after the delete item."""
        library = tmp_path / "library.mp3"
        original = tmp_path / "original.mp3"
        library.write_bytes(b"audio")
        original.write_bytes(b"audio")

        _set_source_path(populated_db, SONG_ID, library)
        StagingRepository(populated_db).set_origin(SONG_ID, str(original))

        request = MutationRequest(
            delete=[
                DeleteOriginalFileItem(type="original_file", song_id=SONG_ID),
                DeleteSongItem(type="song", id=999999),
            ]
        )
        with pytest.raises(LookupError):
            MutationCoordinator(populated_db).apply(request)

        assert original.exists()
        assert _origin_of(populated_db, SONG_ID) == str(original)

    @pytest.mark.xfail(
        strict=True,
        reason="No corroboration of the origin file's identity yet. Comparing it to the "
        "song's audio_hash does not work: WAV imports are transcoded, so the origin and "
        "the stored song never hash alike. Needs OriginHash captured at drop time - see "
        "docs/todo/file_deletion_chokepoint.md.",
    )
    def test_refuses_a_same_named_but_different_file(self, populated_db, tmp_path):
        """A dropped file's origin is only a guess at Downloads/<filename>.

        Drop song B after renaming it to song A's filename and the guess points at
        song A, an unrelated file that must survive.
        """
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        song_a = downloads / "track.mp3"
        song_a.write_bytes(b"song A audio")

        library = tmp_path / "library.mp3"
        library.write_bytes(b"song B audio")

        _set_source_path(populated_db, SONG_ID, library)
        _set_audio_hash(populated_db, SONG_ID, library)
        StagingRepository(populated_db).set_origin(SONG_ID, str(song_a))

        with pytest.raises(ValueError, match="different file"):
            MutationCoordinator(populated_db).apply(_cleanup_request(SONG_ID))

        assert song_a.exists()
        assert song_a.read_bytes() == b"song A audio"
        assert _origin_of(populated_db, SONG_ID) == str(song_a)

    def test_missing_original_file_is_not_an_error(self, populated_db, tmp_path):
        library = tmp_path / "library.mp3"
        library.write_bytes(b"audio")
        _set_source_path(populated_db, SONG_ID, library)
        StagingRepository(populated_db).set_origin(
            SONG_ID, str(tmp_path / "already_gone.mp3")
        )

        MutationCoordinator(populated_db).apply(_cleanup_request(SONG_ID))

        assert _origin_of(populated_db, SONG_ID) is None


class TestCleanupEndpoint:
    def test_deletes_a_redundant_copy(self, api, populated_db, tmp_path):
        library = tmp_path / "library.mp3"
        duplicate = tmp_path / "Downloads" / "dupe.mp3"
        duplicate.parent.mkdir()
        library.write_bytes(b"audio")
        duplicate.write_bytes(b"audio")
        _set_source_path(populated_db, SONG_ID, library)

        res = api.post(
            "/api/v1/ingest/cleanup-original",
            json={"file_path": str(duplicate), "song_id": SONG_ID},
        )

        assert res.status_code == 200
        assert res.json()["status"] == "DELETED"
        assert not duplicate.exists()
        assert library.exists()

    def test_blocks_deleting_the_songs_own_file(self, api, populated_db, tmp_path):
        own = tmp_path / "library.mp3"
        own.write_bytes(b"audio")
        _set_source_path(populated_db, SONG_ID, own)

        res = api.post(
            "/api/v1/ingest/cleanup-original",
            json={"file_path": str(own), "song_id": SONG_ID},
        )

        assert res.status_code == 403
        assert own.exists()

    def test_blocks_case_differing_path_to_the_songs_own_file(
        self, api, populated_db, tmp_path
    ):
        own = tmp_path / "Library.mp3"
        own.write_bytes(b"audio")
        _set_source_path(populated_db, SONG_ID, own)

        res = api.post(
            "/api/v1/ingest/cleanup-original",
            json={
                "file_path": str(own).replace("Library.mp3", "library.mp3"),
                "song_id": SONG_ID,
            },
        )

        assert res.status_code == 403
        assert own.exists()

    def test_file_path_without_song_id_is_rejected(self, api, tmp_path):
        stray = tmp_path / "stray.mp3"
        stray.write_bytes(b"audio")

        res = api.post(
            "/api/v1/ingest/cleanup-original", json={"file_path": str(stray)}
        )

        assert res.status_code == 400
        assert stray.exists()

    def test_unknown_song_id_is_rejected(self, api, tmp_path):
        stray = tmp_path / "stray.mp3"
        stray.write_bytes(b"audio")

        res = api.post(
            "/api/v1/ingest/cleanup-original",
            json={"file_path": str(stray), "song_id": 999999},
        )

        assert res.status_code == 404
        assert stray.exists()

    def test_already_gone_reports_cleanly(self, api, populated_db, tmp_path):
        library = tmp_path / "library.mp3"
        library.write_bytes(b"audio")
        _set_source_path(populated_db, SONG_ID, library)

        res = api.post(
            "/api/v1/ingest/cleanup-original",
            json={"file_path": str(tmp_path / "gone.mp3"), "song_id": SONG_ID},
        )

        assert res.status_code == 200
        assert res.json()["status"] == "ALREADY_GONE"
