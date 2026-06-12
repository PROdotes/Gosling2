from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.exceptions import MergeRequiredError
from src.models.view_models import SongView
from src.services.multi_edit_service import MultiEditService


def _get_service() -> MultiEditService:
    """Centralized service factory for the router."""
    return MultiEditService()


router = APIRouter(prefix="/api/v1", tags=["multi-edit"])


class MultiViewRequest(BaseModel):
    song_ids: List[int] = Field(min_length=2)


class MultiUpdateOp(BaseModel):
    # Collapsed scalars only; unset fields are excluded from the per-song
    # items (untouched mixed fields are simply not sent — exclude_unset).
    # extra="forbid": non-multi-editable fields must 422, not silently drop.
    model_config = ConfigDict(extra="forbid")

    media_name: Optional[str] = None
    bpm: Optional[int] = None
    year: Optional[int] = None
    isrc: Optional[str] = None
    notes: Optional[str] = None


class MultiAddOp(BaseModel):
    # Single-song add shape minus song_id; per-field validation happens when
    # the packer builds the real Add*Item models.
    type: Literal["credit", "tag", "publisher", "album"]
    id: Optional[int] = None
    name: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None
    album_type: Optional[str] = None
    release_year: Optional[int] = None
    make_primary: bool = False


class MultiRemoveOp(BaseModel):
    # id is the entity id (tag/publisher/album) or, for credits, the virtual
    # view's credit_id; the packer resolves per-song rows.
    type: Literal["credit", "tag", "publisher", "album"]
    id: int


class MultiMutateRequest(BaseModel):
    song_ids: List[int] = Field(min_length=2)
    update: Optional[MultiUpdateOp] = None
    add: List[MultiAddOp] = []
    remove: List[MultiRemoveOp] = []

    @model_validator(mode="after")
    def at_least_one_change(self) -> "MultiMutateRequest":
        if not (self.update or self.add or self.remove):
            raise ValueError("request must contain at least one op")
        return self


@router.post("/songs/multi-view", response_model=SongView)
async def multi_view(
    body: MultiViewRequest, service: MultiEditService = Depends(_get_service)
) -> SongView:
    try:
        return service.get_multi_view(body.song_ids)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/songs/multi-mutate")
async def multi_mutate(
    body: MultiMutateRequest, service: MultiEditService = Depends(_get_service)
) -> dict:
    try:
        return service.multi_mutate(
            body.song_ids,
            update=(
                body.update.model_dump(exclude_unset=True) if body.update else None
            ),
            add=[op.model_dump() for op in body.add],
            remove=[op.model_dump() for op in body.remove],
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MergeRequiredError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "MERGE_REQUIRED",
                "entity_type": e.entity_type,
                "collision_id": e.collision_id,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
