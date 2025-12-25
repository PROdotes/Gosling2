import pytest
from unittest.mock import MagicMock
from src.business.services.duplicate_scanner import DuplicateScannerService
from src.data.models.song import Song

class TestImportWorkflowIntegration:
    """
    Integration tests for duplicate detection workflow.
    Validates logical flow: Import -> Hash/ISRC Check -> Decision.
    Per PROPOSAL_DUPLICATE_DETECTION.md Phase 4b (Integration Tests).
    """

    @pytest.fixture
    def mock_library_service(self):
        service = MagicMock()
        service.find_by_isrc.return_value = None
        service.find_by_audio_hash.return_value = None
        return service

    @pytest.fixture
    def scanner(self, mock_library_service):
        return DuplicateScannerService(mock_library_service)

    def test_import_different_files(self, scanner, mock_library_service):
        """
        Scenario: Import different files.
        Result: Both imported successfully (Action: IMPORT).
        """
        # File 1 check
        action1, existing1 = scanner.evaluate_import("hashA", "ISRC A")
        assert action1 == 'IMPORT'
        assert existing1 is None

        # File 2 check
        action2, existing2 = scanner.evaluate_import("hashB", "ISRC B")
        assert action2 == 'IMPORT'
        assert existing2 is None

    def test_import_same_file_twice(self, scanner, mock_library_service):
        """
        Scenario: Import same file twice.
        Result: Second import auto-skipped due to audio hash match.
        """
        # Setup: Library "already has" the song
        existing_song = MagicMock(spec=Song)
        existing_song.name = "Existing Song"
        mock_library_service.find_by_audio_hash.return_value = existing_song
        
        # Action
        action, existing = scanner.evaluate_import("hashA", "ISRC A")
        
        # Assert
        assert action == 'SKIP_HASH'
        assert existing == existing_song

    def test_import_same_audio_different_metadata(self, scanner, mock_library_service):
        """
        Scenario: Import same audio with different metadata (ISRC/Tags).
        Result: Detected as duplicate via hash.
        """
        # Setup: Library has existing song with same hash
        existing_song = MagicMock(spec=Song)
        existing_song.name = "Early Version"
        mock_library_service.find_by_audio_hash.return_value = existing_song
        
        # Input: Same hash, different ISRC
        action, existing = scanner.evaluate_import("hashA", "DIFFERENT_ISRC")
        
        # Assert
        assert action == 'SKIP_HASH'
        assert existing == existing_song

    def test_import_matching_isrc_different_audio(self, scanner, mock_library_service):
        """
        Scenario: Import file with matching ISRC but different audio (e.g. remastered).
        Result: Auto-skipped due to ISRC match (Tier 1 check).
        """
        # Setup: Hash check fails (no match), but ISRC check finds song
        mock_library_service.find_by_audio_hash.return_value = None
        
        existing_song = MagicMock(spec=Song)
        existing_song.name = "Original Master"
        mock_library_service.find_by_isrc.return_value = existing_song
        
        # Input
        action, existing = scanner.evaluate_import("new_remaster_hash", "US-MATCH-12345")
        
        # Assert
        assert action == 'SKIP_ISRC'
        assert existing == existing_song
        # Verify sanitization logic was implicitly used by service (mock call arg check)
        mock_library_service.find_by_isrc.assert_called_with("USMATCH12345")

    def test_import_invalid_isrc(self, scanner, mock_library_service):
        """
        Scenario: Import file with invalid ISRC.
        Result: ISRC check skipped/failed, proceeds to Import (if hash doesn't match).
        """
        # Setup: No matches
        mock_library_service.find_by_audio_hash.return_value = None
        mock_library_service.find_by_isrc.return_value = None
        
        # Input: Invalid ISRC
        action, existing = scanner.evaluate_import("hashA", "INVALID_ISRC_FORMAT")
        
        # Assert
        assert action == 'IMPORT'
        # Should not have queried DB with invalid ISRC (sanitization returns empty)
        # DuplicateScanner.check_isrc_duplicate returns None if sanitize fails
        # So it shouldn't call find_by_isrc with the raw invalid string, 
        # but implementation details of check_isrc_duplicate might strictly NOT call DB if sanitized is empty.
        # Let's verify that assumption.
        # sanitize_isrc("INVALID_ISRC_FORMAT") -> "INVALIDISRCFORMAT" (just uppercased/stripped).
        # Wait, sanitize_isrc changes format, but does it VALIDATE?
        # duplicate_scanner.py -> check_isrc_duplicate:
        #   sanitized = sanitize_isrc(isrc)
        #   if not sanitized: return None
        #   return library_service.find_by_isrc(sanitized)
        # It DOES query DB even if format is weird ("INVALIDISRCFORMAT").
        # The PROPOSAL said "Import file with invalid ISRC → Imported, ISRC validation warning logged".
        # Logic: If DB doesn't have "INVALIDISRCFORMAT", it returns None, so IMPORT.
        # This test ensures it doesn't crash or falsely flag.
