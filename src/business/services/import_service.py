"""
Import service for audio files.

Handles the business logic of importing files into the library,
including hashing, duplicate detection, metadata extraction,
and initial status tagging.
"""

from typing import Optional, Tuple, List
import os
from ...data.models.song import Song
from ...utils.audio_hash import calculate_audio_hash
from ...core import logger
from .library_service import LibraryService
from .metadata_service import MetadataService
from .duplicate_scanner import DuplicateScannerService


class ImportService:
    """Service for managing file imports into the Gosling2 library."""
    
    def __init__(
        self, 
        library_service: LibraryService, 
        metadata_service: MetadataService, 
        duplicate_scanner: DuplicateScannerService
    ):
        self.library_service = library_service
        self.metadata_service = metadata_service
        self.duplicate_scanner = duplicate_scanner

    def import_single_file(self, file_path: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Import a single file into the library.
        
        Returns:
            Tuple of (Success, SID, ErrorMessage)
        """
        try:
            # 1. Calculate Audio Hash
            audio_hash = calculate_audio_hash(file_path)
            
            # 2. Check for Hash-based duplicates
            existing_by_hash = self.duplicate_scanner.check_audio_duplicate(audio_hash)
            if existing_by_hash:
                return False, None, f"Duplicate audio found: {os.path.basename(file_path)}"

            # 3. Extract Metadata (Enforce Source of Truth)
            # Use source_id=0 as temporary placeholder
            temp_song = self.metadata_service.extract_metadata(file_path, source_id=0)
            
            # 4. Check for ISRC-based duplicates
            if temp_song.isrc:
                existing_by_isrc = self.duplicate_scanner.check_isrc_duplicate(temp_song.isrc)
                if existing_by_isrc:
                    return False, None, f"Duplicate ISRC found: {temp_song.isrc}"

            # 5. Create Database Record (Consolidated Insert)
            temp_song.audio_hash = audio_hash
            file_id = self.library_service.add_song(temp_song)
            
            if file_id:
                # Update local ID for subsequent steps
                temp_song.source_id = file_id

                # 6. Apply Initial Status Tag: "Unprocessed" (The Truth)
                self.library_service.set_song_unprocessed(file_id, True)
                
                # 7. Log high-level action
                self.library_service.log_action(
                    "IMPORT", "Songs", file_id, 
                    {"path": file_path, "title": temp_song.name}
                )

                # Bake it into the ID3
                self.metadata_service.write_tags(temp_song)
                
                return True, file_id, None
            else:
                return False, None, "Failed to create database record"
                
        except Exception as e:
            logger.error(f"Error importing {file_path}: {e}", exc_info=True)
            return False, None, str(e)

    def scan_directory_recursive(self, folder_path: str) -> List[str]:
        """Discovery phase: Find all valid audio files in a directory."""
        return self.collect_import_list([folder_path])

    def collect_import_list(self, paths: List[str]) -> List[str]:
        """
        Takes a list of paths (files or folders) and returns a flat list of 
        all supported audio files found.
        """
        valid_extensions = ('.mp3', '.flac', '.wav', '.m4a')
        discovery_list = []
        
        for path in paths:
            if os.path.isfile(path):
                if path.lower().endswith(valid_extensions):
                    discovery_list.append(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith(valid_extensions):
                            discovery_list.append(os.path.join(root, file))
        
        return discovery_list
