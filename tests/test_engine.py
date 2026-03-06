import pytest
from src.engine.routers.catalog import get_song
from src.services.catalog_service import CatalogService
from fastapi import HTTPException
import os

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
