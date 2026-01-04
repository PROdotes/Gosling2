from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Album:
    """Represents a music album."""
    album_id: Optional[int] = None
    title: str = ""
    album_artist: Optional[str] = None  # For disambiguation (TPE2)
    album_type: Optional[str] = None  # Single, Album, EP, Compilation
    release_year: Optional[int] = None
    song_count: int = 0  # Runtime statistic
    
    # Relationships (Optional hydration)
    tracks: List['Song'] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: tuple) -> 'Album':
        """
        Create Album from DB row.
        Expected row: (AlbumID, Title, AlbumArtist, AlbumType, ReleaseYear, [SongCount])
        """
        return cls(
            album_id=row[0],
            title=row[1],
            album_artist=row[2] if len(row) > 2 else None,
            album_type=row[3] if len(row) > 3 else None,
            release_year=row[4] if len(row) > 4 else None,
            song_count=row[5] if len(row) > 5 else 0
        )

    def to_dict(self):
        return {
            "album_id": self.album_id,
            "title": self.title,
            "album_artist": self.album_artist,
            "album_type": self.album_type,
            "release_year": self.release_year
        }

