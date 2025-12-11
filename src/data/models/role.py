"""Role Data Model"""
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class RoleType(Enum):
    """Standard role types"""
    PERFORMER = "Performer"
    COMPOSER = "Composer"
    LYRICIST = "Lyricist"
    PRODUCER = "Producer"


@dataclass
class Role:
    """Represents a contributor role"""

    role_id: Optional[int] = None
    name: str = ""

