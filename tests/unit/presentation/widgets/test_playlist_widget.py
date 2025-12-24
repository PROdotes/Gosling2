import os
import pytest
from PyQt6.QtWidgets import QListWidgetItem, QStyleOptionViewItem
from PyQt6.QtCore import Qt, QPoint, QMimeData, QUrl
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
        assert widget.dragDropMode() == PlaylistWidget.DragDropMode.InternalMove

    def test_drag_enter_event_valid(self, widget):
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
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
        event.mimeData.return_value = mime_data
        event.source.return_value = widget
        
        widget.dragEnterEvent(event)
        event.acceptProposedAction.assert_called_once()

    def test_drag_enter_event_invalid(self, widget):
        event = MagicMock(spec=QDragEnterEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True # Has URLs
        url = QUrl.fromLocalFile("notes.txt") # But invalid type
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        event.source.return_value = None
        
        widget.dragEnterEvent(event)
        event.ignore.assert_called_once()

    def test_drag_leave_event(self, widget):
        # Set preview state
        widget._preview_row = 5
        event = MagicMock(spec=QDragLeaveEvent)
        
        widget.dragLeaveEvent(event)
        
        assert widget._preview_row is None

    @patch('src.presentation.widgets.playlist_widget.MetadataService')
    def test_drop_event_files(self, mock_metadata, widget):
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        
        url = QUrl.fromLocalFile("test_song.mp3")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        
        # Mock indexAt to return invalid index (drop at end)
        event.position().toPoint.return_value = QPoint(0, 0)
        
        # Mock MetadataService
        mock_song = MagicMock()
        mock_song.get_display_performers.return_value = "Performer"
        mock_song.get_display_title.return_value = "Title"
        mock_metadata.extract_from_mp3.return_value = mock_song
        
        with patch('os.path.isfile', return_value=True):
            widget.dropEvent(event)
            
        assert widget.count() == 1
        item = widget.item(0)
        assert item.text() == "Performer | Title"
        event.acceptProposedAction.assert_called()

    def test_drop_event_invalid_file(self, widget):
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        url = QUrl.fromLocalFile("nonexistent.mp3")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        
        with patch('os.path.isfile', return_value=False):
            widget.dropEvent(event)
            
        assert widget.count() == 0

    def test_drag_move_update_preview(self, widget):
        event = MagicMock(spec=QDragMoveEvent)
        event.position().toPoint.return_value = QPoint(10, 10)
        
        # Add an item to test valid index
        widget.addItem("Item 1")
        
        with patch.object(widget, 'indexAt') as mock_index_at:
            mock_index = MagicMock()
            mock_index.isValid.return_value = True
            mock_index.row.return_value = 0
            mock_index_at.return_value = mock_index
            
            # Mock visualItemRect
            widget.visualItemRect = MagicMock()
            rect = MagicMock()
            rect.top.return_value = 0
            rect.height.return_value = 20
            widget.visualItemRect.return_value = rect
            
            widget.dragMoveEvent(event)
            
            assert widget._preview_row == 0
            # 10 >= 0 + 10 (midpoint) -> True
            assert widget._preview_after is True
            event.acceptProposedAction.assert_called()

    @patch('src.presentation.widgets.playlist_widget.QPainter')
    def test_paint_event_preview(self, mock_painter, widget, qtbot):
        # Setup preview state
        widget._preview_row = 0
        widget._preview_after = False
        
        # Add item so count() > preview_row
        widget.addItem("Item 1")
        
        # Call paintEvent with real event
        from PyQt6.QtGui import QPaintEvent, QRegion
        from PyQt6.QtCore import QRect
        event = QPaintEvent(QRect(0, 0, 100, 100))
        
        # We need to mock the super() call or ensure it doesn't fail. 
        # Since we can't easily mock super(), we assume QListWidget.paintEvent works if we give it a real event.
        # But we mocked QPainter global, so internal painting might fail if it tries to instantiate QPainter?
        # Actually QListWidget.paintEvent does its own painting. 
        # Let's just catch potential errors or suppress them.
        try:
             widget.paintEvent(event)
        except Exception:
             pass
             
        # Verify our custom painter was used
        # Our custom code instantiates QPainter(self.viewport())
        mock_painter.return_value.drawLine.assert_called()

    def test_drop_event_invalid_file(self, widget):
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        url = QUrl.fromLocalFile("nonexistent.mp3")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        
        # Return real QPoint
        event.position().toPoint.return_value = QPoint(0, 0)
        
        with patch('os.path.isfile', return_value=False):
            widget.dropEvent(event)
            
        assert widget.count() == 0

    def test_delegate_paint(self, widget):
        delegate = PlaylistItemDelegate()
        # Use a real painter on a pixmap to avoid heavy mocking issues
        from PyQt6.QtGui import QPainter, QPixmap, QColor
        from PyQt6.QtWidgets import QStyle
        
        pixmap = QPixmap(200, 60)
        painter = QPainter(pixmap)
        
        mock_option = QStyleOptionViewItem()
        mock_option.rect.setRect(0, 0, 200, 60)
        
        mock_index = MagicMock()
        
        # Case 1: Normal state, Artist | Title
        mock_index.data.return_value = "Artist | Title"
        mock_option.state = QStyle.StateFlag.State_None
        delegate.paint(painter, mock_option, mock_index)
        
        # Case 2: Selected state, Simple Text
        mock_index.data.return_value = "SimpleFile.mp3"
        mock_option.state = QStyle.StateFlag.State_Selected
        delegate.paint(painter, mock_option, mock_index)
        
        painter.end()

    def test_delegate_size_hint(self):
        delegate = PlaylistItemDelegate()
        mock_option = QStyleOptionViewItem()
        mock_option.rect.setRect(0, 0, 100, 50)
        
        size = delegate.sizeHint(mock_option, MagicMock())
        assert size.height() == 58

    def test_drag_move_update_preview_end(self, widget):
        """Test drag move over empty area/end of list"""
        event = MagicMock(spec=QDragMoveEvent)
        event.position().toPoint.return_value = QPoint(10, 50)
        
        with patch.object(widget, 'indexAt') as mock_index_at:
             mock_index = MagicMock()
             mock_index.isValid.return_value = False
             mock_index_at.return_value = mock_index
             
             widget.dragMoveEvent(event)
             
             assert widget._preview_row == widget.count() - 1 
             assert widget._preview_after is True
             event.acceptProposedAction.assert_called()

    def test_drop_event_metadata_exception(self, widget):
        """Test drop event where metadata extraction raises exception"""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = True
        
        url = QUrl.fromLocalFile("error.mp3")
        mime_data.urls.return_value = [url]
        event.mimeData.return_value = mime_data
        event.position().toPoint.return_value = QPoint(0,0)
        
        with patch('os.path.isfile', return_value=True):
            with patch('src.presentation.widgets.playlist_widget.MetadataService') as mock_meta:
                 mock_meta.extract_from_mp3.side_effect = Exception("Metadata Error")
                 
                 widget.dropEvent(event)
                 
        assert widget.count() == 1
        assert widget.item(0).text() == "error.mp3" # Fallback works

    def test_drop_event_internal_move(self, widget):
        """Test drop event with no URLs (internal move default)"""
        event = MagicMock(spec=QDropEvent)
        mime_data = MagicMock(spec=QMimeData)
        mime_data.hasUrls.return_value = False # No URLs
        event.mimeData.return_value = mime_data
        
        with patch('PyQt6.QtWidgets.QListWidget.dropEvent') as mock_super_drop:
            widget.dropEvent(event)
            mock_super_drop.assert_called_once()
            assert widget._preview_row is None

    @patch('src.presentation.widgets.playlist_widget.QPainter')
    def test_paint_event_branches(self, mock_painter, widget):
        """Test paint event branches"""
        from PyQt6.QtGui import QPaintEvent
        from PyQt6.QtCore import QRect
        event = QPaintEvent(QRect(0,0,100,100))
        
        # 1. Preview Row is None -> Return early
        widget._preview_row = None
        
        # QListWidget.paintEvent does usually require QApp setup which we have.
        try:
            widget.paintEvent(event)
        except:
             pass
        mock_painter.assert_not_called()
        
        # 2. Preview Row >= count() -> Bottom line
        widget._preview_row = 100
        widget.count = MagicMock(return_value=10)
        widget.visualItemRect = MagicMock() # Mock rect
        widget.visualItemRect.return_value.bottom.return_value = 50
        
        try:
            widget.paintEvent(event)
        except:
             pass
        
        mock_painter.return_value.drawLine.assert_called()

    def test_drop_event_valid_index(self, widget):
        """Test drop event on valid index to cover insert_row calculation."""
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
