"""
Duplicate detection service for audio files.

Provides ISRC-based and audio hash-based duplicate detection.
Per PROPOSAL_DUPLICATE_DETECTION.md Phase 2.
"""

from typing import Optional
from src.data.models.song import Song
from src.utils.validation import sanitize_isrc


class DuplicateScannerService:
    """
    Service for detecting duplicate audio files.
    
    Supports two detection methods:
    1. ISRC matching (metadata-based)
    2. Audio hash matching (content-based)
    """
    
    def __init__(self, library_service):
        """
        Initialize the duplicate scanner.
        
        Args:
            library_service: Service for querying the library database
        """
        self.library_service = library_service
    
    def check_isrc_duplicate(self, isrc: Optional[str]) -> Optional[Song]:
        """
        Check if a song with the given ISRC already exists in the library.
        
        The ISRC is sanitized before checking (dashes/spaces removed, uppercased).
        
        Args:
            isrc: ISRC code to check (can have dashes, will be sanitized)
            
        Returns:
            Existing Song if duplicate found, None otherwise
            
        Examples:
            >>> scanner.check_isrc_duplicate("US-AB1-23-45678")
            <Song: existing_song.mp3>
            >>> scanner.check_isrc_duplicate("GB-UM7-12-34567")
            None
        """
        if not isrc or not isrc.strip():
            return None
        
        # Sanitize ISRC (remove dashes, spaces, uppercase)
        sanitized = sanitize_isrc(isrc)
        
        if not sanitized:
            return None
        
        # Query library for existing song with this ISRC
        return self.library_service.find_by_isrc(sanitized)
    
    def check_audio_duplicate(self, audio_hash: Optional[str]) -> Optional[Song]:
        """
        Check if a song with the given audio hash already exists in the library.
        
        Args:
            audio_hash: SHA256 hash of audio frames (64-character hex string)
            
        Returns:
            Existing Song if duplicate found, None otherwise
            
        Examples:
            >>> scanner.check_audio_duplicate("abc123def456...")
            <Song: existing_song.mp3>
            >>> scanner.check_audio_duplicate("xyz789...")
            None
        """
        if not audio_hash or not audio_hash.strip():
            return None
        
        # Query library for existing song with this audio hash
        return self.library_service.find_by_audio_hash(audio_hash)
    
    def evaluate_import(self, audio_hash: str, isrc: Optional[str]) -> tuple[str, Optional[Song]]:
        """
        Evaluate whether to import a file based on duplicate checks.
        
        Args:
            audio_hash: The calculated audio hash
            isrc: The ISRC (if available)
            
        Returns:
            Tuple (Action, ExistingSong)
            Action can be: 'IMPORT', 'SKIP_HASH', 'SKIP_ISRC'
            ExistingSong is the song that caused the collision (or None)
        """
        # 1. Check Audio Hash (Strongest duplicate signal)
        existing_by_hash = self.check_audio_duplicate(audio_hash)
        if existing_by_hash:
            return 'SKIP_HASH', existing_by_hash
            
        # 2. Check ISRC (Metadata equivalent)
        existing_by_isrc = self.check_isrc_duplicate(isrc)
        if existing_by_isrc:
            return 'SKIP_ISRC', existing_by_isrc
            
        return 'IMPORT', None
