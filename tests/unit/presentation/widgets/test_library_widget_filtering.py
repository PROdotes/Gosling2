import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
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
    
    # Mock data with various completeness states
    # Columns: [ID, Perf, Title, Duration, Path, Comp, BPM]
    rows = [
        [1, "Valid Performer", "Valid Title", 180.0, "/path/1.mp3", "Valid Comp", 120], # Complete
        [2, "", "No Performer", 180.0, "/path/2.mp3", "Valid Comp", 120],               # Missing Performer
        [3, "Valid Performer", "", 180.0, "/path/3.mp3", "Valid Comp", 120],               # Missing Title
        [4, "Valid Performer", "Short Duration", 10.0, "/path/4.mp3", "Valid Comp", 120], # Short Duration
        [5, "Valid Performer", "Title", 180.0, "/path/5.mp3", "", 120],                  # Missing Composer (Assuming criteria requires it?)
    ]
    
    lib_service.get_all_songs.return_value = (
        ["ID", "Performer", "Title", "Duration", "Path", "Composer", "BPM"],
        rows
    )
    
    widget = LibraryWidget(lib_service, meta_service, settings)
    
    # Inject known criteria for deterministic testing
    widget.completeness_criteria = {
        "title": {"required": True, "type": "string"},
        "performers": {"required": True, "type": "list", "min_length": 1},
        "duration": {"required": True, "type": "number", "min_value": 30},
        "composers": {"required": True, "type": "list", "min_length": 1} # Let's say required for this test
    }
    
    qtbot.addWidget(widget)
    return widget

def test_get_incomplete_fields_logic(library_widget):
    """Test that _get_incomplete_fields correctly identifies issues."""
    
    # helper
    def check_row(id_val, expected_failures):
        # Find row data by ID from the mock data we injected
        headers, rows = library_widget.library_service.get_all_songs()
        row = next(r for r in rows if r[0] == id_val)
        failures = library_widget._get_incomplete_fields(row)
        assert failures == expected_failures, f"ID {id_val} failed. Got {failures}, expected {expected_failures}"

    # Row 1: Complete
    check_row(1, set())
    
    # Row 2: Missing Performer (Empty String)
    check_row(2, {"performers"})
    
    # Row 3: Missing Title
    check_row(3, {"title"})
    
    # Row 4: Short Duration (10 < 30)
    check_row(4, {"duration"})
    
    # Row 5: Missing Composer
    check_row(5, {"composers"})

def test_filter_hides_complete_rows(library_widget, mock_dependencies):
    """Test that toggling filter hides complete rows."""
    lib_service, _, _ = mock_dependencies
    
    # Reload library to ensure cleaner state
    library_widget.load_library()
    assert library_widget.library_model.rowCount() == 5
    
    # Toggle ON
    library_widget.chk_show_incomplete.setChecked(True)
    
    # Should show ONLY incomplete rows (Rows 2, 3, 4, 5) -> 4 rows
    assert library_widget.library_model.rowCount() == 4
    
    # Verify the Valid row (ID 1) is NOT present
    ids = [library_widget.library_model.data(library_widget.library_model.index(r, 0)) for r in range(4)]
    # Note: data() returns string "1", "2" etc from our model setup
    assert "1" not in ids

def test_highlighting_invalid_cells(library_widget):
    """Test that invalid cells have a red background when filter is ON."""
    
    library_widget.chk_show_incomplete.setChecked(True) # Triggers load_library
    
    rows = library_widget.library_model.rowCount()
    
    # We iterate rows and check highlighted cells match expectations
    for r in range(rows):
        idx_id = library_widget.library_model.index(r, 0)
        file_id = int(library_widget.library_model.data(idx_id))
        
        # Get actual Item objects to check background
        # Row layout: [ID, Perf, Title, Dur, Path, Comp, BPM]
        item_perf = library_widget.library_model.item(r, 1)
        item_title = library_widget.library_model.item(r, 2)
        item_dur = library_widget.library_model.item(r, 3)
        item_comp = library_widget.library_model.item(r, 5)
        
        red_color = QColor("#FFCDD2")
        
        if file_id == 2: # Missing Performer
            assert item_perf.background().color() == red_color
            assert item_title.background().style() == Qt.BrushStyle.NoBrush # Not red
            
        elif file_id == 3: # Missing Title
            assert item_title.background().color() == red_color
            
        elif file_id == 4: # Short Duration
            assert item_dur.background().color() == red_color
            
        elif file_id == 5: # Missing Composer
            assert item_comp.background().color() == red_color

def test_no_highlight_when_filter_off(library_widget):
    """Test that cells are NOT highlighted when filter is OFF, even if invalid."""
    library_widget.chk_show_incomplete.setChecked(False)
    library_widget.load_library()
    
    rows = library_widget.library_model.rowCount()
    for r in range(rows):
        for c in range(library_widget.library_model.columnCount()):
            item = library_widget.library_model.item(r, c)
            # Should have no background set (NoBrush)
            assert item.background().style() == Qt.BrushStyle.NoBrush

def test_filter_toggles_columns_safely(library_widget, mock_dependencies):
    """Test that filter ON shows only required columns, and OFF restores user settings."""
    _, _, settings = mock_dependencies
    
    # 1. Setup User Settings: 
    # Let's say user wants BPM (Col 6) Visible, but Title (Col 2) Hidden (weird usage, but good for test)
    # Default is all visible, let's strictly mock returned visibility
    # Note: LibraryWidget._load_column_visibility_states iterates columns and checks this dict
    settings.get_column_visibility.return_value = {
        "2": False, # Title Hidden
        "6": True   # BPM Visible
    }
    
    # Reload to apply these settings initially
    library_widget.load_library()
    assert library_widget.table_view.isColumnHidden(2) # Title Hidden
    assert not library_widget.table_view.isColumnHidden(6) # BPM Visible
    
    # 2. Toggle ON
    # Criteria: Title IS Required, BPM is NOT Required
    # Expect: Title SHOWS, BPM HIDES
    library_widget.chk_show_incomplete.setChecked(True)
    
    assert not library_widget.table_view.isColumnHidden(2), "Title should be visible because it is required"
    assert library_widget.table_view.isColumnHidden(6), "BPM should be hidden because it is not required"
    
    # Verify we did NOT save this temporary state
    # calling setColumnHidden might trigger save if we don't guard it
    # We check if set_column_visibility was called with the temporary state
    # It might be called during initial load, but shouldn't be called with our temp state
    # We can check specific call args or just ensure the last call wasn't the temp state
    # But easier: check that restoring works in step 3.
    
    # 3. Toggle OFF
    library_widget.chk_show_incomplete.setChecked(False)
    
    # Should restore user settings
    assert library_widget.table_view.isColumnHidden(2), "Title should revert to hidden (user setting)"
    assert not library_widget.table_view.isColumnHidden(6), "BPM should revert to visible (user setting)"
