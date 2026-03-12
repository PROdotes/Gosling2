from fastapi import APIRouter, HTTPException
from typing import List, Optional
from src.models.domain import Song
from src.models.view_models import SongView
from src.services.catalog_service import CatalogService
from src.services.logger import logger
import os

router = APIRouter(prefix="/api/v1", tags=["catalog"])


def _get_service() -> CatalogService:
    """Centralized service factory for the router."""
    db_path = os.getenv("GOSLING_DB_PATH", "sqldb/gosling2.db")
    return CatalogService(db_path)


@router.get("/songs/search", response_model=List[SongView])
async def search_songs(
    q: Optional[str] = None, query: Optional[str] = None
) -> List[Song]:
    """Search for songs by title match. Supports both 'q' and 'query'."""
    MIN_CHAR = 2
    search_term = q or query
    logger.info(f"[CatalogRouter] GET /songs/search search_term='{search_term}'")

    if not search_term or len(search_term) < MIN_CHAR:
        logger.warning(
            f"[CatalogRouter] VIOLATION: Invalid search query '{search_term}'"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Search query must be at least {MIN_CHAR} characters",
        )

    results = _get_service().search_songs(search_term)
    logger.debug(f"[CatalogRouter] Found {len(results)} search results.")
    return [SongView.from_domain(s) for s in results]


@router.get("/songs/{song_id:int}", response_model=SongView)
async def get_song(song_id: int) -> Song:
    """Fetch a single song by ID."""
    logger.debug(f"[CatalogRouter] GET /songs/{song_id}")
    song = _get_service().get_song(song_id)
    if not song:
        logger.warning(f"[CatalogRouter] VIOLATION: Song ID {song_id} not found")
        raise HTTPException(status_code=404, detail=f"Song ID {song_id} not found")
    return SongView.from_domain(song)
