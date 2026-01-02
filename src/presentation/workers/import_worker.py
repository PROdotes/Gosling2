"""
Worker thread for background file imports.
Supports progress reporting and result collection.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from ...business.services.import_service import ImportService


class ImportWorker(QThread):
    """
    Worker thread that processes a list of files for import.
    Communicates with the UI via signals.
    """
    
    # Emitted for each file processed: (current_index, total_count, file_name, success)
    progress = pyqtSignal(int, int, str, bool)
    
    # Emitted when a batch of imports is finished: (success_count, error_count)
    finished_batch = pyqtSignal(int, int)
    
    # Emitted on critical failure
    error = pyqtSignal(str)

    def __init__(self, import_service: ImportService, files: list):
        super().__init__()
        self.import_service = import_service
        self.files = files
        self._is_running = True

    def stop(self):
        """Request the worker to stop processing."""
        self._is_running = False

    def run(self):
        """Execute the import process in the background."""
        if not self.files:
            self.finished_batch.emit(0, 0)
            return

        total = len(self.files)
        success_count = 0
        error_count = 0

        for i, file_path in enumerate(self.files):
            if not self._is_running:
                break

            import_success, sid, err = self.import_service.import_single_file(file_path)
            
            if import_success:
                success_count += 1
            else:
                error_count += 1
            
            # Emit progress update
            self.progress.emit(i + 1, total, file_path, import_success)

        self.finished_batch.emit(success_count, error_count)
