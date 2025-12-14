"""Tests for PlaybackService resource cleanup"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from src.business.services.playback_service import PlaybackService


class TestPlaybackServiceCleanup:
    """Test resource management in PlaybackService"""

    @pytest.fixture(autouse=True)
    def mock_dependencies(self):
        with patch('src.business.services.settings_manager.SettingsManager'), \
             patch('src.business.services.playback_service.QMediaPlayer', side_effect=lambda: MagicMock()) as MockPlayer, \
             patch('src.business.services.playback_service.QAudioOutput', side_effect=lambda: MagicMock()) as MockAudio:
            yield

    def test_cleanup_stops_playback(self, qtbot):
        """Test that cleanup stops playback on all players"""
        service = PlaybackService()
        
        # Mock stop on all players
        for player in service._players:
            player.stop = Mock()
            
        service.cleanup()
        
        for player in service._players:
            player.stop.assert_called_once()

    def test_cleanup_clears_media_source(self, qtbot):
        """Test that cleanup clears the media source on all players"""
        service = PlaybackService()
        
        # Mock setSource
        for player in service._players:
            player.setSource = Mock()
            
        service.cleanup()
        
        for player in service._players:
            # Should look for empty QUrl calls
            # QUrl() creates an empty url
            call_args = player.setSource.call_args[0][0]
            assert call_args.isEmpty()

    def test_cleanup_deletes_resources(self, qtbot):
        """Test that cleanup schedules resources for deletion"""
        service = PlaybackService()
        
        # Spy on deleteLater
        for player in service._players:
            player.deleteLater = Mock()
        for audio in service._audio_outputs:
            audio.deleteLater = Mock()
            
        service.cleanup()
        
        # Verify calls
        for player in service._players:
            player.deleteLater.assert_called_once()
        for audio in service._audio_outputs:
            audio.deleteLater.assert_called_once()
            
        # Verify lists cleared
        assert len(service._players) == 0
        assert len(service._audio_outputs) == 0

    def test_cleanup_can_be_called_multiple_times(self, qtbot):
        """Test that cleanup can be safely called multiple times"""
        service = PlaybackService()
        
        service.cleanup()
        service.cleanup() # Second call
        
        assert len(service._players) == 0
        assert len(service._audio_outputs) == 0
