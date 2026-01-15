"""
Import service for audio files.

Handles the business logic of importing files into the library,
including hashing, duplicate detection, metadata extraction,
and initial status tagging.
"""

from typing import Optional, Tuple, List
import os
import zipfile
import tempfile
from ...data.models.song import Song
from ...utils.audio_hash import calculate_audio_hash
from ...core import logger
from .library_service import LibraryService
from .metadata_service import MetadataService
from .duplicate_scanner import DuplicateScannerService
from .conversion_service import ConversionService
from .settings_manager import SettingsManager

class ImportService:
    """Service for managing file imports into the Gosling2 library."""
    
    def __init__(
        self, 
        library_service: LibraryService, 
        metadata_service: MetadataService, 
        duplicate_scanner: DuplicateScannerService,
        settings_manager: SettingsManager,
        conversion_service: Optional[ConversionService] = None
    ):
        self.library_service = library_service
        self.metadata_service = metadata_service
        self.duplicate_scanner = duplicate_scanner
        self.settings_manager = settings_manager
        self.conversion_service = conversion_service

    def import_single_file(self, file_path: str, conversion_policy: dict = None) -> Tuple[bool, Optional[int], Optional[str], str]:
        """
        Import a single file into the library.
        Handle WAV conversion interactivity or via policy.
        
        conversion_policy: {'convert': bool, 'delete_original': bool} (Optional)
        
        Returns:
            Tuple of (Success, SID, ErrorMessage, FinalFilePath)
        """
        try:
            # -1. Safety Check: Is this EXACT file already in the library?
            # If so, we must prevent the user from "deleting duplicate" as it would delete the master copy.
            existing_record = self.library_service.get_song_by_path(file_path)
            if existing_record:
                return False, existing_record.source_id, "ALREADY_IMPORTED: File is already tracked in library", file_path

            # 0. Handle WAV conversion (Optional via Policy)
            if file_path.lower().endswith('.wav') and self.conversion_service and conversion_policy:
                if conversion_policy.get('convert', False):
                    converted_path = self.conversion_service.convert_wav_to_mp3(file_path)
                    should_delete = conversion_policy.get('delete_original', False)
                    
                    if converted_path:
                        if should_delete and os.path.exists(converted_path):
                             try: os.remove(file_path)
                             except: pass
                        file_path = converted_path # Proceed with the new MP3
                    else:
                        # Conversion failed, but we still import the original WAV
                        pass

            # 1. Calculate Audio Hash
            audio_hash = calculate_audio_hash(file_path)
            
            # 2. Check for Hash-based duplicates
            existing_by_hash = self.duplicate_scanner.check_audio_duplicate(audio_hash)
            if existing_by_hash:
                return False, None, f"Duplicate audio found: {os.path.basename(file_path)}", file_path

            # 3. Extract Metadata (Enforce Source of Truth)
            # Use source_id=0 as temporary placeholder
            temp_song = self.metadata_service.extract_metadata(file_path, source_id=0)
            
            # 4. Check for ISRC-based duplicates
            if temp_song.isrc:
                existing_by_isrc = self.duplicate_scanner.check_isrc_duplicate(temp_song.isrc)
                if existing_by_isrc:
                    return False, None, f"Duplicate ISRC found: {temp_song.isrc}", file_path

            # 5. Create Database Record (Consolidated Insert)
            temp_song.audio_hash = audio_hash
            
            # USER 614: Toggle is_active False on import (Staging Mode)
            temp_song.is_active = False
            
            # T-Default: Use configured album type for auto-created albums
            album_type = self.settings_manager.get_default_album_type()
            file_id = self.library_service.add_song(temp_song, album_type=album_type)
            
            if file_id:
                # Update local ID for subsequent steps
                temp_song.source_id = file_id

                # 7. Apply Initial Status Tag: "Unprocessed" (The Truth)
                self.library_service.set_song_unprocessed(file_id, True)
                
                # 8. Log high-level action
                self.library_service.log_action(
                    "IMPORT", "Songs", file_id, 
                    {"path": file_path, "title": temp_song.name}
                )

                # Bake it into the ID3 (Reflection)
                if self.settings_manager.get_write_tags():
                    self.metadata_service.write_tags(temp_song)
                
                return True, file_id, None, file_path
            else:
                return False, None, "Failed to create database record", file_path
                
        except Exception as e:
            logger.error(f"Error importing {file_path}: {e}", exc_info=True)
            return False, None, str(e), file_path



    def scan_directory_recursive(self, folder_path: str) -> List[str]:
        """Discovery phase: Find all valid audio files in a directory."""
        return self.collect_import_list([folder_path])

    def collect_import_list(self, paths: List[str]) -> List[str]:
        """
        Takes a list of paths (files or folders) and returns a flat list of 
        all supported audio files found. ZIPs are indexed via VFS (Virtual Paths).
        """
        from ...core.vfs import VFS
        valid_extensions = ('.mp3', '.wav')
        discovery_list = []
        
        for path in paths:
            if os.path.isfile(path):
                lower_path = path.lower()
                if lower_path.endswith('.zip'):
                    # T-90: VFS Mode - Do NOT explode, just index.
                    discovery_list.extend(VFS.list_zip_contents(path, audio_only=True))
                elif lower_path.endswith(valid_extensions):
                    discovery_list.append(path)
                    
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        lower_file = file.lower()
                        
                        if lower_file.endswith('.zip'):
                            # Recursive indexing for ZIPs inside folders
                            discovery_list.extend(VFS.list_zip_contents(full_path, audio_only=True))
                        elif lower_file.endswith(valid_extensions):
                            discovery_list.append(full_path)
        
        return list(dict.fromkeys(discovery_list)) # Dedupe results

    def delete_file(self, file_path: str) -> bool:
        """Safely delete a file from disk (e.g. for failed imports)."""
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
        return False

