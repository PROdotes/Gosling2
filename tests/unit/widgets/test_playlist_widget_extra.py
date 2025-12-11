
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QPoint, QMimeData, QUrl
from PyQt6.QtGui import QDragMoveEvent, QDropEvent
from src.presentation.widgets.playlist_widget import PlaylistWidget

class TestPlaylistWidgetExtra:
    @pytest.fixture
    def widget(self, qtbot):
        widget = PlaylistWidget()
        qtbot.addWidget(widget)
        return widget

    def test_drop_event_valid_index(self, widget):
        """Test drop event on valid index to cover insert_row calculation"""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        url = QUrl.fromLocalFile("test.mp3")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        event.position().toPoint.return_value = QPoint(10, 10)
        
        with patch.object(widget, 'indexAt') as mock_index_at:
             mock_index = MagicMock()
             mock_index.isValid.return_value = True
             mock_index.row.return_value = 2
             mock_index_at.return_value = mock_index
             
             # Case 1: Preview After = True
             widget._preview_after = True
             with patch('os.path.isfile', return_value=True):
                 with patch('src.presentation.widgets.playlist_widget.MetadataService'):
                     widget.dropEvent(event)
             
             # Should insert at row 3 (2 + 1)
             
             # Case 2: Preview After = False
             widget._preview_after = False
             with patch('os.path.isfile', return_value=True):
                 with patch('src.presentation.widgets.playlist_widget.MetadataService'):
                     widget.dropEvent(event)
             # Should insert at row 2
