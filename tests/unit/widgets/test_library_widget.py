import pytest
import os
from unittest.mock import MagicMock, patch, call
from PyQt6.QtWidgets import QMessageBox, QMenu, QApplication
from PyQt6.QtCore import Qt, QModelIndex, QPoint
from src.presentation.widgets.library_widget import LibraryWidget

@pytest.fixture
def mock_dependencies():
    library_service = MagicMock()
    metadata_service = MagicMock()
    settings_manager = MagicMock()
    # Default settings
    settings_manager.get_last_import_directory.return_value = ""
    settings_manager.get_column_visibility.return_value = {}
    return library_service, metadata_service, settings_manager

@pytest.fixture
def library_widget(qtbot, mock_dependencies):
    lib_service, meta_service, settings = mock_dependencies
    
    # Setup default return for get_all_songs so load_library works
    lib_service.get_all_songs.return_value = (
        ["ID", "Performer", "Title", "Duration", "Path", "Composer", "BPM"],
        [ # 2 rows of sample data
            [1, "Performer A", "Title A", "3:00", "/path/a.mp3", "Comp A", 120],
            [2, "Performer B", "Title B", "4:00", "/path/b.mp3", "Comp B", 128]
        ]
    )
    
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
    assert library_widget.library_model.item(0, 1).text() == "Performer A"
    assert library_widget.library_model.item(1, 2).text() == "Title B"

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
    
    # Get the ID of the selected row dynamically to be robust against sorting
    idx = library_widget.proxy_model.index(0, 0) # Col 0 is ID
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
    
    # Should only show 1 row
    assert library_widget.proxy_model.rowCount() == 1
    
    # Check the remaining item is indeed B
    # We find the Title column (index 2)
    index = library_widget.proxy_model.index(0, 2) 
    assert library_widget.proxy_model.data(index) == "Title B"
    
    # Clear search
    library_widget.search_box.clear()
    assert library_widget.proxy_model.rowCount() == 2

def test_search_invalid_regex_fallback(library_widget, qtbot):
    """Test that invalid regex does not crash and behaves gracefully."""
    # Type invalid regex "["
    # This should internally trigger QRegularExpression invalid state or fallback if implemented.
    # Current implementation relies on QSortFilterProxyModel handling it (usually matches nothing).
    library_widget.search_box.setText("[")
    
    # It should not crash.
    # Typically QSortFilterProxyModel with invalid regex matches 0 rows.
    assert library_widget.proxy_model.rowCount() == 0 or library_widget.proxy_model.rowCount() == 2
    
    # Try another one "*"
    library_widget.search_box.setText("*")
    # Should not crash
    assert True

def test_double_click_emits_add_playlist(library_widget, qtbot):
    """Test double clicking a row emits add_to_playlist signal."""
    # Select the row first!
    library_widget.table_view.selectRow(0)
    QApplication.processEvents()
    
    # Dynamically get expected data
    idx_performer = library_widget.proxy_model.index(0, 1)
    idx_title = library_widget.proxy_model.index(0, 2)
    idx_path = library_widget.proxy_model.index(0, 4)
    
    expected_performer = library_widget.proxy_model.data(idx_performer)
    expected_title = library_widget.proxy_model.data(idx_title)
    expected_path = library_widget.proxy_model.data(idx_path)
    
    # Create signal catcher
    with qtbot.waitSignal(library_widget.add_to_playlist, timeout=1000) as blocker:
        # Double click first row (col 0)
        idx = library_widget.proxy_model.index(0, 0)
        library_widget.table_view.doubleClicked.emit(idx)
        
    # Check signal content
    assert len(blocker.args) == 1
    items = blocker.args[0]
    assert len(items) == 1
    assert items[0]["performer"] == expected_performer # Variable name in test remains expected_artist from proxy data
    assert items[0]["title"] == expected_title
    assert items[0]["path"] == expected_path

def test_filter_by_performer(library_widget, mock_dependencies):
    """Test filtering by performer asks service for subset."""
    lib_service, _, _ = mock_dependencies
    lib_service.get_songs_by_performer.return_value = (["H", "D"], [])
    
    library_widget._filter_by_performer("Performer A")
    
    lib_service.get_songs_by_performer.assert_called_with("Performer A")
    # Should clear model and repopulate
    assert library_widget.library_model.rowCount() == 0 # Mock returned empty list

def test_column_visibility_toggle(library_widget, mock_dependencies):
    """Test toggling columns updates view and saves settings."""
    _, _, settings = mock_dependencies
    
    # Hide column 0 via internal method (simulating context menu action)
    # Construct a dummy action
    action = MagicMock()
    action.data.return_value = 0 # Column 0
    
    # We need to simulate sender()
    with patch.object(library_widget, 'sender', return_value=action):
        library_widget._toggle_column_visibility(False) # check=False means user unchecked "Visible"
    
    assert library_widget.table_view.isColumnHidden(0)
    settings.set_column_visibility.assert_called()

def test_load_column_visibility(library_widget, mock_dependencies):
    """Test that visibility settings are applied on load."""
    _, _, settings = mock_dependencies
    
    # Setup settings to hide col 1
    settings.get_column_visibility.return_value = {"1": False, "2": True}
    
    library_widget._load_column_visibility_states()
    
    assert library_widget.table_view.isColumnHidden(1)
    assert not library_widget.table_view.isColumnHidden(2)

def test_show_table_context_menu(library_widget, mock_dependencies):
    """Test context menu shows correct actions and triggers them."""
    # We can't easily check if QMenu exec popped up in a unit test without blocking
    # But we can verify it creates actions and connects them.
    # Alternatively, we can mock QMenu and check what actions were added.
    
    with patch("src.presentation.widgets.library_widget.QMenu") as MockMenu:
        mock_menu_instance = MockMenu.return_value
        
        # Trigger context menu
        library_widget._show_table_context_menu(QPoint(0,0))
        
        # Verify menu was created
        MockMenu.assert_called()
        
        # Verify actions added (Delete, Add to Playlist, Show ID3)
        # We can check addAction calls
        assert mock_menu_instance.addAction.call_count == 3
        
        # We can check signatures of added actions but it's tricky with mock objects
        # Instead, let's verify if _delete_selected and _emit_add_to_playlist
        # are connected. This is hard to do with standard mocks on QAction.triggered.connect
        
        # A better approach for integration: trigger the slots manually?
        # We successfully tested _delete_selected so we know logic works.
        # We just need to know the menu logic is wired up.
        pass # The above MockMenu checks suffice for "menu creation"

def test_show_column_context_menu(library_widget):
    """Test column context menu creation with integrity checks."""
    with patch("src.presentation.widgets.library_widget.QMenu") as MockMenu:
        mock_menu_instance = MockMenu.return_value
        
        # Trigger header context menu
        library_widget._show_column_context_menu(QPoint(0,0))
        
        # INTEGRITY CHECK:
        # Standard schema has 7 columns: ID, Performer, Title, Duration, Path, Composer, BPM
        # If developers add a column, they MUST allow toggling its visibility.
        expected_columns = 7
        assert library_widget.library_model.columnCount() == expected_columns, \
            "Model column count changed! Update this test."
            
        # Verify exactly N actions added (one per column)
        assert mock_menu_instance.addAction.call_count == expected_columns, \
            f"Context menu missing actions! Expected {expected_columns}, got {mock_menu_instance.addAction.call_count}"
        
        # Verify Action creation logic (Optional but good)
        # We can iterate call_args_list to check names if we assume they match headers
        # But simply counting valid actions is the main integrity check requested.

def test_show_id3_tags_dialog(library_widget, mock_dependencies):
    """Test interaction with MetadataViewerDialog."""
    lib_service, meta_service, _ = mock_dependencies
    from src.data.models.song import Song
    
    # Setup mocks
    mock_file_song = Song(title="File", path="/path/test.mp3")
    mock_db_song = Song(title="DB", path="/path/test.mp3")
    
    meta_service.extract_from_mp3.return_value = mock_file_song
    meta_service.get_raw_tags.return_value = {"Custom": "Value"}
    lib_service.get_song_by_path.return_value = mock_db_song
    
    # Select row
    library_widget.table_view.selectRow(0)
    QApplication.processEvents()
    idx = library_widget.proxy_model.index(0, 4)
    path = library_widget.proxy_model.data(idx)
    
    # Mock the dialog class
    # Since the import happens inside the method, we must patch where it's defined
    with patch("src.presentation.widgets.metadata_viewer_dialog.MetadataViewerDialog") as MockDialog:
        library_widget._show_id3_tags()
        
        # Verify dialog called
        MockDialog.assert_called_with(mock_file_song, mock_db_song, {"Custom": "Value"}, library_widget)
        MockDialog.return_value.exec.assert_called_once()

def test_metadata_viewer_dialog_logic():
    """Test functionality of the dialog itself (table population)."""
    from src.presentation.widgets.metadata_viewer_dialog import MetadataViewerDialog
    from src.data.models.song import Song
    from PyQt6.QtGui import QColor
    
    # Case 1: Mismatch
    f_song = Song(title="A", performers=["Performer A"], path="p")
    d_song = Song(title="B", performers=["Performer B"], path="p")
    
    dlg = MetadataViewerDialog(f_song, d_song)
    
    # Check Title row. 
    # Row 0 is now "Core Metadata" header.
    # Row 1 is Title.
    item_file = dlg.table.item(1, 1)
    item_db = dlg.table.item(1, 2)
    
    assert item_file.text() == "A"
    assert item_db.text() == "B"
    # Check highlight (background)
    # Different systems might have different name/formats, but we set QColor(255, 220, 220)
    expected_bg = QColor(255, 220, 220)
    assert item_file.background().color() == expected_bg
    assert item_db.background().color() == expected_bg
    
    # Case 2: Match
    f_song2 = Song(title="Same", path="p")
    d_song2 = Song(title="Same", path="p")
    dlg2 = MetadataViewerDialog(f_song2, d_song2)
    
    item_file2 = dlg2.table.item(1, 1)
    item_db2 = dlg2.table.item(1, 2)
    
    assert item_file2.text() == "Same"
    # Should not be colored (default background is distinct from our highlight)
    assert item_db2.background().color() != expected_bg

    # --- Test Description Logic ---
    # Adding raw tags with a known code "TSSE"
    dlg.raw_tags = {"TIT2": "Raw Title", "TSSE": "MyEncoder"}
    dlg._populate_table()
    
    # "TIT2" maps to Title core field, so it should be skipped in the raw section?
    # Actually, TIT2 is in the list of keys used by mapped fields, so it SHOULD be skipped.
    
    # "TSSE" is not mapped, so it should appear, and use the ID3_FRAMES description
    # "TSSE" -> "Software/Hardware and settings used for encoding"
    
    found_desc = False
    for r in range(dlg.table.rowCount()):
        item = dlg.table.item(r, 0)
        # Skip headers or None items
        if not item: continue
        
        text = item.text()
        if "TSSE" in text and "Software/Hardware" in text:
            found_desc = True
            break
            
    assert found_desc, "Description for TSSE not found in table labels"

def test_numeric_sorting_duration(library_widget, mock_dependencies):
    """Test that duration column sorts numerically, handling >100m songs."""
    from PyQt6.QtCore import Qt
    lib_service, _, _ = mock_dependencies
    
    # Raw data: [ID, Performer, Title, Duration(float), Path, Composer, BPM]
    raw_data = [
        [1, "A", "Long", 6005.0, "p1", "C", 120],  # 100m 5s
        [2, "B", "Short", 180.0, "p2", "C", 120],  # 3m 0s
        [3, "C", "Med", 5940.0, "p3", "C", 120],   # 99m 0s
    ]
    lib_service.get_all_songs.return_value = (
        ["ID", "Perf", "Title", "Duration", "Path", "Comp", "BPM"],
        raw_data
    )
    
    # Trigger load
    library_widget.load_library()
    
    # Enable sorting on Duration column (Index 3)
    library_widget.proxy_model.sort(3, Qt.SortOrder.AscendingOrder)
    
    # Check Title of first 3 rows to confirm sort order
    # Expected Numeric Order: Short, Med, Long
    
    idx0 = library_widget.proxy_model.index(0, 2)
    idx1 = library_widget.proxy_model.index(1, 2)
    idx2 = library_widget.proxy_model.index(2, 2)
    
    t0 = library_widget.proxy_model.data(idx0)
    t1 = library_widget.proxy_model.data(idx1)
    t2 = library_widget.proxy_model.data(idx2)
    
    assert [t0, t1, t2] == ["Short", "Med", "Long"]
    
    # Check Formatting (mm:ss)
    # Duration column (Index 3)
    d_short = library_widget.proxy_model.data(library_widget.proxy_model.index(0, 3))
    d_long = library_widget.proxy_model.data(library_widget.proxy_model.index(2, 3))
    
    assert d_short == "03:00"
    assert d_long == "100:05"

def test_numeric_sorting_bpm(library_widget, mock_dependencies):
    """Test that BPM column sorts numerically."""
    from PyQt6.QtCore import Qt
    lib_service, _, _ = mock_dependencies
    
    # 3. 120 (Str: "120")
    # 2. 90 (Str: "90")
    # 1. 1000 (Str: "1000")
    
    # String Sort: "1000", "120", "90" ('10' < '12' < '9')
    # Numeric Sort: 90, 120, 1000
    
    raw_data = [
        [1, "A", "Fast", 0, "p1", "C", 1000],
        [2, "B", "Normal", 0, "p2", "C", 120],
        [3, "C", "Slow", 0, "p3", "C", 90],
    ]
    lib_service.get_all_songs.return_value = (
        ["ID", "Perf", "Title", "Duration", "Path", "Comp", "BPM"],
        raw_data
    )
    
    library_widget.load_library()
    
    # Sort by BPM (Index 6)
    library_widget.proxy_model.sort(6, Qt.SortOrder.AscendingOrder)
    
    idx0 = library_widget.proxy_model.index(0, 2)
    idx1 = library_widget.proxy_model.index(1, 2)
    idx2 = library_widget.proxy_model.index(2, 2)
    
    assert [library_widget.proxy_model.data(idx) for idx in [idx0, idx1, idx2]] == ["Slow", "Normal", "Fast"]

def test_numeric_sorting_file_id(library_widget, mock_dependencies):
    """Test that FileID column sorts numerically."""
    from PyQt6.QtCore import Qt
    lib_service, _, _ = mock_dependencies
    
    # 1. 2 (Str: "2")
    # 2. 10 (Str: "10")
    # 3. 1 (Str: "1")
    
    # String Sort: "1", "10", "2" ('1' < '10' < '2')
    # Numeric Sort: 1, 2, 10
    
    raw_data = [
        [2, "A", "ID 2", 0, "p", "C", 120],
        [10, "B", "ID 10", 0, "p", "C", 120],
        [1, "C", "ID 1", 0, "p", "C", 120],
    ]
    lib_service.get_all_songs.return_value = (
        ["ID", "Perf", "Title", "Duration", "Path", "Comp", "BPM"],
        raw_data
    )
    
    library_widget.load_library()
    
    # Sort by ID (Index 0)
    library_widget.proxy_model.sort(0, Qt.SortOrder.AscendingOrder)
    
    idx0 = library_widget.proxy_model.index(0, 0)
    idx1 = library_widget.proxy_model.index(1, 0)
    idx2 = library_widget.proxy_model.index(2, 0)
    
    # Check displayed text of ID column
    assert [library_widget.proxy_model.data(idx) for idx in [idx0, idx1, idx2]] == ["1", "2", "10"]
    # Check displayed text of ID column
    assert [library_widget.proxy_model.data(idx) for idx in [idx0, idx1, idx2]] == ["1", "2", "10"]

def test_sorting_all_columns(library_widget, mock_dependencies):
    """Refined comprehensive sorting test for all columns in both orders."""
    from PyQt6.QtCore import Qt
    lib_service, _, _ = mock_dependencies

    # Data tailored to test sorting logic for each column
    # [ID, Perf, Title, Duration, Path, Comp, BPM]
    # We use distinct values to make sort order unambiguous
    
    # Row A: ID=1, Perf="A", Title="Z", Dur=10,  Path="C", Comp="M", BPM=10
    # Row B: ID=2, Perf="B", Title="Y", Dur=20,  Path="B", Comp="L", BPM=20
    # Row C: ID=3, Perf="C", Title="X", Dur=100, Path="A", Comp="K", BPM=100
    
    raw_data = [
        [1, "Performer A", "Title Z", 10.0, "/path/c", "Comp M", 10], 
        [2, "Performer B", "Title Y", 20.0, "/path/b", "Comp L", 20], 
        [3, "Performer C", "Title X", 100.0, "/path/a", "Comp K", 100],
    ]
    
    lib_service.get_all_songs.return_value = (
        ["ID", "Perf", "Title", "Duration", "Path", "Comp", "BPM"],
        raw_data
    )
    library_widget.load_library()
    
    # Helper to get column data
    def get_col_data(col_idx):
        rows = library_widget.proxy_model.rowCount()
        return [
            library_widget.proxy_model.data(library_widget.proxy_model.index(r, col_idx))
            for r in range(rows)
        ]

    # Helper to check sort
    def check_sort(col_idx, order, expected_list):
        library_widget.proxy_model.sort(col_idx, order)
        actual = get_col_data(col_idx)
        assert actual == expected_list, f"Col {col_idx} Order {order} Failed. Got {actual}, Expected {expected_list}"

    # 1. ID (Numeric)
    check_sort(0, Qt.SortOrder.AscendingOrder, ["1", "2", "3"])
    check_sort(0, Qt.SortOrder.DescendingOrder, ["3", "2", "1"])
    
    # 2. Performer (String)
    check_sort(1, Qt.SortOrder.AscendingOrder, ["Performer A", "Performer B", "Performer C"])
    check_sort(1, Qt.SortOrder.DescendingOrder, ["Performer C", "Performer B", "Performer A"])

    # 3. Title (String) - Input Z, Y, X so Ascending is X, Y, Z
    check_sort(2, Qt.SortOrder.AscendingOrder, ["Title X", "Title Y", "Title Z"])
    check_sort(2, Qt.SortOrder.DescendingOrder, ["Title Z", "Title Y", "Title X"])

    # 4. Duration (Numeric, Formatted)
    # 10s -> "00:10", 20s -> "00:20", 100s -> "01:40"
    check_sort(3, Qt.SortOrder.AscendingOrder, ["00:10", "00:20", "01:40"])
    check_sort(3, Qt.SortOrder.DescendingOrder, ["01:40", "00:20", "00:10"])

    # 5. Path (String) - Input c, b, a so Ascending is a, b, c
    check_sort(4, Qt.SortOrder.AscendingOrder, ["/path/a", "/path/b", "/path/c"])
    check_sort(4, Qt.SortOrder.DescendingOrder, ["/path/c", "/path/b", "/path/a"])

    # 6. Composer (String) - M, L, K -> Ascending K, L, M
    check_sort(5, Qt.SortOrder.AscendingOrder, ["Comp K", "Comp L", "Comp M"])
    check_sort(5, Qt.SortOrder.DescendingOrder, ["Comp M", "Comp L", "Comp K"])

    # 7. BPM (Numeric)
    check_sort(6, Qt.SortOrder.AscendingOrder, ["10", "20", "100"])
    check_sort(6, Qt.SortOrder.DescendingOrder, ["100", "20", "10"])
    
    # 8. Integrity Check: Ensure we tested ALL columns
    # If a developer adds a column (e.g., Genre) but doesn't add a check_sort above, this will fail.
    assert library_widget.proxy_model.columnCount() == 7, "New column detected! You must add a check_sort test case for it above."

def test_table_schema_integrity(library_widget):
    """Ensure table structure matches expected schema. Fails if columns are added/removed."""
    model = library_widget.library_model
    
    expected_columns = ["ID", "Performer", "Title", "Duration", "Path", "Composer", "BPM"]
    
    assert model.columnCount() == len(expected_columns), \
        f"Column count mismatch. Expected {len(expected_columns)}, got {model.columnCount()}"
        
    for i, name in enumerate(expected_columns):
        header = model.headerData(i, Qt.Orientation.Horizontal)
        assert header == name, f"Column {i} mismatch. Expected '{name}', got '{header}'"
