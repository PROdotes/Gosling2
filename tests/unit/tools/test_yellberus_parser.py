"""
Unit tests for yellberus_parser module.
Tests parsing and writing of yellberus.py and FIELD_REGISTRY.md.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from tools.yellberus_parser import (
    parse_yellberus,
    parse_field_registry_md,
    write_yellberus,
    write_field_registry_md,
    FieldSpec,
    FIELD_DEFAULTS,
)


class TestWriteFieldRegistryMd:
    """Tests for 6.2: generate_md_table produces valid markdown."""
    
    def test_generate_md_table_basic(self, tmp_path):
        """Test that write_field_registry_md produces valid markdown table."""
        # Create a minimal MD file with table structure
        md_content = """# Field Registry

## Current Fields

| Name | UI Header | DB Column | Type | Visible | Filterable | Searchable | Required | Portable | ID3 Tag |
|------|-----------|-----------|------|---------|------------|------------|----------|----------|---------|
| `old_field` | Old | O.Old | TEXT | Yes | No | No | No | Yes | — |

**Total: 1 fields**
"""
        md_file = tmp_path / "FIELD_REGISTRY.md"
        md_file.write_text(md_content, encoding="utf-8")
        
        # Create test fields
        fields = [
            FieldSpec(
                name="title",
                ui_header="Title",
                db_column="MS.Name",
                field_type="TEXT",
                visible=True,
                filterable=False,
                searchable=True,
                required=True,
                portable=True,
                id3_tag="TIT2"
            ),
            FieldSpec(
                name="bpm",
                ui_header="BPM",
                db_column="S.TempoBPM",
                field_type="INTEGER",
                visible=True,
                filterable=True,
                searchable=False,
                required=False,
                portable=True,
                id3_tag="TBPM"
            ),
        ]
        
        # Write
        result = write_field_registry_md(md_file, fields)
        assert result is True
        
        # Verify output
        content = md_file.read_text(encoding="utf-8")
        
        # Check table structure
        assert "| Name | UI Header |" in content
        assert "|------|-----------|" in content
        
        # Check field rows
        assert "| `title` | Title | MS.Name | TEXT | Yes | No | Yes | Yes | Yes | TIT2 |" in content
        assert "| `bpm` | BPM | S.TempoBPM | INTEGER | Yes | Yes | No | No | Yes | TBPM |" in content
        
        # Check total updated
        assert "**Total: 2 fields**" in content
        
        # Check backup created
        backup = tmp_path / "FIELD_REGISTRY.md.bak"
        assert backup.exists()

    def test_generate_md_table_with_missing_id3(self, tmp_path):
        """Test that missing ID3 tags render as em-dash."""
        md_content = """# Field Registry

## Current Fields

| Name | UI Header | DB Column | Type | Visible | Filterable | Searchable | Required | Portable | ID3 Tag |
|------|-----------|-----------|------|---------|------------|------------|----------|----------|---------|

**Total: 0 fields**
"""
        md_file = tmp_path / "FIELD_REGISTRY.md"
        md_file.write_text(md_content, encoding="utf-8")
        
        fields = [
            FieldSpec(
                name="file_id",
                ui_header="ID",
                db_column="MS.SourceID",
                field_type="INTEGER",
                visible=False,
                filterable=False,
                searchable=False,
                required=True,
                portable=False,
                id3_tag=None  # No ID3 tag
            ),
        ]
        
        result = write_field_registry_md(md_file, fields)
        assert result is True
        
        content = md_file.read_text(encoding="utf-8")
        # Should render as em-dash
        assert "| — |" in content or "| — |" in content


class TestWriteYellberus:
    """Tests for 7.2: generate_python_block produces valid Python."""
    
    def test_generate_python_block_basic(self, tmp_path):
        """Test that write_yellberus produces valid Python."""
        # Copy real yellberus.py to temp
        real_yellberus = Path(__file__).parent.parent.parent.parent / "src" / "core" / "yellberus.py"
        test_yellberus = tmp_path / "yellberus.py"
        shutil.copy(real_yellberus, test_yellberus)
        
        # Parse existing fields
        original_fields = parse_yellberus(test_yellberus)
        assert len(original_fields) > 0
        
        # Modify one field
        modified_fields = list(original_fields)
        modified_fields[0] = FieldSpec(
            name=modified_fields[0].name,
            ui_header="MODIFIED_HEADER",
            db_column=modified_fields[0].db_column,
            field_type=modified_fields[0].field_type,
            visible=modified_fields[0].visible,
            filterable=modified_fields[0].filterable,
            searchable=modified_fields[0].searchable,
            required=modified_fields[0].required,
            portable=modified_fields[0].portable,
        )
        
        # Write
        result = write_yellberus(test_yellberus, modified_fields)
        assert result is True
        
        # Verify Python is syntactically valid
        content = test_yellberus.read_text(encoding="utf-8")
        compile(content, test_yellberus, "exec")  # Raises SyntaxError if invalid
        
        # Verify modification persisted
        reloaded = parse_yellberus(test_yellberus)
        assert reloaded[0].ui_header == "MODIFIED_HEADER"
        
        # Check backup created
        backup = tmp_path / "yellberus.py.bak"
        assert backup.exists()

    def test_sparse_writing(self, tmp_path):
        """Test that only non-default values are written (sparse output)."""
        real_yellberus = Path(__file__).parent.parent.parent.parent / "src" / "core" / "yellberus.py"
        test_yellberus = tmp_path / "yellberus.py"
        shutil.copy(real_yellberus, test_yellberus)
        
        # Create a field with all defaults
        fields = [
            FieldSpec(
                name="test_field",
                ui_header="Test",
                db_column="T.Test",
                field_type="TEXT",
                visible=True,      # default
                filterable=False,  # default
                searchable=False,  # default
                required=False,    # default
                portable=True,     # default
            ),
        ]
        
        # Use default defaults
        result = write_yellberus(test_yellberus, fields, defaults=FIELD_DEFAULTS)
        assert result is True
        
        content = test_yellberus.read_text(encoding="utf-8")
        
        # Find the test_field block
        # Should NOT contain explicit visible=True, filterable=False, etc.
        # since they match defaults
        import re
        field_block = re.search(r'FieldDef\(\s*name="test_field"[^)]+\)', content, re.DOTALL)
        assert field_block is not None
        block_text = field_block.group(0)
        
        # These should NOT appear (they match defaults)
        assert "visible=True" not in block_text
        assert "filterable=False" not in block_text
        assert "searchable=False" not in block_text
        assert "required=False" not in block_text
        assert "portable=True" not in block_text

    def test_roundtrip(self, tmp_path):
        """Test 7.6: Load → Save → Load produces identical data."""
        real_yellberus = Path(__file__).parent.parent.parent.parent / "src" / "core" / "yellberus.py"
        test_yellberus = tmp_path / "yellberus.py"
        shutil.copy(real_yellberus, test_yellberus)
        
        # Load original
        original = parse_yellberus(test_yellberus)
        
        # Save without modification
        write_yellberus(test_yellberus, original)
        
        # Load again
        reloaded = parse_yellberus(test_yellberus)
        
        # Compare
        assert len(original) == len(reloaded)
        for orig, new in zip(original, reloaded):
            assert orig.name == new.name
            assert orig.ui_header == new.ui_header
            assert orig.db_column == new.db_column
            assert orig.field_type == new.field_type
            assert orig.visible == new.visible
            assert orig.filterable == new.filterable
            assert orig.searchable == new.searchable
            assert orig.required == new.required
            assert orig.portable == new.portable
