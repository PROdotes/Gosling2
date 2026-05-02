from fastapi import APIRouter, Depends, HTTPException
from src.services.catalog_service import CatalogService
from src.services.edit_service import EditService
from src.services.metadata_service import MetadataService
from src.services.metadata_parser import MetadataParser
from src.services.logger import logger

router = APIRouter(prefix="/api/v1", tags=["song-updates"])


def _get_service() -> CatalogService:
    return CatalogService()


@router.get("/roles")
async def get_all_roles(service: CatalogService = Depends(_get_service)):
    return service.get_all_roles()


@router.get("/songs/{song_id}/sync-status", status_code=200)
async def get_sync_status(
    song_id: int,
    service: CatalogService = Depends(_get_service),
):
    db_song = service.get_song(song_id)
    if not db_song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    try:
        raw = MetadataService().extract_metadata(db_song.source_path)
        file_song = MetadataParser().parse(raw, db_song.source_path)
    except FileNotFoundError:
        return {"in_sync": False, "mismatches": ["file_not_found"]}
    except Exception:
        return {"in_sync": False, "mismatches": ["file_unreadable"]}
    svc = MetadataService()
    result = svc.compare_songs(db_song, file_song)
    filtered = svc.filter_sync_mismatches(db_song, result["mismatches"])
    return {"in_sync": len(filtered) == 0, "mismatches": filtered}


@router.get("/songs/{song_id}/sync-id3", status_code=200)
async def sync_id3(song_id: int):
    logger.debug(f"[SongUpdates] -> sync_id3(id={song_id})")
    edit_service = EditService()
    song = edit_service._library_service.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    try:
        edit_service._metadata_writer.write_metadata(song)
        logger.debug(f"[SongUpdates] <- sync_id3(id={song_id}) OK")
        return {"status": "ok", "song_id": song_id}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[SongUpdates] <- sync_id3(id={song_id}) CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))
