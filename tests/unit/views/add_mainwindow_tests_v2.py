
    def test_add_selected_to_playlist(self, main_window, mock_services):
        # Setup selection
        mock_selection_model = MagicMock()
        mock_index = MagicMock()
        mock_index.row.return_value = 0
        mock_selection_model.selectedRows.return_value = [mock_index]
        main_window.table_view.selectionModel = MagicMock(return_value=mock_selection_model)
        
        # Setup Proxy map
        main_window.proxy_model.mapToSource = MagicMock(return_value=mock_index)
        
        # Setup Library Item Data
        mock_path_item = MagicMock()
        mock_path_item.text.return_value = "/path/to/song.mp3"
        mock_artist = MagicMock()
        mock_artist.text.return_value = "Artist"
        mock_title = MagicMock()
        mock_title.text.return_value = "Title"
        
        def item_side_effect(row, col):
            if col == 4: return mock_path_item
            if col == 1: return mock_artist
            if col == 2: return mock_title
            return None
            
        main_window.library_model.item = MagicMock(side_effect=item_side_effect)
        
        # Mock Playlist Widget addItem
        main_window.playlist_widget.addItem = MagicMock()
        
        main_window._add_selected_to_playlist()
        
        # Verify item added
        main_window.playlist_widget.addItem.assert_called()
        args = main_window.playlist_widget.addItem.call_args[0][0]
        # Check text format
        assert args.text() == "Artist | Title"

    def test_on_playlist_double_click(self, main_window, mock_services):
        mock_item = MagicMock()
        mock_item.data.return_value = {"path": "/path/to/song.mp3"}
        
        main_window._on_playlist_double_click(mock_item)
        
        mock_services['playback'].load.assert_called_with("/path/to/song.mp3")
        mock_services['playback'].play.assert_called()

    @patch('src.presentation.views.main_window.QFileDialog')
    @patch('src.presentation.views.main_window.os.walk')
    @patch('src.presentation.views.main_window.QMessageBox')
    def test_scan_folder_error_handling(self, mock_msg, mock_walk, mock_dialog, main_window, mock_services):
        mock_dialog.getExistingDirectory.return_value = "/music/folder"
        mock_walk.return_value = [("/music/folder", [], ["song1.mp3"])]
        
        # Simulate error triggers exception print but no crash
        mock_services['library'].add_file.side_effect = Exception("DB Error")
        
        # Should not crash
        main_window._scan_folder()
        
        # Verify add_file attempted
        assert mock_services['library'].add_file.call_count == 1
