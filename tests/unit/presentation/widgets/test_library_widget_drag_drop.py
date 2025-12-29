import pytest
import os
import zipfile
from unittest.mock import MagicMock, patch, call
from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import Qt, QMimeData, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from src.presentation.widgets.library_widget import LibraryWidget
from src.core import yellberus

@pytest.fixture
def mock_conversion_service():
    return MagicMock()

@pytest.fixture
def library_widget_with_conv(qtbot, mock_widget_deps, mock_conversion_service):
    """Create LibraryWidget with conversion service"""
    deps = mock_widget_deps
    widget = LibraryWidget(
        deps['library_service'], 
        deps['metadata_service'], 
        deps['settings_manager'],
        deps['renaming_service'],
        deps['duplicate_scanner'],
        conversion_service=mock_conversion_service
    )
    qtbot.addWidget(widget)
    return widget

class TestLibraryWidgetDragDropAdvanced:
    """Advanced Drag and Drop tests for LibraryWidget (WAV detection, ZIP inspection)."""

    def test_drag_enter_accepts_wav(self, library_widget_with_conv):
        """Test that dragging a WAV file is accepted."""
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        mime_data.urls.return_value = [QUrl.fromLocalFile("C:/Music/song.wav")]
        event.mimeData.return_value = mime_data
        
        library_widget_with_conv.dragEnterEvent(event)
        event.acceptProposedAction.assert_called_once()

    def test_drop_standalone_wav_convert_yes(self, library_widget_with_conv, mock_conversion_service):
        """Test dropping a WAV and choosing to convert."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        wav_path = os.path.abspath("C:/Music/test.wav")
        mime_data.urls.return_value = [QUrl.fromLocalFile(wav_path)]
        event.mimeData.return_value = mime_data

        mock_conversion_service.convert_wav_to_mp3.return_value = "C:/Music/test.mp3"
        
        with patch("src.presentation.widgets.library_widget.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
             patch.object(library_widget_with_conv, 'import_files_list', return_value=1), \
             patch("PyQt6.QtWidgets.QMessageBox.information"), \
             patch('os.remove') as mock_remove:
            
            library_widget_with_conv.dropEvent(event)
            
            mock_conversion_service.convert_wav_to_mp3.assert_called_with(wav_path)
            library_widget_with_conv.import_files_list.assert_called_once()
            args = library_widget_with_conv.import_files_list.call_args[0][0]
            assert "C:\\Music\\test.mp3" in args or "C:/Music/test.mp3" in args
            mock_remove.assert_called_with(wav_path)

    def test_drop_standalone_wav_convert_no(self, library_widget_with_conv, mock_conversion_service):
        """Test dropping a WAV and choosing NOT to convert."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        wav_path = os.path.abspath("C:/Music/test.wav")
        mime_data.urls.return_value = [QUrl.fromLocalFile(wav_path)]
        event.mimeData.return_value = mime_data

        with patch("src.presentation.widgets.library_widget.QMessageBox.question", return_value=QMessageBox.StandardButton.No), \
             patch.object(library_widget_with_conv, 'import_files_list') as mock_import:
            
            library_widget_with_conv.dropEvent(event)
            
            mock_conversion_service.convert_wav_to_mp3.assert_not_called()
            mock_import.assert_not_called()

    def test_drop_wav_ffmpeg_missing(self, library_widget_with_conv, mock_conversion_service):
        """Test that prompt is skipped if FFmpeg is missing."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.urls.return_value = [QUrl.fromLocalFile("C:/Music/test.wav")]
        event.mimeData.return_value = mime_data

        mock_conversion_service.is_ffmpeg_available.return_value = False
        
        with patch("src.presentation.widgets.library_widget.QMessageBox.question") as mock_quest:
            library_widget_with_conv.dropEvent(event)
            mock_quest.assert_not_called()

    def test_drop_mixed_zip_convert_yes(self, library_widget_with_conv, mock_conversion_service):
        """Test dropping a ZIP with MP3 and WAV, choosing YES."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        zip_path = os.path.abspath("C:/Downloads/album.zip")
        mime_data.urls.return_value = [QUrl.fromLocalFile(zip_path)]
        event.mimeData.return_value = mime_data

        # Mock ZIP content
        mock_zip = MagicMock()
        mock_zip.__enter__.return_value = mock_zip
        mock_zip.namelist.return_value = ["song.mp3", "song.wav"]
        
        mock_conversion_service.convert_wav_to_mp3.return_value = os.path.abspath("C:/Downloads/song.mp3")

        with patch('zipfile.ZipFile', return_value=mock_zip), \
             patch("src.presentation.widgets.library_widget.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
             patch.object(library_widget_with_conv, 'import_files_list', return_value=2), \
             patch("PyQt6.QtWidgets.QMessageBox.information"), \
             patch('os.remove') as mock_remove:
            
            library_widget_with_conv.dropEvent(event)
            
            # Verify extraction
            mock_zip.extract.assert_any_call("song.mp3", os.path.dirname(zip_path))
            mock_zip.extract.assert_any_call("song.wav", os.path.dirname(zip_path))
            
            # Verify conversion
            mock_conversion_service.convert_wav_to_mp3.assert_called_once()
            
            # Verify cleanup
            # 1. Removal of temp wav
            # 2. Removal of zip
            assert mock_remove.call_count >= 2
            mock_remove.assert_any_call(zip_path)

    def test_drop_mixed_zip_convert_no(self, library_widget_with_conv, mock_conversion_service):
        """Test dropping a ZIP with MP3 and WAV, choosing NO."""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        zip_path = os.path.abspath("C:/Downloads/album.zip")
        mime_data.urls.return_value = [QUrl.fromLocalFile(zip_path)]
        event.mimeData.return_value = mime_data

        # Mock ZIP content
        mock_zip = MagicMock()
        mock_zip.__enter__.return_value = mock_zip
        mock_zip.namelist.return_value = ["song.mp3", "song.wav"]

        with patch('zipfile.ZipFile', return_value=mock_zip), \
             patch("src.presentation.widgets.library_widget.QMessageBox.question", return_value=QMessageBox.StandardButton.No), \
             patch.object(library_widget_with_conv, 'import_files_list', return_value=1), \
             patch("PyQt6.QtWidgets.QMessageBox.information"), \
             patch('os.remove') as mock_remove:
            
            library_widget_with_conv.dropEvent(event)
            
            # Should extract MP3 but NOT WAV
            mock_zip.extract.assert_called_once_with("song.mp3", os.path.dirname(zip_path))
            
            # Should NOT delete ZIP (because it still has the WAV)
            mock_remove.assert_not_called()
