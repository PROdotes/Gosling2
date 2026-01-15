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
    
    # Emitted when a batch of imports is finished: (success_list, failure_list)
    finished_batch = pyqtSignal(list, list)
    
    # Emitted on critical failure
    error = pyqtSignal(str)

    def __init__(self, import_service: ImportService, files: list, conversion_policy: dict = None):
        super().__init__()
        self.import_service = import_service
        self.files = files
        self.conversion_policy = conversion_policy
        self._is_running = True

    def stop(self):
        """Request the worker to stop processing."""
        self._is_running = False

    def run(self):
        """Execute the import process in the background."""
        if not self.files:
            self.finished_batch.emit([], [])
            return

        total = len(self.files)
        success_list = []
        failure_list = []

        for i, file_path in enumerate(self.files):
            if not self._is_running:
                break

            import_success, sid, err, final_path = self.import_service.import_single_file(file_path, conversion_policy=self.conversion_policy)
            
            if import_success:
                success_list.append({
                    'path': final_path,
                    'id': sid
                })
            else:
                failure_list.append({
                    'path': final_path,
                    'error': err
                })
            
            # Emit progress update (Legacy int interface for LCD)
            self.progress.emit(i + 1, total, file_path, import_success)

        self.finished_batch.emit(success_list, failure_list)
