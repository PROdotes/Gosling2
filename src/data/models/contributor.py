"""Contributor Data Model"""
from typing import Optional
from dataclasses import dataclass


@dataclass
class Contributor:
    """Represents a contributor (artist, composer, etc.)"""

    contributor_id: Optional[int] = None
    name: str = ""
    sort_name: Optional[str] = None
    type: str = "person"  # 'person' or 'group' - matches DB CHECK constraint
    matched_alias: Optional[str] = None

    def __post_init__(self) -> None:
        """Ensure sort_name is set"""
        if self.sort_name is None:
            self.sort_name = self.name

    def to_dict(self):
        return {
            "contributor_id": self.contributor_id,
            "name": self.name,
            "sort_name": self.sort_name,
            "type": self.type
        }

    @classmethod
    def from_row(cls, row: tuple) -> 'Contributor':
        """Create Contributor from DB row."""
        if not row:
            return None
        return cls(
            contributor_id=row[0],
            name=row[1],
            sort_name=row[2],
            type=row[3]
        )

