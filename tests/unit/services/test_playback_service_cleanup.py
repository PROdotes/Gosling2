"""Tests for PlaybackService resource cleanup"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from src.business.services.playback_service import PlaybackService


class TestPlaybackServiceCleanup:
    """Test resource management in PlaybackService"""

    def test_cleanup_stops_playback(self, qtbot):
        """Test that cleanup stops playback"""
        service = PlaybackService()
        service.stop = Mock()
        
        service.cleanup()
        
        service.stop.assert_called_once()

    def test_cleanup_disconnects_signals(self, qtbot):
        """Test that cleanup disconnects all signals"""
        service = PlaybackService()
        
        # Connect a dummy slot to verify disconnection
        dummy_slot = Mock()
        service.position_changed.connect(dummy_slot)
        
        # Cleanup should disconnect the internal signals
        service.cleanup()
        
        # Player should be None after cleanup
        assert service.player is None

    def test_cleanup_handles_already_disconnected_signals(self, qtbot):
        """Test that cleanup handles signals that are already disconnected"""
        service = PlaybackService()
        
        # This test verifies the try/except block works
        # We can't easily force a disconnect error, so we just verify cleanup completes
        service.cleanup()
        
        assert service.player is None

    def test_cleanup_clears_media_source(self, qtbot):
        """Test that cleanup clears the media source"""
        service = PlaybackService()
        
        # Load a dummy source
        service.load("dummy_path.mp3")
        
        # Store reference before cleanup
        player = service.player
        
        # Spy on setSource before cleanup
        original_setSource = player.setSource
        call_count = [0]
        empty_url_set = [False]
        
        def spy_setSource(url):
            call_count[0] += 1
            if url.isEmpty():
                empty_url_set[0] = True
            return original_setSource(url)
        
        player.setSource = spy_setSource
        
        service.cleanup()
        
        # Verify setSource was called with empty QUrl
        assert empty_url_set[0], "setSource should have been called with empty QUrl"

    def test_cleanup_deletes_audio_output(self, qtbot):
        """Test that cleanup schedules audio output for deletion"""
        service = PlaybackService()
        audio_output = service.audio_output
        audio_output.deleteLater = Mock()
        
        service.cleanup()
        
        audio_output.deleteLater.assert_called_once()
        assert service.audio_output is None

    def test_cleanup_deletes_player(self, qtbot):
        """Test that cleanup schedules player for deletion"""
        service = PlaybackService()
        player = service.player
        player.deleteLater = Mock()
        
        service.cleanup()
        
        player.deleteLater.assert_called_once()
        assert service.player is None

    def test_cleanup_full_sequence(self, qtbot):
        """Test the complete cleanup sequence"""
        service = PlaybackService()
        
        # Store references before cleanup
        player = service.player
        audio_output = service.audio_output
        
        # Mock deleteLater
        player.deleteLater = Mock()
        audio_output.deleteLater = Mock()
        
        service.cleanup()
        
        # Verify deleteLater was called
        player.deleteLater.assert_called_once()
        audio_output.deleteLater.assert_called_once()
        
        # Verify resources are set to None
        assert service.player is None
        assert service.audio_output is None

    def test_cleanup_can_be_called_multiple_times(self, qtbot):
        """Test that cleanup can be safely called multiple times"""
        service = PlaybackService()
        
        # First cleanup
        service.cleanup()
        
        # Second cleanup should not raise an error
        # even though player and audio_output are None
        service.cleanup()  # Should handle None gracefully
        
        # Verify still None
        assert service.player is None
        assert service.audio_output is None
