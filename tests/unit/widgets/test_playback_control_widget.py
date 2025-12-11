
import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtMultimedia import QMediaPlayer
from src.presentation.widgets.playback_control_widget import PlaybackControlWidget

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

class TestPlaybackControlWidget:
    """Tests for PlaybackControlWidget"""

    @pytest.fixture
    def widget(self, qapp):
        mock_service = MagicMock()
        mock_service.player = MagicMock()
        mock_settings = MagicMock()
        return PlaybackControlWidget(mock_service, mock_settings)

    def test_update_play_button_state(self, widget):
        """Test play button text updates based on state"""
        # Test Playing State
        widget.update_play_button_state(QMediaPlayer.PlaybackState.PlayingState)
        assert widget.btn_play_pause.text() == "|| Pause"
        
        # Test Stopped State
        widget.update_play_button_state(QMediaPlayer.PlaybackState.StoppedState)
        assert widget.btn_play_pause.text() == "▶ Play"

        # Test Paused State
        widget.update_play_button_state(QMediaPlayer.PlaybackState.PausedState)
        assert widget.btn_play_pause.text() == "▶ Play"
