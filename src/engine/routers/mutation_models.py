import re
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from src.engine.config import SCALAR_VALIDATION, YEAR_MIN, YEAR_MAX


# ---------------------------------------------------------------------------
# Shared validators
# ---------------------------------------------------------------------------

_ISRC_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}\d{7}$")


def _reject_empty_string(v: Optional[str], field_name: str) -> Optional[str]:
    if v is not None and v == "":
        raise ValueError(f"{field_name} may not be empty string; use null to clear")
    return v


# ---------------------------------------------------------------------------
# Add items
# ---------------------------------------------------------------------------

class AddCreditItem(BaseModel):
    type: Literal["credit"]
    song_id: int
    name: str
    id: Optional[int] = None
    role: str

    @field_validator("name", "role")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


class AddTagItem(BaseModel):
    type: Literal["tag"]
    song_id: int
    name: str
    id: Optional[int] = None
    category: str
    make_primary: bool = False

    @field_validator("name", "category")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


class AddPublisherItem(BaseModel):
    type: Literal["publisher"]
    song_id: int
    name: str
    id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


class AddAlbumItem(BaseModel):
    type: Literal["album"]
    song_id: int
    name: str
    id: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    make_primary: bool = False

    @field_validator("name")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


AddItem = Annotated[
    Union[AddCreditItem, AddTagItem, AddPublisherItem, AddAlbumItem],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Update items
# ---------------------------------------------------------------------------

class UpdateSongItem(BaseModel):
    # TODO: split into UpdateMediaItem / UpdateSongItem when MediaMutator boundary is designed
    type: Literal["song"]
    id: int
    media_name: Optional[str] = None
    bpm: Optional[int] = None
    year: Optional[int] = None
    isrc: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("media_name")
    @classmethod
    def media_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        return _reject_empty_string(v, "media_name")

    @field_validator("isrc")
    @classmethod
    def isrc_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _ISRC_RE.match(v):
            raise ValueError("ISRC must be 12 characters: 2 country + 3 registrant + 7 digits (e.g. GBAYE0000001)")
        return v

    @field_validator("year")
    @classmethod
    def year_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (YEAR_MIN <= v <= YEAR_MAX):
            raise ValueError(f"year must be between {YEAR_MIN} and {YEAR_MAX}")
        return v

    @field_validator("bpm")
    @classmethod
    def bpm_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            rules = SCALAR_VALIDATION["bpm"]
            if not (rules["min"] <= v <= rules["max"]):
                raise ValueError(f"bpm must be between {rules['min']} and {rules['max']}")
        return v


class UpdateTagEntityItem(BaseModel):
    type: Literal["tag"]
    id: int
    name: Optional[str] = None
    category: Optional[str] = None

    @field_validator("name", "category")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        return _reject_empty_string(v, "field")


class UpdateSongTagItem(BaseModel):
    type: Literal["song_tag"]
    song_id: int
    tag_id: int
    is_primary: bool


class UpdateSongAlbumItem(BaseModel):
    type: Literal["song_album"]
    song_id: int
    album_id: int
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    is_primary: Optional[bool] = None


class UpdateAlbumEntityItem(BaseModel):
    type: Literal["album"]
    id: int
    title: Optional[str] = None
    album_type: Optional[str] = None
    release_year: Optional[int] = None

    @field_validator("title", "album_type")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        return _reject_empty_string(v, "field")

    @field_validator("release_year")
    @classmethod
    def year_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (YEAR_MIN <= v <= YEAR_MAX):
            raise ValueError(f"release_year must be between {YEAR_MIN} and {YEAR_MAX}")
        return v


class UpdateCreditEntityItem(BaseModel):
    type: Literal["credit"]
    id: int
    display_name: Optional[str] = None

    @field_validator("display_name")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        return _reject_empty_string(v, "display_name")


class UpdatePublisherEntityItem(BaseModel):
    type: Literal["publisher"]
    id: int
    name: Optional[str] = None
    parent_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        return _reject_empty_string(v, "name")


UpdateItem = Annotated[
    Union[
        UpdateSongItem,
        UpdateTagEntityItem,
        UpdateSongTagItem,
        UpdateSongAlbumItem,
        UpdateAlbumEntityItem,
        UpdateCreditEntityItem,
        UpdatePublisherEntityItem,
    ],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Remove items
# ---------------------------------------------------------------------------

class RemoveCreditItem(BaseModel):
    type: Literal["credit"]
    song_id: int
    id: int


class RemoveTagItem(BaseModel):
    type: Literal["tag"]
    song_id: int
    id: int


class RemovePublisherItem(BaseModel):
    type: Literal["publisher"]
    song_id: int
    id: int


class RemoveAlbumItem(BaseModel):
    type: Literal["album"]
    song_id: int
    id: int


RemoveItem = Annotated[
    Union[RemoveCreditItem, RemoveTagItem, RemovePublisherItem, RemoveAlbumItem],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Top-level request
# ---------------------------------------------------------------------------

class MutationRequest(BaseModel):
    add: Optional[List[AddItem]] = None
    update: Optional[List[UpdateItem]] = None
    remove: Optional[List[RemoveItem]] = None

    @model_validator(mode="after")
    def at_least_one_change(self) -> "MutationRequest":
        if not (self.add or self.update or self.remove):
            raise ValueError("request must contain at least one item in add, update, or remove")
        return self
