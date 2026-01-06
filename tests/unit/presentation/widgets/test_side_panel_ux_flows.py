"""
Tests for SidePanel UX flows and interactions.
Focuses on dialog triggering via ChipTrays.
"""
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QDialog
from src.presentation.widgets.side_panel_widget import SidePanelWidget
from src.data.models.song import Song
from src.core.entity_registry import EntityType

class TestSidePanelUXFlows:

    @pytest.fixture
    def side_panel(self, qtbot, mock_widget_deps):
        """Fixture for SidePanelWidget with mocked dependencies."""
        deps = mock_widget_deps
        
        # Configure Mocks to return INT IDs to prevent adapter crash
        # 1. Contributor Service (Artist)
        artist_mock = MagicMock()
        artist_mock.contributor_id = 99
        artist_mock.type = 'person'
        deps['library_service'].contributor_service.get_by_name.return_value = artist_mock
        
        # 2. Publisher Service
        pub_mock = MagicMock()
        pub_mock.publisher_id = 88
        pub_mock.publisher_name = "Mock Pub"
        pub_mock.parent_publisher_id = 0
        deps['library_service'].publisher_service.get_or_create.return_value = (pub_mock, False)
        deps['library_service'].publisher_service.get_by_name.return_value = pub_mock

        # 3. Album Service
        alb_mock = MagicMock()
        alb_mock.album_id = 77
        deps['library_service'].album_service.search.return_value = [alb_mock]
        
        widget = SidePanelWidget(
            deps['library_service'],
            deps['metadata_service'],
            deps['renaming_service'],
            deps['duplicate_scanner'],
            deps['settings_manager']
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
        s.album = ["Test Album"] # Use list for consistency
        s.album_id = [101] # Provide ID to prevent MagicMock comparison error in adapter
        s.album_artist = "Test Artist"
        s.unified_artist = "Test Artist"
        s.is_done = False
        s.recording_year = 2023
        s.publisher = ["Test Publisher"]
        s.publisher_id = [202]
        s.tags = ["Genre:Test Genre", "Mood:Test Mood"]
        s.tags_id = [303, 304]
        s.composers = []
        s.producers = []
        s.lyricists = []
        # Add any other fields accessed by _update_header or _refresh_field_values
        return s

    def test_album_add_button_opens_manager(self, side_panel, mock_song):
        """Test clicking the Album ChipTray 'Add' button requests ALDUM picker."""
        side_panel.set_songs([mock_song])
        
        # Get the EntityListWidget
        widget = side_panel._get_actual_widget('album')
        assert widget is not None, "Album widget not found"
        # Unwrap to get actual ChipTray
        tray = widget.tray
        assert tray is not None
        
        # Patch open_picker to catch the request before dialog instantiation
        with patch('src.core.entity_click_router.EntityClickRouter.open_picker') as mock_open:
            mock_open.return_value = None # Simulate cancel/no selection
            
            # Trigger the add signal manually (simulating click)
            tray.add_requested.emit()
            
            # Verify router was called with correct EntityType
            mock_open.assert_called_once()
            args, _ = mock_open.call_args
            assert args[0] == EntityType.ALBUM

    def test_publisher_add_button_opens_manager(self, side_panel, mock_song):
        """Test clicking the Publisher ChipTray 'Add' button requests PUBLISHER picker."""
        side_panel.set_songs([mock_song])
        
        widget = side_panel._get_actual_widget('publisher')
        tray = widget.tray
        
        with patch('src.core.entity_click_router.EntityClickRouter.open_picker') as mock_open:
            tray.add_requested.emit()
            
            mock_open.assert_called_once()
            args, _ = mock_open.call_args
            assert args[0] == EntityType.PUBLISHER

    def test_artist_add_button_opens_manager(self, side_panel, mock_song):
        """Test clicking the Performers ChipTray 'Add' button requests ARTIST picker."""
        side_panel.set_songs([mock_song])
        
        widget = side_panel._get_actual_widget('performers')
        tray = widget.tray
        
        with patch('src.core.entity_click_router.EntityClickRouter.open_picker') as mock_open:
            tray.add_requested.emit()
            
            mock_open.assert_called_once()
            args, _ = mock_open.call_args
            assert args[0] == EntityType.ARTIST
