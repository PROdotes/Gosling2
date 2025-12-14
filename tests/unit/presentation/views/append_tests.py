
    def test_populate_filter_tree(self, main_window, mock_services):
        # Setup mock data
        mock_services['library'].get_contributors_by_role.return_value = [
            (1, "Abba"), (2, "AC/DC"), (3, "Beatles")
        ]
        
        main_window._populate_filter_tree()
        
        # Verify root item
        model = main_window.filter_tree_model
        root = model.item(0)
        assert root.text() == "Artists"
        assert root.hasChildren()
        
        # Check A group
        a_group = root.child(0) # Logic sorts: A comes first
        assert a_group.text() == "A"
        assert a_group.rowCount() == 2 # Abba, AC/DC
        
        # Check B group
        b_group = root.child(1)
        assert b_group.text() == "B"
        assert b_group.rowCount() == 1 # Beatles

    def test_filter_tree_clicked(self, main_window, mock_services):
        # Setup mock click
        from PyQt6.QtGui import QStandardItem
        mock_item = QStandardItem("Abba")
        mock_item.setData("Abba", Qt.ItemDataRole.UserRole)
        
        # We need an index. Easier to assume model is populated/mocked or just mock itemFromIndex
        mock_index = MagicMock()
        main_window.filter_tree_model.itemFromIndex = MagicMock(return_value=mock_item)
        
        # Verify it calls service to filter
        mock_services['library'].get_songs_by_artist.return_value = (["Cols"], [[1, "Abba", "Song"]])
        
        main_window._on_filter_tree_clicked(mock_index)
        
        mock_services['library'].get_songs_by_artist.assert_called_with("Abba")
        assert main_window.library_model.rowCount() == 1

    def test_play_next(self, main_window, mock_services):
        # Setup playlist with 2 items
        main_window.playlist_widget.addItem("Song 1")
        main_window.playlist_widget.addItem("Song 2")
        
        # Mock item data retrieval
        item2 = main_window.playlist_widget.item(1)
        item2.setData(Qt.ItemDataRole.UserRole, {"path": "song2.mp3"})
        
        main_window._play_next()
        
        # Verify playing second item
        mock_services['playback'].load.assert_called_with("song2.mp3")
        mock_services['playback'].play.assert_called()
        
        # Verify first item removed
        # Note: Logic says "play next song ... delete the first one that's currently playing"
        # So count should decrease
        assert main_window.playlist_widget.count() == 1
        assert main_window.playlist_widget.item(0).text() == "Song 2"

    def test_volume_changed(self, main_window, mock_services):
        main_window._on_volume_changed(50)
        mock_services['playback'].set_volume.assert_called_with(0.5)
        
        main_window._on_volume_changed(100)
        mock_services['playback'].set_volume.assert_called_with(1.0)

    def test_update_position(self, main_window, mock_services):
        # Setup widgets to verify
        # Initial slider max is 0, duration update usually sets it
        main_window.playback_slider.setMaximum(10000)
        mock_services['playback'].player.duration.return_value = 10000
        
        main_window._update_position(5000)
        
        # Check slider
        assert main_window.playback_slider.value() == 5000
        # Check labels
        assert main_window.lbl_time_passed.text() == "00:05"
        # Remaining: 10000 - 5000 = 5000 -> 00:05 but label adds "- "
        assert main_window.lbl_time_remaining.text() == "- 00:05"
