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

