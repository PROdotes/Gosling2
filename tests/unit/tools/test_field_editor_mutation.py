"""
Robustness (Mutation) tests for Field Editor and Yellberus Parser.
Focuses on corruption, injection, and environment failures.
Follows TESTING.md Law 1 (Separation) and Law 7 (Trust Boundaries).
"""

import pytest
import shutil
import ast
from pathlib import Path
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox

from tools.field_editor import FieldEditorWindow
from tools.yellberus_parser import write_yellberus, DynamicFieldSpec

@pytest.fixture
def mock_yellberus_file(tmp_path):
    """Create a temporary yellberus-like file for destructive testing."""
    content = '''
from typing import List, Any
from dataclasses import dataclass

@dataclass
class FieldDef:
    name: str
    ui_header: str
    db_column: str
    visible: bool = True
    editable: bool = True

FIELDS: List[FieldDef] = [
    FieldDef(name="title", ui_header="Title", db_column="MS.Name"),
    FieldDef(name="artist", ui_header="Artist", db_column="MS.Artist")
]
'''
    path = tmp_path / "yellberus_temp.py"
    path.write_text(content, encoding="utf-8")
    return path

@pytest.fixture
def editor_in_chaos(qtbot):
    """Initialize a window in test mode."""
    window = FieldEditorWindow()
    window._test_mode = True
    qtbot.add_widget(window)
    return window

class TestPersistenceRobustness:
    """Robustness tests for the file-writing logic."""

    def test_write_yellberus_syntax_error_resilience(self, mock_yellberus_file):
        """Mutation: Handling an existing file with syntax errors."""
        # Corrupt the file
        mock_yellberus_file.write_text("This is not valid python code {[[}", encoding="utf-8")
        
        fields = [DynamicFieldSpec(name="test", ui_header="Test", db_column="T.C")]
        
        # Should return False rather than raising an unhandled exception
        success = write_yellberus(mock_yellberus_file, fields)
        assert success is False

    def test_injection_protection(self, mock_yellberus_file):
        """Mutation: SQL and Python injection in field attributes."""
        # Dangerous strings
        sql_injection = '"; DROP TABLE Songs; --'
        python_injection = '", required=True); print("hacked"); #'
        
        f = DynamicFieldSpec(name="safe_name", ui_header=sql_injection, db_column=python_injection)
        f.visible = True
        f.editable = True
        f.filterable = True
        f.searchable = True
        f.required = False
        f.portable = False
        fields = [f]
        
        success = write_yellberus(mock_yellberus_file, fields)
        assert success is True
        
        # Verify result is correctly escaped in the file (not executed)
        content = mock_yellberus_file.read_text(encoding="utf-8")
        
        # Check that the injection strings are present in the content
        assert 'DROP TABLE Songs' in content
        assert 'hacked' in content
        
        # PROOF OF NO BREAKOUT: count the number of FieldDef calls
        # We only sent 1 field, so there should be exactly one FieldDef call in the FIELDS list
        assert content.count("FieldDef(") == 1

    def test_attribute_preservation_convergence(self, mock_yellberus_file):
        """Mutation: Ensure 'hidden' attributes survive a sparse write."""
        # 1. Manually add a field with a hidden attribute to the mock file
        content = mock_yellberus_file.read_text(encoding="utf-8")
        content = content.replace(
            'FieldDef(name="title", ui_header="Title", db_column="MS.Name")',
            'FieldDef(name="title", ui_header="Title", db_column="MS.Name", legacy_id=999)'
        )
        mock_yellberus_file.write_text(content, encoding="utf-8")
        
        # 2. Extract fields via parser
        from tools.yellberus_parser import parse_yellberus
        fields = parse_yellberus(mock_yellberus_file)
        
        # Verify legacy_id was parsed into _attributes
        title_field = next(f for f in fields if f.name == "title")
        assert title_field.legacy_id == 999
        
        # 3. Modify a DIFFERENT attribute (UI update)
        title_field.visible = False
        
        # 4. Write back
        success = write_yellberus(mock_yellberus_file, fields)
        assert success is True
        
        # 5. Verify legacy_id survived the burial
        new_content = mock_yellberus_file.read_text(encoding="utf-8")
        assert "legacy_id=999" in new_content
        assert "visible=False" in new_content

class TestUIEnvironmentRobustness:
    """Robustness tests for UI-level environment failures."""

    def test_save_failure_disk_full(self, editor_in_chaos, monkeypatch):
        """Mutation: PermissionError/Disk Full during save."""
        # Mock gather to return something with all required attributes
        f = DynamicFieldSpec(name="t", ui_header="T", db_column="C")
        f.visible = True
        f.editable = True
        f.filterable = True
        f.searchable = True
        f.required = False
        f.portable = False
        mock_fields = [f]
        monkeypatch.setattr(editor_in_chaos, "_gather_fields_for_save", lambda: mock_fields)
        
        # Set dirty state
        editor_in_chaos._dirty = True
        
        # Mock write_yellberus to raise an exception (simulating Disk Full or Locked File)
        from tools import yellberus_parser
        def mock_raise(*args, **kwargs):
            raise PermissionError("Access Denied or Disk Full")
            
        monkeypatch.setattr(yellberus_parser, "write_yellberus", mock_raise)
        
        # Mock QMessageBox to ensure it's called
        mock_msg = MagicMock()
        monkeypatch.setattr(QMessageBox, "critical", mock_msg)
        
        # Trigger save
        editor_in_chaos._on_save_clicked()
        
        # Verify:
        # 1. Error message was shown
        assert mock_msg.called
        # 2. Window is STILL DIRTY (did not reset dirty flag on failure)
        # Assuming the implementation doesn't reset it if logic fails
        # In field_editor.py: success_code = write_yellberus(...); if success_code: _dirty = False
        # If it raises before that, _dirty stays True.
        assert editor_in_chaos._dirty is True

    def test_load_malformed_md_table(self, editor_in_chaos, tmp_path):
        """Mutation: malformed Markdown table does not crash loader."""
        bad_md = tmp_path / "bad.md"
        bad_md.write_text("| Name | Title |\n|---|---|\n| garbage | without | enough | pipes |\n", encoding="utf-8")
        
        # Mock the path in the window
        from tools import field_editor
        old_md_path = Path("design/FIELD_REGISTRY.md")
        # We can't easily monkeypatch the path inside the method without mocking Path
        
        # Instead, let's test the parser directly for robustness
        from tools.yellberus_parser import parse_field_registry_md
        
        # Should not crash on malformed lines
        fields = parse_field_registry_md(bad_md)
        assert isinstance(fields, list)
        assert len(fields) == 0 # Garbage lines skipped

