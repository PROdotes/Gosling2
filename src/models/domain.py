from typing import Optional
from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """The base class for all domain values."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class MediaSource(DomainModel):
    """The base record for any airable file in the Prodo library."""

    id: int
    type_id: int
    source_path: str
    duration_ms: int
    audio_hash: Optional[str] = None
    processing_status: int = 0
    is_active: bool = True
    notes: Optional[str] = None


class SongCredit(DomainModel):
    """The bridge between a Track and an Actor (Alias)."""

    source_id: int
    name_id: int
    role_id: int  # 1=Performer, 2=Composer, 3=Producer, etc.
    display_name: str  # Hydrated from ArtistNames table


class Song(MediaSource):
    """A music-specific record inheriting from MediaSource."""

    title: str
    bpm: Optional[int] = None
    year: Optional[int] = None
    isrc: Optional[str] = None
    album_id: Optional[int] = None
    credits: list[SongCredit] = []
