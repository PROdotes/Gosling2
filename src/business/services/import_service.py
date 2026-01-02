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
        # Bridge to tag repository for status tagging
        self.tag_repo = library_service.tag_repo if hasattr(library_service, 'tag_repo') else None

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

            # 5. Create Database Record
            file_id = self.library_service.add_file(file_path)
            if file_id:
                # Update ID and Hash on the song object
                temp_song.source_id = file_id
                temp_song.audio_hash = audio_hash
                
                # Save full metadata to DB
                self.library_service.update_song(temp_song)

                # 6. Apply Initial Status Tag: "Unprocessed"
                # This replaces the previous "Unverified" as per the new workflow
                if self.tag_repo:
                    self.tag_repo.add_tag_to_source(file_id, "Unprocessed", category="Status")
                
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
