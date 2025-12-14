import pytest
from unittest.mock import MagicMock, patch, call
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QMessageBox
from src.presentation.views.main_window import MainWindow

class TestMainWindow:
    @pytest.fixture
    def mock_services(self):
        with patch('src.presentation.views.main_window.LibraryService') as mock_library_cls, \
             patch('src.presentation.views.main_window.MetadataService') as mock_metadata_cls, \
             patch('src.presentation.views.main_window.PlaybackService') as mock_playback_cls, \
             patch('src.presentation.views.main_window.SettingsManager') as mock_settings_cls:

            # Mock SettingsManager
            mock_settings = MagicMock()
            mock_settings_cls.return_value = mock_settings
            mock_settings.get_window_geometry.return_value = None
            mock_settings.get_main_splitter_state.return_value = None
            mock_settings.get_default_window_size.return_value = (1200, 800)
            mock_settings.get_column_visibility.return_value = {}
            mock_settings.get_volume.return_value = 50
            mock_settings.get_last_playlist.return_value = []
            mock_settings.get_last_import_directory.return_value = None

            mock_library = MagicMock()
            mock_library_cls.return_value = mock_library
            mock_library.get_all_songs.return_value = (["ID", "performer", "Title", "Dur", "Path"], [])

            mock_metadata = MagicMock()
            mock_metadata_cls.return_value = mock_metadata

            mock_playback = MagicMock()
            mock_playback_cls.return_value = mock_playback
            
            # Setup player for SeekSlider
            mock_playback.player = MagicMock()
            mock_playback.player.duration.return_value = 0

            yield {
                'library': mock_library,
                'metadata': mock_metadata,
                'playback': mock_playback,
                'settings': mock_settings
            }

    @pytest.fixture
    def main_window(self, qtbot, mock_services):
        window = MainWindow()
        qtbot.addWidget(window)
        return window

    def test_window_initialization(self, main_window):
        assert main_window.windowTitle() == "Gosling2 Music Player"
        assert main_window.centralWidget() is not None
        # Check services initialized
        assert main_window.library_service is not None
        assert main_window.metadata_service is not None
        assert main_window.playback_service is not None
        assert main_window.library_widget is not None

    def test_ui_elements_exist(self, main_window):
        assert main_window.library_widget.btn_import is not None
        assert main_window.library_widget.btn_scan_folder is not None
        assert main_window.library_widget.search_box is not None
        assert main_window.library_widget.table_view is not None
        assert main_window.playlist_widget is not None
        assert main_window.playback_widget is not None
        assert main_window.library_widget.filter_widget is not None

    def test_search_filtering(self, main_window):
        # Verify text changed connects to proxy filter
        main_window.library_widget.search_box.setText("Test")
        assert main_window.library_widget.proxy_model.filterRegularExpression().pattern() != ""

    def test_toggle_play_pause_calls_service(self, main_window, mock_services):
        # Initial state: stopped
        mock_services['playback'].is_playing.return_value = False
        
        main_window._toggle_play_pause()
        mock_services['playback'].play.assert_called()

        # Playing state -> Pause
        mock_services['playback'].is_playing.return_value = True
        main_window._toggle_play_pause()
        mock_services['playback'].pause.assert_called()

    def test_load_library_populates_model(self, main_window, mock_services):
        # Setup mock data
        mock_services['library'].get_all_songs.return_value = (
            ["ID", "performer", "Title"],
            [[1, "performer 1", "Song 1"], [2, "performer 2", "Song 2"]]
        )
        
        main_window.library_widget.load_library()
        
        assert main_window.library_widget.library_model.rowCount() == 2
        assert main_window.library_widget.library_model.item(0, 1).text() == "performer 1"
        assert main_window.library_widget.library_model.item(1, 2).text() == "Song 2"

    @patch('src.presentation.widgets.library_widget.QFileDialog')
    @patch('src.presentation.widgets.library_widget.QMessageBox')
    def test_import_files(self, mock_msg, mock_dialog, main_window, mock_services):
        mock_dialog.getOpenFileNames.return_value = (["/path/to/song.mp3"], "mp3")
        mock_services['library'].add_file.return_value = 1
        mock_song = MagicMock()
        mock_services['metadata'].extract_from_mp3.return_value = mock_song
        
        # Ensure reload returns items
        mock_services['library'].get_all_songs.return_value = (["Cols"], [[1]])

        main_window.library_widget._import_files()

        mock_services['library'].add_file.assert_called_with("/path/to/song.mp3")
        mock_services['metadata'].extract_from_mp3.assert_called()
        mock_services['library'].update_song.assert_called_with(mock_song)
        # Should verify library reloaded
        assert main_window.library_widget.library_model.rowCount() == 1

    @patch('src.presentation.widgets.library_widget.QFileDialog')
    @patch('src.presentation.widgets.library_widget.os.walk')
    @patch('src.presentation.widgets.library_widget.QMessageBox')
    def test_scan_folder(self, mock_msg, mock_walk, mock_dialog, main_window, mock_services):
        mock_dialog.getExistingDirectory.return_value = "/music/folder"
        mock_walk.return_value = [("/music/folder", [], ["song1.mp3", "image.jpg"])]
        
        mock_services['library'].add_file.return_value = 1
        
        main_window.library_widget._scan_folder()
        
        assert mock_services['library'].add_file.call_count == 1

    @patch('src.presentation.widgets.library_widget.QMessageBox')
    def test_delete_selected(self, mock_msg, main_window, mock_services):
        # Setup model with one item
        from PyQt6.QtGui import QStandardItem
        row = 0
        id_item = QStandardItem("123")
        main_window.library_widget.library_model.setItem(row, 0, id_item)
        
        # Mock selection
        mock_index = main_window.library_widget.library_model.index(0, 0)
        
        # Mock the selection model specifically
        mock_selection_model = MagicMock()
        mock_proxy_index = MagicMock()
        mock_proxy_index.row.return_value = 0
        mock_selection_model.selectedRows.return_value = [mock_proxy_index]
        
        main_window.library_widget.table_view.selectionModel = MagicMock(return_value=mock_selection_model)
        
        # Mock mapping on the REAL proxy model instance
        main_window.library_widget.proxy_model.mapToSource = MagicMock(return_value=mock_index)
        
        # Mock confirmation Yes and mock enum attributes
        mock_msg.StandardButton.Yes = QMessageBox.StandardButton.Yes
        mock_msg.StandardButton.No = QMessageBox.StandardButton.No
        mock_msg.question.return_value = QMessageBox.StandardButton.Yes
        
        main_window.library_widget._delete_selected()
        
        mock_services['library'].delete_song.assert_called_with(123)

    def test_show_table_context_menu_actions(self, main_window):
        # Verify menu has correct actions and triggers callbacks
        with patch('src.presentation.widgets.library_widget.QMenu') as mock_menu_cls, \
             patch('src.presentation.widgets.library_widget.QAction') as mock_action_cls:
            
            mock_menu = mock_menu_cls.return_value
            
            # Setup specific mocks for actions
            mock_delete = MagicMock()
            mock_playlist = MagicMock()
            
            def action_side_effect(text, parent):
                if "Delete" in text:
                    return mock_delete
                if "Playlist" in text:
                    return mock_playlist
                return MagicMock()
            
            mock_action_cls.side_effect = action_side_effect
            
            # Run method
            main_window.library_widget._show_table_context_menu(QPoint(0,0))
            
            # Verify actions created
            mock_delete.triggered.connect.assert_called_with(main_window.library_widget._delete_selected)
            mock_playlist.triggered.connect.assert_called_with(main_window.library_widget._emit_add_to_playlist)
            
            # Verify added to menu
            mock_menu.addAction.assert_any_call(mock_delete)
            mock_menu.addAction.assert_any_call(mock_playlist)
            
            # Verify menu shown
            mock_menu.exec.assert_called()

    def test_table_double_click(self, main_window):
        """Test double clicking table row emits add to playlist"""
        with patch.object(main_window.library_widget, '_emit_add_to_playlist') as mock_emit:
            main_window.library_widget._on_table_double_click(MagicMock())
            mock_emit.assert_called_once()

    def test_add_selected_to_playlist(self, main_window, mock_services):
        # Setup selection
        mock_selection_model = MagicMock()
        mock_index = MagicMock()
        mock_index.row.return_value = 0
        mock_selection_model.selectedRows.return_value = [mock_index]
        main_window.library_widget.table_view.selectionModel = MagicMock(return_value=mock_selection_model)
        
        # Setup Proxy map
        main_window.library_widget.proxy_model.mapToSource = MagicMock(return_value=mock_index)
        
        # Setup Library Item Data
        mock_path_item = MagicMock()
        mock_path_item.text.return_value = "/path/to/song.mp3"
        mock_performer = MagicMock()
        mock_performer.text.return_value = "performer"
        mock_title = MagicMock()
        mock_title.text.return_value = "Title"
        
        def item_side_effect(row, col):
            if col == 4: return mock_path_item
            if col == 1: return mock_performer
            if col == 2: return mock_title
            return None
            
        main_window.library_widget.library_model.item = MagicMock(side_effect=item_side_effect)
        
        # Mock Playlist Widget addItem
        main_window.playlist_widget.addItem = MagicMock()
        
        # Calling signal emit method on library widget
        main_window.library_widget._emit_add_to_playlist()
        
        # Verify item added via signal connection
        main_window.playlist_widget.addItem.assert_called()
        args = main_window.playlist_widget.addItem.call_args[0][0]
        # Check text format
        assert args.text() == "performer | Title"

    def test_on_playlist_double_click(self, main_window, mock_services):
        mock_item = MagicMock()
        mock_item.data.return_value = {"path": "/path/to/song.mp3"}
        
        main_window._on_playlist_double_click(mock_item)
        
        mock_services['playback'].load.assert_called_with("/path/to/song.mp3")
        mock_services['playback'].play.assert_called()

    @patch('src.presentation.widgets.library_widget.QFileDialog')
    @patch('src.presentation.widgets.library_widget.os.walk')
    @patch('src.presentation.widgets.library_widget.QMessageBox')
    def test_scan_folder_error_handling(self, mock_msg, mock_walk, mock_dialog, main_window, mock_services):
        mock_dialog.getExistingDirectory.return_value = "/music/folder"
        mock_walk.return_value = [("/music/folder", [], ["song1.mp3"])]
        
        # Simulate error triggers exception print but no crash
        mock_services['library'].add_file.side_effect = Exception("DB Error")
        
        # Should not crash
        main_window.library_widget._scan_folder()
        
        # Verify add_file attempted
        assert mock_services['library'].add_file.call_count == 1

    def test_populate_filter_tree(self, main_window, mock_services):
        # Setup mock data for widget
        mock_services['library'].get_contributors_by_role.return_value = [
            (1, "Abba"), (2, "AC/DC"), (3, "Beatles")
        ]
        
        # Use widget method
        main_window.library_widget.filter_widget.populate()
        
        # Verify root item via widget model
        model = main_window.library_widget.filter_widget.tree_model
        root = model.item(0)
        assert root.text() == "Performers"
        assert root.hasChildren()
        
        # Check A group
        a_group = root.child(0) 
        assert a_group.text() == "A"
        assert a_group.rowCount() == 2 

    def test_filter_tree_clicked(self, main_window, mock_services):
        # Verify it calls service to filter (Logic in MainWindow)
        # MUST setup mock return value BEFORE emit because signal is synchronous
        mock_services['library'].get_songs_by_performer.return_value = (["Cols"], [[1, "Abba", "Song"]])

        # Trigger signal manually to simulate click
        main_window.library_widget.filter_widget.filter_by_performer.emit("Abba")
        
        mock_services['library'].get_songs_by_performer.assert_called_with("Abba")
        assert main_window.library_widget.library_model.rowCount() == 1

    def test_play_next(self, main_window, mock_services):
        # Setup playlist with 2 items
        main_window.playlist_widget.addItem("Song 1")
        main_window.playlist_widget.addItem("Song 2")
        
        # Mock item data retrieval
        item2 = main_window.playlist_widget.item(1)
        item2.setData(Qt.ItemDataRole.UserRole, {"path": "song2.mp3"})
        
        main_window._play_next()
        
        # Verify playing second item
        mock_services['playback'].load.assert_called_with("song2.mp3")
        mock_services['playback'].play.assert_called()
        
        assert main_window.playlist_widget.count() == 1
        assert main_window.playlist_widget.item(0).text() == "Song 2"

    def test_volume_changed(self, main_window, mock_services):
        main_window._on_volume_changed(50)
        mock_services['playback'].set_volume.assert_called_with(0.5)
        
        main_window._on_volume_changed(100)
        mock_services['playback'].set_volume.assert_called_with(1.0)

    def test_update_position(self, main_window, mock_services):
        # Initial slider max is 0, duration update usually sets it
        main_window.playback_widget.playback_slider = MagicMock() 
        
        # We need to ensure the service player mock returns the duration
        # because update_position reads it from there
        mock_services['playback'].player.duration.return_value = 10000

        # Use widget methods directly to test widget logic
        main_window.playback_widget.update_duration(10000)
        main_window.playback_widget.update_position(5000)
        
        # Check slider in widget - verify setValue was called
        main_window.playback_widget.playback_slider.setValue.assert_called_with(5000)
        # Check labels
        assert main_window.playback_widget.lbl_time_passed.text() == "00:05"
        assert main_window.playback_widget.lbl_time_remaining.text() == "- 00:05"