from fastapi import APIRouter, HTTPException
from src.models.domain import Song
from src.services.catalog_service import CatalogService
import os

router = APIRouter(prefix="/api/v1", tags=["catalog"])

@router.get("/songs/{song_id}", response_model=Song)
async def get_song(song_id: int) -> Song:
    """Fetch a single song by ID."""
    db_path = os.getenv("GOSLING_DB_PATH", "sqldb/prodo.db")
    service = CatalogService(db_path)
    song = service.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song ID {song_id} not found")
    return song
