from fastapi import APIRouter, Depends, HTTPException, Response
from src.engine.models.spotify import (
    SpotifyParseRequest,
    SpotifyParseResult,
    SpotifyImportRequest,
)
from src.services.spotify_service import SpotifyService
from src.services.catalog_service import CatalogService
from src.services.mutation_coordinator import MutationCoordinator
from src.engine.routers.mutation_models import (
    MutationRequest,
    AddCreditItem,
    AddPublisherItem,
)
from src.services.logger import logger
from src.engine.config import get_db_path

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
def import_credits(request: SpotifyImportRequest):
    """
    Atomically import parsed credits and publishers into the catalog.
    """
    logger.debug(f"[SpotifyRouter] -> import_credits(song_id={request.song_id})")
    db_path = str(get_db_path())
    if not CatalogService(db_path).get_song(request.song_id):
        raise HTTPException(status_code=404, detail=f"Song {request.song_id} not found")
    try:
        add_items = [
            AddCreditItem(
                type="credit",
                song_id=request.song_id,
                name=c.name,
                role=c.role,
                id=c.identity_id,
            )
            for c in request.credits
        ] + [
            AddPublisherItem(type="publisher", song_id=request.song_id, name=pub)
            for pub in request.publishers
        ]
        if add_items:
            MutationCoordinator(db_path).apply(MutationRequest(add=add_items))
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
