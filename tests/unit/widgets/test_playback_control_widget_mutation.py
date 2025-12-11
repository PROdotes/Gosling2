
import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from src.presentation.widgets.playback_control_widget import PlaybackControlWidget

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

class TestPlaybackControlWidgetMutation:
    @pytest.fixture
    def widget(self, qapp):
        mock_service = MagicMock()
        mock_service.player = MagicMock()
        # Default duration 300s (5 min)
        mock_service.player.duration.return_value = 300000 
        return PlaybackControlWidget(mock_service)

    def test_format_time_logic(self, widget):
        """Kill Mutants: _format_time logic (div/mod constants)"""
        # 0s -> 00:00
        assert widget._format_time(0) == "00:00"
        
        # 59s -> 00:59 (If %60 mutated to %61, this might change or not, but logic integrity important)
        assert widget._format_time(59000) == "00:59"
        
        # 60s -> 01:00 (If //60 mutated, this fails)
        assert widget._format_time(60000) == "01:00"
        
        # 61s -> 01:01
        assert widget._format_time(61000) == "01:01"
        
        # 3599s -> 59:59
        assert widget._format_time(3599000) == "59:59"

    def test_update_position_labels(self, widget):
        """Kill Mutants: update_position label updates"""
        widget.playback_service.player.duration.return_value = 120000 # 2 mins
        
        # Position 30s
        widget.update_position(30000)
        
        # Verify passed label
        assert widget.lbl_time_passed.text() == "00:30"
        
        # Verify remaining label (120 - 30 = 90s = 01:30)
        # If max(0, duration-position) mutated, this catches it
        assert widget.lbl_time_remaining.text() == "- 01:30"

    def test_update_position_past_duration(self, widget):
        """Kill Mutants: max(0, duration - position)"""
        widget.playback_service.player.duration.return_value = 10000 # 10s
        
        # Position 20s (weird but possible glitch)
        widget.update_position(20000)
        
        # Remaining should be 0, not negative
        assert widget.lbl_time_remaining.text() == "- 00:00"
