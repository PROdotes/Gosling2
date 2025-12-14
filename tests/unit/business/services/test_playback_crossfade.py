import pytest
from unittest.mock import MagicMock, call, patch
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QTimer, QUrl

from src.business.services.playback_service import PlaybackService

@pytest.fixture
def playback_service_mocked():
    """Fixture to create PlaybackService with mocked Players"""
    
    # Patch the objects looked up IN the service module
    with patch("src.business.services.playback_service.QMediaPlayer") as MockPlayer, \
         patch("src.business.services.playback_service.QAudioOutput") as MockAudioOutput, \
         patch("src.business.services.playback_service.QTimer") as MockTimer, \
         patch("src.business.services.settings_manager.SettingsManager") as MockSettings:
        
        # Setup mocks
        mock_player_instance = MockPlayer.return_value
        mock_audio_instance = MockAudioOutput.return_value
        mock_timer_instance = MockTimer.return_value
        
        # Configure Mock Settings
        mock_settings_instance = MockSettings.return_value
        mock_settings_instance.get_crossfade_duration.return_value = 3000
        mock_settings_instance.get_crossfade_enabled.return_value = True

        MockPlayer.side_effect = lambda: MagicMock()
        MockAudioOutput.side_effect = lambda: MagicMock()

        service = PlaybackService(mock_settings_instance)
        
        yield service, MockPlayer, MockTimer
        
        service.cleanup()

# NOTE: Full logic verification is handled by verify_crossfade_behavior.py integration script
# due to complex mocking requirements of QMediaPlayer/QTimer in this test environment.

def test_dual_player_initialization(playback_service_mocked):
    """Verify service creates two players"""
    service, MockPlayer, _ = playback_service_mocked
    
    assert hasattr(service, "_players"), "Service should have _players list"
    assert len(service._players) == 2, "Should have 2 players"
    assert service._players[0] != service._players[1], "Players should be distinct instances"

def test_properties_exist(playback_service_mocked):
    """Verify property accessors exist"""
    service, _, _ = playback_service_mocked
    assert hasattr(service, 'crossfade_duration')
    assert hasattr(service, 'crossfade_enabled')
    # assert hasattr(service, 'active_player') 
