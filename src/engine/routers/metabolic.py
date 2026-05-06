from fastapi import APIRouter, HTTPException
from src.services.metadata_service import MetadataService
from src.services.metadata_parser import MetadataParser
from src.services.metadata_frames_reader import load_id3_frames
from src.models.view_models import SongView

router = APIRouter(prefix="/api/v1/metabolic", tags=["Metabolic"])


@router.post("/inspect-file")
async def inspect_file(db_song: SongView):
    """
    Reads the file at db_song.source_path, compares against db_song, and returns
    {diff, raw_tags}. The frontend already holds the SongView in state, so we accept
    it in the body to avoid a redundant DB hydration on this path.

    diff: {field_key: {db, file}} — empty when in sync. Keys align with frontend
    chip/scalar identifiers (media_name, year, bpm, isrc, notes, credit:{Role},
    tag:{Cat}, publisher, album).
    raw_tags: every ID3 frame the parser didn't map to a domain field, for the
    File-Only Data panel.
    """
    if not db_song.source_path:
        raise HTTPException(status_code=400, detail="db_song missing source_path")

    try:
        raw_map = MetadataService().extract_metadata(db_song.source_path)
        file_song = MetadataParser().parse(raw_map, db_song.source_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inspecting file: {str(e)}")

    diff = MetadataService().compare_songs(db_song, file_song)
    return {"diff": diff, "raw_tags": file_song.raw_tags or {}}


@router.get("/id3-frames")
async def get_id3_frames():
    """
    Returns the raw frame-to-category mapping.
    Used by the UI to style tags and categories dynamically.
    """
    return load_id3_frames()
