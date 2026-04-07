from fastapi import APIRouter, Depends, HTTPException
from src.services.catalog_service import CatalogService
from src.services.metadata_service import MetadataService
from src.services.metadata_parser import MetadataParser
from src.services.metadata_frames_reader import load_id3_frames
from src.models.view_models import SongView

router = APIRouter(prefix="/api/v1/metabolic", tags=["Metabolic"])


def _get_catalog_service():
    return CatalogService()


@router.get("/inspect-file/{song_id}", response_model=SongView)
async def inspect_file(
    song_id: int, catalog: CatalogService = Depends(_get_catalog_service)
):
    """
    Reads a file's raw metadata and returns a SongView model.
    Used for comparison against the stored database state.
    """
    song = catalog.get_song(song_id)
    if not song or not song.source_path:
        raise HTTPException(status_code=404, detail="Song or file path not found")

    reader = MetadataService()
    parser = MetadataParser()

    try:
        raw_map = reader.extract_metadata(song.source_path)
        parsed_song = parser.parse(raw_map, song.source_path)
        return SongView.from_domain(parsed_song)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inspecting file: {str(e)}")


@router.get("/id3-frames")
async def get_id3_frames():
    """
    Returns the raw frame-to-category mapping.
    Used by the UI to style tags and categories dynamically.
    """
    return load_id3_frames()
