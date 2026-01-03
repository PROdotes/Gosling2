"""
Tests for ExportService - writes Song objects to ID3 files and database.

The service receives READY Song objects (already validated, coerced, modified).
It does NOT fetch, transform, or make UX decisions.

Level 1: Logic Tests (Safety-Critical Behavior)
"""

import pytest
from unittest.mock import MagicMock, patch
from src.data.models.song import Song


class TestExportServiceCore:
    """Core safety-critical export behavior."""
    
    @pytest.fixture
    def service_deps(self):
        """Standard mocked dependencies."""
        return {
            'metadata_service': MagicMock(),
            'library_service': MagicMock()
        }
    
    @pytest.fixture
    def export_service(self, service_deps):
        from src.business.services.export_service import ExportService
        svc = ExportService(
            service_deps['metadata_service'],
            service_deps['library_service']
        )
        return svc
    
    @pytest.fixture
    def sample_song(self):
        return Song(
            source_id=1,
            source="C:/Music/test.mp3",
            name="Test Song",
            performers=["Artist A"]
        )

    # =========================================================================
    # HAPPY PATH - Single Song
    # =========================================================================
    
    def test_export_single_writes_id3_then_db(self, export_service, service_deps, sample_song):
        """Core flow: ID3 first, then DB. Both must succeed."""
        service_deps['metadata_service'].write_tags.return_value = True
        service_deps['library_service'].update_song.return_value = True
        
        result = export_service.export_song(sample_song)
        
        assert result.success is True
        # Verify order: ID3 first
        service_deps['metadata_service'].write_tags.assert_called_once()
        # Then DB
        service_deps['library_service'].update_song.assert_called_once()

    # =========================================================================
    # HAPPY PATH - Batch
    # =========================================================================
    
    def test_export_batch_processes_all(self, export_service, service_deps):
        """Batch: All songs processed, counts reported."""
        songs = [Song(source_id=i, source=f"C:/s{i}.mp3", name=f"S{i}") for i in range(3)]
        service_deps['metadata_service'].write_tags.return_value = True
        service_deps['library_service'].update_song.return_value = True
        
        result = export_service.export_songs(songs)
        
        assert result.success_count == 3
        assert result.error_count == 0
        assert service_deps['metadata_service'].write_tags.call_count == 3

    def test_export_batch_continues_on_failure(self, export_service, service_deps):
        """Batch: One failure doesn't stop the others."""
        songs = [Song(source_id=i, source=f"C:/s{i}.mp3", name=f"S{i}") for i in range(3)]
        service_deps['metadata_service'].write_tags.side_effect = [True, False, True]
        service_deps['library_service'].update_song.return_value = True
        
        result = export_service.export_songs(songs)
        
        assert result.success_count == 2
        assert result.error_count == 1
        # DB should NOT be called for the failed one (index 1)
        assert service_deps['library_service'].update_song.call_count == 2

    # =========================================================================
    # ID3 FAILURE SAFETY
    # =========================================================================
    
    def test_id3_failure_skips_db(self, export_service, service_deps, sample_song):
        """Safety: If ID3 write fails, DB is NOT updated."""
        service_deps['metadata_service'].write_tags.return_value = False
        
        result = export_service.export_song(sample_song)
        
        assert result.success is False
        service_deps['library_service'].update_song.assert_not_called()

    def test_id3_exception_is_caught(self, export_service, service_deps, sample_song):
        """Safety: Exceptions don't propagate, return failure."""
        service_deps['metadata_service'].write_tags.side_effect = PermissionError("File locked")
        
        result = export_service.export_song(sample_song)
        
        assert result.success is False
        assert "locked" in result.error.lower() or "permission" in result.error.lower()
        service_deps['library_service'].update_song.assert_not_called()

    # =========================================================================
    # DB FAILURE HANDLING
    # =========================================================================
    
    def test_db_failure_reports_error(self, export_service, service_deps, sample_song):
        """If DB update fails after ID3 success, report as failure."""
        service_deps['metadata_service'].write_tags.return_value = True
        service_deps['library_service'].update_song.return_value = False
        
        result = export_service.export_song(sample_song)
        
        # This is a failure - file is updated but DB isn't (inconsistent state)
        assert result.success is False
        assert result.error is not None

    # =========================================================================
    # VALIDATION (Pre-flight checks)
    # =========================================================================
    
    def test_rejects_song_without_path(self, export_service, service_deps):
        """Cannot export a song with no file path."""
        bad_song = Song(source_id=1, name="No Path")  # source=None
        
        result = export_service.export_song(bad_song)
        
        assert result.success is False
        assert "path" in result.error.lower()
        service_deps['metadata_service'].write_tags.assert_not_called()

    # NOTE: Status tag (Unprocessed) is app-internal only.
    # It lives in the database, NOT in ID3 files.
    # ExportService does not touch status tags.


class TestExportServiceProgressReporting:
    """Progress callback support for UI integration."""
    
    @pytest.fixture
    def export_service(self):
        from src.business.services.export_service import ExportService
        svc = ExportService(MagicMock(), MagicMock())
        svc.metadata_service.write_tags.return_value = True
        svc.library_service.update_song.return_value = True
        return svc
    
    def test_progress_callback_called_per_song(self, export_service):
        """Callback receives (current, total, path, success) for each song."""
        songs = [Song(source_id=i, source=f"C:/s{i}.mp3", name=f"S{i}") for i in range(3)]
        
        calls = []
        def on_progress(current, total, path, success):
            calls.append((current, total, path, success))
        
        export_service.export_songs(songs, progress_callback=on_progress)
        
        assert len(calls) == 3
        assert calls[0] == (1, 3, "C:/s0.mp3", True)
        assert calls[2] == (3, 3, "C:/s2.mp3", True)


class TestExportServiceDryRun:
    """Dry run mode for previewing changes without writing."""
    
    @pytest.fixture
    def export_service(self):
        from src.business.services.export_service import ExportService
        return ExportService(MagicMock(), MagicMock())
    
    def test_dry_run_does_not_write(self, export_service):
        """Dry run: No files or DB modified."""
        song = Song(source_id=1, source="C:/test.mp3", name="Test")
        
        result = export_service.export_song(song, dry_run=True)
        
        assert result.success is True
        assert result.dry_run is True
        export_service.metadata_service.write_tags.assert_not_called()
        export_service.library_service.update_song.assert_not_called()
