from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Album:
    """Represents a music album."""
    album_id: Optional[int] = None
    title: str = ""
    album_type: Optional[str] = None  # Single, Album, EP, Compilation
    release_year: Optional[int] = None
    
    # Relationships (Optional hydration)
    tracks: List['Song'] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: tuple) -> 'Album':
        """
        Create Album from DB row.
        Expected row: (AlbumID, Title, AlbumType, ReleaseYear)
        """
        return cls(
            album_id=row[0],
            title=row[1],
            album_type=row[2],
            release_year=row[3]
        )
