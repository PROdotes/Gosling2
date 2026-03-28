from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """The base class for all domain values."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class MediaSource(DomainModel):
    """The base record for any airable file in the Gosling library."""

    id: Optional[int] = None
    type_id: Optional[int] = None
    media_name: str  # The "Title" in the database
    source_path: str
    duration_s: float
    audio_hash: Optional[str] = None
    processing_status: int
    is_active: bool = False
    notes: Optional[str] = None

    @property
    def duration_ms(self) -> int:
        """Legacy compatibility property."""
        return int(self.duration_s * 1000)


class SongCredit(DomainModel):
    """The bridge between a Track and an Actor (Alias)."""

    credit_id: Optional[int] = None
    source_id: Optional[int] = None
    name_id: Optional[int] = None
    identity_id: Optional[int] = None  # The parent Identity ID
    role_id: Optional[int] = None  # 1=Performer, 2=Composer, 3=Producer, etc.
    role_name: str  # Hydrated from Roles table
    display_name: str  # Hydrated from ArtistNames table
    is_primary: bool = False  # Is this the Identity's primary stage name?


class AlbumCredit(DomainModel):
    """The bridge between an Album and an Actor (Alias)."""

    album_id: Optional[int] = None
    name_id: Optional[int] = None
    identity_id: Optional[int] = None
    role_id: Optional[int] = None
    role_name: str
    display_name: str
    is_primary: bool = False


class Publisher(DomainModel):
    """The copyright owner or distributor."""

    id: Optional[int] = None
    name: str
    parent_id: Optional[int] = None
    parent_name: Optional[str] = None
    sub_publishers: List["Publisher"] = []


class Tag(DomainModel):
    """A descriptive metadata marker (Genre, Mood, Era, etc.)."""

    id: Optional[int] = None
    name: str
    category: Optional[str] = None
    is_primary: bool = False


class SongAlbum(DomainModel):
    """The link between a song and an album."""

    source_id: Optional[int] = None
    album_id: Optional[int] = None
    is_primary: bool = True
    track_number: Optional[int] = None
    disc_number: Optional[int] = None

    # Resolved Metadata
    album_title: str
    album_type: Optional[str] = None
    release_year: Optional[int] = None
    album_publishers: List[Publisher] = []
    credits: List[AlbumCredit] = []


class Album(DomainModel):
    """A first-class album directory record."""

    id: Optional[int] = None
    title: str
    album_type: Optional[str] = None
    release_year: Optional[int] = None
    publishers: List[Publisher] = []
    credits: List[AlbumCredit] = []
    songs: List["Song"] = []


class ArtistName(DomainModel):
    """A specific stage name or alias for an Identity."""

    id: int
    display_name: str
    is_primary: bool = False


class Identity(DomainModel):
    """A resolved artist entity (Person or Group)."""

    id: int
    type: str  # person, group, placeholder
    display_name: Optional[str] = None
    legal_name: Optional[str] = None

    # The Tree Connections
    aliases: List[ArtistName] = []  # Formerly List[str]
    members: List["Identity"] = []  # If type='group', the constituent persons
    groups: List["Identity"] = []  # If type='person', the parent groups


class Song(MediaSource):
    """A music-specific record inheriting from MediaSource."""

    bpm: Optional[int] = None
    year: Optional[int] = None
    isrc: Optional[str] = None

    credits: List[SongCredit] = []
    albums: List[SongAlbum] = []
    publishers: List[Publisher] = []
    tags: List[Tag] = []

    # Storage for every raw ID3 frame found that wasn't explicitly mapped.
    # Format: { "TIT2": ["Title"], "TXXX:STATUS": ["Ready"] }
    raw_tags: Dict[str, List[str]] = {}

    @property
    def title(self) -> str:
        """Domain-level title alias for media_name."""
        return self.media_name


class AuditAction(DomainModel):
    """A high-level event log (IMPORT, DELETE, etc.)."""

    id: Optional[int] = None
    action_type: str
    target_table: Optional[str] = None
    target_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: Optional[str] = None
    user_id: Optional[str] = None
    batch_id: Optional[str] = None


class AuditChange(DomainModel):
    """A field-level modification log."""

    id: Optional[int] = None
    table_name: str
    record_id: str
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: Optional[str] = None
    batch_id: Optional[str] = None


class DeletedRecord(DomainModel):
    """A JSON snapshot of a purged record."""

    id: Optional[int] = None
    table_name: str
    record_id: str
    snapshot: str
    deleted_at: Optional[str] = None
    restored_at: Optional[str] = None
    batch_id: Optional[str] = None


# Recursive model rebuilding for Pydantic v2
Publisher.model_rebuild()
Identity.model_rebuild()
Album.model_rebuild()
SongAlbum.model_rebuild()
Song.model_rebuild()
