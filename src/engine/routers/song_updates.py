import os
import subprocess

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


@router.post("/songs/{song_id}/reveal", status_code=200)
async def reveal_file(song_id: int):
    """Open the song's containing folder in Explorer with the file selected.

    Server-local only: this opens a window on the machine running the server,
    so it is only meaningful when the browser and server share a desktop.
    """
    logger.debug(f"[SongUpdates] -> reveal_file(id={song_id})")
    library = LibraryService(get_db_path())
    song = library.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")

    path = song.source_path
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=400, detail="File not found on disk")

    try:
        # Pass as a raw string (not a list): Windows hands it to CreateProcess
        # verbatim. A list would let subprocess quote the whole "/select,<path>"
        # argument when the path has spaces, which Explorer cannot parse and so
        # it silently opens a default folder. The canonical form Explorer wants
        # is the comma OUTSIDE the quotes: explorer /select,"C:\path\file".
        # explorer returns exit code 1 even on success, so do not check it.
        subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
        logger.debug(f"[SongUpdates] <- reveal_file(id={song_id}) OK")
        return {"status": "ok", "song_id": song_id}
    except Exception as e:
        logger.error(f"[SongUpdates] <- reveal_file(id={song_id}) CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))
