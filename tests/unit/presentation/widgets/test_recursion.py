
import pytest
from PyQt6.QtWidgets import QApplication
from src.presentation.widgets.side_panel_widget import SidePanelWidget
from unittest.mock import MagicMock

def test_refresh_content_no_recursion(qtbot):
    # Setup
    mock_service = MagicMock()
    mock_song_repo = MagicMock()
    mock_tag_repo = MagicMock()
    
    # Mock a song
    mock_song = MagicMock()
    mock_song.source_id = 1
    mock_song.processing_status = 0
    mock_song.is_done = False
    mock_song.performers = []
    mock_song.unified_artist = "Test"
    mock_song.title = "Song"
    
    mock_service.get_song_by_id.return_value = mock_song
    
    mock_metadata = MagicMock()
    mock_renaming = MagicMock()
    mock_scanner = MagicMock()
    mock_settings = MagicMock()
    
    widget = SidePanelWidget(mock_service, mock_metadata, mock_renaming, mock_scanner, mock_settings)
    widget.current_songs = [mock_song]
    
    # Trigger refresh
    # If recursion exists, this will hang or hit recursion limit
    widget.refresh_content()
    
    # If we reached here, no infinite recursion
    assert True
