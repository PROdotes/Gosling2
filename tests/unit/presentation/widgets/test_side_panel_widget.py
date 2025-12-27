import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QLineEdit
from src.presentation.widgets.side_panel_widget import SidePanelWidget
from src.data.models.song import Song
from datetime import datetime

@pytest.fixture
def side_panel(qtbot, mock_widget_deps):
    """Fixture for SidePanelWidget with mocked dependencies."""
    deps = mock_widget_deps
    
    # Ensure current_songs is handled gracefully if needed
    widget = SidePanelWidget(
        deps['library_service'],
        deps['metadata_service'],
        deps['renaming_service'],
        deps['duplicate_scanner']
    )
    qtbot.addWidget(widget)
    return widget

class TestSidePanelLogic:
    """Level 1: Logic Tests for SidePanelWidget (New Feature Coverage)"""

    def test_validate_isrc_format_invalid(self, side_panel):
        """Test that invalid ISRC format triggers red error style."""
        widget = QLineEdit()
        # "INVALID" is definitely invalid
        side_panel._validate_isrc_field(widget, "INVALID")
        assert widget.property("invalid") is True
        assert widget.property("warning") in [False, None]

    def test_validate_isrc_duplicate_warning(self, side_panel, mock_widget_deps):
        """Test that duplicate ISRC triggers amber warning style."""
        deps = mock_widget_deps
        mock_song = MagicMock(spec=Song)
        mock_song.source_id = 999
        mock_song.name = "Duplicate Song"
        deps['duplicate_scanner'].check_isrc_duplicate.return_value = mock_song
        
        # Setup side panel with a DIFFERENT song (ID 1)
        current_song = MagicMock(spec=Song)
        current_song.source_id = 1
        side_panel.set_songs([current_song])
        
        widget = QLineEdit()
        side_panel._validate_isrc_field(widget, "US-123-45-67890")
        
        assert widget.property("warning") is True
        assert "Duplicate ISRC found" in widget.toolTip()
        assert side_panel.isrc_collision is True

    def test_validate_isrc_duplicate_self_ignored(self, side_panel, mock_widget_deps):
        """Test that duplicate ISRC is ignored if it matches current song ID."""
        deps = mock_widget_deps
        mock_song = MagicMock(spec=Song)
        mock_song.source_id = 1
        deps['duplicate_scanner'].check_isrc_duplicate.return_value = mock_song
        
        # Setup side panel with SAME song (ID 1)
        current_song = MagicMock(spec=Song)
        current_song.source_id = 1
        side_panel.set_songs([current_song])
        
        widget = QLineEdit()
        side_panel._validate_isrc_field(widget, "US-123-45-67890")
        
        # Should be valid (no amber/red)
        assert widget.property("warning") in [False, None]
        assert widget.property("invalid") in [False, None]
        assert side_panel.isrc_collision is False

    def test_save_button_collision_state(self, side_panel):
        """Test save button enters collision state."""
        side_panel._staged_changes = {1: {'title': 'New'}} # Must have staged changes to enable save
        side_panel.isrc_collision = True
        side_panel._update_save_state()
        
        assert side_panel.btn_save.isEnabled()
        assert side_panel.btn_save.property("alert") is True
        assert "Duplicate" in side_panel.btn_save.text()

    def test_autofill_year_on_save(self, side_panel, mock_widget_deps, qtbot):
        """Test that saving with empty year autofills current year."""
        deps = mock_widget_deps
        # Mock DB value as 0 (Empty)
        mock_song = MagicMock(spec=Song)
        # Assuming Song fields are now property-based or dict-like
        mock_song.recording_year = 0
        deps['library_service'].get_song_by_id.return_value = mock_song
        
        # Store current songs to avoid attribute errors
        side_panel.current_songs = [mock_song]
        # Stage a change without year
        side_panel._staged_changes = {1: {'title': 'Changed'}}
        
        # Catch signal
        with qtbot.waitSignal(side_panel.save_requested) as blocker:
            side_panel._on_save_clicked()
            
        args = blocker.args[0]
        # args[1] is the changes dict
        assert args[1]['recording_year'] == datetime.now().year

    def test_composer_splitter(self, side_panel, qtbot, mock_widget_deps):
        """Test that trailing comma splits CamelCase composers."""
        # Setup mock song
        mock_song = MagicMock(spec=Song)
        mock_song.source_id = 1
        mock_widget_deps['library_service'].get_song_by_id.return_value = mock_song
        side_panel.current_songs = [mock_song]
        
        # Stage a change with camelcase and trailing comma
        side_panel._staged_changes = {1: {'composers': 'JohnPaul,'}}
        
        with qtbot.waitSignal(side_panel.save_requested) as blocker:
            side_panel._on_save_clicked()
            
        args = blocker.args[0]
        # Expect: "John, Paul"
        assert args[1]['composers'] == "John, Paul"
