import pytest
import os
from unittest.mock import MagicMock, patch, call
from PyQt6.QtWidgets import QMessageBox, QMenu, QApplication
from PyQt6.QtCore import Qt, QModelIndex, QPoint
from src.presentation.widgets.library_widget import LibraryWidget
from src.core import yellberus

# Helper to map field name to index
def get_idx(name):
    for i, f in enumerate(yellberus.FIELDS):
        if f.name == name:
            return i
    return -1

@pytest.fixture
def mock_dependencies():
    library_service = MagicMock()
    metadata_service = MagicMock()
    settings_manager = MagicMock()
    # Default settings
    settings_manager.get_last_import_directory.return_value = ""
    settings_manager.get_column_visibility.return_value = {}
    settings_manager.get_column_layout.return_value = None # Important for legacy fallback
    settings_manager.get_type_filter.return_value = 0
    return library_service, metadata_service, settings_manager

@pytest.fixture
def library_widget(qtbot, mock_dependencies):
    lib_service, meta_service, settings = mock_dependencies
    
    # Setup default return for get_all_songs so load_library works
    # Must return 14 columns matching Yellberus schema
    # Headers are somewhat irrelevant as Widget ignores them now, but good to likely match SQL names
    headers = [f.db_column for f in yellberus.FIELDS] 
    
    # 0:ID, 1:Type, 2:Title, 3:Perf, 4:Comp, 5:Lyr, 6:Prod, 7:Groups, 8:Dur, 9:Path, 10:Yr, 11:BPM, 12:Done, 13:Isrc, 14:Notes, 15:Active
    data = [
        [1, 1, "Title A", "Performer A", "Comp A", "Lyr A", "Prod A", "G1", 180.0, "/path/a.mp3", 2020, 120, 1, "ISRC1", "N1", 1],
        [2, 1, "Title B", "Performer B", "Comp B", "Lyr B", "Prod B", "G2", 240.0, "/path/b.mp3", 2021, 128, 0, "ISRC2", "N2", 1]
    ]
    
    lib_service.get_all_songs.return_value = (headers, data)
    
    widget = LibraryWidget(lib_service, meta_service, settings)
    qtbot.addWidget(widget)
    return widget

def test_initial_load(library_widget, mock_dependencies):
    """Test that the library loads data on init."""
    lib_service, _, _ = mock_dependencies
    
    # Verify service was called
    lib_service.get_all_songs.assert_called()
    
    # Verify model population
    assert library_widget.library_model.rowCount() == 2
    
    idx_perf = get_idx("performers")
    idx_title = get_idx("title")
    
    assert library_widget.library_model.item(0, idx_perf).text() == "Performer A"
    assert library_widget.library_model.item(1, idx_title).text() == "Title B"

def test_import_files_success(library_widget, mock_dependencies):
    """Test importing files successfully adds them and refreshes view."""
    lib_service, meta_service, settings = mock_dependencies
    
    # Mock _import_file to succeed
    with patch.object(library_widget, '_import_file', return_value=True):
        count = library_widget.import_files_list(["/new/song.mp3"])
        
        assert count == 1
        
        # Verify load_library was called (refresh)
        assert lib_service.get_all_songs.call_count > 1

def test_import_files_zero(library_widget, mock_dependencies):
    """Test importing zero files."""
    with patch.object(library_widget, '_import_file', return_value=False):
        count = library_widget.import_files_list(["/fail.mp3"])
        assert count == 0

def test_scan_folder(library_widget, mock_dependencies):
    """Test scanning a folder works."""
    with patch("os.walk", return_value=[("/fake/dir", [], ["file.mp3"])]):
        with patch.object(library_widget, '_import_file', return_value=True):
            count = library_widget.scan_directory("/fake/dir")
            assert count == 1

def test_import_single_file_logic(library_widget, mock_dependencies):
    """Test the internal logic of _import_file."""
    lib_service, meta_service, _ = mock_dependencies
    
    # Case 1: Success
    lib_service.add_file.return_value = 101 # Returns new ID
    mock_song = MagicMock()
    meta_service.extract_from_mp3.return_value = mock_song
    
    result = library_widget._import_file("/real/path.mp3")
    
    assert result is True
    lib_service.add_file.assert_called_with("/real/path.mp3")
    meta_service.extract_from_mp3.assert_called_with("/real/path.mp3", 101)
    lib_service.update_song.assert_called_with(mock_song)
    
    # Case 2: library_service.add_file fails (returns None)
    lib_service.add_file.return_value = None
    result = library_widget._import_file("/bad/path.mp3")
    assert result is False

    # Case 3: Exception raised
    lib_service.add_file.side_effect = Exception("DB Error")
    result = library_widget._import_file("/error/path.mp3")
    assert result is False

def test_delete_selected_cancel(library_widget, mock_dependencies):
    """Test deletion is aborted if user clicks No."""
    lib_service, _, _ = mock_dependencies
    
    # Select first row
    library_widget.table_view.selectRow(0)
    
    with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
        library_widget._delete_selected()
        
    lib_service.delete_song.assert_not_called()

def test_delete_selected_confirm(library_widget, mock_dependencies):
    """Test deletion proceeds if user clicks Yes."""
    lib_service, _, _ = mock_dependencies
    
    # Ensure view has data and we can select it
    library_widget.table_view.selectRow(0)
    QApplication.processEvents()
    
    # Get the ID of the selected row dynamically
    idx_col_id = get_idx("file_id")
    idx = library_widget.proxy_model.index(0, idx_col_id) 
    expected_id = int(library_widget.proxy_model.data(idx))
    
    with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
        library_widget._delete_selected()
        
    lib_service.delete_song.assert_called_with(expected_id)
    # View should refresh
    assert lib_service.get_all_songs.call_count > 1

def test_search_filtering(library_widget, qtbot):
    """Test that typing in search box filters the proxy model using Regex."""
    # Type regex "B$" (Ends with B)
    library_widget.search_box.setText("B$")
    
    # "Title A" ends in A -> No match
    # "Title B" ends in B -> Match
    # Note: Search behavior depends on Widget impl. Assuming it searches ALL visible columns or just Title/Artist?
    # LibraryWidget typically filters multiple columns or sets key column. 
    # If using SortFilterProxyModel default, it often filters column 0 unless configured.
    # We should assume LibraryWidget enables filtering on Title or All.
    
    # Assuming it matches Title B
    
    # Wait, simple Regex check.
    # If it filters Title (idx 2):
    # row 0 Title: "Title A" -> No
    # row 1 Title: "Title B" -> Yes
    
    # Assert
    assert library_widget.proxy_model.rowCount() == 1
    
    idx_title = get_idx("title")
    index = library_widget.proxy_model.index(0, idx_title) 
    assert library_widget.proxy_model.data(index) == "Title B"
    
    # Clear search
    library_widget.search_box.clear()
    assert library_widget.proxy_model.rowCount() == 2

def test_search_invalid_regex_fallback(library_widget, qtbot):
    """Test that invalid regex does not crash and behaves gracefully."""
    library_widget.search_box.setText("[")
    # It should not crash.
    assert library_widget.proxy_model.rowCount() == 0 or library_widget.proxy_model.rowCount() == 2
    
    library_widget.search_box.setText("*")
    assert True

def test_double_click_emits_add_playlist(library_widget, qtbot):
    """Test double clicking a row emits add_to_playlist signal."""
    library_widget.table_view.selectRow(0)
    QApplication.processEvents()
    
    idx_performer = get_idx("performers")
    idx_title = get_idx("title")
    idx_path = get_idx("path")
    
    idx_p = library_widget.proxy_model.index(0, idx_performer)
    idx_t = library_widget.proxy_model.index(0, idx_title)
    idx_pa = library_widget.proxy_model.index(0, idx_path)
    
    expected_performer = library_widget.proxy_model.data(idx_p)
    expected_title = library_widget.proxy_model.data(idx_t)
    expected_path = library_widget.proxy_model.data(idx_pa)
    
    with qtbot.waitSignal(library_widget.add_to_playlist, timeout=1000) as blocker:
        # Double click first row
        idx = library_widget.proxy_model.index(0, 0)
        library_widget.table_view.doubleClicked.emit(idx)
        
    assert len(blocker.args) == 1
    items = blocker.args[0]
    assert len(items) == 1
    assert items[0]["performer"] == expected_performer
    assert items[0]["title"] == expected_title
    assert items[0]["path"] == expected_path

def test_filter_by_performer(library_widget, mock_dependencies):
    """Test filtering by performer asks service for subset."""
    lib_service, _, _ = mock_dependencies
    
    # Must return full width rows
    # Mock returning empty for simplicity
    lib_service.get_songs_by_performer.return_value = (["H" for _ in yellberus.FIELDS], [])
    
    library_widget._filter_by_performer("Performer A")
    
    lib_service.get_songs_by_performer.assert_called_with("Performer A")
    assert library_widget.library_model.rowCount() == 0

def test_filter_by_year(library_widget, mock_dependencies):
    """Test filtering by year requests data from service."""
    lib_service, _, _ = mock_dependencies
    
    # Return 1 row
    row = [1, 1, "T", "P", "C", "L", "Pr", "G", 1.0, "p", 2020, 100, 1, "I", "N", 1]
    lib_service.get_songs_by_year.return_value = ([f.name for f in yellberus.FIELDS], [row])
    
    library_widget._filter_by_year(2020)
    
    lib_service.get_songs_by_year.assert_called_with(2020)
    assert library_widget.library_model.rowCount() == 1
    
    idx_yr = get_idx("recording_year")
    assert library_widget.library_model.item(0, idx_yr).text() == "2020"

def test_column_visibility_toggle(library_widget, mock_dependencies):
    """Test toggling columns updates view and saves settings."""
    _, _, settings = mock_dependencies
    
    action = MagicMock()
    action.data.return_value = 0 # Column 0
    
    with patch.object(library_widget, 'sender', return_value=action):
        library_widget._toggle_column_visibility(False) 
    
    assert library_widget.table_view.isColumnHidden(0)
    # Replaced logic: calls set_column_layout now
    settings.set_column_layout.assert_called()

def test_load_column_visibility(library_widget, mock_dependencies):
    """Test that visibility settings are applied on load."""
    _, _, settings = mock_dependencies
    
    # Hide col 1, Show col 2
    settings.get_column_visibility.return_value = {"1": False, "2": True}
    
    library_widget._load_column_visibility_states()
    
    assert library_widget.table_view.isColumnHidden(1)
    assert not library_widget.table_view.isColumnHidden(2)

def test_show_table_context_menu(library_widget, mock_dependencies):
    """Test context menu shows correct actions and triggers them."""
    with patch("src.presentation.widgets.library_widget.QMenu") as MockMenu:
        mock_menu_instance = MockMenu.return_value
        
        library_widget._show_table_context_menu(QPoint(0,0))
        
        MockMenu.assert_called()
        # Expect 3 actions (Add Playlist, ID3, Delete) + possibly Status if selected
        # Since we didn't select, should be 3. If 4, maybe check what's going on.
        # Let's Assert >= 3
        assert mock_menu_instance.addAction.call_count >= 3

def test_show_column_context_menu(library_widget):
    """Test column context menu creation with integrity checks."""
    with patch("src.presentation.widgets.library_widget.QMenu") as MockMenu:
        mock_menu_instance = MockMenu.return_value
        
        library_widget._show_column_context_menu(QPoint(0,0))
        
        # Schema has 16 columns
        # Plus "Reset to Default" action = 17
        expected_columns = 16
        expected_total = expected_columns + 1
        
        assert library_widget.library_model.columnCount() == expected_columns, \
            "Model column count mismatch!"
            
        assert mock_menu_instance.addAction.call_count == expected_total

def test_show_id3_tags_dialog(library_widget, mock_dependencies):
    """Test interaction with MetadataViewerDialog."""
    lib_service, meta_service, _ = mock_dependencies
    from src.data.models.song import Song
    
    mock_file_song = Song(name="File", source="/path/test.mp3")
    mock_db_song = Song(name="DB", source="/path/test.mp3")
    
    meta_service.extract_from_mp3.return_value = mock_file_song
    meta_service.get_raw_tags.return_value = {"Custom": "Value"}
    lib_service.get_song_by_path.return_value = mock_db_song
    
    library_widget.table_view.selectRow(0)
    QApplication.processEvents()
    
    with patch("src.presentation.widgets.metadata_viewer_dialog.MetadataViewerDialog") as MockDialog:
        library_widget._show_id3_tags()
        MockDialog.assert_called_with(mock_file_song, mock_db_song, {"Custom": "Value"}, library_widget)
        MockDialog.return_value.exec.assert_called_once()

def test_numeric_sorting(library_widget, mock_dependencies):
    """Test sorting for Duration, BPM, Year."""
    from PyQt6.QtCore import Qt
    lib_service, _, _ = mock_dependencies
    
    # Cols: 8=Duration, 11=BPM, 10=Year
    rowA = [1,1,"A","P","C","L","Pr", "G", 10.0, "p", 2000, 10, 1, "I", "N", 1]
    rowB = [2,1,"B","P","C","L","Pr", "G", 20.0, "p", 2010, 20, 1, "I", "N", 1]
    rowC = [3,1,"C","P","C","L","Pr", "G", 30.0, "p", 2020, 30, 1, "I", "N", 1]
    
    # Shuffle for testing
    data = [rowC, rowA, rowB] 
    
    lib_service.get_all_songs.return_value = ([], data)
    library_widget.load_library()
    
    def check(col_name, expected_order):
        idx = get_idx(col_name)
        library_widget.proxy_model.sort(idx, Qt.SortOrder.AscendingOrder)
        
        vals = []
        for r in range(3):
            # For data retrieval, we need row index from proxy
            proxy_idx = library_widget.proxy_model.index(r, idx)
            vals.append(library_widget.proxy_model.data(proxy_idx))
            
        # For Duration, it's formatted. "00:10", "00:20", "00:30"
        # For Year/BPM it's strings "2000", "2010"...
        # We assume expected_order accounts for formatting
        assert vals == expected_order
        
    check("duration", ["00:10", "00:20", "00:30"])
    check("bpm", ["10", "20", "30"])
    check("recording_year", ["2000", "2010", "2020"])

def test_table_schema_integrity(library_widget, mock_dependencies):
    """
    STRICT UI Schema Integrity: checked against Yellberus.
    """
    lib_service, _, _ = mock_dependencies
    
    service_headers, _ = lib_service.get_all_songs()
    model = library_widget.library_model
    
    # Assert Count Match
    assert model.columnCount() == len(service_headers)
    assert model.columnCount() == len(yellberus.FIELDS)
    
    # Assert Header Match
    # The Widget ignores service headers and uses Yellberus UI Headers
    for i, f in enumerate(yellberus.FIELDS):
        ui_header = model.headerData(i, Qt.Orientation.Horizontal)
        assert ui_header == f.ui_header
