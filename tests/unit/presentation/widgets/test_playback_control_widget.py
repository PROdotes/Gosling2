
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
        mock_service.get_duration.return_value = 0
        mock_service.crossfade_enabled = False
        mock_service.crossfade_duration = 0
        mock_settings = MagicMock()
        return PlaybackControlWidget(mock_service, mock_settings)

    def test_update_song_label(self, widget):
        """Test song label updates"""
        widget.update_song_label("New Song Title")
        assert widget.song_label.text() == "New Song Title"

    def test_volume_slider_connection(self, widget):
        """Test volume slider triggers signal"""
        spy = MagicMock()
        widget.volume_changed.connect(spy)
        widget.volume_slider.setValue(75)
        spy.assert_called_once_with(75)

    def test_set_get_volume(self, widget):
        """Test volume getter/setter"""
        widget.set_volume(42)
        assert widget.get_volume() == 42
        assert widget.volume_slider.value() == 42

    def test_update_duration(self, widget):
        """Test duration update and formatting"""
        # 125000 ms = 2m 05s
        widget.update_duration(125000)
        assert widget.lbl_time_remaining.text() == "-02:05"

    def test_update_position(self, widget):
        """Test position update and remaining time"""
        duration = 300000
        widget.playback_service.get_duration.return_value = duration # 5 min
        widget.update_duration(duration) # Set slider range
        
        # 60000 ms = 1 min passed
        widget.update_position(60000)
        
        assert widget.lbl_time_passed.text() == "01:00"
        # 4 min remaining = 04:00
        assert widget.lbl_time_remaining.text() == "- 04:00"
        assert widget.playback_slider.value() == 60000
