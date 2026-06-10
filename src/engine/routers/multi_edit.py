from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.models.view_models import SongView
from src.services.multi_edit_service import MultiEditService


def _get_service() -> MultiEditService:
    """Centralized service factory for the router."""
    return MultiEditService()


router = APIRouter(prefix="/api/v1", tags=["multi-edit"])


class MultiViewRequest(BaseModel):
    song_ids: List[int] = Field(min_length=2)


@router.post("/songs/multi-view", response_model=SongView)
async def multi_view(
    body: MultiViewRequest, service: MultiEditService = Depends(_get_service)
) -> SongView:
    try:
        return service.get_multi_view(body.song_ids)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
