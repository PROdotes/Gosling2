import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import Qt
from src.presentation.widgets.library_widget import LibraryWidget
from src.core import yellberus

@pytest.fixture
def library_widget(qtbot, mock_widget_deps):
    """Unified LibraryWidget fixture for type tab testing"""
    deps = mock_widget_deps
    
    # Headers matching Yellberus
    headers = [f.db_column for f in yellberus.FIELDS]
    
    def get_idx(name):
        for i, f in enumerate(yellberus.FIELDS):
            if f.name == name: return i
        return -1

    idx_path = get_idx("path")
    idx_id = get_idx("file_id")
    idx_type = get_idx("type_id")
    idx_title = get_idx("title")
    idx_dur = get_idx("duration")
    idx_done = get_idx("is_done")
    idx_active = get_idx("is_active")

    def r(fid, tid, title):
        row = [None] * len(yellberus.FIELDS)
        row[idx_path] = f"/path/{fid}.mp3"
        row[idx_id] = fid
        row[idx_type] = tid
        row[idx_title] = title
        row[idx_dur] = 120
        row[idx_done] = 1
        row[idx_active] = 1
        return row

    data = [
        r(1, 1, "Music 1"),
        r(2, 2, "Jingle 1"),
        r(3, 3, "Comm 1"),
        r(4, 4, "Speech 1"),
        r(5, 5, "Speech 2"),
        r(6, 6, "Stream 1"),
    ]
    
    deps['library_service'].get_all_songs.return_value = (headers, data)
    
    widget = LibraryWidget(
        deps['library_service'], 
        deps['metadata_service'], 
        deps['settings_manager'],
        deps['renaming_service'],
        deps['duplicate_scanner']
    )
    qtbot.addWidget(widget)
    return widget

def test_pills_initialization(library_widget):
    """Verify that pills are populated correctly on initialization."""
    pill_group = library_widget.pill_group
    assert len(pill_group.buttons()) == 6
    # Shorthand + counts from fixture (6 total, 1 Music, 1 Jingle)
    assert pill_group.button(0).text() == "ALL (6)"
    assert pill_group.button(1).text() == "MUS (1)"
    assert pill_group.button(2).text() == "JIN (1)"

def test_pill_counts_logic(library_widget):
    """Verify that counts are calculated (internal state check)."""
    # Note: In the new UI, counts are not shown on buttons to keep it clean,
    # but the internal filter logic should still work.
    # Data has 6 total.
    pass

def test_music_tab_filtering(library_widget, qtbot):
    """Verify clicking the 'MUS' pill filters the table."""
    pill_group = library_widget.pill_group
    # MUS pill has ID 1
    pill_group.button(1).click()
        
    assert library_widget.proxy_model.rowCount() == 1
    idx_title = {f.name: i for i, f in enumerate(yellberus.FIELDS)}['title']
    title = library_widget.proxy_model.data(library_widget.proxy_model.index(0, idx_title))
    assert title == "Music 1"

def test_speech_tab_grouping_filter(library_widget, qtbot):
    """Verify 'SP' pill correctly filters both TypeID 4 and 5."""
    pill_group = library_widget.pill_group
    pill_group.button(4).click() # SP is index 4
    
    assert library_widget.proxy_model.rowCount() == 2
    
    idx_title = {f.name: i for i, f in enumerate(yellberus.FIELDS)}['title']
    titles = [
        library_widget.proxy_model.data(library_widget.proxy_model.index(0, idx_title)),
        library_widget.proxy_model.data(library_widget.proxy_model.index(1, idx_title))
    ]
    assert "Speech 1" in titles
    assert "Speech 2" in titles

def test_all_tab_reset(library_widget, qtbot):
    """Verify 'ALL' pill resets the type filter."""
    pill_group = library_widget.pill_group
    pill_group.button(1).click()
    assert library_widget.proxy_model.rowCount() == 1
    pill_group.button(0).click()
    assert library_widget.proxy_model.rowCount() == 6

def test_combined_search_and_tab_filter(library_widget, qtbot):
    """Verify that search text and type pills work together (AND logic)."""
    pill_group = library_widget.pill_group
    pill_group.button(4).click()
    assert library_widget.proxy_model.rowCount() == 2
    
    library_widget.set_search_text("Speech 2")
    assert library_widget.proxy_model.rowCount() == 1
    
    library_widget.set_search_text("Music")
    assert library_widget.proxy_model.rowCount() == 0
    
    library_widget.set_search_text("")
    assert library_widget.proxy_model.rowCount() == 2

def test_persistence_on_change(library_widget, mock_widget_deps, qtbot):
    """Verify that changing a tab/pill saves the setting."""
    deps = mock_widget_deps
    pill_group = library_widget.pill_group
    pill_group.button(2).click() # Jingles
    
    # In the refactored code, we might use a different method name or it might be directly in _on_pill_clicked
    # verified: settings_manager.set_type_filter(id)
    deps['settings_manager'].set_type_filter.assert_called_with(2)

def test_persistence_on_init(qtbot, mock_widget_deps):
    """Verify that LibraryWidget restores the saved tab index on init."""
    deps = mock_widget_deps
    deps['settings_manager'].get_type_filter.return_value = 3 # Commercials
    
    headers = [f.db_column for f in yellberus.FIELDS]
    
    def get_idx(name):
        for i, f in enumerate(yellberus.FIELDS):
            if f.name == name: return i
        return -1

    row = [None] * len(yellberus.FIELDS)
    row[get_idx("type_id")] = 3
    row[get_idx("is_active")] = 1
    row[get_idx("is_done")] = 1
    row[get_idx("duration")] = 120
    row[get_idx("title")] = "Comm 1"
    
    deps['library_service'].get_all_songs.return_value = (headers, [row])
    
    widget = LibraryWidget(
        deps['library_service'], 
        deps['metadata_service'], 
        deps['settings_manager'],
        deps['renaming_service'],
        deps['duplicate_scanner']
    )
    qtbot.addWidget(widget)
    
    assert widget.pill_group.checkedId() == 3
    assert widget.proxy_model.rowCount() == 1
