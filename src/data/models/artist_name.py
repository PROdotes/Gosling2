"""ArtistName Data Model"""
from typing import Optional
from dataclasses import dataclass


@dataclass
class ArtistName:
    """Represents a name owned by an identity."""

    name_id: Optional[int] = None
    owner_identity_id: Optional[int] = None
    display_name: str = ""
    sort_name: Optional[str] = None
    is_primary_name: bool = False
    disambiguation_note: Optional[str] = None

    def __post_init__(self) -> None:
        """Ensure sort_name is set"""
        if self.sort_name is None:
            self.sort_name = self.display_name

    def to_dict(self) -> dict:
        return {
            "name_id": self.name_id,
            "owner_identity_id": self.owner_identity_id,
            "display_name": self.display_name,
            "sort_name": self.sort_name,
            "is_primary_name": self.is_primary_name,
            "disambiguation_note": self.disambiguation_note
        }

    @classmethod
    def from_row(cls, row: tuple) -> 'ArtistName':
        """Create ArtistName from DB row."""
        if not row:
            return None
        return cls(
            name_id=row[0],
            owner_identity_id=row[1],
            display_name=row[2],
            sort_name=row[3],
            is_primary_name=bool(row[4]),
            disambiguation_note=row[5]
        )
