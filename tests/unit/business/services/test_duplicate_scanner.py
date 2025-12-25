"""
Unit tests for DuplicateScannerService.

Tests duplicate detection logic for ISRC and audio hash matching.
Per PROPOSAL_DUPLICATE_DETECTION.md Phase 2.

Per TESTING.md:
- Logic tests (this file): Duplicate detection, quality comparison
- Integration tests: End-to-end import workflow
"""

import pytest
from src.business.services.duplicate_scanner import DuplicateScannerService
from src.data.models.song import Song


@pytest.fixture
def scanner(mock_library_service):
    """Create a DuplicateScannerService instance for testing."""
    return DuplicateScannerService(mock_library_service)


@pytest.fixture
def existing_song():
    """Create a sample existing song in the database."""
    return Song(
        source_id=1,
        source="C:\\existing.mp3",
        name="Existing Song",
        isrc="USAB12345678",
        audio_hash="abc123def456",
        duration=180.0
    )


class TestISRCDuplicateDetection:
    """Test ISRC-based duplicate detection."""
    
    def test_no_duplicate_when_isrc_different(self, scanner, existing_song):
        """Different ISRC should not be detected as duplicate."""
        new_song = Song(
            source="C:\\new.mp3",
            name="New Song",
            isrc="GBUM71234567",  # Different ISRC
            duration=180.0
        )
        
        # Configure mock to return None (no song found)
        scanner.library_service.find_by_isrc.return_value = None

        
        result = scanner.check_isrc_duplicate(new_song.isrc)
        
        assert result is None, "Should not find duplicate with different ISRC"
    
    def test_duplicate_detected_with_same_isrc(self, scanner, existing_song):
        """Same ISRC should be detected as duplicate."""
        # Mock library service to return existing song
        scanner.library_service.find_by_isrc.return_value = existing_song
        
        result = scanner.check_isrc_duplicate("USAB12345678")
        
        assert result is not None
        assert result.source_id == existing_song.source_id
    
    def test_isrc_sanitization_before_check(self, scanner, existing_song):
        """ISRC should be sanitized before duplicate check."""
        scanner.library_service.find_by_isrc.return_value = existing_song
        
        # Try with dashes and lowercase
        result = scanner.check_isrc_duplicate("us-ab1-23-45678")
        
        # Should find the duplicate (sanitized to USAB12345678)
        scanner.library_service.find_by_isrc.assert_called_with("USAB12345678")
    
    def test_empty_isrc_returns_none(self, scanner):
        """Empty or None ISRC should return None (no duplicate)."""
        assert scanner.check_isrc_duplicate(None) is None
        assert scanner.check_isrc_duplicate("") is None
        assert scanner.check_isrc_duplicate("   ") is None


class TestAudioHashDuplicateDetection:
    """Test audio hash-based duplicate detection."""
    
    def test_no_duplicate_when_hash_different(self, scanner):
        """Different audio hash should not be detected as duplicate."""
        scanner.library_service.find_by_audio_hash.return_value = None
        
        result = scanner.check_audio_duplicate("xyz789")
        
        assert result is None
    
    def test_duplicate_detected_with_same_hash(self, scanner, existing_song):
        """Same audio hash should be detected as duplicate."""
        scanner.library_service.find_by_audio_hash.return_value = existing_song
        
        result = scanner.check_audio_duplicate("abc123def456")
        
        assert result is not None
        assert result.audio_hash == existing_song.audio_hash
    
    def test_empty_hash_returns_none(self, scanner):
        """Empty or None hash should return None (no duplicate)."""
        assert scanner.check_audio_duplicate(None) is None
        assert scanner.check_audio_duplicate("") is None


class TestImportEvaluation:
    """Test the evaluate_import logic."""
    
    def test_audio_hash_duplicate_returns_skip(self, scanner, existing_song):
        """Audio hash duplicate should return SKIP_HASH."""
        scanner.library_service.find_by_audio_hash.return_value = existing_song
        
        action, song = scanner.evaluate_import("abc123def456", "ISRC_NEW")
        
        assert action == 'SKIP_HASH'
        assert song == existing_song
    
    def test_isrc_duplicate_returns_skip(self, scanner, existing_song):
        """ISRC duplicate should return SKIP_ISRC."""
        # Ensure audio hash check passes (returns None)
        scanner.library_service.find_by_audio_hash.return_value = None
        scanner.library_service.find_by_isrc.return_value = existing_song
        
        action, song = scanner.evaluate_import("new_hash", "USAB12345678")
        
        assert action == 'SKIP_ISRC'
        assert song == existing_song
        
    def test_no_duplicate_returns_import(self, scanner):
        """No duplicate should return IMPORT."""
        scanner.library_service.find_by_audio_hash.return_value = None
        scanner.library_service.find_by_isrc.return_value = None
        
        action, song = scanner.evaluate_import("new_hash", "new_isrc")
        
        assert action == 'IMPORT'
        assert song is None
        
    def test_higher_quality_duplicate_still_skips(self, scanner, existing_song):
        """
        Even if quality is better, current logic dictates SKIP.
        (Future Feature: Prompt for upgrade)
        """
        scanner.library_service.find_by_audio_hash.return_value = existing_song
        
        # Hypothetical high bitrate file, same hash (unlikely but logic holds)
        action, song = scanner.evaluate_import("abc123def456", "ISRC_NEW")
        
        assert action == 'SKIP_HASH'
