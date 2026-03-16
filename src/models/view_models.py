from typing import List, Optional
from pydantic import BaseModel, computed_field
from src.models.domain import Song, SongCredit, SongAlbum, Tag, Publisher


class SongView(BaseModel):
    """View-model for Song data, including computed presentation fields."""

    # Core Data from Song
    id: int
    media_name: str
    title: str
    source_path: str
    duration_ms: int
    audio_hash: Optional[str] = None
    processing_status: int = 1
    is_active: bool = False
    notes: Optional[str] = None
    bpm: Optional[int] = None
    year: Optional[int] = None
    isrc: Optional[str] = None

    # Hydrated Metadata
    credits: List[SongCredit] = []
    albums: List[SongAlbum] = []
    publishers: List[Publisher] = []
    tags: List[Tag] = []

    @classmethod
    def from_domain(cls, song: Song) -> "SongView":
        """Factory to create a view-model from a domain model."""
        data = song.model_dump()
        data["title"] = song.title
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
        """Heuristic for the UI: First tag in 'Genre' category."""
        genres = [t.name for t in self.tags if t.category == "Genre"]
        if genres:
            return genres[0]
        return self.tags[0].name if self.tags else None
