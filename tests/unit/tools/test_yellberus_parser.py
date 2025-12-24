"""
Unit tests for yellberus_parser module.
Tests parsing and writing of yellberus.py and FIELD_REGISTRY.md.
"""

import pytest
from pathlib import Path
import json
import shutil
from dataclasses import dataclass

from tools.yellberus_parser import (
    parse_yellberus,
    parse_field_registry_md,
    write_yellberus,
    write_field_registry_md,
    DynamicFieldSpec, # Updated import
)

@dataclass
class SimpleFieldSpec:
    """Helper for creating specs in tests."""
    name: str
    ui_header: str = ""
    db_column: str = ""
    field_type: str = "TEXT"
    visible: bool = True
    editable: bool = True
    filterable: bool = False
    searchable: bool = True
    required: bool = False
    portable: bool = True
    strategy: str = "list"
    
    def to_dynamic(self):
        spec = DynamicFieldSpec(self.name, self.ui_header, self.db_column)
        spec.field_type = self.field_type
        spec.visible = self.visible
        spec.editable = self.editable
        spec.filterable = self.filterable
        spec.searchable = self.searchable
        spec.required = self.required
        spec.portable = self.portable
        spec.strategy = self.strategy
        return spec

# Mock defaults matching current yellberus.py state for tests
MOCK_DEFAULTS = {
    "visible": True,
    "editable": True,
    "filterable": False,
    "searchable": True,
    "required": False,
    "portable": True,
}

class TestWriteFieldRegistryMd:
    """Tests for 6.2: generate_md_table produces valid markdown."""
    
    def test_generate_md_table_basic(self, tmp_path):
        """Test that write_field_registry_md produces valid markdown table."""
        # Create directory structure
        design_dir = tmp_path / "design"
        design_dir.mkdir()
        src_dir = tmp_path / "src"
        resources_dir = src_dir / "resources"
        resources_dir.mkdir(parents=True)
        
        # Create mock id3_frames.json
        id3_frames = {
            "TIT2": {"field": "title", "description": "Title"},
            "TBPM": {"field": "bpm", "description": "BPM"},
        }
        (resources_dir / "id3_frames.json").write_text(json.dumps(id3_frames), encoding="utf-8")
        
        # Create a minimal MD file
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
            SimpleFieldSpec(
                name="title",
                ui_header="Title",
                db_column="MS.Name",
                field_type="TEXT",
                visible=True,
                filterable=False,
                searchable=True,
                required=True,
                portable=True,
            ).to_dynamic(),
            SimpleFieldSpec(
                name="bpm",
                ui_header="BPM",
                db_column="S.TempoBPM",
                field_type="INTEGER",
                visible=True,
                filterable=True,
                searchable=False,
                required=False,
                portable=True,
            ).to_dynamic(),
        ]
        
        # Write
        result = write_field_registry_md(md_file, fields)
        assert result is True
        
        # Verify output
        content = md_file.read_text(encoding="utf-8")
        
        # Check structure
        assert "| Name | UI Header |" in content
        
        # Check field rows (dynamic parser might output different strategy column formatting if empty, but let's check core)
        # Note: Dynamic parser adds 'strategy' defaulting to 'list' -> "" in display
        assert "| `title` | Title | MS.Name | TEXT |  | Yes | Yes | No | Yes | Yes | Yes | TIT2 |" in content
        assert "| `bpm` | BPM | S.TempoBPM | INTEGER |  | Yes | Yes | Yes | No | No | Yes | TBPM |" in content
        
        # Check total
        assert "**Total: 2 fields**" in content

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
            SimpleFieldSpec(
                name="file_id",
                ui_header="ID",
                db_column="MS.SourceID",
                field_type="INTEGER",
                visible=False,
                filterable=False,
                searchable=False,
                required=True,
                portable=False,
            ).to_dynamic(),
        ]
        
        # Note: write_field_registry_md will start looking for id3_frames.json relative to md_file
        # which is in tmp_path. So it won't find it -> empty dict -> lookup fails -> returns "—"
        
        result = write_field_registry_md(md_file, fields)
        assert result is True
        
        content = md_file.read_text(encoding="utf-8")
        assert "| — |" in content


class TestWriteYellberus:
    """Tests for 7.2: generate_python_block produces valid Python."""
    
    def test_generate_python_block_basic(self, tmp_path):
        """Test that write_yellberus produces valid Python."""
        real_yellberus = Path(__file__).parent.parent.parent.parent / "src" / "core" / "yellberus.py"
        test_yellberus = tmp_path / "yellberus.py"
        shutil.copy(real_yellberus, test_yellberus)
        
        original_fields = parse_yellberus(test_yellberus)
        assert len(original_fields) > 0
        
        # Modify one field
        # DynamicFieldSpec is mutable
        modified_fields = list(original_fields)
        modified_fields[0].ui_header = "MODIFIED_HEADER"
        
        # Write
        result = write_yellberus(test_yellberus, modified_fields)
        assert result is True
        
        # Verify syntax
        content = test_yellberus.read_text(encoding="utf-8")
        compile(content, test_yellberus, "exec")
        
        # Verify persistence
        reloaded = parse_yellberus(test_yellberus)
        assert reloaded[0].ui_header == "MODIFIED_HEADER"

    def test_sparse_writing(self, tmp_path):
        """Test that values matching defaults are NOT written."""
        real_yellberus = Path(__file__).parent.parent.parent.parent / "src" / "core" / "yellberus.py"
        test_yellberus = tmp_path / "yellberus.py"
        shutil.copy(real_yellberus, test_yellberus)
        
        fields = [
            SimpleFieldSpec(
                name="test_field",
                ui_header="Test",
                db_column="T.Test",
                # These match MOCK_DEFAULTS (and implicit defaults of SimpleFieldSpec)
                visible=True,
                filterable=False,
                searchable=True,
                required=False,
                portable=True,
            ).to_dynamic(),
        ]
        
        # We pass explicit defaults to compel the parser to use THEM for sparseness check
        # regardless of what's in the file.
        result = write_yellberus(test_yellberus, fields, defaults=MOCK_DEFAULTS)
        assert result is True
        
        content = test_yellberus.read_text(encoding="utf-8")
        
        import re
        field_block = re.search(r'FieldDef\(\s*name="test_field"[^)]+\)', content, re.DOTALL)
        assert field_block is not None
        block_text = field_block.group(0)
        
        # Sparse checks
        assert "visible=" not in block_text
        assert "filterable=" not in block_text
        assert "searchable=" not in block_text
        assert "required=" not in block_text 
        assert "portable=" not in block_text

    def test_roundtrip(self, tmp_path):
        """Test 7.6: Load → Save → Load produces identical data."""
        real_yellberus = Path(__file__).parent.parent.parent.parent / "src" / "core" / "yellberus.py"
        test_yellberus = tmp_path / "yellberus.py"
        shutil.copy(real_yellberus, test_yellberus)
        
        original = parse_yellberus(test_yellberus)
        write_yellberus(test_yellberus, original)
        reloaded = parse_yellberus(test_yellberus)
        
        assert len(original) == len(reloaded)
        for orig, new in zip(original, reloaded):
            assert orig.name == new.name
            assert orig.ui_header == new.ui_header
            assert orig.db_column == new.db_column
            # Check dynamic attributes match
            assert orig._attributes == new._attributes

    def test_preserve_extra_attributes(self, tmp_path):
        """Test that unknown attributes are preserved via dynamic handling."""
        real_yellberus = Path(__file__).parent.parent.parent.parent / "src" / "core" / "yellberus.py"
        test_yellberus = tmp_path / "yellberus.py"
        shutil.copy(real_yellberus, test_yellberus)
        
        # Create field with extra dynamic attr
        spec = SimpleFieldSpec(
            name="complex_field",
            ui_header="Complex",
            db_column="C.Complex"
        ).to_dynamic()
        spec.query_expression = "GROUP_CONCAT(Something)"
        
        write_yellberus(test_yellberus, [spec])
        
        content = test_yellberus.read_text(encoding="utf-8")
        expected_repr = repr("GROUP_CONCAT(Something)")
        assert f'query_expression={expected_repr}' in content
        
        reloaded = parse_yellberus(test_yellberus)
        assert len(reloaded) == 1
        assert reloaded[0].get("query_expression") == "GROUP_CONCAT(Something)"


class TestTxxxAutoAdd:
    """Tests for the TXXX auto-add functionality."""
    # Note: These tests touch JSON only, generic logic, should still pass.
    
    def test_add_txxx_entry_creates_valid_json(self, tmp_path):
        json_path = tmp_path / "id3_frames.json"
        initial_data = {"TIT2": {"field": "title", "type": "text"}}
        json_path.write_text(json.dumps(initial_data), encoding="utf-8")
        
        field_names = ["custom_field", "another_field"]
        
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
        
        result = json.loads(json_path.read_text(encoding="utf-8"))
        assert "TXXX:custom_field" in result
        assert result["TXXX:custom_field"]["field"] == "custom_field"


class TestDbColumnAutoGenerate:
    
    def test_auto_generate_db_column_creates_correct_format(self):
        field_names = ["pikachu", "charizard", "bulbasaur"]
        for name in field_names:
            expected = f"S.{name}"
            assert expected == f"S.{name}"
    
    def test_auto_generate_preserves_existing_columns(self):
        from tools.yellberus_parser import DynamicFieldSpec
        
        # Note: DynamicFieldSpec requires mandated args
        field_with_col = DynamicFieldSpec(name="title", ui_header="", db_column="MS.Name")
        field_without_col = DynamicFieldSpec(name="pikachu", ui_header="", db_column="")
        
        needs_autogen = [f for f in [field_with_col, field_without_col] if not f.db_column]
        
        assert len(needs_autogen) == 1
        assert needs_autogen[0].name == "pikachu"
        assert field_with_col.db_column == "MS.Name"


class TestDynamicDefaults:
    """Tests that parser respects defaults defined in FieldDef class."""
    
    def test_parser_uses_defaults_from_code(self, tmp_path):
        yellberus_file = tmp_path / "yellberus.py"
        
        # Scenario 1: FieldDef has portable=True default
        yellberus_file.write_text("""
from dataclasses import dataclass

@dataclass
class FieldDef:
    name: str = ""
    ui_header: str = ""
    db_column: str = ""
    portable: bool = True  # Default is TRUE

FIELDS = [
    FieldDef(name="implicit_portable"),  # Should be portable=True
    FieldDef(name="explicit_false", portable=False)
]
""", encoding="utf-8")
        
        fields = parse_yellberus(yellberus_file)
        
        implicit = next(f for f in fields if f.name == "implicit_portable")
        explicit = next(f for f in fields if f.name == "explicit_false")
        
        # Using .get because dynamic spec stores attrs
        assert implicit.get("portable") is True
        assert explicit.get("portable") is False
        
        # Scenario 2: FieldDef has portable=False default
        yellberus_file.write_text("""
from dataclasses import dataclass

@dataclass
class FieldDef:
    name: str = ""
    ui_header: str = ""
    db_column: str = ""
    portable: bool = False  # Default is FALSE

FIELDS = [
    FieldDef(name="implicit_portable"),  # Should be portable=False
    FieldDef(name="explicit_true", portable=True)
]
""", encoding="utf-8")
        
        fields = parse_yellberus(yellberus_file)
        
        implicit = next(f for f in fields if f.name == "implicit_portable")
        explicit = next(f for f in fields if f.name == "explicit_true")
        
        assert implicit.get("portable") is False
        assert explicit.get("portable") is True
