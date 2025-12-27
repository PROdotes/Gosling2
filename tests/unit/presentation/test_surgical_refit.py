import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray
from PyQt6.QtWidgets import QWidget
from src.presentation.views.main_window import MainWindow, TerminalHeader

class MockTitleBar(QWidget):
    minimize_requested = pyqtSignal()
    maximize_requested = pyqtSignal()
    close_requested = pyqtSignal()
    search_text_changed = pyqtSignal(str)
    settings_requested = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_box = MagicMock()

class MockSidePanel(QWidget):
    save_requested = pyqtSignal(dict)
    staging_changed = pyqtSignal(bool)
    def set_songs(self, songs): pass
    def set_mini_mode(self, enabled): pass
    def clear_staged(self, ids): pass
    def trigger_save(self): pass

class MockPlaylist(QWidget):
    rows_moved = pyqtSignal(int, int)
    itemDoubleClicked = pyqtSignal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = MagicMock()
        # Mocking the signal object itself
        self.model().rowsMoved = MagicMock()
    def set_mini_mode(self, enabled): pass
    def count(self): return 0

class MockLibrary(QWidget):
    add_to_playlist = pyqtSignal(list)
    remove_from_playlist = pyqtSignal(list)
    play_immediately = pyqtSignal(str)
    focus_search_requested = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.field_indices = {}
        self.table_view = MagicMock()
        self.proxy_model = MagicMock()
        self.library_model = MagicMock()
        self.search_box = MagicMock()
        self.type_tabs = [("All", []), ("Music", [1])]
        self.pill_group = MagicMock()
    def update_dirty_rows(self, state): pass
    def load_library(self, refresh_filters=True): pass
    def set_search_text(self, text): pass
    def mark_selection_done(self): pass
    def focus_search(self): pass
    def rename_selection(self): pass

class MockPlayback(QWidget):
    play_pause_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    volume_changed = pyqtSignal(int)
    def set_playlist_count(self, count): pass
    def set_volume(self, vol): pass
    def get_volume(self): return 50
    def set_is_playing(self, state): pass

class TestSurgicalRefit:
    @pytest.fixture
    def mock_services(self):
        with patch('src.presentation.views.main_window.LibraryService') as m_lib_cls, \
             patch('src.presentation.views.main_window.MetadataService') as m_meta_cls, \
             patch('src.presentation.views.main_window.PlaybackService') as m_play_cls, \
             patch('src.presentation.views.main_window.SettingsManager') as m_set_cls, \
             patch('src.presentation.views.main_window.RenamingService') as m_ren_cls, \
             patch('src.presentation.views.main_window.DuplicateScannerService') as m_dup_cls, \
             patch('src.data.repositories.SongRepository'), \
             patch('src.data.repositories.ContributorRepository'), \
             patch('src.data.repositories.AlbumRepository'):

            m_set = MagicMock()
            m_set_cls.return_value = m_set
            m_set.get_main_splitter_state.return_value = QByteArray()
            m_set.get_v_splitter_state.return_value = QByteArray()
            m_set.get_window_geometry.return_value = QByteArray()
            m_set.get_default_window_size.return_value = (1024, 768)
            m_set.get_volume.return_value = 50
            m_set.get_last_playlist.return_value = []
            m_set.get_right_panel_toggles.return_value = {}
            m_set.get_right_panel_splitter_state.return_value = QByteArray()

            m_lib = MagicMock()
            m_lib_cls.return_value = m_lib
            m_lib.get_all_songs.return_value = ([], [])

            yield {
                'library': m_lib,
                'settings': m_set,
                'metadata': m_meta_cls.return_value
            }

    @pytest.fixture
    def window(self, mock_services, qtbot):
        with patch('src.presentation.views.main_window.CustomTitleBar', return_value=MockTitleBar()), \
             patch('src.presentation.views.main_window.LibraryWidget', return_value=MockLibrary()), \
             patch('src.presentation.views.main_window.PlaylistWidget', return_value=MockPlaylist()), \
             patch('src.presentation.views.main_window.SidePanelWidget', return_value=MockSidePanel()), \
             patch('src.presentation.views.main_window.PlaybackControlWidget', return_value=MockPlayback()), \
             patch('src.presentation.widgets.jingle_curtain.JingleCurtain', return_value=QWidget()), \
             patch('src.presentation.widgets.history_drawer.HistoryDrawer', return_value=QWidget()):
            
            win = MainWindow()
            qtbot.addWidget(win)
            return win

    def test_surgical_mode_exists_with_toggles(self, window):
        assert hasattr(window, 'right_panel')
        assert window.right_panel.header.btn_edit.text() == "[ EDIT MODE ]"

    def test_toggle_surgical_mode(self, window):
        # Initial state (Editor Hidden)
        assert window.right_panel.editor_widget.isHidden()
        
        # Enable Surgical Mode
        window.right_panel.header.btn_edit.setChecked(True)
        assert not window.right_panel.editor_widget.isHidden()
        
        # Disable
        window.right_panel.header.btn_edit.setChecked(False)
        assert window.right_panel.editor_widget.isHidden()

    def test_toggle_history_log(self, window):
        # Initial state (History Hidden)
        assert window.right_panel.history_widget.isHidden()
        
        # Enable History
        window.right_panel.header.btn_hist.setChecked(True)
        assert not window.right_panel.history_widget.isHidden()
        
        # Disable
        window.right_panel.header.btn_hist.setChecked(False)
        assert window.right_panel.history_widget.isHidden()

    def test_library_selection_behavior(self, window):
        mock_song = MagicMock()
        window._get_selected_song_object = MagicMock(return_value=mock_song)
        mock_index = MagicMock()
        window.library_widget.table_view.selectionModel().selectedRows.return_value = [mock_index]
        
        # 1. Edit Mode OFF
        window.right_panel.header.btn_edit.setChecked(False)
        window._on_library_selection_changed(None, None)
        assert window.right_panel.editor_widget.isHidden()
        
        # 2. Edit Mode ON
        window.right_panel.header.btn_edit.setChecked(True)
        window._on_library_selection_changed(None, None)
        # It should be visible
        assert not window.right_panel.editor_widget.isHidden()
