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
        # We need to maintain the QObject inheritance but mock the internals
        with patch('src.business.services.playback_service.QMediaPlayer') as mock_player_cls:
            with patch('src.business.services.playback_service.QAudioOutput') as mock_audio_cls:
                mock_player = MagicMock(spec=QMediaPlayer)
                mock_audio = MagicMock(spec=QAudioOutput)
                
                mock_player_cls.return_value = mock_player
                mock_audio_cls.return_value = mock_audio
                
                service = PlaybackService()
                
                # Verify setup
                assert service.player == mock_player
                assert service.audio_output == mock_audio
                
                return service

    def test_service_creation(self, service):
        """Test creating a playback service"""
        assert service.player is not None
        assert service.audio_output is not None
        service.player.setAudioOutput.assert_called_with(service.audio_output)

    def test_set_volume(self, service):
        """Test setting volume"""
        service.set_volume(0.5)
        service.audio_output.setVolume.assert_called_with(0.5)

    def test_get_volume(self, service):
        """Test getting current volume"""
        service.audio_output.volume.return_value = 0.7
        assert service.get_volume() == 0.7

    def test_player_controls(self, service):
        """Test play, pause, stop calls"""
        service.play()
        service.player.play.assert_called_once()
        
        service.pause()
        service.player.pause.assert_called_once()
        
        service.stop()
        service.player.stop.assert_called_once()

    def test_playlist_management_flow(self, service):
        """Test playlist navigation logic"""
        playlist = ["song1.mp3", "song2.mp3", "song3.mp3"]
        service.set_playlist(playlist)
        
        assert service.get_playlist() == playlist
        assert service.get_current_index() == -1

        # Play first song
        with patch.object(service, 'load') as mock_load:
            service.play_at_index(0)
            mock_load.assert_called_with("song1.mp3")
            assert service.get_current_index() == 0
            service.player.play.assert_called()

        # Play next
        with patch.object(service, 'load') as mock_load:
            service.play_next()
            mock_load.assert_called_with("song2.mp3")
            assert service.get_current_index() == 1

        # Play next
        with patch.object(service, 'load') as mock_load:
            service.play_next()
            mock_load.assert_called_with("song3.mp3")
            assert service.get_current_index() == 2

        # Play next (at end, should do nothing)
        with patch.object(service, 'load') as mock_load:
            service.play_next()
            mock_load.assert_not_called()
            assert service.get_current_index() == 2

        # Play previous
        with patch.object(service, 'load') as mock_load:
            service.play_previous()
            mock_load.assert_called_with("song2.mp3")
            assert service.get_current_index() == 1

        # Play previous (at start, should do nothing relative to new index logic, 
        # but if at 0 we stop? Here logic is > 0)
        service.play_at_index(0)
        with patch.object(service, 'load') as mock_load:
            service.play_previous()
            mock_load.assert_not_called()
            assert service.get_current_index() == 0

    def test_signal_propagation(self, service, qapp):
        """Test that internal player signals emit service signals"""
        # Just verify that the connections were made
        assert service.player.positionChanged.connect.called
        assert service.player.durationChanged.connect.called
        assert service.player.playbackStateChanged.connect.called
        assert service.player.mediaStatusChanged.connect.called
    def test_seek(self, service):
        """Test seeking"""
        service.seek(5000)
        service.player.setPosition.assert_called_with(5000)

    def test_get_properties(self, service):
        """Test getters for position, duration, state"""
        service.player.position.return_value = 1000
        assert service.get_position() == 1000

        service.player.duration.return_value = 20000
        assert service.get_duration() == 20000

        service.player.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
        assert service.get_state() == QMediaPlayer.PlaybackState.PlayingState
        assert service.is_playing() is True

        service.player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
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
