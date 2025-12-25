"""MediaSource Data Model"""
from typing import Optional
from dataclasses import dataclass


@dataclass
class MediaSource:
    """Base model for all media sources (Songs, Streams, etc.)"""
    
    source_id: Optional[int] = None
    type_id: int = 1  # Default to Song
    name: Optional[str] = None
    source: Optional[str] = None
    duration: Optional[float] = None
    audio_hash: Optional[str] = None  # Hash of MP3 audio frames (excludes ID3 tags)
    notes: Optional[str] = None
    is_active: bool = True
