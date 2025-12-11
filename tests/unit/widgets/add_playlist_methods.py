
    @patch('src.presentation.widgets.playlist_widget.QPainter')
    def test_paint_event_preview(self, mock_painter, widget, qtbot):
        # Setup preview state
        widget._preview_row = 0
        widget._preview_after = False
        
        # Call paintEvent
        widget.paintEvent(MagicMock())
        
        # Verify painter was used
        mock_painter.return_value.drawLine.assert_called()

    def test_delegate_paint(self, widget):
        delegate = PlaylistItemDelegate()
        mock_painter = MagicMock()
        mock_option = QStyleOptionViewItem()
        mock_option.rect.setRect(0, 0, 100, 50)
        mock_index = MagicMock()
        mock_index.data.return_value = "Artist | Title"
        
        delegate.paint(mock_painter, mock_option, mock_index)
        
        # Verify drawing calls
        mock_painter.drawText.assert_called()
        mock_painter.drawEllipse.assert_called()

    def test_delegate_size_hint(self):
        delegate = PlaylistItemDelegate()
        mock_option = QStyleOptionViewItem()
        mock_option.rect.setRect(0, 0, 100, 50)
        
        size = delegate.sizeHint(mock_option, MagicMock())
        assert size.height() == 54
