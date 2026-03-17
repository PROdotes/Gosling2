import pytest
import os
from src.engine.routers.catalog import get_song
from fastapi import HTTPException


@pytest.mark.anyio
async def test_get_song_logic_success(populated_db, monkeypatch):
    """LAW: Directly calling the router function returns the Song model."""
    # Mock the DB path to use the populated test DB
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)

    song = await get_song(2)

    assert song is not None
    assert song.id == 2
    assert song.title == "Everlong"


@pytest.mark.anyio
async def test_get_song_logic_not_found(populated_db, monkeypatch):
    """LAW: Directly calling the router function with a bad ID raises 404."""
    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)

    with pytest.raises(HTTPException) as excinfo:
        await get_song(999)

    assert excinfo.value.status_code == 404


@pytest.mark.anyio
async def test_inspect_file_integration(populated_db, monkeypatch):
    """LAW: inspect_file must parse real files and return a valid SongView."""
    import sqlite3
    from src.engine.routers.metabolic import inspect_file, _get_catalog_service
    from src.models.view_models import SongView

    # 1. Update Song ID 1 to point to a REAL fixture on disk
    fixture_path = os.path.abspath("tests/fixtures/silence.mp3")
    conn = sqlite3.connect(populated_db)
    conn.execute("UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1", (fixture_path,))
    # Also set a real title in the ID3 tag metadata for this file if we want it to match
    conn.commit()
    conn.close()

    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    service = _get_catalog_service()

    # Success Case: SongID 1 now points to a real file
    res = await inspect_file(1, service)

    assert isinstance(res, SongView)
    # The silence.mp3 fixture has NO tags by default, or maybe some. 
    # But it should return a SongView without crashing.
    assert res.source_path == fixture_path


@pytest.mark.anyio
async def test_inspect_file_not_found(populated_db, monkeypatch):
    """Cover metabolic.py: 26 (404 Path)."""
    from src.engine.routers.metabolic import inspect_file, _get_catalog_service
    import os

    monkeypatch.setenv("GOSLING_DB_PATH", populated_db)
    service = _get_catalog_service()

    with pytest.raises(HTTPException) as exc:
        await inspect_file(9999, service)
    assert exc.value.status_code == 404
