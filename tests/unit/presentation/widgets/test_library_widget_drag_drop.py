import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QMimeData, QUrl, QPoint, Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QLabel, QMessageBox
from src.presentation.widgets.library_widget import LibraryWidget

class TestLibraryWidgetDragDrop:
    
    @pytest.fixture
    def mock_deps(self):
        """Create mock dependencies for LibraryWidget"""
        return {
            'library_service': MagicMock(),
            'metadata_service': MagicMock(),
            'settings_manager': MagicMock()
        }

    @pytest.fixture
    def widget(self, qtbot, mock_deps):
        """Create LibraryWidget with mocks"""
        mock_deps['settings_manager'].get_column_visibility.return_value = {}
        mock_deps['settings_manager'].get_type_filter.return_value = 0
        mock_deps['library_service'].get_all_songs.return_value = ([], [])

        widget = LibraryWidget(
            mock_deps['library_service'],
            mock_deps['metadata_service'],
            mock_deps['settings_manager']
        )
        qtbot.addWidget(widget)
        with qtbot.waitExposed(widget):
            widget.show()
            
        # Global mock for QMessageBox to prevent windows opening during tests
        # This replaces the class itself on the widget instance or globally
        with patch('PyQt6.QtWidgets.QMessageBox.information'), \
             patch('PyQt6.QtWidgets.QMessageBox.warning'), \
             patch('PyQt6.QtWidgets.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            yield widget

    def test_drop_zip_extracts_and_deletes(self, widget):
        """Test that dropping a zip extracts MP3s, imports them, and DELETES zip."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False # Default to not being a playlist drop
        url = QUrl.fromLocalFile("C:/Downloads/archive.zip")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data

        # Mock ZipFile context manager
        mock_zip = MagicMock()
        mock_zip.__enter__.return_value = mock_zip
        mock_zip.namelist.return_value = ["song1.mp3", "subval/song2.mp3"]
        
        with patch('zipfile.ZipFile', return_value=mock_zip), \
             patch('os.path.exists', return_value=False), \
             patch('os.remove') as mock_remove, \
             patch.object(widget, 'import_files_list', return_value=2):
            
            widget.dropEvent(event)
            
            # 1. Verify Extraction
            assert mock_zip.extract.call_count == 2
            mock_zip.extract.assert_any_call("song1.mp3", "C:/Downloads")
            
            # 2. Verify Deletion
            mock_remove.assert_called_once_with("C:/Downloads/archive.zip")
            
            # 3. Verify Import
            widget.import_files_list.assert_called_once()

    def test_drop_zip_aborts_on_collision(self, widget):
        """Test that we ABORT extraction if ANY file already exists."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        url = QUrl.fromLocalFile("C:/Downloads/archive.zip")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data

        mock_zip = MagicMock()
        mock_zip.__enter__.return_value = mock_zip
        mock_zip.namelist.return_value = ["song1.mp3", "song2.mp3"]
        
        # Scenario: song2.mp3 exists
        def side_effect_exists(path):
            return path.endswith("song2.mp3")
            
        with patch('zipfile.ZipFile', return_value=mock_zip), \
             patch('os.path.exists', side_effect=side_effect_exists), \
             patch('os.remove') as mock_remove, \
             patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warn, \
             patch.object(widget, 'import_files_list'):
            
            widget.dropEvent(event)
            
            # 1. Verify NO Extraction
            mock_zip.extract.assert_not_called()
            
            # 2. Verify NO Deletion
            mock_remove.assert_not_called()
            
            # 3. Verify Warning
            mock_warn.assert_called_once()
            
            # 4. Verify NO Import
            widget.import_files_list.assert_not_called()

    def test_drag_enter_valid_mp3(self, widget):
        """Test that dragging an MP3 file is accepted."""
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        
        # Valid MP3 URL
        url = QUrl.fromLocalFile("C:/Music/song.mp3")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        
        # Act
        widget.dragEnterEvent(event)
        
        # Assert
        event.acceptProposedAction.assert_called_once()

    def test_drag_enter_mixed_case_mp3(self, widget):
        """Test that extension check is case-insensitive (.MP3)."""
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        
        url = QUrl.fromLocalFile("C:/Music/SONG.MP3")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        
        # Act
        widget.dragEnterEvent(event)
        
        # Assert
        event.acceptProposedAction.assert_called_once()

    def test_drag_enter_invalid_extension(self, widget):
        """Test that dragging a non-MP3 file (e.g. .txt) is ignored."""
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        
        # Invalid Text File
        url = QUrl.fromLocalFile("C:/Docs/notes.txt")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        
        # Act
        widget.dragEnterEvent(event)
        
        # Assert
        event.ignore.assert_called() # Should explicitly ignore or just not accept
        event.acceptProposedAction.assert_not_called()

    def test_drag_visual_feedback(self, widget):
        """Test that dragging over the table changes its style (border)."""
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        url = QUrl.fromLocalFile("song.mp3")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        
        # 1. Enter (Should set style)
        widget.dragEnterEvent(event)
        assert "border" in widget.table_view.styleSheet()
        
        # 2. Leave (Should clear style)
        # We need to simulate a leave event manually or call the handler if we implement dragLeaveEvent
        # Assuming we implement dragLeaveEvent
        from PyQt6.QtGui import QDragLeaveEvent
        widget.dragLeaveEvent(MagicMock(spec=QDragLeaveEvent))
        assert "border" not in widget.table_view.styleSheet()

    def test_drop_event_shows_feedback(self, widget):
        """Test that dropping a file shows a confirmation message."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        url = QUrl.fromLocalFile("song.mp3")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        
        # Mock import_files_list to return count 1
        with patch.object(widget, 'import_files_list', return_value=1):
            # Mock QMessageBox to verify feedback
            with patch('PyQt6.QtWidgets.QMessageBox.information') as mock_msg:
                widget.dropEvent(event)
                
                # Verify we cleared the style
                assert "border" not in widget.table_view.styleSheet()
                
                # Verify message box
                mock_msg.assert_called_once()
                args = mock_msg.call_args[0]
                assert "1 file(s)" in args[2]

    def test_drag_enter_zip(self, widget):
        """Test that dragging a ZIP file is accepted."""
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        url = QUrl.fromLocalFile("archive.zip")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        
        widget.dragEnterEvent(event)
        event.acceptProposedAction.assert_called_once()



    def test_zip_slip_prevention(self, widget):
        """Test that files with '..' in path are ignored (Zip Slip)."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        url = QUrl.fromLocalFile("C:/Downloads/malicious.zip")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data

        mock_zip = MagicMock()
        mock_zip.__enter__.return_value = mock_zip
        # One valid, one malicious
        mock_zip.namelist.return_value = ["song1.mp3", "../exposed/song2.mp3"]
        
        with patch('zipfile.ZipFile', return_value=mock_zip), \
             patch('os.path.exists', return_value=False), \
             patch('os.remove') as mock_remove, \
             patch.object(widget, 'import_files_list', return_value=1):
            
            widget.dropEvent(event)
            
            # Verify only song1 was extracted
            assert mock_zip.extract.call_count == 1
            mock_zip.extract.assert_called_with("song1.mp3", "C:/Downloads")
            
            # Verify import called with only the valid one
            args = widget.import_files_list.call_args[0][0]
            assert len(args) == 1
            assert "song1.mp3" in args[0]
            
            # Should still delete zip if successful otherwise
            mock_remove.assert_called_once()

    def test_bad_zip_file(self, widget):
        """Test handling of corrupt zip file."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        url = QUrl.fromLocalFile("C:/Downloads/corrupt.zip")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        
        # Make ZipFile constructor raise BadZipFile
        import zipfile
        with patch('zipfile.ZipFile', side_effect=zipfile.BadZipFile("Bad zip")), \
             patch.object(widget, 'import_files_list'):
            
            # Should catch exception and print error, not crash
            widget.dropEvent(event)
            
            widget.import_files_list.assert_not_called()

    def test_delete_zip_error(self, widget):
        """Test valid extraction but failure to delete zip."""
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
             patch('os.remove', side_effect=OSError("Permission denied")), \
             patch.object(widget, 'import_files_list', return_value=1):
             
            # Should catch OSError and continue to import
            widget.dropEvent(event)
            
            # Verify extraction happened
            mock_zip.extract.assert_called_once()
            
            # Verify import still happened even though delete failed
            widget.import_files_list.assert_called_once()

    def test_empty_state_label_exists(self, widget):
        """Test that an 'empty state' label exists and is configured correctly."""
        # Find all QLabels in the widget
        labels = widget.findChildren(QLabel)
        
        # We expect at least one label specifically for the empty state
        empty_label = None
        for lbl in labels:
            if "Drag" in lbl.text():
                empty_label = lbl
                break
        
        assert empty_label is not None, "Empty state label with text 'Drag...' not found"
        assert empty_label.isVisible() is True, "Empty state label should be visible initially"
        assert empty_label.alignment() == Qt.AlignmentFlag.AlignCenter

    def test_empty_state_visibility_toggles(self, widget):
        """Test that empty state label hides when data is present."""
        # Setup: Find the label
        empty_label = None
        for lbl in widget.findChildren(QLabel):
            if "Drag" in lbl.text():
                empty_label = lbl
                break
        
        # Simulate loading data
        headers = ["ID", "Title"]
        data = [[1, "Song A"]]
        
        # Act: Load library with data
        widget._populate_table(headers, data)
        # We also need to check if _populate_table or a helper updates the visibility
        # In our plan, we said `load_library` or `_populate_table` would do it.
        # Let's call the method that logic resides in (refer to plan: load_library handles it)
        
        # Manually triggering the visibility check if it's separate, 
        # or relying on _populate_table if we put it there. 
        # For TDD, let's assume valid implementation updates it.
        # We might need to mock library_service.get_all_songs if we call load_library
        widget.library_service.get_all_songs.return_value = (headers, data)
        widget.load_library()
        
        assert empty_label.isHidden(), "Label should hide when table has data"
        
        # Act: Clear data
        widget.library_service.get_all_songs.return_value = ([], [])
        widget.load_library()
        
        assert empty_label.isVisible(), "Label should reappear when table is empty"

    def test_drop_playlist_removes_from_playlist(self, widget):
        """Test that dropping internal playlist items emits signal to remove them."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        
        # Setup Playlist Mime Data
        mime_data.hasFormat.side_effect = lambda fmt: fmt == "application/x-gosling-playlist-rows"
        mime_data.hasUrls.return_value = False
        
        # Mock Data (Rows)
        import json
        rows = [1, 3] # Indices
        data_mock = MagicMock()
        data_mock.data.return_value = json.dumps(rows).encode('utf-8')
        mime_data.data.return_value = data_mock
        
        event.mimeData.return_value = mime_data
        
        # Connect signal
        mock_signal = MagicMock()
        widget.remove_from_playlist.connect(mock_signal)
        
        # Act
        widget.dropEvent(event)
        
        # Assert
        event.acceptProposedAction.assert_called_once()
        mock_signal.assert_called_once()
        args = mock_signal.call_args[0][0]
        assert args == rows
        
        # Ensure imports were NOT called
        # (We can check by mocking import_files_list logic if needed, but it shouldn't be reached)
        with patch.object(widget, 'import_files_list') as mock_import:
            widget.dropEvent(event)
            mock_import.assert_not_called()
