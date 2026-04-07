from fastapi import APIRouter, Depends, HTTPException, Response
from src.engine.models.spotify import (
    SpotifyParseRequest,
    SpotifyParseResult,
    SpotifyImportRequest,
)
from src.services.spotify_service import SpotifyService
from src.services.catalog_service import CatalogService
from src.services.logger import logger

router = APIRouter(prefix="/api/v1/spotify", tags=["Spotify"])


def _get_service() -> CatalogService:
    return CatalogService()


@router.post("/parse", response_model=SpotifyParseResult)
def parse_credits(
    request: SpotifyParseRequest, service: CatalogService = Depends(_get_service)
):
    """
    Parse raw Spotify credits text into a structured result.
    """
    logger.debug(f"[SpotifyRouter] -> parse_credits(title='{request.reference_title}')")
    return SpotifyService.parse_credits(
        request.raw_text, request.reference_title, service.get_all_roles()
    )


@router.post("/import", status_code=204)
def import_credits(
    request: SpotifyImportRequest, service: CatalogService = Depends(_get_service)
):
    """
    Atomically import parsed credits and publishers into the catalog.
    """
    logger.debug(f"[SpotifyRouter] -> import_credits(song_id={request.song_id})")
    try:
        service.import_credits_bulk(
            song_id=request.song_id,
            credits=request.credits,
            publishers=request.publishers,
        )
        return Response(status_code=204)
    except LookupError as e:
        logger.warning(
            f"[SpotifyRouter] <- import_credits(id={request.song_id}) NOT_FOUND: {e}"
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            f"[SpotifyRouter] <- import_credits(id={request.song_id}) FAILED: {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))
