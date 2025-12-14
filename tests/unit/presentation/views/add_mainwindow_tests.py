
    @patch('src.presentation.views.main_window.QFileDialog')
    @patch('src.presentation.views.main_window.QMessageBox')
    def test_import_files(self, mock_msg, mock_dialog, main_window, mock_services):
        mock_dialog.getOpenFileNames.return_value = (["/path/to/song.mp3"], "mp3")
        mock_services['library'].add_file.return_value = 1
        mock_song = MagicMock()
        mock_services['metadata'].extract_from_mp3.return_value = mock_song

        main_window._import_files()

        mock_services['library'].add_file.assert_called_with("/path/to/song.mp3")
        mock_services['metadata'].extract_from_mp3.assert_called()
        mock_services['library'].update_song.assert_called_with(mock_song)
        # Should verify library reloaded
        assert main_window.library_model.rowCount() == 2 # From previous mock Setup

    @patch('src.presentation.views.main_window.QFileDialog')
    @patch('src.presentation.views.main_window.os.walk')
    @patch('src.presentation.views.main_window.QMessageBox')
    def test_scan_folder(self, mock_msg, mock_walk, mock_dialog, main_window, mock_services):
        mock_dialog.getExistingDirectory.return_value = "/music/folder"
        mock_walk.return_value = [("/music/folder", [], ["song1.mp3", "image.jpg"])]
        
        mock_services['library'].add_file.return_value = 1
        
        main_window._scan_folder()
        
        # Check add_file called for song1.mp3 but not image.jpg
        # os.path.join used in implementation, so we expect full path
        # But constructing precise full path mock in portable way is hard, just check if called
        assert mock_services['library'].add_file.call_count == 1

    @patch('src.presentation.views.main_window.QMessageBox')
    def test_delete_selected(self, mock_msg, main_window, mock_services):
        # Mock selection
        # This is tricky with QTableView and Proxies.
        # We invoke _delete_selected directly after mocking selectionModel
        
        mock_selection_model = MagicMock()
        mock_index = MagicMock()
        mock_index.row.return_value = 0
        mock_selection_model.selectedRows.return_value = [mock_index]
        
        main_window.table_view.selectionModel = MagicMock(return_value=mock_selection_model)
        
        # Mock mapToSource
        main_window.proxy_model.mapToSource = MagicMock(return_value=mock_index)
        
        # Mock item in library model to have ID 123
        mock_item_id = MagicMock()
        mock_item_id.text.return_value = "123"
        main_window.library_model.item = MagicMock(return_value=mock_item_id)
        
        # Mock confirmation Yes
        mock_msg.question.return_value = QMessageBox.StandardButton.Yes
        
        main_window._delete_selected()
        
        mock_services['library'].delete_song.assert_called_with(123)

    def test_show_table_context_menu(self, main_window):
        # Just ensure it doesn't crash and creates a menu
        with patch('src.presentation.views.main_window.QMenu') as mock_menu:
            main_window._show_table_context_menu(QPoint(0,0))
            mock_menu.return_value.exec.assert_called()
