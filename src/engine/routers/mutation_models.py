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
    song_id: Optional[int] = None
    album_id: Optional[int] = None
    name: str
    id: Optional[int] = None
    role: str

    @field_validator("name", "role")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v

    @model_validator(mode="after")
    def exactly_one_target(self) -> "AddCreditItem":
        if (self.song_id is None) == (self.album_id is None):
            raise ValueError("exactly one of song_id or album_id must be set")
        return self


class AddTagItem(BaseModel):
    type: Literal["tag"]
    song_id: int
    name: Optional[str] = None
    id: Optional[int] = None
    category: Optional[str] = None
    make_primary: bool = False

    @field_validator("name", "category")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("must not be blank")
        return v

    @model_validator(mode="after")
    def id_or_name_and_category(self) -> "AddTagItem":
        if self.id is None and not (self.name and self.category):
            raise ValueError("either id or both name and category are required")
        return self


class AddPublisherItem(BaseModel):
    type: Literal["publisher"]
    song_id: Optional[int] = None
    album_id: Optional[int] = None
    name: str
    id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v

    @model_validator(mode="after")
    def exactly_one_target(self) -> "AddPublisherItem":
        if (self.song_id is None) == (self.album_id is None):
            raise ValueError("exactly one of song_id or album_id must be set")
        return self


class AddIdentityMemberItem(BaseModel):
    type: Literal["identity_member"]
    group_id: int
    member_id: int


class AddIdentityAliasItem(BaseModel):
    type: Literal["identity_alias"]
    identity_id: int
    display_name: Optional[str] = None
    name_id: Optional[int] = None

    @model_validator(mode="after")
    def name_or_id(self) -> "AddIdentityAliasItem":
        if self.display_name is None and self.name_id is None:
            raise ValueError("either display_name or name_id is required")
        return self


class AddAlbumItem(BaseModel):
    type: Literal["album"]
    song_id: int
    name: Optional[str] = None
    id: Optional[int] = None
    album_type: Optional[str] = None
    release_year: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    make_primary: bool = False

    @model_validator(mode="after")
    def name_required_without_id(self) -> "AddAlbumItem":
        if self.id is None and not (self.name and self.name.strip()):
            raise ValueError("name is required when id is not provided")
        return self

    @field_validator("name")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if v is not None and not v.strip():
            raise ValueError("must not be blank")
        return v


AddItem = Annotated[
    Union[AddCreditItem, AddTagItem, AddPublisherItem, AddAlbumItem, AddIdentityMemberItem, AddIdentityAliasItem],
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
    processing_status: Optional[int] = None
    source_path: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("media_name")
    @classmethod
    def media_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        return _reject_empty_string(v, "media_name")

    @field_validator("isrc")
    @classmethod
    def isrc_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _ISRC_RE.match(v):
            raise ValueError(
                "ISRC must be 12 characters: 2 country + 3 registrant + 7 digits (e.g. GBAYE0000001)"
            )
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
                raise ValueError(
                    f"bpm must be between {rules['min']} and {rules['max']}"
                )
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
    is_primary: Optional[bool] = None


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


class MergeIdentityItem(BaseModel):
    type: Literal["identity_merge"]
    source_name_id: int
    target_name_id: int


class MergePublisherItem(BaseModel):
    type: Literal["publisher_merge"]
    source_id: int
    target_id: int


class MergeTagItem(BaseModel):
    type: Literal["tag_merge"]
    source_id: int
    target_id: int


class UpdateIdentityItem(BaseModel):
    type: Literal["identity"]
    id: int
    identity_type: Optional[str] = None

    @field_validator("identity_type")
    @classmethod
    def valid_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("person", "group"):
            raise ValueError("identity_type must be 'person' or 'group'")
        return v


UpdateItem = Annotated[
    Union[
        UpdateSongItem,
        UpdateTagEntityItem,
        UpdateSongTagItem,
        UpdateSongAlbumItem,
        UpdateAlbumEntityItem,
        UpdateCreditEntityItem,
        UpdatePublisherEntityItem,
        MergeIdentityItem,
        MergePublisherItem,
        MergeTagItem,
        UpdateIdentityItem,
    ],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Remove items
# ---------------------------------------------------------------------------


class RemoveCreditItem(BaseModel):
    type: Literal["credit"]
    song_id: Optional[int] = None
    album_id: Optional[int] = None
    id: int

    @model_validator(mode="after")
    def exactly_one_target(self) -> "RemoveCreditItem":
        if (self.song_id is None) == (self.album_id is None):
            raise ValueError("exactly one of song_id or album_id must be set")
        return self


class RemoveTagItem(BaseModel):
    type: Literal["tag"]
    song_id: int
    id: int


class RemovePublisherItem(BaseModel):
    type: Literal["publisher"]
    song_id: Optional[int] = None
    album_id: Optional[int] = None
    id: int

    @model_validator(mode="after")
    def exactly_one_target(self) -> "RemovePublisherItem":
        if (self.song_id is None) == (self.album_id is None):
            raise ValueError("exactly one of song_id or album_id must be set")
        return self


class RemoveAlbumItem(BaseModel):
    type: Literal["album"]
    song_id: int
    id: int


class RemoveIdentityMemberItem(BaseModel):
    type: Literal["identity_member"]
    group_id: int
    member_id: int


class RemoveIdentityAliasItem(BaseModel):
    type: Literal["identity_alias"]
    identity_id: int
    name_id: int


RemoveItem = Annotated[
    Union[RemoveCreditItem, RemoveTagItem, RemovePublisherItem, RemoveAlbumItem, RemoveIdentityMemberItem, RemoveIdentityAliasItem],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Delete items (entity-level soft-delete)
# ---------------------------------------------------------------------------


class DeleteSongItem(BaseModel):
    type: Literal["song"]
    id: Optional[int] = None
    unlinked: bool = False
    delete_file: bool = False

    @model_validator(mode="after")
    def id_or_unlinked(self) -> "DeleteSongItem":
        if self.id is None and not self.unlinked:
            raise ValueError("either id or unlinked=True is required")
        return self


class DeleteTagItem(BaseModel):
    type: Literal["tag"]
    id: Optional[int] = None
    unlinked: bool = False

    @model_validator(mode="after")
    def id_or_unlinked(self) -> "DeleteTagItem":
        if self.id is None and not self.unlinked:
            raise ValueError("either id or unlinked=True is required")
        return self


class DeletePublisherItem(BaseModel):
    type: Literal["publisher"]
    id: Optional[int] = None
    unlinked: bool = False

    @model_validator(mode="after")
    def id_or_unlinked(self) -> "DeletePublisherItem":
        if self.id is None and not self.unlinked:
            raise ValueError("either id or unlinked=True is required")
        return self


class DeleteAlbumItem(BaseModel):
    type: Literal["album"]
    id: Optional[int] = None
    unlinked: bool = False

    @model_validator(mode="after")
    def id_or_unlinked(self) -> "DeleteAlbumItem":
        if self.id is None and not self.unlinked:
            raise ValueError("either id or unlinked=True is required")
        return self


class DeleteIdentityItem(BaseModel):
    type: Literal["identity"]
    id: Optional[int] = None
    unlinked: bool = False

    @model_validator(mode="after")
    def id_or_unlinked(self) -> "DeleteIdentityItem":
        if self.id is None and not self.unlinked:
            raise ValueError("either id or unlinked=True is required")
        return self


class DeleteOriginalFileItem(BaseModel):
    type: Literal["original_file"]
    song_id: int


DeleteItem = Annotated[
    Union[
        DeleteSongItem,
        DeleteTagItem,
        DeletePublisherItem,
        DeleteAlbumItem,
        DeleteIdentityItem,
        DeleteOriginalFileItem,
    ],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Top-level request
# ---------------------------------------------------------------------------


class MutationRequest(BaseModel):
    add: Optional[List[AddItem]] = None
    update: Optional[List[UpdateItem]] = None
    remove: Optional[List[RemoveItem]] = None
    delete: Optional[List[DeleteItem]] = None

    @model_validator(mode="after")
    def at_least_one_change(self) -> "MutationRequest":
        if not (self.add or self.update or self.remove or self.delete):
            raise ValueError(
                "request must contain at least one item in add, update, remove, or delete"
            )
        return self
