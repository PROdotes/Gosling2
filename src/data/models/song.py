from typing import Optional, List
from dataclasses import dataclass, field
from .media_source import MediaSource


@dataclass
class Song(MediaSource):
    """Represents a song with its metadata"""

    # Specific fields
    is_done: bool = False
    isrc: Optional[str] = None
    bpm: Optional[int] = None

    recording_year: Optional[int] = None
    unified_artist: Optional[str] = None
    album: Optional[str] = None
    album_id: Optional[int] = None # Added for precise linking (T-46)
    album_artist: Optional[str] = None  # From TPE2 (Album Artist)
    publisher: Optional[object] = None # Union[str, List[str]]
    genre: Optional[str] = None
    mood: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    
    # Relationships
    performers: List[str] = field(default_factory=list)
    composers: List[str] = field(default_factory=list)
    lyricists: List[str] = field(default_factory=list)
    producers: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    
    # Multi-Album Support (T-22)
    # List of dicts: {album_id, title, year, track_number, is_primary}
    releases: List[dict] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: tuple) -> 'Song':
        """
        Create a Song from a Yellberus query result row.
        
        Flow:
        1. Yellberus converts row to tagged tuples: [(value, frame_or_tag), ...]
        2. Song looks up each tag in id3_frames.json to find the field name
        3. Song sets attributes directly via setattr
        """
        from src.core import yellberus
        import json
        import os
        
        from src.business.services.metadata_service import MetadataService
        id3_frames = MetadataService._get_id3_map()
        
        # Map known aliases (JSON uses user-friendly names, Song uses internal names)
        attr_map = {
            'file_id': 'source_id',
            'path': 'source', 
            'title': 'name',
        }
        
        # Get tagged tuples from Yellberus
        tagged_data = yellberus.row_to_tagged_tuples(row)
        
        # Create Song with defaults
        song = cls()
        
        for value, tag in tagged_data:
            if tag.startswith('_'):
                # Local field: strip underscore
                field_name = tag[1:]
            else:
                # ID3 frame: look up in JSON
                frame_info = id3_frames.get(tag, {})
                if isinstance(frame_info, dict) and 'field' in frame_info:
                    field_name = frame_info['field']
                else:
                    yellberus.yell(f"Unknown ID3 frame '{tag}' not in id3_frames.json")
                    continue
            
            # Apply alias mapping
            attr = attr_map.get(field_name, field_name)
            
            # Set attribute directly (skip None to let defaults apply)
            if value is not None and hasattr(song, attr):
                setattr(song, attr, value)
            elif value is not None:
                yellberus.yell(f"Song model missing attribute '{attr}' for tag '{tag}'")
        
        return song

    def __post_init__(self) -> None:
        """Set type_id and normalize lists."""
        self.type_id = 1
        if self.performers is None: self.performers = []
        if self.composers is None: self.composers = []
        if self.lyricists is None: self.lyricists = []
        if self.producers is None: self.producers = []
        if self.groups is None: self.groups = []

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
    def year(self) -> Optional[int]:
        """Alias for recording_year"""
        return self.recording_year

    @year.setter
    def year(self, value: Optional[int]):
        self.recording_year = value

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

