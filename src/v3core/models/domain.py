from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict

class DomainModel(BaseModel):
    """Base model for all v3core domain entities with strict validation."""
    model_config = ConfigDict(extra="forbid", frozen=True)

class MediaSource(DomainModel):
    """The base record for any airable file (Song, Report, Sweeper, etc.)."""
    id: int
    type_id: int  # 1=Song, 2=Report, etc.
    source_path: str
    duration_ms: int
    audio_hash: Optional[str] = None
    processing_status: int = 0  # 0=New, 1=Done, 2=Error
    is_active: bool = True
    notes: Optional[str] = None

class Song(MediaSource):
    """A music-specific record inheriting from MediaSource."""
    title: str
    bpm: Optional[int] = None
    year: Optional[int] = None
    isrc: Optional[str] = None
    album_id: Optional[int] = None

class Identity(DomainModel):
    """The persistent human or group entity (The 'Actor')."""
    id: int
    identity_type: Literal["person", "group", "collective"]
    display_name: str
    legal_name: Optional[str] = None

class ArtistName(DomainModel):
    """A specific alias or 'sticker' owned by an Identity."""
    id: int
    owner_identity_id: int
    display_name: str
    is_primary: bool = False

class IdentityRelation(DomainModel):
    """The link between two identities (e.g., Member of Group)."""
    parent_id: int  # The Group / Collective
    child_id: int   # The Person / Member
    role_name: Optional[str] = "member"

class SongCredit(DomainModel):
    """The bridge between a Track and an Actor (Alias)."""
    source_id: int
    name_id: int
    role_id: int  # 1=Performer, 2=Composer, 3=Producer, etc.
