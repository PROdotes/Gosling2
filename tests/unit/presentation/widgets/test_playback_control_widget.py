
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

    def test_crossfade_combo_sync_initial(self, widget):
        """Test combo box inits to correct value from service"""
        # Re-init widget with specific service state
        widget.playback_service.crossfade_enabled = True
        widget.playback_service.crossfade_duration = 5000 # 5s
        
        # Call sync manually since we modified mocks after init
        widget._sync_crossfade_combo()
        
        # 5s corresponds to data=5000. 
        # Check current data
        assert widget.combo_crossfade.currentData() == 5000

    def test_crossfade_combo_sync_initial_off(self, widget):
        """Test combo box inits to 0s if disabled"""
        widget.playback_service.crossfade_enabled = False
        widget.playback_service.crossfade_duration = 5000 # Even if duration is set
        
        widget._sync_crossfade_combo()
        
        assert widget.combo_crossfade.currentData() == 0

    def test_crossfade_change_updates_service(self, widget):
        """Test changing combo updates service"""
        # Find index for 3s (3000)
        idx = widget.combo_crossfade.findData(3000)
        assert idx != -1
        
        widget.combo_crossfade.setCurrentIndex(idx)
        # Should trigger signal -> slot
        
        assert widget.playback_service.crossfade_enabled is True
        assert widget.playback_service.crossfade_duration == 3000
        
        # Set to 0s
        idx_0 = widget.combo_crossfade.findData(0)
        widget.combo_crossfade.setCurrentIndex(idx_0)
        
        assert widget.playback_service.crossfade_enabled is False
        # duration not strictly required to change effectively if enabled is False, 
        # but our impl doesn't clear it. That's fine.

    def test_skip_enabled_when_crossfade_disabled(self, widget):
        """Test bug report: Skip button disables when crossfade set to 0."""
        # 1. Setup: Playlist > 1, Crossfade Enabled
        widget.playback_service.crossfade_enabled = True
        widget.playback_service.crossfade_duration = 5000
        widget._sync_crossfade_combo() # Ensure combo matches service (Index > 0)
        widget.set_playlist_count(5)
        
        # Ensure initial state
        # _is_crossfading defaults to False
        assert widget._is_crossfading is False
        assert widget.btn_next.isEnabled() is True
        
        # 2. Action: Set Crossfade to 0s
        idx_0 = widget.combo_crossfade.findData(0)
        widget.combo_crossfade.setCurrentIndex(idx_0)
        
        # 3. Expectation: Skip button remains Enabled
        assert widget.playback_service.crossfade_enabled is False
        assert widget._is_crossfading is False # Should not change
        assert widget.btn_next.isEnabled() is True # Should not disable
