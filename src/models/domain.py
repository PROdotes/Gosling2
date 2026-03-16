from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """The base class for all domain values."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class MediaSource(DomainModel):
    """The base record for any airable file in the Gosling library."""

    id: int
    type_id: int
    media_name: str  # The "Title" in the database
    source_path: str
    duration_ms: int
    audio_hash: Optional[str] = None
    processing_status: int = 1
    is_active: bool = False
    notes: Optional[str] = None


class SongCredit(DomainModel):
    """The bridge between a Track and an Actor (Alias)."""

    source_id: int
    name_id: int
    role_id: int  # 1=Performer, 2=Composer, 3=Producer, etc.
    role_name: str  # Hydrated from Roles table
    display_name: str  # Hydrated from ArtistNames table
    is_primary: bool = False  # Is this the Identity's primary stage name?


class Publisher(DomainModel):
    """The copyright owner or distributor."""

    id: int
    name: str
    parent_id: Optional[int] = None


class Tag(DomainModel):
    """A descriptive metadata marker (Genre, Mood, Era, etc.)."""

    id: int
    name: str
    category: Optional[str] = None


class SongAlbum(DomainModel):
    """The link between a song and an album."""

    source_id: int
    album_id: int
    is_primary: bool = True
    track_number: Optional[int] = None
    disc_number: Optional[int] = 1
    track_publisher_id: Optional[int] = None

    # Resolved Metadata
    album_title: str
    album_type: Optional[str] = None
    release_year: Optional[int] = None
    publishers: List[Publisher] = []


class Song(MediaSource):
    """A music-specific record inheriting from MediaSource."""

    bpm: Optional[int] = None
    year: Optional[int] = None
    isrc: Optional[str] = None

    credits: List[SongCredit] = []
    albums: List[SongAlbum] = []
    publishers: List[Publisher] = []
    tags: List[Tag] = []

    @property
    def title(self) -> str:
        """Domain-level title alias for media_name."""
        return self.media_name
