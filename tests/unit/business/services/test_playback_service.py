"""Unit tests for PlaybackService"""
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from src.business.services.playback_service import PlaybackService


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for tests"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestPlaybackService:
    """Test cases for PlaybackService"""

    @pytest.fixture
    def service(self, qapp):
        """Create a playback service instance with mocked player"""
        with patch('src.business.services.settings_manager.SettingsManager') as MockSettingsManager, \
             patch('src.business.services.playback_service.QMediaPlayer') as mock_player_cls, \
             patch('src.business.services.playback_service.QAudioOutput') as mock_audio_cls:
            
            mock_player = MagicMock()
            mock_audio = MagicMock()
            
            mock_player_cls.return_value = mock_player
            mock_audio_cls.return_value = mock_audio
            
            # Ensure Players are distinct for checking list usage
            mock_player_cls.side_effect = lambda: MagicMock()
            mock_audio_cls.side_effect = lambda: MagicMock()

            mock_settings_instance = MockSettingsManager.return_value
            service = PlaybackService(mock_settings_instance)
            
            return service

    def test_service_creation(self, service):
        """Test creating a playback service"""
        assert service.active_player is not None
        assert service.active_audio is not None
        # Check internal lists
        assert len(service._players) == 2

    def test_set_volume(self, service):
        """Test setting volume"""
        service._settings.get_volume.return_value = 50
        service.set_volume(0.5)
        # Should call setVolume on active audio output
        service.active_audio.setVolume.assert_called_with(0.5)

    def test_get_volume(self, service):
        """Test getting current volume"""
        # We need to mock settings to return volume
        service._settings.get_volume.return_value = 70
        assert service.get_volume() == 0.7

    def test_player_controls(self, service):
        """Test play, pause, stop calls"""
        service.play()
        service.active_player.play.assert_called_once()
        
        service.pause()
        service.active_player.pause.assert_called_once()
        
        service.stop()
        service.active_player.stop.assert_called_once()

    def test_playlist_management_flow(self, service):
        """Test playlist navigation logic"""
        playlist = ["song1.mp3", "song2.mp3", "song3.mp3"]
        service.set_playlist(playlist)
        
        assert service.get_playlist() == playlist
        assert service.get_current_index() == -1

        # Play first song
        with patch.object(service, 'load') as mock_load:
            # play_at_index might call load/play
            service.play_at_index(0)
            mock_load.assert_called_with("song1.mp3")
            assert service.get_current_index() == 0
            # load calls stop_crossfade which might affect player state

        # Play next
        # play_next calls crossfade_to
        with patch.object(service, 'crossfade_to') as mock_fade:
            service.play_next()
            mock_fade.assert_called_with("song2.mp3")
            assert service.get_current_index() == 1

        # Play next
        with patch.object(service, 'crossfade_to') as mock_fade:
            service.play_next()
            mock_fade.assert_called_with("song3.mp3")
            assert service.get_current_index() == 2

        # Play next (at end, should do nothing)
        with patch.object(service, 'crossfade_to') as mock_fade:
            service.play_next()
            mock_fade.assert_not_called()
            assert service.get_current_index() == 2

        # Play previous -> Hard switch
        with patch.object(service, 'play_at_index') as mock_play_idx:
            service.play_previous()
            mock_play_idx.assert_called_with(1)

        # Play previous (at start)
        service._current_index = 0
        with patch.object(service, 'play_at_index') as mock_play_idx:
            service.play_previous()
            mock_play_idx.assert_not_called()

    def test_seek(self, service):
        """Test seeking"""
        service.seek(5000)
        service.active_player.setPosition.assert_called_with(5000)

    def test_get_properties(self, service):
        """Test getters for position, duration, state"""
        service.active_player.position.return_value = 1000
        assert service.get_position() == 1000

        service.active_player.duration.return_value = 20000
        assert service.get_duration() == 20000

        service.active_player.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
        assert service.get_state() == QMediaPlayer.PlaybackState.PlayingState
        assert service.is_playing() is True

        service.active_player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
        assert service.is_playing() is False

    def test_play_at_index_invalid(self, service):
        """Test playing at invalid index"""
        service.set_playlist(["song1.mp3"])
        
        # Invalid index low
        with patch.object(service, 'load') as mock_load:
            service.play_at_index(-1)
            mock_load.assert_not_called()
            
        # Invalid index high
        with patch.object(service, 'load') as mock_load:
            service.play_at_index(5)
            mock_load.assert_not_called()


