"""
ExportService - Writes Song objects to ID3 files and database.

Counterpart to ImportService (which reads from files into the app).
This service receives READY Song objects (already validated, coerced, modified)
and persists them to their source files and the database.

Does NOT:
- Fetch songs from DB
- Apply field transformations
- Make UX decisions
- Touch status tags (Unprocessed is DB-only)
- Handle orphan albums
"""

from dataclasses import dataclass, field
from typing import List, Optional, Callable
from ..services.metadata_service import MetadataService
from ..services.library_service import LibraryService
from ...data.models.song import Song
from ...core import logger


@dataclass
class ExportResult:
    """Result of exporting a single song."""
    success: bool
    error: Optional[str] = None
    dry_run: bool = False


@dataclass
class BatchExportResult:
    """Result of exporting multiple songs."""
    success_count: int = 0
    error_count: int = 0
    errors: List[str] = field(default_factory=list)


class ExportService:
    """
    Exports application metadata changes back to source files (ID3 tags).
    
    Usage:
        result = export_service.export_song(song)
        batch_result = export_service.export_songs(songs, progress_callback=on_progress)
    """
    
    def __init__(self, 
                 metadata_service: MetadataService,
                 library_service: LibraryService):
        self.metadata_service = metadata_service
        self.library_service = library_service
    
    def export_song(self, song: Song, dry_run: bool = False, write_tags: bool = True, batch_id: Optional[str] = None, **kwargs) -> ExportResult:
        """
        Export a single song to database and optionally ID3.
        
        Args:
            song: The Song object with metadata to write.
            dry_run: If True, validate but don't actually write.
            write_tags: If True, also write metadata to the physical file.
        """
        if not song.path:
            return ExportResult(success=False, error="Song has no file path")
        
        if dry_run:
            return ExportResult(success=True, dry_run=True)
        
        try:
            # Step 1: Update database (The source of truth)
            if not self.library_service.update_song(song, batch_id=batch_id, **kwargs):
                return ExportResult(success=False, error=f"Database update failed for {song.path}")
            
            # Step 2: Write ID3 tags (The reflection)
            if write_tags:
                if not self.metadata_service.write_tags(song):
                    return ExportResult(
                        success=False, 
                        error=f"Database saved, but failed to write ID3 tags to {song.path} (File may be missing or locked)"
                    )
            
            return ExportResult(success=True)
            
        except Exception as e:
            logger.error(f"Export failed for {song.path}: {e}")
            return ExportResult(success=False, error=f"Error exporting {song.name or 'file'}:\n{e}")
    
