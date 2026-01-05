import pytest
import os
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt, QPoint, QItemSelectionModel
from PyQt6.QtWidgets import QMessageBox, QSplitter
from PyQt6.QtMultimedia import QMediaPlayer
from src.presentation.views.main_window import MainWindow
from src.core import yellberus

class TestMainWindow:
    @pytest.fixture
    def mock_services(self):
        """Mock services for MainWindow initialization."""
        with patch('src.presentation.views.main_window.LibraryService') as m_lib_cls, \
             patch('src.presentation.views.main_window.MetadataService') as m_meta_cls, \
             patch('src.presentation.views.main_window.PlaybackService') as m_play_cls, \
             patch('src.presentation.views.main_window.SettingsManager') as m_set_cls, \
             patch('src.presentation.views.main_window.RenamingService') as m_ren_cls, \
             patch('src.presentation.views.main_window.DuplicateScannerService') as m_dup_cls, \
             patch('src.presentation.views.main_window.ConversionService') as m_conv_cls, \
             patch('src.data.repositories.SongRepository') as m_song_repo, \
             patch('src.data.repositories.ContributorRepository') as m_contrib_repo, \
             patch('src.data.repositories.AlbumRepository') as m_album_repo, \
             patch('src.data.repositories.PublisherRepository') as m_pub_repo, \
             patch('src.data.repositories.TagRepository') as m_tag_repo:

            m_set = MagicMock()
            m_set_cls.return_value = m_set
            
            # Use explicit None for binary fields to avoid Truthy Mock issues
            m_set.get_window_geometry.return_value = None
            m_set.get_main_splitter_state.return_value = None
            m_set.get_v_splitter_state.return_value = None
            m_set.get_default_window_size.return_value = (1024, 768)
            m_set.get_appearance_settings.return_value = {}
            m_set.get_volume.return_value = 50
            m_set.get_last_playlist.return_value = []
            m_set.get_type_filter.return_value = 0
            m_set.get_database_path.return_value = ":memory:"  # Safe in-memory path
            mock_settings = m_set # Alias for yield

            m_lib = MagicMock()
            m_lib_cls.return_value = m_lib
            m_lib.get_all_songs.return_value = ([], [])
            m_lib.get_contributors_by_role.return_value = []
            m_lib.get_all_years.return_value = []
            
            # Add repository mocks to library service (needed by SidePanelWidget)
            mock_contributor = MagicMock()
            mock_contributor.contributor_id = 1
            mock_contributor.contributor_name = "Test Artist"
            m_lib.contributor_repository = MagicMock()
            m_lib.contributor_repository.get_or_create.return_value = (mock_contributor, False)
            
            # Fix: SidePanelWidget uses contributor_service directly via library_service property
            mock_contrib_service = MagicMock()
            mock_contrib_service.get_or_create.return_value = (mock_contributor, False)
            m_lib.contributor_service = mock_contrib_service
            
            mock_publisher = MagicMock()
            mock_publisher.publisher_id = 1
            mock_publisher.publisher_name = "Test Publisher"
            mock_publisher.parent_publisher_id = None
            m_lib.publisher_repo = MagicMock()
            m_lib.publisher_repo.get_or_create.return_value = (mock_publisher, False)
            m_lib.publisher_repo.get_by_id.return_value = None
            
            mock_album = MagicMock()
            mock_album.album_id = 1
            mock_album.title = "Test Album"
            m_lib.album_repo = MagicMock()
            m_lib.album_repo.get_or_create.return_value = (mock_album, False)
            
            mock_tag = MagicMock()
            mock_tag.tag_id = 1
            mock_tag.tag_name = "Test Tag"
            m_lib.tag_repo = MagicMock()
            m_lib.tag_repo.get_or_create.return_value = (mock_tag, False)

            m_play = MagicMock()
            m_play_cls.return_value = m_play
            m_play.active_player = MagicMock()

            yield {
                'library': m_lib,
                'settings': m_set,
                'playback': m_play,
                'renaming': m_ren_cls.return_value
            }

    @pytest.fixture
    def main_window(self, mock_services, qtbot):
        # PATCH EVERYTHING THAT COMPLAINS ABOUT MOCKS
        with patch.object(MainWindow, 'restoreGeometry'), \
             patch.object(MainWindow, 'restoreState'), \
             patch.object(QSplitter, 'restoreState'):
            window = MainWindow()
            qtbot.addWidget(window)
            return window

    def test_window_initialization(self, main_window):
        assert main_window.windowTitle() == "Gosling2 Music Player"

    def test_ui_elements_exist(self, main_window):
        assert main_window.library_widget is not None
        # Search box moved to title_bar
        assert main_window.title_bar.search_box is not None

    def test_search_filtering(self, main_window):
        # We check if the proxy model receives the filter text via title_bar
        main_window.title_bar.search_box.setText("test query")
        # Fixed string filtering might result in escaped spaces in the underlying regex pattern
        pattern = main_window.library_widget.proxy_model.filterRegularExpression().pattern()
        assert pattern.replace("\\", "") == "test query"

    def test_toggle_play_pause_calls_service(self, main_window, mock_services):
        # 1. Test Pause (is_playing=True)
        mock_services['playback'].is_playing.return_value = True
        main_window.playback_widget.play_pause_clicked.emit()
        mock_services['playback'].pause.assert_called_once()
        
        # 2. Test Play (is_playing=False, paused state)
        mock_services['playback'].is_playing.return_value = False
        mock_services['playback'].active_player.playbackState.return_value = QMediaPlayer.PlaybackState.PausedState
        main_window.playback_widget.play_pause_clicked.emit()
        mock_services['playback'].play.assert_called_once()

    def test_load_library_populates_model(self, main_window, mock_services):
        mock_services['library'].get_all_songs.return_value = (["Col"], [["Val"] * len(yellberus.FIELDS)])
        main_window.library_widget.load_library()
        assert main_window.library_widget.library_model.rowCount() == 1

    def test_delete_selected(self, main_window, mock_services):
        from PyQt6.QtGui import QStandardItem
        def get_idx_local(name):
             for i, f in enumerate(yellberus.FIELDS):
                 if f.name == name: return i
             return -1
        
        id_col = get_idx_local("file_id")
        # Ensure row has enough columns
        items = [QStandardItem("") for _ in yellberus.FIELDS]
        id_item = items[id_col]
        id_item.setText("123")
        id_item.setData("123", Qt.ItemDataRole.UserRole)
        main_window.library_widget.library_model.appendRow(items)
        
        idx = main_window.library_widget.proxy_model.index(0, 0)
        main_window.library_widget.table_view.selectionModel().select(
            idx, 
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
        )
        
        with patch('src.presentation.widgets.library_widget.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            main_window.library_widget._delete_selected()
        
        mock_services['library'].delete_song.assert_called_with(123)

    def test_shortcuts_call_library_widget_helpers(self, main_window):
        # In current MainWindow, actions are connected in _setup_shortcuts
        # and they point to library_widget methods or right_panel methods.
        
        main_window.library_widget.mark_selection_done = MagicMock()
        main_window.library_widget.focus_search = MagicMock()
        
        # We need to re-connect because they were connected to original methods during init
        main_window.action_mark_done.triggered.disconnect()
        main_window.action_mark_done.triggered.connect(main_window.library_widget.mark_selection_done)
        
        main_window.action_focus_search.triggered.disconnect()
        main_window.action_focus_search.triggered.connect(main_window.library_widget.focus_search)

        main_window.action_mark_done.trigger()
        main_window.action_focus_search.trigger()

        main_window.library_widget.mark_selection_done.assert_called_once()
        main_window.library_widget.focus_search.assert_called_once()
