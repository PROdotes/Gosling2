import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.services.catalog_service import CatalogService
from src.services.waveform_service import get_or_build_peaks

router = APIRouter(prefix="/api/v1", tags=["audio"])


def _get_service() -> CatalogService:
    return CatalogService()


@router.get("/songs/{song_id}/audio")
async def stream_song_audio(song_id: int):
    """Stream the audio file for a song by its ID."""
    service = _get_service()
    song = service.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    path = Path(song.source_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    media_type, _ = mimetypes.guess_type(str(path))
    if not media_type:
        media_type = "audio/mpeg"

    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/songs/{song_id}/waveform")
async def get_song_waveform(song_id: int) -> dict:
    """Return 1000 normalized RMS peaks (0..1) for the song's working copy. Builds on first call, then cached."""
    service = _get_service()
    song = service.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    path = Path(song.source_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    try:
        peaks = get_or_build_peaks(song_id, path)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"peaks": peaks}
