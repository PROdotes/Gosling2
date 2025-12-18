"""Song Data Model"""
from typing import Optional, List
from dataclasses import dataclass, field
from .media_source import MediaSource


@dataclass
class Song(MediaSource):
    """Represents a song with its metadata"""

    # Inherited fields: source_id, type_id, name, source, duration, ...
    
    # Specific fields
    is_done: bool = False
    isrc: Optional[str] = None
    bpm: Optional[int] = None
    recording_year: Optional[int] = None
    
    # Relationships
    performers: List[str] = field(default_factory=list)
    composers: List[str] = field(default_factory=list)
    lyricists: List[str] = field(default_factory=list)
    producers: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Ensure lists are initialized properly"""
        # Ensure type_id is set to Song (1)
        self.type_id = 1
        
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

    @property
    def title(self) -> Optional[str]:
        """Alias for name for backward compatibility"""
        return self.name

    @title.setter
    def title(self, value: Optional[str]):
        """Alias for name for backward compatibility"""
        self.name = value

    @property
    def path(self) -> Optional[str]:
        """Alias for source for backward compatibility"""
        return self.source

    @path.setter
    def path(self, value: Optional[str]):
        """Alias for source for backward compatibility"""
        self.source = value

    @property
    def file_id(self) -> Optional[int]:
        """Alias for source_id for backward compatibility"""
        return self.source_id

    @file_id.setter
    def file_id(self, value: Optional[int]):
        """Alias for source_id for backward compatibility"""
        self.source_id = value

    def get_display_performers(self) -> str:
        """Get formatted performers for display"""
        if self.performers:
            return ', '.join(self.performers)
        return 'Unknown Performer'

    def get_display_title(self) -> str:
        """Get formatted title for display"""
        return self.name or 'Unknown Title'

    @property
    def formatted_duration(self) -> str:
        """Get duration formatted as mm:ss"""
        return self.get_formatted_duration()

    def get_formatted_duration(self) -> str:
        """Get duration formatted as mm:ss"""
        if self.duration is None:
            return "00:00"
        minutes, seconds = divmod(int(self.duration), 60)
        return f"{minutes:02d}:{seconds:02d}"

