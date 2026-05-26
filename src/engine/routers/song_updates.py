from fastapi import APIRouter, Depends, HTTPException
from src.services.catalog_service import CatalogService
from src.services.library_service import LibraryService
from src.services.metadata_writer import MetadataWriter
from src.services.logger import logger
from src.engine.config import get_db_path

router = APIRouter(prefix="/api/v1", tags=["song-updates"])


def _get_service() -> CatalogService:
    return CatalogService()


@router.get("/roles")
async def get_all_roles(service: CatalogService = Depends(_get_service)):
    return service.get_all_roles()


@router.get("/songs/{song_id}/sync-id3", status_code=200)
async def sync_id3(song_id: int):
    logger.debug(f"[SongUpdates] -> sync_id3(id={song_id})")
    library = LibraryService(get_db_path())
    song = library.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    try:
        MetadataWriter().write_metadata(song)
        logger.debug(f"[SongUpdates] <- sync_id3(id={song_id}) OK")
        return {"status": "ok", "song_id": song_id}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[SongUpdates] <- sync_id3(id={song_id}) CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))
