"""Song Data Model"""
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class Song:
    """Represents a song with its metadata"""

    file_id: Optional[int] = None
    path: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[float] = None
    bpm: Optional[int] = None
    performers: List[str] = field(default_factory=list)
    composers: List[str] = field(default_factory=list)
    lyricists: List[str] = field(default_factory=list)
    producers: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Ensure lists are initialized properly"""
        if self.performers is None:
            self.performers = []
        if self.composers is None:
            self.composers = []
        if self.lyricists is None:
            self.lyricists = []
        if self.producers is None:
            self.producers = []
        if self.groups is None:
            self.groups = []

    def get_display_artists(self) -> str:
        """Get formatted artists for display"""
        if self.performers:
            return ', '.join(self.performers)
        return 'Unknown Artist'

    def get_display_title(self) -> str:
        """Get formatted title for display"""
        return self.title or 'Unknown Title'

    def get_formatted_duration(self) -> str:
        """Get duration formatted as mm:ss"""
        if self.duration is None:
            return "00:00"
        minutes, seconds = divmod(int(self.duration), 60)
        return f"{minutes:02d}:{seconds:02d}"

