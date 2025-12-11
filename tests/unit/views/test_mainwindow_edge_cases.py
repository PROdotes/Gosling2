
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox, QMenu
from PyQt6.QtCore import Qt, QSettings, QPoint
from PyQt6.QtGui import QAction
from src.presentation.views.main_window import MainWindow

@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

class TestMainWindowEdgeCases:
    """Test edge cases and UI branches in MainWindow"""

    @pytest.fixture
    def window(self, qapp):
        with patch('src.presentation.views.main_window.QSettings') as mock_settings:
            # Mock settings value to return default if provided, else None
            def get_value(key, default=None):
                return default
            
            mock_settings.return_value.value.side_effect = get_value
            
            window = MainWindow()
            # Mock services to avoid DB/Audio hits
            window.library_service = MagicMock()
            window.metadata_service = MagicMock()
            window.playback_service = MagicMock()
            
            # CRITICAL: Propagate mocks to child widgets
            window.library_widget.library_service = window.library_service
            window.library_widget.metadata_service = window.metadata_service
            
            window.playlist_widget = MagicMock() 
            # We mock playlist_widget partial functions for specific tests
            return window

    def test_import_files_cancel(self, window):
        """Test file import cancellation"""
        with patch('src.presentation.widgets.library_widget.QFileDialog.getOpenFileNames', return_value=([], "")) as mock_dialog:
            window.library_widget._import_files()
            # Should just return without calling library service
            window.library_service.add_file.assert_not_called()

    def test_scan_folder_cancel(self, window):
        """Test folder scan cancellation"""
        with patch('src.presentation.widgets.library_widget.QFileDialog.getExistingDirectory', return_value="") as mock_dialog:
            window.library_widget._scan_folder()
            window.library_service.add_file.assert_not_called()

    def test_delete_selected_cancel(self, window):
        """Test validation cancellation on delete"""
        # Mock selection
        mock_selection = MagicMock()
        mock_selection.selectedRows.return_value = [MagicMock()]
        window.library_widget.table_view.selectionModel = MagicMock(return_value=mock_selection)
        
        with patch('src.presentation.widgets.library_widget.QMessageBox.question', return_value=QMessageBox.StandardButton.No):
            window.library_widget._delete_selected()
            window.library_service.delete_song.assert_not_called()

    def test_delete_no_selection(self, window):
        """Test delete with no selection"""
        mock_selection = MagicMock()
        mock_selection.selectedRows.return_value = []
        window.library_widget.table_view.selectionModel = MagicMock(return_value=mock_selection)
        
        with patch('src.presentation.widgets.library_widget.QMessageBox.question') as mock_box:
            window.library_widget._delete_selected()
            mock_box.assert_not_called()

    def test_close_event_saves_settings(self, window):
        """Test settings are saved on close"""
        event = MagicMock()
        window.closeEvent(event)
        
        # Check settings.setValue calls
        # We mocked QSettings class, so window.settings is the mock instance
        # window.settings.setValue.assert_called() 
        # Actually correct way is to check the specific keys if we care, 
        # or just that it was called multiple times
        assert window.settings.setValue.call_count >= 2 # geometry, splitter (columns moved to library widget)
        event.accept.assert_called_once()

    def test_column_visibility_toggle(self, window):
        """Test showing column context menu and toggling"""
        # We need to simulate the action text and data
        
        # 1. Setup headers
        window.library_widget.library_model.setHorizontalHeaderLabels(["ID", "Artist", "Title"])
        
        # 2. Call _show_column_context_menu
        # We mock QMenu.exec to not actually block
        with patch('src.presentation.widgets.library_widget.QMenu.exec') as mock_menu_exec:
            window.library_widget._show_column_context_menu(QPoint(0,0))
            mock_menu_exec.assert_called_once()
            
        # 3. Test toggle_column_visibility directly
        # Simulate sender action
        mock_action = MagicMock(spec=QAction)
        mock_action.data.return_value = 1 # Column index
        
        with patch.object(window.library_widget, 'sender', return_value=mock_action):
            # Check unhide (checked=True -> hidden=False)
            window.library_widget._toggle_column_visibility(True)
            assert window.library_widget.table_view.isColumnHidden(1) is False
            
            # Check hide (checked=False -> hidden=True)
            window.library_widget._toggle_column_visibility(False)
            assert window.library_widget.table_view.isColumnHidden(1) is True

    def test_play_next_empty_playlist(self, window):
        """Test play_next with insufficient items"""
        # 0 items
        window.playlist_widget.count.return_value = 0
        window._play_next()
        # Should do nothing, no crash
        
        # 1 item
        window.playlist_widget.count.return_value = 1
        window._play_next()
        # Should do nothing
        window.playback_service.load.assert_not_called()

    def test_on_search(self, window):
        """Test search filter update"""
        with patch.object(window.library_widget.proxy_model, 'setFilterWildcard') as mock_filter:
            window.library_widget._on_search("test")
            mock_filter.assert_called_with("*test*")

    def test_import_files_exception(self, window):
        """Test exception handling during file import"""
        with patch('src.presentation.widgets.library_widget.QFileDialog.getOpenFileNames', return_value=(["bad.mp3"], "")):
            # Raise exception when adding file
            window.library_service.add_file.side_effect = Exception("DB Error")
            # Should catch and print, not crash
            window.library_widget._import_files()
            # Verify it tried
            window.library_service.add_file.assert_called()

    def test_toggle_play_pause_paused(self, window):
        """Test toggle when paused -> play"""
        from PyQt6.QtMultimedia import QMediaPlayer
        window.playback_service.is_playing.return_value = False
        window.playback_service.player.playbackState.return_value = QMediaPlayer.PlaybackState.PausedState
        
        window._toggle_play_pause()
        window.playback_service.play.assert_called()

    def test_toggle_play_pause_auto_play_first(self, window):
        """Test toggle when stopped -> auto play first item"""
        from PyQt6.QtMultimedia import QMediaPlayer
        window.playback_service.is_playing.return_value = False
        window.playback_service.player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
        
        window.playlist_widget.count.return_value = 1
        item = MagicMock()
        window.playlist_widget.item.return_value = item
        
        with patch.object(window, '_on_playlist_double_click') as mock_dbl_click:
            window._toggle_play_pause()
            mock_dbl_click.assert_called_with(item)



    def test_media_status_end_of_media(self, window):
        """Test EndOfMedia triggers play_next"""
        from PyQt6.QtMultimedia import QMediaPlayer
        with patch.object(window, '_play_next') as mock_next:
            window._on_media_status_changed(QMediaPlayer.MediaStatus.EndOfMedia)
            mock_next.assert_called()

    def test_update_song_label_exception(self, window):
        """Test exception handling in update_song_label"""
        window.playback_widget = MagicMock() # Mock the whole widget
        window.metadata_service.extract_from_mp3.side_effect = Exception("Meta Error")
        
        window._update_song_label("path/to/song.mp3")
        
        # Should fallback to basename
        window.playback_widget.update_song_label.assert_called_with("song.mp3")
