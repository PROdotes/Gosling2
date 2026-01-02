
import pytest
from unittest.mock import MagicMock
from src.presentation.workers.import_worker import ImportWorker

class TestImportWorker:
    @pytest.fixture
    def mock_service(self):
        return MagicMock()

    def test_worker_signals_success(self, qtbot, mock_service):
        """Worker should emit progress and checkmark status for each file."""
        files = ["f1.mp3", "f2.mp3"]
        mock_service.import_single_file.return_value = (True, 101, None)
        
        worker = ImportWorker(mock_service, files)
        
        with qtbot.waitSignals([worker.progress, worker.finished_batch], timeout=5000):
            worker.start()

        assert mock_service.import_single_file.call_count == 2
        # finished_batch emitted (success_count, error_count)
        # We can't easily check final signal args with waitSignals, 
        # but we verified start/end flow.

    def test_worker_handles_errors(self, qtbot, mock_service):
        """Worker should report failures and continue to next file."""
        files = ["good.mp3", "bad.mp3"]
        # Cycle through success and failure
        mock_service.import_single_file.side_effect = [
            (True, 1, None),
            (False, None, "Duplicate")
        ]
        
        worker = ImportWorker(mock_service, files)
        
        results = []
        worker.progress.connect(lambda i, t, f, s: results.append(s))
        
        with qtbot.waitSignal(worker.finished_batch):
            worker.start()
            
        assert results == [True, False]

    def test_worker_stop_request(self, qtbot, mock_service):
        """Worker should honor the stop flag."""
        files = ["f1.mp3", "f2.mp3", "f3.mp3"]
        mock_service.import_single_file.return_value = (True, 1, None)
        
        worker = ImportWorker(mock_service, files)
        worker.stop() # Stop immediately
        
        with qtbot.waitSignal(worker.finished_batch):
            worker.start()
            
        # Should stop before first import or after check
        # Depending on loop timing, but call_count should be at most 1 
        # in this specific stop-before-start scenario.
        assert mock_service.import_single_file.call_count <= 1
