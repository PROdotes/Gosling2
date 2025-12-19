import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import Qt
from src.presentation.widgets.library_widget import LibraryWidget
from src.core import yellberus

@pytest.fixture
def mock_dependencies():
    library_service = MagicMock()
    metadata_service = MagicMock()
    settings_manager = MagicMock()
    
    # Default settings
    settings_manager.get_last_import_directory.return_value = ""
    settings_manager.get_column_layout.return_value = None
    settings_manager.get_type_filter.return_value = 0 # "All"
    
    return library_service, metadata_service, settings_manager

@pytest.fixture
def library_widget(qtbot, mock_dependencies):
    lib_service, meta_service, settings = mock_dependencies
    
    # Headers matching Yellberus
    headers = [f.db_column for f in yellberus.FIELDS]
    
    # Data with different types
    # 0:ID, 1:Type, 2:Title, 3:Artist ... 11:BPM, 12:Done
    data = [
        [1, 1, "Music 1", "Artist 1", "", "", "", "", 180, "", 2020, 120, 1, ""], # Type 1 (Music)
        [2, 2, "Jingle 1", "Artist 2", "", "", "", "", 30, "", 2021, 0, 1, ""],   # Type 2 (Jingle)
        [3, 3, "Comm 1", "Artist 3", "", "", "", "", 60, "", 2022, 0, 1, ""],     # Type 3 (Commercial)
        [4, 4, "Speech 1", "Artist 4", "", "", "", "", 300, "", 2023, 0, 1, ""],  # Type 4 (VoiceTrack)
        [5, 5, "Speech 2", "Artist 5", "", "", "", "", 600, "", 2024, 0, 1, ""],  # Type 5 (Recording)
        [6, 6, "Stream 1", "Artist 6", "", "", "", "", 0, "", 2025, 0, 1, ""],    # Type 6 (Stream)
    ]
    
    lib_service.get_all_songs.return_value = (headers, data)
    
    widget = LibraryWidget(lib_service, meta_service, settings)
    qtbot.addWidget(widget)
    return widget

def test_tabs_initialization(library_widget):
    """Verify that tabs are populated correctly on initialization."""
    tab_bar = library_widget.type_tab_bar
    assert tab_bar.count() == 6
    assert tab_bar.tabText(0).startswith("All")
    assert tab_bar.tabText(1).startswith("Music")
    assert tab_bar.tabText(2).startswith("Jingles")
    assert tab_bar.tabText(3).startswith("Commercials")
    assert tab_bar.tabText(4).startswith("Speech")
    assert tab_bar.tabText(5).startswith("Streams")

def test_tab_counts(library_widget):
    """Verify that tab labels include correct item counts."""
    tab_bar = library_widget.type_tab_bar
    # Data: 6 total, 1 Music, 1 Jingle, 1 Comm, 2 Speech (IDs 4,5), 1 Stream
    assert "6" in tab_bar.tabText(0) # All
    assert "1" in tab_bar.tabText(1) # Music
    assert "1" in tab_bar.tabText(2) # Jingles
    assert "1" in tab_bar.tabText(3) # Commercials
    assert "2" in tab_bar.tabText(4) # Speech
    assert "1" in tab_bar.tabText(5) # Streams

def test_music_tab_filtering(library_widget, qtbot):
    """Verify clicking the 'Music' tab filters the table."""
    # Music is tab index 1
    with qtbot.waitSignal(library_widget.type_tab_bar.currentChanged):
        library_widget.type_tab_bar.setCurrentIndex(1)
        
    # Proxy model should now only show 1 row (Music 1)
    assert library_widget.proxy_model.rowCount() == 1
    
    # Check content
    idx_title = library_widget.field_indices['title']
    title = library_widget.proxy_model.data(library_widget.proxy_model.index(0, idx_title))
    assert title == "Music 1"

def test_speech_tab_grouping_filter(library_widget, qtbot):
    """Verify 'Speech' tab correctly filters both TypeID 4 and 5."""
    # Speech is tab index 4
    library_widget.type_tab_bar.setCurrentIndex(4)
    
    # Proxy model should show 2 rows (Speech 1 and Speech 2)
    assert library_widget.proxy_model.rowCount() == 2
    
    # Verify titles
    idx_title = library_widget.field_indices['title']
    titles = [
        library_widget.proxy_model.data(library_widget.proxy_model.index(0, idx_title)),
        library_widget.proxy_model.data(library_widget.proxy_model.index(1, idx_title))
    ]
    assert "Speech 1" in titles
    assert "Speech 2" in titles

def test_all_tab_reset(library_widget, qtbot):
    """Verify 'All' tab resets the type filter."""
    # First filter to Music
    library_widget.type_tab_bar.setCurrentIndex(1)
    assert library_widget.proxy_model.rowCount() == 1
    
    # Back to All
    library_widget.type_tab_bar.setCurrentIndex(0)
    assert library_widget.proxy_model.rowCount() == 6

def test_combined_search_and_tab_filter(library_widget, qtbot):
    """Verify that search text and type tabs work together (AND logic)."""
    # 1. Set tab to Speech (2 items)
    library_widget.type_tab_bar.setCurrentIndex(4)
    assert library_widget.proxy_model.rowCount() == 2
    
    # 2. Add search filter for "Speech 2"
    library_widget.search_box.setText("Speech 2")
    assert library_widget.proxy_model.rowCount() == 1
    
    # 3. Change search to "Music" (should be 0 because tab is still Speech)
    library_widget.search_box.setText("Music")
    assert library_widget.proxy_model.rowCount() == 0
    
    # 4. Clear search, return to 2
    library_widget.search_box.clear()
    assert library_widget.proxy_model.rowCount() == 2

def test_persistence_on_change(library_widget, mock_dependencies, qtbot):
    """Verify that changing a tab saves the setting."""
    _, _, settings = mock_dependencies
    
    library_widget.type_tab_bar.setCurrentIndex(2) # Jingles
    
    settings.set_type_filter.assert_called_with(2)

def test_persistence_on_init(qtbot, mock_dependencies):
    """Verify that LibraryWidget restores the saved tab index on init."""
    lib_service, meta_service, settings = mock_dependencies
    
    # Save a specific index
    settings.get_type_filter.return_value = 3 # Commercials
    
    # Mock some data
    headers = [f.db_column for f in yellberus.FIELDS]
    data = [[1, 3, "Comm 1", "P", "", "", "", "", 60, "", 2022, 0, 1, ""]]
    lib_service.get_all_songs.return_value = (headers, data)
    
    widget = LibraryWidget(lib_service, meta_service, settings)
    qtbot.addWidget(widget)
    
    # Verify tab is set
    assert widget.type_tab_bar.currentIndex() == 3
    # Verify filter is active
    assert widget.proxy_model.rowCount() == 1
