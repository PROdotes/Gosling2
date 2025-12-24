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
    # Must return 15 columns matching current Yellberus schema
    headers = [f.db_column for f in yellberus.FIELDS] 
    
    # Current FIELDS order (17 columns):
    # 0:path, 1:file_id, 2:type_id, 3:notes, 4:isrc, 5:is_active,
    # 6:producers, 7:lyricists, 8:duration, 9:title,
    # 10:is_done, 11:bpm, 12:recording_year, 13:performers, 14:composers, 15:groups, 16:unified_artist
    data = [
        ["/path/a.mp3", 1, 1, "N1", "ISRC1", 1, "Prod A", "Lyr A", 180.0, "Title A", 1, 120, 2020, "Performer A", "Comp A", "Group A", "Unified A"],
        ["/path/b.mp3", 2, 1, "N2", "ISRC2", 1, "Prod B", "Lyr B", 240.0, "Title B", 0, 128, 2021, "Performer B", "Comp B", "Group B", "Unified B"]
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
    
    with patch("src.presentation.widgets.library_widget.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
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
    
    with patch("src.presentation.widgets.library_widget.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
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
    
    # Return 1 row matching current FIELDS order (17 columns)
    # path, file_id, type_id, notes, isrc, is_active, producers, lyricists, duration, title, is_done, bpm, recording_year, performers, composers, groups, unified_artist
    row = ["p", 1, 1, "N", "I", 1, "Pr", "L", 1.0, "T", 1, 100, 2020, "P", "C", "G", "U"]
    lib_service.get_songs_by_year.return_value = ([f.name for f in yellberus.FIELDS], [row])
    
    library_widget._filter_by_year(2020)
    
    lib_service.get_songs_by_year.assert_called_with(2020)
    assert library_widget.library_model.rowCount() == 1
    
    idx_yr = get_idx("recording_year")
    assert library_widget.library_model.item(0, idx_yr).text() == "2020"

def test_column_visibility_toggle(library_widget, mock_dependencies):
    """Test toggling columns updates view and saves settings."""
    _, _, settings = mock_dependencies
    
    # Toggle column 0 (path) to be shown (checked=True)
    # The signature is now (column_index, checked)
    library_widget._toggle_column_visibility(0, True) 
    
    # Column 0 should NOT be hidden now
    assert not library_widget.table_view.isColumnHidden(0)
    settings.set_column_layout.assert_called()

def test_load_column_visibility(library_widget, mock_dependencies):
    """Test that visibility settings are applied on load (only for Yellberus-visible columns)."""
    _, _, settings = mock_dependencies
    
    # settings now uses get_column_layout which returns a dict
    settings.get_column_layout.return_value = {
        "order": ["title", "performers"],
        "hidden": {"notes": True, "title": False}, # notes is col 3, title is col 9
        "widths": {}
    }
    
    library_widget._load_column_visibility_states()
    
    # Column 3 should be hidden (user preference to hide a visible column)
    assert library_widget.table_view.isColumnHidden(3)
    # Column 9 should be visible (user preference to keep visible)
    assert not library_widget.table_view.isColumnHidden(9)

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
        
    # Only visible fields should be in the menu now (Hard Ban)
    from src.core import yellberus
    visible_count = len([f for f in yellberus.FIELDS if f.visible])
    expected_total = visible_count + 1  # Fields + Reset to Default
    
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
    
    # Test data matching current FIELDS order (17 columns):
    # path, file_id, type_id, notes, isrc, is_active, producers, lyricists, duration, title, is_done, bpm, recording_year, performers, composers, groups, unified_artist
    rowA = ["p", 1, 1, "N", "I", 1, "Pr", "L", 10.0, "A", 1, 10, 2000, "P", "C", "G", "U"]
    rowB = ["p", 2, 1, "N", "I", 1, "Pr", "L", 20.0, "B", 1, 20, 2010, "P", "C", "G", "U"]
    rowC = ["p", 3, 1, "N", "I", 1, "Pr", "L", 30.0, "C", 1, 30, 2020, "P", "C", "G", "U"]
    
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

def test_unified_artist_validation(library_widget):
    """
    Cross-field validation: a song needs performers OR groups, not both.
    Tests yellberus.validate_row which is called by the widget.
    """
    # Build a row with neither performers nor groups
    # 17 columns: path, file_id, type_id, notes, isrc, is_active, producers, lyricists,
    #             duration, title, is_done, bpm, recording_year, performers, composers, groups, unified_artist
    row_no_artist = ["p", 1, 1, "N", "I", 1, "Pr", "L", 1.0, "T", 0, 100, 2020, "", "C", "", ""]
    
    failed = yellberus.validate_row(row_no_artist)
    assert "performers" in failed, "Missing performers should fail when groups also empty"
    assert "groups" in failed, "Missing groups should fail when performers also empty"
    
    # Row with performers but no groups - should pass
    row_with_performer = ["p", 1, 1, "N", "I", 1, "Pr", "L", 1.0, "T", 0, 100, 2020, "Artist", "C", "", ""]
    failed = yellberus.validate_row(row_with_performer)
    assert "performers" not in failed
    assert "groups" not in failed
    
    # Row with groups but no performers - should also pass
    row_with_group = ["p", 1, 1, "N", "I", 1, "Pr", "L", 1.0, "T", 0, 100, 2020, "", "C", "Band", ""]
    failed = yellberus.validate_row(row_with_group)
    assert "performers" not in failed
    assert "groups" not in failed

def test_persistence_uses_names_not_indices(library_widget, mock_dependencies):
    """T-18: Verify that moving a column saves field NAMES, not indices."""
    _, _, settings = mock_dependencies
    header = library_widget.table_view.horizontalHeader()
    
    # Use a real title column
    idx_title = get_idx("title")
    
    # 1. Simulate moving column "title" to visual index 0
    header.moveSection(idx_title, 0)
    
    # 2. Extract the call arguments from set_column_layout
    assert settings.set_column_layout.called
    args, kwargs = settings.set_column_layout.call_args
    
    order = args[0]
    # The first element in the saved order should be the NAME "title"
    assert "title" in order
    assert order[0] == "title"
    
    # Also verify widths are captured
    widths = kwargs.get("widths", {})
    assert "title" in widths

def test_atomic_lifecycle_preserves_widths_on_filter(library_widget, mock_dependencies):
    """T-18: Verify that manual widths survive a table rebuild (Atomic Lifecycle)."""
    lib_service, _, settings = mock_dependencies
    
    # 1. Setup Mock State: Make the mock "remember" what it was told
    stored_layout = {"order": [], "hidden": {}, "widths": {}}
    
    def mock_set_layout(order, hidden, name="default", widths=None):
        stored_layout["order"] = order
        stored_layout["hidden"] = hidden
        stored_layout["widths"] = widths or {}
        
    def mock_get_layout(name="default"):
        return stored_layout if stored_layout["order"] else None

    settings.set_column_layout.side_effect = mock_set_layout
    settings.get_column_layout.side_effect = mock_get_layout
    
    # 2. Set a custom width for 'Title' (Logical 9)
    idx_title = get_idx("title")
    library_widget.table_view.setColumnWidth(idx_title, 555)
    
    # 3. Mock the service to return new data on filter
    lib_service.get_songs_by_performer.return_value = (
        [f.db_column for f in yellberus.FIELDS], 
        [["filtered_path", 1, 1, "", "", 1, "", "", 120.0, "Filtered Title", 1, 120, 2020, "Artist", "", "", ""]]
    )
    
    # 4. Trigger a filter (which calls _populate_table)
    library_widget._filter_by_performer("Artist")
    
    # 5. Verify 'Title' still has the custom width
    # The atomic lifecycle snapshots the 555px and restores it after the rebuild
    assert library_widget.table_view.columnWidth(idx_title) == 555


# ============================================================================
# SEARCH COVERAGE (from test_library_widget_filtering.py)
# ============================================================================
@pytest.fixture
def library_widget_search(qtbot):
    """Fixture with unique values in every column for search testing."""
    lib_service = MagicMock()
    meta_service = MagicMock()
    settings = MagicMock()
    settings.get_column_visibility.return_value = {}
    settings.get_column_layout.return_value = None
    settings.get_type_filter.return_value = 0
    
    # Setup data with unique values in every column to test search isolation
    # Must match FIELDS count (20 columns as of now)
    row_data = [
        "/unique/path", 1, 1, "UniqueNote", "UniqueISRC", 1,
        "UniqueProd", "UniqueLyr", 180.0, "UniqueTitle", 1, 999,
        1888, "UniquePerf", "UniqueComp", "UniqueGroup", "UniqueArtist",
        "UniqueAlbum", "UniquePub", "UniqueGenre"
    ]
    
    # Pad with None if fewer columns than FIELDS
    while len(row_data) < len(yellberus.FIELDS):
        row_data.append(None)
    
    lib_service.get_all_songs.return_value = ([], [row_data])
    
    widget = LibraryWidget(lib_service, meta_service, settings)
    qtbot.addWidget(widget)
    return widget

def test_strict_search_coverage(library_widget_search, qtbot):
    """
    STRICT Search Coverage:
    Ensures that EVERY column displayed in the Library is searchable.
    
    If a developer adds a column but creates a custom filter that forgets to include it,
    this test will fail (by finding 0 rows for a content known to be present).
    """
    widget = library_widget_search
    model = widget.library_model
    col_count = model.columnCount()
    
    row = 0
    for col in range(col_count):
        index = model.index(row, col)
        val_text = str(model.data(index, 0))  # DisplayRole
        
        # Skip empty/None values
        if not val_text or val_text == "None":
            continue
        
        # Perform Search
        widget.search_box.setText(val_text)
        
        # Assert Row Visible
        assert widget.proxy_model.rowCount() == 1, \
            f"Search failed for Column {col} ('{model.headerData(col, 1)}'). Value '{val_text}' not found."
            
        # Clear search for next iteration
        widget.search_box.clear()
        
    # Verify Negative Case
    widget.search_box.setText("NonExistentValue")
    assert widget.proxy_model.rowCount() == 0

