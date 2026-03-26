from typing import List, Optional, Dict
from pydantic import BaseModel, computed_field, ConfigDict
from src.models.domain import (
    Album,
    Song,
    SongCredit,
    Tag,
    Publisher,
    AlbumCredit,
    Identity,
    ArtistName,
)


class SongAlbumView(BaseModel):
    """View-model for Album associations."""

    source_id: Optional[int] = None
    album_id: Optional[int] = None
    album_title: str
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    album_type: Optional[str] = None
    release_year: Optional[int] = None
    album_publishers: List[Publisher] = []
    credits: List[AlbumCredit] = []

    @computed_field
    @property
    def display_publisher(self) -> str:
        """Name(s) of the album-level publishers with parent hierarchy."""
        if not self.album_publishers:
            return ""

        display_names = []
        for p in self.album_publishers:
            name = p.name
            if p.parent_name:
                name = f"{name} ({p.parent_name})"
            display_names.append(name)

        return ", ".join(display_names)

    @computed_field
    @property
    def display_title(self) -> str:
        """Standardized presentation including track/disc context."""
        context = ""
        if (self.disc_number or 1) > 1:
            context = f"{self.disc_number}-"

        if self.track_number:
            context += f"{self.track_number:02d} "

        if context:
            return f"[{context.strip()}] {self.album_title}"
        return self.album_title


class SongView(BaseModel):
    """View-model for Song data, including computed presentation fields."""

    # Core Data from Song
    id: Optional[int] = None
    media_name: str
    title: str
    source_path: str
    duration_s: float
    audio_hash: Optional[str] = None
    processing_status: Optional[int] = 0
    is_active: bool = False
    notes: Optional[str] = None
    bpm: Optional[int] = None
    year: Optional[int] = None
    isrc: Optional[str] = None

    # Hydrated Metadata
    credits: List[SongCredit] = []
    albums: List[SongAlbumView] = []
    publishers: List[Publisher] = []
    tags: List[Tag] = []
    raw_tags: Dict[str, List[str]] = {}

    @classmethod
    def from_domain(cls, song: Song) -> "SongView":
        """Factory to create a view-model from a domain model."""
        data = song.model_dump()
        data["title"] = song.title

        # Map domain albums to album views
        data["albums"] = [SongAlbumView(**a.model_dump()) for a in song.albums]
        return cls(**data)

    @computed_field
    @property
    def duration_ms(self) -> int:
        """Legacy compatibility field for API consumers."""
        return int(self.duration_s * 1000)

    @computed_field
    @property
    def formatted_duration(self) -> str:
        """MM:SS formatting for UI displays."""
        if not self.duration_s:
            return "0:00"

        total_seconds = int(self.duration_s)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"

    @computed_field
    @property
    def display_artist(self) -> Optional[str]:
        """
        Joined primary performer names.
        Returns None if no Performer exists.
        STRICT: Never fallback to Composer/Producer/etc.
        """
        if not self.credits:
            return None

        # 1. Filter to Performers only
        performers = [
            c.display_name for c in self.credits if c.role_name == "Performer"
        ]
        if not performers:
            return None

        # 2. Deduplicate while preserving order (avoid 'clever' comprehensions)
        unique_names = []
        for name in performers:
            if name not in unique_names:
                unique_names.append(name)

        if len(unique_names) > 1:
            return ", ".join(unique_names)
        return unique_names[0]

    @computed_field
    @property
    def display_master_publisher(self) -> str:
        """Joined names of the master rights holders with parent hierarchy."""
        if not self.publishers:
            return ""

        display_names = []
        for p in self.publishers:
            name = p.name
            if p.parent_name:
                name = f"{name} ({p.parent_name})"
            display_names.append(name)

        return ", ".join(display_names)

    @computed_field
    @property
    def primary_genre(self) -> Optional[str]:
        """
        Picks the headline genre for the UI badge.
        Only considers tags with category='Genre'.
        Priority:
        1. Genre tag explicitly marked as is_primary=True.
        2. First tag with category 'Genre'.
        """
        if not self.tags:
            return None

        genre_tags = [
            t for t in self.tags if t.category and t.category.lower() == "genre"
        ]

        # 1. Explicit primary Genre tag wins
        for t in genre_tags:
            if t.is_primary:
                return t.name

        # 2. First Genre tag wins if no explicit primary
        if genre_tags:
            return genre_tags[0].name

        return None


class AlbumView(BaseModel):
    """View-model for album directory records."""

    id: Optional[int] = None
    title: str
    album_type: Optional[str] = None
    release_year: Optional[int] = None
    publishers: List[Publisher] = []
    credits: List[AlbumCredit] = []
    songs: List[SongView] = []

    @classmethod
    def from_domain(cls, album: Album) -> "AlbumView":
        """Maps a domain Album to its view-model. Note: excludes 'songs' from base dump but re-attaches hydrated views."""
        data = album.model_dump(exclude={"songs"})
        data["songs"] = [SongView.from_domain(song) for song in album.songs]
        return cls(**data)

    @computed_field
    @property
    def display_publisher(self) -> str:
        if not self.publishers:
            return ""

        display_names = []
        for publisher in self.publishers:
            name = publisher.name
            if publisher.parent_name:
                name = f"{name} ({publisher.parent_name})"
            display_names.append(name)
        return ", ".join(display_names)

    @computed_field
    @property
    def display_artist(self) -> Optional[str]:
        """
        Joined performer names for the album.
        Returns None if no Performer exists.
        STRICT: Never fallback to Composer/Producer/etc.
        """
        if not self.credits:
            return None

        # 1. Performer roles only
        performers = [
            credit.display_name
            for credit in self.credits
            if credit.role_name == "Performer"
        ]
        if not performers:
            return None

        # 2. Simple deduplication while preserving order
        unique_names = []
        for name in performers:
            if name not in unique_names:
                unique_names.append(name)
        return ", ".join(unique_names)

    @computed_field
    @property
    def song_count(self) -> int:
        return len(self.songs)


class IdentityView(BaseModel):
    """View-model for the bidirectional artist tree."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    display_name: Optional[str] = None
    legal_name: Optional[str] = None
    aliases: List[ArtistName] = []  # Can reuse domain model here as it's simple

    # Recursive connections
    members: List["IdentityView"] = []
    groups: List["IdentityView"] = []

    @classmethod
    def from_domain(cls, identity: Identity) -> "IdentityView":
        """Factory to convert a domain Identity tree into a view model."""
        data = identity.model_dump()
        data["members"] = []
        data["groups"] = []

        # Recursive mapping for members
        if identity.members:
            data["members"] = [cls.from_domain(m) for m in identity.members]

        # Recursive mapping for groups
        if identity.groups:
            data["groups"] = [cls.from_domain(g) for g in identity.groups]

        return cls(**data)


class IngestionCheckRequest(BaseModel):
    """Payload for the dry-run ingestion check."""

    file_path: str


class IngestionReportView(BaseModel):
    """The result of a dry-run ingestion check or an actual ingestion attempt."""

    status: str  # NEW, ALREADY_EXISTS, CONFLICT, ERROR
    match_type: Optional[str] = None  # "HASH", "PATH", "METADATA"
    message: Optional[str] = None
    song: Optional[SongView] = None
    
    # Conflict/Ghost Metadata (Populated on 409 CONFLICT)
    ghost_id: Optional[int] = None
    title: Optional[str] = None
    duration_s: Optional[float] = None
    staged_path: Optional[str] = None


class FolderScanRequest(BaseModel):
    """Payload for server-side folder scanning."""

    folder_path: str
    recursive: bool = True


class BatchIngestReport(BaseModel):
    """The result of a batch ingestion operation."""

    total_files: int
    ingested: int
    duplicates: int
    conflicts: int = 0
    errors: int
    results: List[IngestionReportView]


IdentityView.model_rebuild()
SongAlbumView.model_rebuild()
SongView.model_rebuild()
AlbumView.model_rebuild()
IngestionReportView.model_rebuild()
BatchIngestReport.model_rebuild()
