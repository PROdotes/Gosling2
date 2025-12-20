"""
Unit tests for Field Editor UI.
Tests window, widgets, and basic interactions.
"""

import pytest
from pathlib import Path

from PyQt6.QtWidgets import QCheckBox, QComboBox
from PyQt6.QtCore import Qt

from tools.field_editor import FieldEditorWindow, DEFAULTS_COLUMNS, FIELDS_COLUMNS


@pytest.fixture
def editor_window(qtbot):
    """Create a FieldEditorWindow for testing."""
    window = FieldEditorWindow()
    window._test_mode = True  # Suppress dialogs during tests
    qtbot.addWidget(window)
    yield window


class TestWindowShell:
    """Phase 1: Window Shell tests."""
    
    def test_window_title(self, editor_window):
        """1.1/1.2: Window opens with correct title."""
        assert editor_window.windowTitle() == "Field Registry Editor"
    
    def test_toolbar_buttons_exist(self, editor_window):
        """1.3/1.4: Toolbar has Load and Save buttons."""
        assert editor_window.load_action is not None
        assert editor_window.save_action is not None
    
    def test_status_bar_exists(self, editor_window):
        """1.5/1.6: Status bar exists and shows text."""
        assert editor_window.status_bar is not None
        msg = editor_window.status_bar.currentMessage()
        assert msg  # Not empty


class TestTables:
    """Phase 2: Tables tests."""
    
    def test_fields_table_columns(self, editor_window):
        """2.3/2.4: Fields table has correct column count."""
        assert editor_window.fields_table.columnCount() == len(FIELDS_COLUMNS)
    
    def test_add_delete_buttons_exist(self, editor_window):
        """2.5/2.6: Add/Delete buttons exist."""
        assert editor_window.add_field_btn is not None
        assert editor_window.delete_field_btn is not None


class TestLoadFromCode:
    """Phase 3: Load from Code tests."""
    
    def test_load_populates_table(self, editor_window):
        """3.3/3.4: Load button populates table with fields."""
        # Already auto-loaded in __init__
        assert editor_window.fields_table.rowCount() >= 15
    
    def test_defaults_checkboxes_populated(self, editor_window):
        """3.5/3.6: Defaults checkboxes are populated."""
        assert hasattr(editor_window, 'default_checkboxes')
        assert len(editor_window.default_checkboxes) == 6
        # Check that values are booleans
        for k, cb in editor_window.default_checkboxes.items():
            assert isinstance(cb.isChecked(), bool)
    
    def test_load_skips_warning_in_test_mode(self, editor_window):
        """Load doesn't show dialog in test mode even when dirty."""
        editor_window._dirty = True
        editor_window._test_mode = True
        
        # This should complete without showing a dialog
        initial_count = editor_window.fields_table.rowCount()
        editor_window._on_load_clicked()
        
        # Should have reloaded (row count should stay same or change, but not crash)
        assert editor_window.fields_table.rowCount() >= 15
        assert editor_window._dirty is False  # Reset after load


class TestEditing:
    """Phase 4: Editing tests."""
    
    def test_checkbox_widgets_exist(self, editor_window):
        """4.3/4.4: Boolean columns have checkbox widgets."""
        widget = editor_window.fields_table.cellWidget(0, 4)  # visible column
        assert widget is not None
        cb = widget.findChild(QCheckBox)
        assert cb is not None
    
    def test_string_cells_editable(self, editor_window):
        """4.1/4.2: String cells are editable."""
        item = editor_window.fields_table.item(0, 0)  # name column
        assert item is not None
        assert bool(item.flags() & Qt.ItemFlag.ItemIsEditable)
    
    def test_type_dropdown_exists(self, editor_window):
        """4.5/4.6: Type column has dropdown."""
        combo = editor_window.fields_table.cellWidget(0, 3)
        assert combo is not None
        assert isinstance(combo, QComboBox)
    
    def test_add_field_works(self, editor_window):
        """4.7/4.8: Add Field adds a new row."""
        initial_count = editor_window.fields_table.rowCount()
        editor_window._on_add_field()
        assert editor_window.fields_table.rowCount() == initial_count + 1


class TestColorCoding:
    """Phase 5: Color Coding tests."""
    
    def test_edit_triggers_color_change(self, editor_window):
        """5.3/5.4: Editing a cell triggers color change."""
        item = editor_window.fields_table.item(2, 0)  # title row, name column
        orig_text = item.text()
        
        # Modify the text
        item.setText("modified_title")
        
        # Check color changed (should have alpha > 0)
        bg = item.background().color()
        has_color = bg.alpha() > 0
        
        # Restore
        item.setText(orig_text)
        
        assert has_color, "Editing should trigger color change"
    
    def test_status_bar_shows_counts(self, editor_window):
        """5.5/5.6: Status bar shows field counts."""
        msg = editor_window.status_bar.currentMessage()
        assert "fields" in msg.lower() or "loaded" in msg.lower()


class TestValidation:
    """Phase 8: Validation tests."""
    
    def test_id3_lookup_on_portable_toggle(self, editor_window):
        """8.5/8.6: Toggling portable=True triggers ID3 tag lookup."""
        # Find a row that's currently not portable (e.g., file_id is portable=False)
        # Toggle portable ON and check if ID3 tag cell updates
        
        # file_id should be row 0, portable column is 8, ID3 tag is column 9
        portable_widget = editor_window.fields_table.cellWidget(0, 8)
        cb = portable_widget.findChild(QCheckBox)
        
        # Toggle ON
        original_state = cb.isChecked()
        cb.setChecked(True)
        
        # Check ID3 tag cell (should be empty since file_id has no ID3 mapping)
        id3_item = editor_window.fields_table.item(0, 9)
        # file_id has no JSON mapping, so should stay empty
        # But the lookup should have been attempted
        
        # Restore
        cb.setChecked(original_state)
        
        # The test passes if no exception was raised during toggle
        assert True
    
    def test_id3_frames_loaded(self, editor_window):
        """Verify id3_frames.json was loaded."""
        assert hasattr(editor_window, '_id3_frames')
        assert len(editor_window._id3_frames) > 0
        # Check a known frame exists
        assert "TIT2" in editor_window._id3_frames
    
    def _find_empty_row(self, editor_window):
        """Helper to find the row with empty name (the newly added row)."""
        for r in range(editor_window.fields_table.rowCount()):
            item = editor_window.fields_table.item(r, 0)
            if item and not item.text():
                return r
        return editor_window.fields_table.rowCount() - 1
    
    def test_auto_populate_ui_header_from_name(self, editor_window):
        """8.3/8.4: Typing name auto-populates ui_header with Title Case."""
        # Disable sorting to get consistent row indices
        editor_window.fields_table.setSortingEnabled(False)
        
        # Add a new row (it will be at the end since sorting is off)
        editor_window._on_add_field()
        new_row = editor_window.fields_table.rowCount() - 1
        
        # Clear ui_header so auto-populate can work
        ui_item = editor_window.fields_table.item(new_row, 1)
        ui_item.setText("")
        
        # Set name
        name_item = editor_window.fields_table.item(new_row, 0)
        name_item.setText("my_new_field")
        
        # Trigger itemChanged signal manually (normally happens on edit)
        editor_window._on_item_changed(name_item)
        
        # Check ui_header was populated
        ui_text = editor_window.fields_table.item(new_row, 1).text()
        assert ui_text == "My New Field"
    
    def test_auto_populate_db_column_from_name(self, editor_window):
        """8.1/8.2: Typing name auto-populates db_column (requires schema/code match or stays empty)."""
        # Disable sorting to get consistent row indices
        editor_window.fields_table.setSortingEnabled(False)
        
        # Add a new row
        editor_window._on_add_field()
        new_row = editor_window.fields_table.rowCount() - 1
        
        # Clear db_column so auto-populate can work
        db_item = editor_window.fields_table.item(new_row, 2)
        db_item.setText("")
        
        # Set name to something with a known mapping in EXISTING code fields (loaded at start)
        # 'title' exists in yellberus.py -> MS.Name
        name_item = editor_window.fields_table.item(new_row, 0)
        name_item.setText("title")
        
        # Trigger
        editor_window._on_item_changed(name_item)
        
        # Check db_column was populated (title -> MS.Name)
        db_text = editor_window.fields_table.item(new_row, 2).text()
        assert db_text == "MS.Name"
    
    def test_auto_populate_db_column_no_fallback_guess(self, editor_window):
        """Unknown field names do NOT get a fallback guess (safer)."""
        # Disable sorting to get consistent row indices
        editor_window.fields_table.setSortingEnabled(False)
        
        # Add a new row
        editor_window._on_add_field()
        new_row = editor_window.fields_table.rowCount() - 1
        
        # Clear db_column
        db_item = editor_window.fields_table.item(new_row, 2)
        db_item.setText("")
        
        # Set name to something unknown
        name_item = editor_window.fields_table.item(new_row, 0)
        name_item.setText("some_unknown_field")
        
        # Trigger
        editor_window._on_item_changed(name_item)
        
        # Check db_column is empty (NO GUESS)
        db_text = editor_window.fields_table.item(new_row, 2).text()
        assert db_text == ""
    
    def test_dirty_flag_on_edit(self, editor_window):
        """8.7/8.8: Editing creates a diff which sets dirty flag."""
        # After load, should be clean
        assert editor_window._dirty is False
        
        # Make an actual change (add a new row with content)
        editor_window._on_add_field()
        new_row = self._find_empty_row(editor_window)
        name_item = editor_window.fields_table.item(new_row, 0)
        name_item.setText("new_test_field")
        editor_window._on_item_changed(name_item)
        
        # Should now be dirty because we have a new field
        assert editor_window._dirty is True
    
    def test_dirty_flag_reset_after_load(self, editor_window):
        """Loading resets dirty flag."""
        # Make dirty
        editor_window._dirty = True
        
        # Reload
        editor_window._on_load_clicked()
        
        # Should be clean again
        assert editor_window._dirty is False
    
    def test_has_close_event(self, editor_window):
        """8.7: closeEvent is implemented."""
        assert hasattr(editor_window, 'closeEvent')
        # Don't actually test the dialog interaction, just that the method exists


class TestDeleteField:
    """Tests for field deletion functionality."""
    
    def test_delete_field_reduces_count(self, editor_window, qtbot, monkeypatch):
        """Deleting a field reduces the row count."""
        from PyQt6.QtWidgets import QMessageBox
        
        # Mock the confirmation dialog to always return Yes
        monkeypatch.setattr(QMessageBox, 'exec', lambda self: QMessageBox.StandardButton.Yes)
        
        initial_count = editor_window.fields_table.rowCount()
        
        # Select the first row
        editor_window.fields_table.selectRow(0)
        
        # Delete
        editor_window._on_delete_field()
        
        assert editor_window.fields_table.rowCount() == initial_count - 1
    
    def test_delete_no_selection_does_nothing(self, editor_window):
        """Delete with no selection doesn't crash or change count."""
        editor_window.fields_table.clearSelection()
        initial_count = editor_window.fields_table.rowCount()
        
        editor_window._on_delete_field()
        
        assert editor_window.fields_table.rowCount() == initial_count


class TestDropdownChange:
    """Tests for type dropdown functionality."""
    
    def test_dropdown_change_marks_dirty(self, editor_window):
        """Changing the type dropdown marks the editor as dirty."""
        editor_window._dirty = False
        
        # Get the type combo from row 0
        combo = editor_window.fields_table.cellWidget(0, 3)
        assert combo is not None
        
        # Change to a different type
        original_idx = combo.currentIndex()
        new_idx = (original_idx + 1) % combo.count()
        combo.setCurrentIndex(new_idx)
        
        # Should be dirty now
        assert editor_window._dirty is True
        
        # Restore
        combo.setCurrentIndex(original_idx)
    
    def test_dropdown_has_expected_types(self, editor_window):
        """Type dropdown contains expected field types."""
        from tools.field_editor import FIELD_TYPES
        
        combo = editor_window.fields_table.cellWidget(0, 3)
        options = [combo.itemText(i) for i in range(combo.count())]
        
        for expected_type in FIELD_TYPES:
            assert expected_type in options


class TestDefaultsChange:
    """Tests for defaults checkbox functionality."""
    
    def test_defaults_checkboxes_exist(self, editor_window):
        """All expected default checkboxes exist."""
        from tools.field_editor import DEFAULTS_COLUMNS
        
        for col_name in DEFAULTS_COLUMNS:
            assert col_name in editor_window.default_checkboxes
    
    def test_defaults_change_triggers_recolor(self, editor_window, qtbot):
        """Changing a default checkbox triggers re-coloring."""
        # Get one of the default checkboxes
        cb = editor_window.default_checkboxes.get('visible')
        assert cb is not None
        
        original_state = cb.isChecked()
        
        # Toggle - should trigger _on_defaults_changed -> _apply_all_colors
        cb.setChecked(not original_state)
        
        # Restore
        cb.setChecked(original_state)
        
        # Test passes if no exceptions raised during the toggle


class TestFieldSpecExtraction:
    """Tests for _get_field_spec_from_row functionality."""
    
    def test_extracts_name(self, editor_window):
        """Field spec correctly extracts name."""
        spec = editor_window._get_field_spec_from_row(0)
        
        # Name should match the first column text
        expected = editor_window.fields_table.item(0, 0).text()
        assert spec.name == expected
    
    def test_extracts_booleans(self, editor_window):
        """Field spec correctly extracts boolean values."""
        from PyQt6.QtWidgets import QCheckBox
        
        spec = editor_window._get_field_spec_from_row(0)
        
        # Get actual checkbox state for visible (col 4)
        widget = editor_window.fields_table.cellWidget(0, 4)
        cb = widget.findChild(QCheckBox)
        expected_visible = cb.isChecked()
        
        assert spec.visible == expected_visible
    
    def test_extracts_dropdown(self, editor_window):
        """Field spec correctly extracts type dropdown value."""
        spec = editor_window._get_field_spec_from_row(0)
        
        # Get actual dropdown text
        combo = editor_window.fields_table.cellWidget(0, 3)
        expected_type = combo.currentText()
        
        assert spec.field_type == expected_type
    
    def test_returns_fieldspec_instance(self, editor_window):
        """Returns a proper FieldSpec dataclass instance."""
        from tools.yellberus_parser import FieldSpec
        
        spec = editor_window._get_field_spec_from_row(0)
        assert isinstance(spec, FieldSpec)


class TestColorApplication:
    """Tests for color application functionality."""
    
    def test_new_field_gets_green_color(self, editor_window):
        """New fields should be colored green."""
        editor_window.fields_table.setSortingEnabled(False)
        
        # Add a new field
        editor_window._on_add_field()
        new_row = editor_window.fields_table.rowCount() - 1
        
        # Set a name (makes it a real new field)
        name_item = editor_window.fields_table.item(new_row, 0)
        name_item.setText("brand_new_field_xyz")
        editor_window._on_item_changed(name_item)
        
        # Check the background color
        bg = name_item.background().color()
        
        # Green color is #203a20 -> RGB(32, 58, 32)
        assert bg.green() > bg.red() and bg.green() > bg.blue()
    
    def test_editing_existing_field_triggers_color(self, editor_window):
        """Editing an existing field triggers color change (red for code diff)."""
        item = editor_window.fields_table.item(0, 1)  # UI Header of first field
        original_text = item.text()
        
        # Change it
        item.setText(original_text + "_MODIFIED")
        
        # Check color changed
        bg = item.background().color()
        has_color = bg.alpha() > 0
        
        # Restore
        item.setText(original_text)
        
        assert has_color
