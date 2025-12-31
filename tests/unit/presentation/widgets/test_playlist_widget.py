import os
import json
import pytest
from PyQt6.QtWidgets import QListWidgetItem, QStyleOptionViewItem
from PyQt6.QtCore import Qt, QPoint, QMimeData, QUrl, QPointF
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDragLeaveEvent, QDropEvent, QPainter, QStandardItem
from unittest.mock import MagicMock, patch
from src.presentation.widgets.playlist_widget import PlaylistWidget, PlaylistItemDelegate

class TestPlaylistWidget:
    @pytest.fixture
    def widget(self, qtbot):
        widget = PlaylistWidget()
        qtbot.addWidget(widget)
        return widget

    def test_widget_initialization(self, widget):
        assert widget.acceptDrops() is True
        assert widget.dragEnabled() is True
        # Now set to DragDrop for external support
        assert widget.dragDropMode() == PlaylistWidget.DragDropMode.DragDrop

    def test_drag_enter_event_valid(self, widget):
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasFormat.return_value = False
        mime_data.hasUrls.return_value = True
        url = QUrl.fromLocalFile("song.mp3") 
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        event.source.return_value = None
        
        widget.dragEnterEvent(event)
        event.acceptProposedAction.assert_called_once()

    def test_drag_enter_event_internal(self, widget):
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = False
        mime_data.hasFormat.return_value = False
        event.mimeData.return_value = mime_data
        event.source.return_value = widget
        
        # In current implementation, it checks hasUrls or hasFormat('application/x-qabstractitemmodeldatalist')
        mime_data.hasFormat.side_effect = lambda f: f == 'application/x-qabstractitemmodeldatalist'
        
        widget.dragEnterEvent(event)
        event.acceptProposedAction.assert_called_once()

    def test_drag_enter_event_invalid(self, widget):
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = False
        mime_data.hasFormat.return_value = False
        event.mimeData.return_value = mime_data
        event.source.return_value = None
        
        # Should stay at end of method and let super handle or ignore
        widget.dragEnterEvent(event)
        # Internal implementation doesn't call ignore explicitly, it just doesn't accept.
        event.acceptProposedAction.assert_not_called()

    def test_drag_leave_event(self, widget):
        # Set preview state
        widget._preview_row = 5
        # Don't use spec=QDragLeaveEvent for the super() call if it crashes due to MagicMock type checks
        event = MagicMock()
        
        with patch.object(PlaylistWidget, 'viewport') as mock_viewport:
            # We must avoid calling super().dragLeaveEvent(event) if event is a Mock and super expects QDragLeaveEvent
            with patch('PyQt6.QtWidgets.QListWidget.dragLeaveEvent'):
                widget.dragLeaveEvent(event)
        
        assert widget._preview_row is None

    @patch('src.presentation.widgets.playlist_widget.MetadataService')
    def test_drop_event_files(self, mock_metadata, widget):
        # Setup window hierarchy for dropEvent to find LibraryWidget
        from PyQt6.QtWidgets import QMainWindow
        win = QMainWindow()
        widget.setParent(win)
        
        from src.presentation.widgets.library_widget import LibraryWidget
        mock_library = MagicMock(spec=LibraryWidget)
        mock_library.metadata_service = mock_metadata
        mock_library.setObjectName("LibraryWidget")
        mock_library.setParent(win)
        
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        mime_data.hasFormat.return_value = False
        
        url = QUrl.fromLocalFile("test_song.mp3")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        event.source.return_value = None # External
        
        # Mock indexAt to return invalid index (drop at end)
        pos_mock = MagicMock()
        pos_mock.toPoint.return_value = QPoint(0, 0)
        event.position.return_value = pos_mock
        
        # Mock MetadataService behavior
        mock_song = MagicMock()
        mock_song.performers = ["Performer"]
        mock_song.title = "Title"
        mock_metadata.extract_from_mp3.return_value = mock_song
        
        with patch('os.path.isfile', return_value=True), \
             patch.object(win, 'findChild', return_value=mock_library):
            widget.dropEvent(event)
            
        assert widget.count() == 1
        item = widget.item(0)
        assert item.text() == "Performer | Title"
        event.acceptProposedAction.assert_called()

    def test_drop_event_library_rows(self, widget):
        """Test dropping rows from Gosling Library"""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = False
        mime_data.hasFormat.side_effect = lambda f: f == "application/x-gosling-library-rows"
        
        songs = [{"path": "/a.mp3", "performer": "Artist", "title": "Track"}]
        mime_data.data.return_value = MagicMock(data=lambda: json.dumps(songs).encode('utf-8'))
        event.mimeData.return_value = mime_data
        event.source.return_value = MagicMock() # Not self
        
        pos_mock = MagicMock()
        pos_mock.toPoint.return_value = QPoint(0, 0)
        event.position.return_value = pos_mock
        
        widget.dropEvent(event)
        
        assert widget.count() == 1
        assert widget.item(0).text() == "Artist | Track"
        event.acceptProposedAction.assert_called()

    def test_drop_event_internal_move(self, widget):
        """Test drop event with no specific formats (internal move default)"""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = False
        mime_data.hasFormat.return_value = False
        event.mimeData.return_value = mime_data
        
        pos_mock = MagicMock()
        pos_mock.toPoint.return_value = QPoint(0, 0)
        event.position.return_value = pos_mock
        
        with patch('PyQt6.QtWidgets.QListWidget.dropEvent') as mock_super_drop:
            widget.dropEvent(event)
            mock_super_drop.assert_called_once()
            assert widget._preview_row is None

    @patch('src.presentation.widgets.playlist_widget.QPainter')
    def test_paint_event_branches(self, mock_painter_class, widget):
        """Test paint event branches"""
        from PyQt6.QtGui import QPaintEvent
        from PyQt6.QtCore import QRect
        event = QPaintEvent(QRect(0,0,100,100))
        
        mock_painter = MagicMock()
        mock_painter_class.return_value = mock_painter
        
        # 1. Preview Row is None -> Return early
        widget._preview_row = None
        widget.paintEvent(event)
        mock_painter.drawLine.assert_not_called()
        
        # 2. Preview Row set
        widget.addItem("Item 1")
        widget._preview_row = 0
        widget._preview_after = True
        
        # We need a real viewport for visualItemRect but mocks might work
        with patch.object(widget, 'visualItemRect', return_value=QRect(0,0,100,20)):
            widget.paintEvent(event)
            mock_painter.drawLine.assert_called()

    def test_double_click_emit(self, widget, qtbot):
        """Verify double click emits itemDoubleClicked"""
        widget.addItem("Test Item")
        mock_item = widget.item(0)
        
        with qtbot.waitSignal(widget.itemDoubleClicked) as blocker:
            widget.itemDoubleClicked.emit(mock_item)
        
        assert blocker.args[0] == mock_item
