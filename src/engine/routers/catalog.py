from fastapi import APIRouter, HTTPException
from typing import List
from src.models.domain import Song
from src.services.catalog_service import CatalogService
from src.services.logger import logger
import os

router = APIRouter(prefix="/api/v1", tags=["catalog"])


def _get_service() -> CatalogService:
    """Centralized service factory for the router."""
    db_path = os.getenv("GOSLING_DB_PATH", "sqldb/gosling2.db")
    return CatalogService(db_path)


@router.get("/songs/search", response_model=List[Song])
async def search_songs(q: str) -> List[Song]:
    """Search for songs by title match."""
    logger.info(f"[CatalogRouter] GET /songs/search?q='{q}'")
    if not q or len(q) < 2:
        logger.warning(f"[CatalogRouter] VIOLATION: Invalid search query '{q}'")
        raise HTTPException(
            status_code=400, detail="Search query must be at least 2 characters"
        )

    results = _get_service().search_songs(q)
    logger.debug(f"[CatalogRouter] Found {len(results)} search results.")
    return results


@router.get("/songs/{song_id}", response_model=Song)
async def get_song(song_id: int) -> Song:
    """Fetch a single song by ID."""
    logger.debug(f"[CatalogRouter] GET /songs/{song_id}")
    song = _get_service().get_song(song_id)
    if not song:
        logger.warning(f"[CatalogRouter] VIOLATION: Song ID {song_id} not found")
        raise HTTPException(status_code=404, detail=f"Song ID {song_id} not found")
    return song
