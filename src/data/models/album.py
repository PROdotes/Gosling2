from dataclasses import dataclass, field
from typing import Optional, List

from .contributor import Contributor

@dataclass
class Album:
    """Represents a music album."""
    album_id: Optional[int] = None
    title: str = ""
    album_artist: Optional[str] = None  # COMPUTED via repository (M2M), not persisted in Albums table
    album_type: Optional[str] = None  # Single, Album, EP, Compilation
    release_year: Optional[int] = None
    song_count: int = 0  # Runtime statistic
    
    # Relationships (Optional hydration)
    tracks: List['Song'] = field(default_factory=list)
    contributors: List[Contributor] = field(default_factory=list)
    publishers: List[dict] = field(default_factory=list) # [{'id': 1, 'name': 'Label'}]

    @classmethod
    def from_row(cls, row: tuple) -> 'Album':
        """
        Create Album from DB row.
        Expected row: (AlbumID, Title, AlbumType, ReleaseYear, [SongCount])
        NOTE: album_artist is NOT in the row anymore - it must be hydrated separately.
        """
        return cls(
            album_id=row[0],
            title=row[1],
            # album_artist IS NONE by default, must be hydrated via _get_joined_album_artist
            album_type=row[2] if len(row) > 2 else None,
            release_year=row[3] if len(row) > 3 else None,
            song_count=row[4] if len(row) > 4 else 0
        )

    def to_dict(self):
        return {
            "album_id": self.album_id,
            "title": self.title,
            "album_artist": self.album_artist,
            "album_type": self.album_type,
            "release_year": self.release_year
        }

