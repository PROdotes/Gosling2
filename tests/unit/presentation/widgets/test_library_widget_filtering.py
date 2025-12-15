import pytest
from unittest.mock import MagicMock
from src.presentation.widgets.library_widget import LibraryWidget
from PyQt6.QtWidgets import QHeaderView

@pytest.fixture
def library_widget(qtbot):
    lib_service = MagicMock()
    meta_service = MagicMock()
    settings = MagicMock()
    settings.get_column_visibility.return_value = {}
    
    # Setup data with unique values in every column to test search isolation
    headers = ["ID", "Performer", "Title", "Duration", "Path", "Composer", "BPM", "Year", "Genre"]
    # We add "Genre" to simulate future column addition
    
    # Unique values for Row 1
    row_data = [
        1, 
        "UniquePerformer", 
        "UniqueTitle", 
        "10:00", 
        "/unique/path", 
        "UniqueComposer", 
        999,      # Unique BPM
        1888,     # Unique Year
        "UniqueGenre"
    ]
    
    lib_service.get_all_songs.return_value = (headers, [row_data])
    
    widget = LibraryWidget(lib_service, meta_service, settings)
    qtbot.addWidget(widget)
    return widget

def test_strict_search_coverage(library_widget, qtbot):
    """
    STRICT Search Coverage:
    Ensures that EVERY column displayed in the Library is searchable.
    
    If a developer adds a column but creates a custom filter that forgets to include it,
    this test will fail (by finding 0 rows for a content known to be present).
    """
    # 1. Get List of Columns from Model
    model = library_widget.library_model
    col_count = model.columnCount()
    
    # 2. Iterate each column and search for its content
    # We generated data where every column has a unique value identifiable by string.
    
    # Map col index to the unique string valid for that column in Row 0
    # ID (0) -> "1"
    # Performer (1) -> "UniquePerformer"
    # ...
    
    # Note: LibraryWidget might format things (e.g. BPM might be stringified).
    # We grab the data directly from the model to see what is rendered.
    
    row = 0
    for col in range(col_count):
        index = model.index(row, col)
        val_text = str(model.data(index, 0)) # DisplayRole
        
        # 3. Perform Search
        library_widget.search_box.setText(val_text)
        
        # 4. Assert Row Visible
        # Proxy model should show 1 row
        assert library_widget.proxy_model.rowCount() == 1, \
            f"Search failed for Column {col} ('{model.headerData(col, 1)}'). Value '{val_text}' not found."
            
        # Clear search for next iteration
        library_widget.search_box.clear()
        
    # 5. Verify Negative Case (optional)
    library_widget.search_box.setText("NonExistentValue")
    assert library_widget.proxy_model.rowCount() == 0
