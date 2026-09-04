"""
Origin-path handling on the re-ingest path (POST /api/v1/ingest/resolve-conflict).

The router used to derive the origin from the staged filename with
`Path(staged_path).name.split("_", 1)[-1]`. The staged file is the app's own artifact:
uuid-prefixed, and transcoded to .mp3 for WAV imports. So for a dropped WAV that guess
fabricated a `Downloads\\....mp3` that never existed, overwriting the correct `.wav`
origin recorded at drop time.

The origin must be carried in, never reconstructed.
"""

import shutil
import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.data.staging_repository import StagingRepository

GHOST_ID = 1


@pytest.fixture
def api(populated_db, monkeypatch):
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    from src.engine_server import app

    return TestClient(app)


def _make_ghost(db_path, song_id=GHOST_ID):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE MediaSources SET IsDeleted = 1 WHERE SourceID = ?", (song_id,)
    )
    conn.execute("DELETE FROM SongCredits WHERE SourceID = ?", (song_id,))
    conn.commit()
    conn.close()


def _stage(tmp_path, test_audio_file, name="abc-123_Some Song.mp3"):
    staged = tmp_path / name
    shutil.copy(test_audio_file, staged)
    return str(staged)


def _resolve(api, staged_path, original_path=None):
    params = {"ghost_id": GHOST_ID, "staged_path": staged_path}
    if original_path is not None:
        params["original_path"] = original_path
    return api.post("/api/v1/ingest/resolve-conflict", params=params)


def test_existing_origin_survives_reingest(
    api, populated_db, tmp_path, test_audio_file
):
    """The correct origin recorded at drop time must not be clobbered.

    This is the WAV case: Downloads holds a .wav, the staged file is a converted .mp3.
    """
    downloads_original = str(tmp_path / "Downloads" / "Arlo Parks - Heaven.wav")
    StagingRepository(populated_db).set_origin(GHOST_ID, downloads_original)
    _make_ghost(populated_db)
    staged = _stage(tmp_path, test_audio_file, "abc-123_Arlo Parks - Heaven.mp3")

    res = _resolve(api, staged)

    assert res.status_code == 200
    assert StagingRepository(populated_db).get_origin(GHOST_ID) == downloads_original


def test_no_origin_is_invented_when_none_is_known(
    api, populated_db, tmp_path, test_audio_file
):
    """Staging-orphan reactivation knows no original, so none may be recorded."""
    _make_ghost(populated_db)
    staged = _stage(tmp_path, test_audio_file)

    res = _resolve(api, staged)

    assert res.status_code == 200
    assert StagingRepository(populated_db).get_origin(GHOST_ID) is None


def test_supplied_origin_is_recorded(api, populated_db, tmp_path, test_audio_file):
    _make_ghost(populated_db)
    staged = _stage(tmp_path, test_audio_file)
    original = str(tmp_path / "Downloads" / "Some Song.mp3")

    res = _resolve(api, staged, original_path=original)

    assert res.status_code == 200
    assert StagingRepository(populated_db).get_origin(GHOST_ID) == original


def test_in_place_import_records_no_origin(
    api, populated_db, tmp_path, test_audio_file
):
    """In-place imports hand back the file itself; that is not a deletable original."""
    _make_ghost(populated_db)
    staged = _stage(tmp_path, test_audio_file)

    res = _resolve(api, staged, original_path=staged)

    assert res.status_code == 200
    assert StagingRepository(populated_db).get_origin(GHOST_ID) is None
