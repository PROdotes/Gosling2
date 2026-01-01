"""
Tests for SidePanel UX flows and interactions.
Focuses on dialog triggering via ChipTrays.
"""
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QDialog
from src.presentation.widgets.side_panel_widget import SidePanelWidget
from src.data.models.song import Song

class TestSidePanelUXFlows:

    @pytest.fixture
    def side_panel(self, qtbot, mock_widget_deps):
        """Fixture for SidePanelWidget with mocked dependencies."""
        deps = mock_widget_deps
        widget = SidePanelWidget(
            deps['library_service'],
            deps['metadata_service'],
            deps['renaming_service'],
            deps['duplicate_scanner']
        )
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def mock_song(self):
        s = MagicMock(spec=Song)
        s.source_id = 1
        s.source = "C:\\test.mp3"
        s.title = "Test Title"
        s.performers = ["Test Artist"]
        s.album = "Test Album"
        s.album_artist = "Test Artist"
        s.unified_artist = "Test Artist"
        s.is_done = False
        s.recording_year = 2023
        s.publisher = "Test Publisher"
        s.genre = "Test Genre"
        s.mood = "Test Mood"
        s.composers = []
        s.producers = []
        s.lyricists = []
        # Add any other fields accessed by _update_header or _refresh_field_values
        return s

    def test_album_add_button_opens_manager(self, side_panel, mock_song):
        """Test clicking the Album ChipTray 'Add' button opens AlbumManagerDialog."""
        side_panel.set_songs([mock_song])
        
        # Get the ChipTray for album (unwrapped)
        tray = side_panel._get_actual_widget('album')
        assert tray is not None, "Album widget not found"
        
        with patch('src.presentation.dialogs.album_manager_dialog.AlbumManagerDialog') as MockDialog:
            mock_inst = MagicMock()
            MockDialog.return_value = mock_inst
            mock_inst.exec.return_value = QDialog.DialogCode.Accepted
            
            # Trigger the add signal manually (simulating click)
            tray.add_requested.emit()
            
            # Verify
            MockDialog.assert_called_once()
            mock_inst.exec.assert_called_once()

    def test_publisher_add_button_opens_manager(self, side_panel, mock_song):
        """Test clicking the Publisher ChipTray 'Add' button opens PublisherPickerDialog."""
        side_panel.set_songs([mock_song])
        
        tray = side_panel._get_actual_widget('publisher')
        assert tray is not None, "Publisher widget not found"
        
        with patch('src.presentation.dialogs.publisher_manager_dialog.PublisherPickerDialog') as MockDialog:
            mock_inst = MagicMock()
            MockDialog.return_value = mock_inst
            mock_inst.exec.return_value = QDialog.DialogCode.Accepted
            
            # Trigger
            tray.add_requested.emit()
            
            # Verify
            MockDialog.assert_called_once()
            mock_inst.exec.assert_called_once()

    def test_artist_add_button_opens_manager(self, side_panel, mock_song):
        """Test clicking the Performers ChipTray 'Add' button opens ArtistPickerDialog."""
        side_panel.set_songs([mock_song])
        
        tray = side_panel._get_actual_widget('performers')
        assert tray is not None
        
        with patch('src.presentation.dialogs.artist_manager_dialog.ArtistPickerDialog') as MockDialog:
            mock_inst = MagicMock()
            MockDialog.return_value = mock_inst
            mock_inst.exec.return_value = QDialog.DialogCode.Accepted
            
            tray.add_requested.emit()
            
            MockDialog.assert_called_once()
            mock_inst.exec.assert_called_once()
