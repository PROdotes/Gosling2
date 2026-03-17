from typing import List, Optional, Dict
from pydantic import BaseModel, computed_field
from src.models.domain import Song, SongCredit, Tag, Publisher, AlbumCredit


class SongAlbumView(BaseModel):
    """View-model for Album associations."""

    album_title: str
    track_number: Optional[int] = None
    disc_number: Optional[int] = 1
    album_type: Optional[str] = None
    release_year: Optional[int] = None
    publishers: List[Publisher] = []
    credits: List[AlbumCredit] = []

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
    duration_ms: int
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
    def formatted_duration(self) -> str:
        """MM:SS formatting for UI displays."""
        if not self.duration_ms:
            return "0:00"

        total_seconds = int(self.duration_ms / 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"

    @computed_field
    @property
    def display_artist(self) -> Optional[str]:
        """Provides the joined primary performer names."""
        if not self.credits:
            return None

        performers = [
            c.display_name for c in self.credits if c.role_name == "Performer"
        ]
        if performers:
            unique_names = []
            [unique_names.append(n) for n in performers if n not in unique_names]

            if len(unique_names) > 1:
                return ", ".join(unique_names)
            return unique_names[0]

        return self.credits[0].display_name if self.credits else None

    @computed_field
    @property
    def primary_genre(self) -> Optional[str]:
        """
        Picks the headline genre for the UI badge.
        Priority:
        1. Any tag explicitly marked as is_primary=True.
        2. First tag with category 'Genre'.
        """
        if not self.tags:
            return None

        # 1. Explicit primary marker wins everything
        for t in self.tags:
            if t.is_primary:
                return t.name

        # 2. First 'Genre' tag wins if no explicit primary
        for t in self.tags:
            if t.category and t.category.lower() == "genre":
                return t.name

        return None
