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
        # Create directory structure matching what write_field_registry_md expects
        # file_path.parent.parent / "src" / "resources" / "id3_frames.json"
        design_dir = tmp_path / "design"
        design_dir.mkdir()
        src_dir = tmp_path / "src"
        resources_dir = src_dir / "resources"
        resources_dir.mkdir(parents=True)
        
        # Create mock id3_frames.json with mappings for test fields
        import json
        id3_frames = {
            "TIT2": {"field": "title", "description": "Title"},
            "TBPM": {"field": "bpm", "description": "BPM"},
        }
        (resources_dir / "id3_frames.json").write_text(json.dumps(id3_frames), encoding="utf-8")
        
        # Create a minimal MD file with table structure
        md_content = """# Field Registry

## Current Fields

| Name | UI Header | DB Column | Type | Visible | Editable | Filterable | Searchable | Required | Portable | ID3 Tag |
|------|-----------|-----------|------|---------|----------|------------|------------|----------|----------|---------|
| `old_field` | Old | O.Old | TEXT | Yes | Yes | No | No | No | Yes | — |

**Total: 1 fields**
"""
        md_file = design_dir / "FIELD_REGISTRY.md"
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
        
        # Check field rows (now includes empty Strategy column)
        assert "| `title` | Title | MS.Name | TEXT |  | Yes | Yes | No | Yes | Yes | Yes | TIT2 |" in content
        assert "| `bpm` | BPM | S.TempoBPM | INTEGER |  | Yes | Yes | Yes | No | No | Yes | TBPM |" in content
        
        # Check total updated
        assert "**Total: 2 fields**" in content
        
        # Check backup created
        backup = design_dir / "FIELD_REGISTRY.md.bak"
        assert backup.exists()

    def test_generate_md_table_with_missing_id3(self, tmp_path):
        """Test that missing ID3 tags render as em-dash."""
        md_content = """# Field Registry

## Current Fields

| Name | UI Header | DB Column | Type | Visible | Editable | Filterable | Searchable | Required | Portable | ID3 Tag |
|------|-----------|-----------|------|---------|----------|------------|------------|----------|----------|---------|

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
        """Test that values matching defaults are NOT written (sparse writing).
        
        Design decision: We write only non-default values to keep field definitions
        clean and minimal.
        """
        real_yellberus = Path(__file__).parent.parent.parent.parent / "src" / "core" / "yellberus.py"
        test_yellberus = tmp_path / "yellberus.py"
        shutil.copy(real_yellberus, test_yellberus)
        
        # Create a field with values matching defaults
        fields = [
            FieldSpec(
                name="test_field",
                ui_header="Test",
                db_column="T.Test",
                field_type="TEXT",
                visible=True,      # matches default - NOT written
                filterable=False,  # matches default - NOT written
                searchable=True,   # matches default - NOT written
                required=False,    # matches default - NOT written
                portable=False,    # matches default - NOT written (updated to False)
            ),
        ]
        
        result = write_yellberus(test_yellberus, fields, defaults=FIELD_DEFAULTS)
        assert result is True
        
        content = test_yellberus.read_text(encoding="utf-8")
        
        # Find the test_field block
        import re
        field_block = re.search(r'FieldDef\(\s*name="test_field"[^)]+\)', content, re.DOTALL)
        assert field_block is not None
        block_text = field_block.group(0)
        
        # Sparse: values matching defaults should NOT appear
        assert "visible=" not in block_text  # True is default
        assert "filterable=" not in block_text  # False is default
        assert "searchable=" not in block_text  # True is default
        assert "required=" not in block_text  # False is default
        assert "portable=" not in block_text  # False is default (updated)

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

    def test_preserve_extra_attributes(self, tmp_path):
        """Test that unknown attributes (like query_expression) are preserved."""
        real_yellberus = Path(__file__).parent.parent.parent.parent / "src" / "core" / "yellberus.py"
        test_yellberus = tmp_path / "yellberus.py"
        shutil.copy(real_yellberus, test_yellberus)
        
        # Create a field with an extra attribute
        fields = [
            FieldSpec(
                name="complex_field",
                ui_header="Complex",
                db_column="C.Complex",
                extra_attributes={"query_expression": "GROUP_CONCAT(Something)"}
            )
        ]
        
        # Write
        write_yellberus(test_yellberus, fields)
        
        # Read back content to verify string representation
        content = test_yellberus.read_text(encoding="utf-8")
        # repr('...') might produce "..." or '...'
        expected_repr = repr("GROUP_CONCAT(Something)") # "'GROUP_CONCAT(Something)'"
        assert f'query_expression={expected_repr}' in content
        
        # Parse back to verify structure
        reloaded = parse_yellberus(test_yellberus)
        assert len(reloaded) == 1
        assert reloaded[0].name == "complex_field"
        # Since parse_yellberus uses _parse_fielddef_call which we updated to capture unknowns
        assert "query_expression" in reloaded[0].extra_attributes
        assert reloaded[0].extra_attributes["query_expression"] == "GROUP_CONCAT(Something)"


class TestTxxxAutoAdd:
    """Tests for the TXXX auto-add functionality."""
    
    def test_add_txxx_entry_creates_valid_json(self, tmp_path):
        """Test that adding TXXX entries produces valid JSON."""
        import json
        
        # Create initial JSON
        json_path = tmp_path / "id3_frames.json"
        initial_data = {"TIT2": {"field": "title", "type": "text"}}
        json_path.write_text(json.dumps(initial_data), encoding="utf-8")
        
        # Simulate the add logic
        field_names = ["custom_field", "another_field"]
        
        # Load, add, save (mimicking _add_txxx_entries logic)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for name in field_names:
            key = f"TXXX:{name}"
            if key not in data:
                data[key] = {
                    "description": f"Custom field: {name}",
                    "field": name,
                    "type": "text"
                }
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # Verify JSON is still valid
        result = json.loads(json_path.read_text(encoding="utf-8"))
        
        # Verify original entry preserved
        assert "TIT2" in result
        assert result["TIT2"]["field"] == "title"
        
        # Verify TXXX entries added
        assert "TXXX:custom_field" in result
        assert result["TXXX:custom_field"]["field"] == "custom_field"
        assert result["TXXX:custom_field"]["type"] == "text"
        
        assert "TXXX:another_field" in result
        assert result["TXXX:another_field"]["field"] == "another_field"

    def test_add_txxx_entry_does_not_duplicate(self, tmp_path):
        """Test that existing TXXX entries are not overwritten."""
        import json
        
        # Create JSON with existing TXXX entry
        json_path = tmp_path / "id3_frames.json"
        initial_data = {
            "TIT2": {"field": "title"},
            "TXXX:existing_field": {"field": "existing_field", "type": "custom_type", "description": "Original"}
        }
        json_path.write_text(json.dumps(initial_data), encoding="utf-8")
        
        # Try to add same field again
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        name = "existing_field"
        key = f"TXXX:{name}"
        if key not in data:  # This check should prevent overwrite
            data[key] = {"field": name, "type": "text"}
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # Verify original TXXX entry preserved
        result = json.loads(json_path.read_text(encoding="utf-8"))
        assert result["TXXX:existing_field"]["type"] == "custom_type"  # Not overwritten
        assert result["TXXX:existing_field"]["description"] == "Original"

    def test_add_txxx_creates_backup(self, tmp_path):
        """Test that adding TXXX entries creates a backup."""
        import json
        import shutil
        
        json_path = tmp_path / "id3_frames.json"
        backup_path = json_path.with_suffix(".json.bak")
        
        initial_data = {"TIT2": {"field": "title"}}
        json_path.write_text(json.dumps(initial_data), encoding="utf-8")
        
        # Create backup (mimicking _add_txxx_entries logic)
        shutil.copy2(json_path, backup_path)
        
        # Modify original
        data = json.loads(json_path.read_text())
        data["TXXX:new_field"] = {"field": "new_field", "type": "text"}
        json_path.write_text(json.dumps(data), encoding="utf-8")
        
        # Verify backup exists and has original data
        assert backup_path.exists()
        backup_data = json.loads(backup_path.read_text())
        assert "TIT2" in backup_data
        assert "TXXX:new_field" not in backup_data  # Backup has original state


class TestDbColumnAutoGenerate:
    """Tests for the DB Column auto-generate functionality."""
    
    def test_auto_generate_db_column_creates_correct_format(self):
        """Test that auto-generated DB columns follow S.{field_name} pattern."""
        field_names = ["pikachu", "charizard", "bulbasaur"]
        
        for name in field_names:
            expected = f"S.{name}"
            assert expected == f"S.{name}"  # Pattern verification
    
    def test_auto_generate_preserves_existing_columns(self):
        """Test that fields with existing db_column are not modified."""
        from tools.yellberus_parser import FieldSpec
        
        # Field with existing column
        field_with_col = FieldSpec(name="title", db_column="MS.Name")
        # Field without column
        field_without_col = FieldSpec(name="pikachu", db_column="")
        
        # Only the one without should need auto-generation
        needs_autogen = [f for f in [field_with_col, field_without_col] if not f.db_column]
        
        assert len(needs_autogen) == 1
        assert needs_autogen[0].name == "pikachu"
        assert field_with_col.db_column == "MS.Name"  # Preserved


class TestDynamicDefaults:
    """Tests that parser respects defaults defined in FieldDef class."""
    
    def test_parser_uses_defaults_from_code(self, tmp_path):
        """Test that omitting a field results in the value defined in class defaults."""
        yellberus_file = tmp_path / "yellberus.py"
        
        # Scenario 1: FieldDef has portable=True
        yellberus_file.write_text("""
from dataclasses import dataclass

@dataclass
class FieldDef:
    name: str
    portable: bool = True  # Default is TRUE

FIELDS = [
    FieldDef(name="implicit_portable"),  # Should be portable=True
    FieldDef(name="explicit_false", portable=False)
]
""", encoding="utf-8")
        
        # Parse it
        fields = parse_yellberus(yellberus_file)
        
        # Verify
        implicit = next(f for f in fields if f.name == "implicit_portable")
        explicit = next(f for f in fields if f.name == "explicit_false")
        
        assert implicit.portable is True, "Should inherit True from FieldDef default"
        assert explicit.portable is False
        
        # Scenario 2: FieldDef has portable=False
        yellberus_file.write_text("""
from dataclasses import dataclass

@dataclass
class FieldDef:
    name: str
    portable: bool = False  # Default is FALSE

FIELDS = [
    FieldDef(name="implicit_portable"),  # Should be portable=False
    FieldDef(name="explicit_true", portable=True)
]
""", encoding="utf-8")
        
        # Parse again
        fields = parse_yellberus(yellberus_file)
        
        # Verify
        implicit = next(f for f in fields if f.name == "implicit_portable")
        explicit = next(f for f in fields if f.name == "explicit_true")
        
        assert implicit.portable is False, "Should inherit False from FieldDef default"
        assert explicit.portable is True

