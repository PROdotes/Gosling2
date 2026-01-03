"""
Worker thread for background file exports.
Supports progress reporting and result collection.

Counterpart to ImportWorker.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from ...business.services.export_service import ExportService, BatchExportResult
from ...data.models.song import Song
from typing import List


class ExportWorker(QThread):
    """
    Worker thread that processes a list of songs for export.
    Communicates with the UI via signals.
    """
    
    # Emitted for each song processed: (current_index, total_count, file_path, success)
    progress = pyqtSignal(int, int, str, bool)
    
    # Emitted when batch is finished: (success_count, error_count)
    finished_batch = pyqtSignal(int, int)
    
    # Emitted with full result object when done
    result_ready = pyqtSignal(object)  # BatchExportResult
    
    # Emitted on critical failure
    error = pyqtSignal(str)

    def __init__(self, export_service: ExportService, songs: List[Song]):
        super().__init__()
        self.export_service = export_service
        self.songs = songs
        self._is_running = True

    def stop(self):
        """Request the worker to stop processing."""
        self._is_running = False

    def run(self):
        """Execute the export process in the background."""
        if not self.songs:
            self.finished_batch.emit(0, 0)
            self.result_ready.emit(BatchExportResult())
            return

        total = len(self.songs)
        success_count = 0
        error_count = 0
        errors = []

        for i, song in enumerate(self.songs, start=1):
            if not self._is_running:
                break

            result = self.export_service.export_song(song)
            
            if result.success:
                success_count += 1
            else:
                error_count += 1
                errors.append(result.error or f"Unknown error for {song.path}")
            
            # Emit progress update
            self.progress.emit(i, total, song.path or "unknown", result.success)

        batch_result = BatchExportResult(
            success_count=success_count,
            error_count=error_count,
            errors=errors
        )
        
        self.finished_batch.emit(success_count, error_count)
        self.result_ready.emit(batch_result)
