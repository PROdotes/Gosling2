from fastapi import APIRouter, Depends, HTTPException
from src.services.edit_service import EditService
from src.models.domain import Album
from src.services.logger import logger

router = APIRouter(prefix="/api/v1/albums", tags=["albums", "write"])


def _get_edit_service() -> EditService:
    return EditService()


@router.post("/{album_id}/sync-from-song/{song_id}", response_model=Album)
async def sync_album_with_song(
    album_id: int,
    song_id: int,
    service: EditService = Depends(_get_edit_service),
) -> Album:
    """
    Sync album metadata from a song (backend implementation of CW-1).
    Syncs: release_year (if missing), Performer credits, publishers.
    Atomic operation.
    """
    logger.debug(
        f"[AlbumUpdates] -> sync_album_with_song(album_id={album_id}, song_id={song_id})"
    )
    try:
        result = service.sync_album_with_song(album_id, song_id)
        logger.debug("[AlbumUpdates] <- sync_album_with_song OK")
        return result
    except LookupError as e:
        logger.warning(f"[AlbumUpdates] <- sync_album_with_song NOT_FOUND: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[AlbumUpdates] <- sync_album_with_song CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))
