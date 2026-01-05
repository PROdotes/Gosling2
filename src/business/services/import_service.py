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

    def import_single_file(self, file_path: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Import a single file into the library.
        Handle WAV conversion interactivity if needed.
        
        Returns:
            Tuple of (Success, SID, ErrorMessage)
        """
        try:
            # 0. Handle WAV conversion
            if file_path.lower().endswith('.wav'):
                if self.conversion_service:
                    converted_path = self.conversion_service.prompt_and_convert(file_path)
                    if converted_path:
                        file_path = converted_path # Proceed with the new MP3
                    else:
                        return False, None, f"Skipped WAV conversion: {os.path.basename(file_path)}"
                else:
                    return False, None, "Conversion service unavailable for WAV file."

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

                # 7. Apply Initial Status Tag: "Unprocessed" (The Truth)
                self.library_service.set_song_unprocessed(file_id, True)
                
                # 8. Log high-level action
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
        valid_extensions = ('.mp3', '.wav', '.zip')
        discovery_list = []
        
        for path in paths:
            if os.path.isfile(path):
                lower_path = path.lower()
                if lower_path.endswith('.zip') and zipfile.is_zipfile(path):
                    # Handle In-Place ZIP Explosion
                    try:
                        target_dir = os.path.dirname(path)
                        processing_succeeded = False
                        
                        with zipfile.ZipFile(path, 'r') as zip_ref:
                            all_names = zip_ref.namelist()
                            
                            # A. Collision Check using Transactional Logic
                            # If ANY file in the zip already exists on disk, we abort the entire zip.
                            collision_found = False
                            for name in all_names:
                                full_target_path = os.path.join(target_dir, name)
                                if os.path.exists(full_target_path):
                                    if "gosling_nested_" not in full_target_path: # Allow recursion to pass
                                        logger.warning(f"Skipping ZIP {path}: Collision detected with existing file {name}")
                                        collision_found = True
                                        break
                            
                            if collision_found:
                                continue # Skip this zip
                            
                            # B. Atomic Extraction
                            try:
                                zip_ref.extractall(target_dir)
                            except Exception as extract_err:
                                logger.error(f"Failed to extract ZIP {path}: {extract_err}. Attempting rollback.")
                                # Rollback: Delete any files we might have just created (best effort)
                                for name in all_names:
                                    full_target_path = os.path.join(target_dir, name)
                                    if os.path.exists(full_target_path):
                                        try:
                                            os.remove(full_target_path)
                                        except:
                                            pass
                                continue # Skip this zip
                            
                            # C. Add extracted files to discovery list
                            for name in all_names:
                                full_extracted_path = os.path.join(target_dir, name)
                                
                                # Recursive check for the extracted file
                                if os.path.isdir(full_extracted_path):
                                     discovery_list.extend(self.scan_directory_recursive(full_extracted_path))
                                elif os.path.isfile(full_extracted_path):
                                     f_lower = full_extracted_path.lower()
                                     if f_lower.endswith(valid_extensions) and not f_lower.endswith('.zip'):
                                         discovery_list.append(full_extracted_path)
                                         
                            # Mark success for deletion logic
                            processing_succeeded = True

                        # D. ZIP Cleanup (Safe: File handle closed)
                        if processing_succeeded and self.settings_manager.get_delete_zip_after_import():
                            try:
                                os.remove(path)
                                logger.info(f"Deleted source ZIP after successful extraction: {path}")
                            except Exception as del_err:
                                logger.warning(f"Failed to delete source ZIP {path}: {del_err}")
                        
                    except Exception as e:
                        logger.error(f"Failed to explode zip {path}: {e}")
                
                elif lower_path.endswith(valid_extensions):
                    discovery_list.append(path)
                    
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        lower_file = file.lower()
                        
                        if lower_file.endswith('.zip') and zipfile.is_zipfile(full_path):
                             # Recursive logic for nested zips?
                             # Reuse the file logic
                             temp_dir = tempfile.mkdtemp(prefix="gosling_nested_")
                             try:
                                 with zipfile.ZipFile(full_path, 'r') as zip_ref:
                                     zip_ref.extractall(temp_dir)
                                 discovery_list.extend(self.scan_directory_recursive(temp_dir))
                             except Exception as e:
                                 logger.error(f"Failed to explode nested zip {full_path}: {e}")
                        
                        elif lower_file.endswith(valid_extensions):
                            discovery_list.append(full_path)
        
        return discovery_list
