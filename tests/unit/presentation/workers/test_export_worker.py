"""
Tests for ExportWorker - QThread wrapper for async export operations.

Level 1: Logic Tests (Happy Path + Basic Behavior)
"""

import pytest
from unittest.mock import MagicMock
from src.presentation.workers.export_worker import ExportWorker
from src.business.services.export_service import ExportResult, BatchExportResult
from src.data.models.song import Song


class TestExportWorker:
    
    @pytest.fixture
    def mock_service(self):
        svc = MagicMock()
        svc.export_song.return_value = ExportResult(success=True)
        return svc
    
    @pytest.fixture
    def sample_songs(self):
        return [
            Song(source_id=i, source=f"C:/s{i}.mp3", name=f"Song {i}")
            for i in range(3)
        ]

    def test_worker_signals_success(self, qtbot, mock_service, sample_songs):
        """Worker should emit progress and finished signals for each song."""
        worker = ExportWorker(mock_service, sample_songs)
        
        with qtbot.waitSignals([worker.progress, worker.finished_batch], timeout=5000):
            worker.start()

        assert mock_service.export_song.call_count == 3

    def test_worker_emits_correct_counts(self, qtbot, mock_service, sample_songs):
        """finished_batch should emit correct success/error counts."""
        results = []
        
        worker = ExportWorker(mock_service, sample_songs)
        worker.finished_batch.connect(lambda s, e: results.append((s, e)))
        
        with qtbot.waitSignal(worker.finished_batch, timeout=5000):
            worker.start()
        
        assert results == [(3, 0)]  # 3 success, 0 error

    def test_worker_handles_errors(self, qtbot, mock_service, sample_songs):
        """Worker should report failures and continue to next song."""
        # Middle one fails
        mock_service.export_song.side_effect = [
            ExportResult(success=True),
            ExportResult(success=False, error="Failed"),
            ExportResult(success=True),
        ]
        
        progress_results = []
        worker = ExportWorker(mock_service, sample_songs)
        worker.progress.connect(lambda i, t, p, s: progress_results.append(s))
        
        with qtbot.waitSignal(worker.finished_batch, timeout=5000):
            worker.start()
            
        assert progress_results == [True, False, True]

    def test_worker_stop_request(self, qtbot, mock_service, sample_songs):
        """Worker should honor the stop flag."""
        worker = ExportWorker(mock_service, sample_songs)
        worker.stop()  # Stop immediately
        
        with qtbot.waitSignal(worker.finished_batch, timeout=5000):
            worker.start()
            
        # Should stop before processing all (or none)
        assert mock_service.export_song.call_count <= 1

    def test_worker_result_ready_signal(self, qtbot, mock_service, sample_songs):
        """result_ready should emit full BatchExportResult."""
        results = []
        
        worker = ExportWorker(mock_service, sample_songs)
        worker.result_ready.connect(lambda r: results.append(r))
        
        with qtbot.waitSignal(worker.result_ready, timeout=5000):
            worker.start()
        
        assert len(results) == 1
        assert results[0].success_count == 3
        assert results[0].error_count == 0

    def test_worker_empty_list(self, qtbot, mock_service):
        """Worker handles empty song list gracefully."""
        worker = ExportWorker(mock_service, [])
        
        results = []
        worker.finished_batch.connect(lambda s, e: results.append((s, e)))
        
        with qtbot.waitSignal(worker.finished_batch, timeout=5000):
            worker.start()
        
        assert results == [(0, 0)]
        mock_service.export_song.assert_not_called()
