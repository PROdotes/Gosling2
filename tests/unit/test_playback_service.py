"""Unit tests for PlaybackService"""
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtMultimedia import QMediaPlayer
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
        """Create a playback service instance"""
        return PlaybackService()

    def test_service_creation(self, service):
        """Test creating a playback service"""
        assert service.player is not None
        assert service.audio_output is not None

    def test_initial_state(self, service):
        """Test initial playback state"""
        assert service.get_state() == QMediaPlayer.PlaybackState.StoppedState
        assert not service.is_playing()

    def test_set_volume(self, service):
        """Test setting volume"""
        service.set_volume(0.5)
        assert service.get_volume() == 0.5

        service.set_volume(0.0)
        assert service.get_volume() == 0.0

        service.set_volume(1.0)
        assert service.get_volume() == 1.0

    def test_playlist_management(self, service):
        """Test playlist management"""
        playlist = ["/path/to/song1.mp3", "/path/to/song2.mp3", "/path/to/song3.mp3"]
        service.set_playlist(playlist)

        assert service.get_playlist() == playlist
        assert service.get_current_index() == -1

    def test_get_position_initial(self, service):
        """Test getting initial position"""
        position = service.get_position()
        assert position >= 0

    def test_get_duration_initial(self, service):
        """Test getting initial duration"""
        duration = service.get_duration()
        assert duration >= 0

