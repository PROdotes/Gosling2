import pytest
import os
import json
import zipfile
from unittest.mock import MagicMock, patch, call
from PyQt6.QtWidgets import QMessageBox, QMenu, QApplication, QLabel
from PyQt6.QtCore import Qt, QModelIndex, QPoint, QMimeData, QUrl, QItemSelectionModel
from PyQt6.QtGui import QAction, QStandardItem, QDragEnterEvent, QDropEvent, QDragLeaveEvent
from src.presentation.widgets.library_widget import LibraryWidget
from src.core import yellberus

# Helper to map field name to index
def get_idx(name):
    for i, f in enumerate(yellberus.FIELDS):
        if f.name == name:
            return i
    return -1

@pytest.fixture
def library_widget(qtbot, mock_widget_deps):
    """Create LibraryWidget with mock dependencies and sample data"""
    deps = mock_widget_deps
    
    # Headers matching Yellberus
    headers = [f.db_column for f in yellberus.FIELDS] 
    
    # Create sample data row matching yellberus.FIELDS (21 columns)
    def create_row(prefix):
        row = [None] * len(yellberus.FIELDS)
        row[get_idx("path")] = f"/path/{prefix}.mp3"
        row[get_idx("file_id")] = ord(prefix) if isinstance(prefix, str) else prefix
        row[get_idx("type_id")] = 1
        row[get_idx("title")] = f"Title {str(prefix).upper()}"
        row[get_idx("performers")] = f"Performer {str(prefix).upper()}"
        row[get_idx("album")] = f"Album {str(prefix).upper()}"
        row[get_idx("composers")] = f"Composer {str(prefix).upper()}"
        row[get_idx("publisher")] = f"Publisher {str(prefix).upper()}"
        row[get_idx("genre")] = "Genre"
        row[get_idx("recording_year")] = 2020
        row[get_idx("bpm")] = 120
        row[get_idx("duration")] = 180.0
        row[get_idx("is_done")] = 1 if prefix == 'a' else 0 # 'a' is Done, 'b' is Not Done
        row[get_idx("is_active")] = 1
        return row

    data = [create_row('a'), create_row('b')]
    deps['library_service'].get_all_songs.return_value = (headers, data)
    
    widget = LibraryWidget(
        deps['library_service'], 
        deps['metadata_service'], 
        deps['settings_manager'],
        deps['renaming_service'],
        deps['duplicate_scanner']
    )
    qtbot.addWidget(widget)
    return widget

class TestLibraryWidgetLogic:
    """Level 1: Happy Path and Basic Logic for LibraryWidget"""
    
    def test_initial_load(self, library_widget, mock_widget_deps):
        """Test that the library loads data on init."""
        deps = mock_widget_deps
        deps['library_service'].get_all_songs.assert_called()
        assert library_widget.library_model.rowCount() == 2
        
        idx_perf = get_idx("performers")
        # Find row with prefix A
        found = False
        for r in range(library_widget.library_model.rowCount()):
            if library_widget.library_model.item(r, get_idx("title")).text() == "Title A":
                assert library_widget.library_model.item(r, idx_perf).text() == "Performer A"
                found = True
        assert found

    def test_import_files_success(self, library_widget, mock_widget_deps):
        """Test importing files successfully refreshes view."""
        deps = mock_widget_deps
        with patch.object(library_widget, '_import_file', return_value=True):
            count = library_widget.import_files_list(["/new/song.mp3"])
            assert count == 1
            assert deps['library_service'].get_all_songs.call_count > 1

    def test_delete_selected_confirm(self, library_widget, mock_widget_deps):
        """Test deletion proceeds if user clicks Yes."""
        deps = mock_widget_deps
        # Select first row
        idx = library_widget.proxy_model.index(0, 0)
        library_widget.table_view.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        
        idx_col_id = get_idx("file_id")
        idx_id = library_widget.proxy_model.index(0, idx_col_id) 
        expected_id = int(library_widget.proxy_model.data(idx_id))
        
        with patch("src.presentation.widgets.library_widget.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            library_widget._delete_selected()
            
        deps['library_service'].delete_song.assert_called_with(expected_id)

    def test_search_filtering(self, library_widget):
        """Test basic search filtering."""
        library_widget.search_box.setText("Title B")
        assert library_widget.proxy_model.rowCount() == 1
        
        library_widget.search_box.clear()
        assert library_widget.proxy_model.rowCount() == 2

    def test_import_file_skips_duplicate_audio(self, library_widget, mock_widget_deps):
        """Test that import is skipped if audio duplicate is found."""
        deps = mock_widget_deps
        # Mock duplicate found (returning a Song object means it exists)
        deps['duplicate_scanner'].check_audio_duplicate.return_value = MagicMock()
        
        path = "C:/Music/duplicate.mp3"
        
        # Patch the utility at source (since it's imported locally)
        with patch("src.utils.audio_hash.calculate_audio_hash", return_value="hash123"):
             result = library_widget._import_file(path)
             
             assert result is False
             deps['duplicate_scanner'].check_audio_duplicate.assert_called_with("hash123")
             deps['library_service'].add_file.assert_not_called()

    def test_import_file_skips_duplicate_isrc(self, library_widget, mock_widget_deps):
        """Test that import is skipped if ISRC duplicate is found."""
        deps = mock_widget_deps
        deps['duplicate_scanner'].check_audio_duplicate.return_value = None # No audio dup
        
        # Mock metadata extraction returning duplicate ISRC
        mock_song = MagicMock()
        mock_song.isrc = "US-DUP-00-00001"
        deps['metadata_service'].extract_from_mp3.return_value = mock_song
        
        # Mock duplicate ISRC found
        deps['duplicate_scanner'].check_isrc_duplicate.return_value = MagicMock()
        
        path = "C:/Music/duplicate_isrc.mp3"
        
        with patch("src.utils.audio_hash.calculate_audio_hash", return_value="hash123"):
             result = library_widget._import_file(path)
             
             assert result is False
             deps['duplicate_scanner'].check_isrc_duplicate.assert_called_with("US-DUP-00-00001")
             deps['library_service'].add_file.assert_not_called()

class TestLibraryWidgetDragDrop:
    """Level 1: Logic for Drag and Drop operations (Consolidated)"""

    def test_drag_enter_valid_mp3(self, library_widget):
        """Test that dragging an MP3 file is accepted."""
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        mime_data.urls.return_value = [QUrl.fromLocalFile("C:/Music/song.mp3")]
        event.mimeData.return_value = mime_data
        
        library_widget.dragEnterEvent(event)
        event.acceptProposedAction.assert_called_once()

    def test_drop_zip_extracts_and_deletes(self, library_widget):
        """Test zip file drop logic."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        url = QUrl.fromLocalFile("C:/Downloads/archive.zip")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data

        mock_zip = MagicMock()
        mock_zip.__enter__.return_value = mock_zip
        mock_zip.namelist.return_value = ["song1.mp3"]
        
        with patch('zipfile.ZipFile', return_value=mock_zip), \
             patch('os.path.exists', return_value=False), \
             patch('os.remove') as mock_remove, \
             patch.object(library_widget, 'import_files_list', return_value=1), \
             patch('PyQt6.QtWidgets.QMessageBox.information'):
            
            library_widget.dropEvent(event)
            assert mock_zip.extract.call_count == 1
            mock_remove.assert_called_once()

class TestLibraryWidgetContextMenu:
    """Level 1: Logic for Context Menu behavior (Consolidated)"""

    def test_item_status_toggle(self, library_widget, mock_widget_deps):
        """Test toggling 'Done' status from context menu."""
        deps = mock_widget_deps
        
        # Explicitly find row for Title B (Not Done)
        row_idx = -1
        idx_title = get_idx("title")
        for r in range(library_widget.proxy_model.rowCount()):
            if library_widget.proxy_model.data(library_widget.proxy_model.index(r, idx_title)) == "Title B":
                row_idx = r
                break
        assert row_idx != -1, "Title B not found in library"

        idx = library_widget.proxy_model.index(row_idx, 0)
        library_widget.table_view.selectionModel().clearSelection()
        library_widget.table_view.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        QApplication.processEvents()
        
        with patch('PyQt6.QtWidgets.QMenu.exec'), \
             patch('PyQt6.QtWidgets.QMenu.addAction') as mock_add:
            
            actions = []
            mock_add.side_effect = lambda a: actions.append(a)
            
            library_widget._show_table_context_menu(QPoint(0,0))
            
            status_action = None
            for action in actions:
                if action and hasattr(action, 'text') and "Mark as Done" in action.text():
                    status_action = action
                    break
            
            assert status_action is not None, f"Status action not found in menu. Actions: {[a.text() for a in actions if a]}"
            
            if status_action.isEnabled():
                deps['library_service'].update_song_status.return_value = True
                status_action.trigger()
                # ID for 'b' is 98
                deps['library_service'].update_song_status.assert_called_with(98, True)
            else:
                pytest.fail(f"Status action is disabled. Text: {status_action.text()}, Tooltip: {status_action.toolTip()}")

    def test_show_id3_tags_dialog(self, library_widget, mock_widget_deps):
        """Test interaction with MetadataViewerDialog."""
        deps = mock_widget_deps
        from src.data.models.song import Song
        
        mock_song = Song(name="Test", source="/path/a.mp3")
        deps['metadata_service'].extract_from_mp3.return_value = mock_song
        deps['library_service'].get_song_by_path.return_value = mock_song
        
        idx = library_widget.proxy_model.index(0, 0)
        library_widget.table_view.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        
        with patch("src.presentation.widgets.metadata_viewer_dialog.MetadataViewerDialog") as MockDialog:
            library_widget._show_id3_tags()
            MockDialog.assert_called()
            MockDialog.return_value.exec.assert_called_once()

    def test_status_toggle_blocked_if_incomplete(self, library_widget, mock_widget_deps):
        """Test that the 'Mark as Done' action is disabled if required fields are missing."""
        deps = mock_widget_deps
        
        # Explicitly find row for Title B
        row_idx = -1
        idx_title = get_idx("title")
        for r in range(library_widget.proxy_model.rowCount()):
            if library_widget.proxy_model.data(library_widget.proxy_model.index(r, idx_title)) == "Title B":
                row_idx = r
                break
        assert row_idx != -1

        # Corrupt Title B checkbox via the source model (mapping back)
        source_idx = library_widget.proxy_model.mapToSource(library_widget.proxy_model.index(row_idx, 0))
        is_done_idx = get_idx("is_done")
        
        # Manually disable the item to simulate valid incompleteness as per _populate_table logic
        item = library_widget.library_model.item(source_idx.row(), is_done_idx)
        item.setEnabled(False)
        
        # Force selection
        idx = library_widget.proxy_model.index(row_idx, 0)
        library_widget.table_view.selectionModel().clearSelection()
        library_widget.table_view.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        QApplication.processEvents()
        
        with patch('PyQt6.QtWidgets.QMenu.exec'), \
             patch('PyQt6.QtWidgets.QMenu.addAction') as mock_add:
            
            actions = []
            mock_add.side_effect = lambda a: actions.append(a)
            
            library_widget._show_table_context_menu(QPoint(0,0))
            
            status_action = None
            for action in actions:
                if action and hasattr(action, 'text') and "Mark as Done" in action.text():
                    status_action = action
                    break
            
            assert status_action is not None, f"Status action not found. Actions: {[a.text() for a in actions if a]}"
            assert not status_action.isEnabled(), f"Status action should be disabled. Text: {status_action.text()}"
            assert "Fix Errors First" in status_action.text()
