"""
Unit tests for yellberus_parser module.
Tests parsing and writing of yellberus.py and FIELD_REGISTRY.md.
Follows Law 5 (Isolation) — Uses pure mocks, no dependencies on live src/core files.
"""

import pytest
import json
from pathlib import Path
from tools.yellberus_parser import (
    parse_yellberus,
    parse_field_registry_md,
    write_yellberus,
    write_field_registry_md,
    DynamicFieldSpec,
    extract_class_defaults,
)

MOCK_YELLBERUS_CONTENT = '''
from dataclasses import dataclass, field
from typing import List

@dataclass
class FieldDef:
    name: str = ""
    ui_header: str = ""
    db_column: str = ""
    visible: bool = True
    editable: bool = True
    filterable: bool = False
    searchable: bool = True
    required: bool = False
    portable: bool = True
    strategy: str = "list"

FIELDS: List[FieldDef] = [
    FieldDef(name="title", ui_header="Title", db_column="MS.Name"),
    FieldDef(name="artist", ui_header="Artist", db_column="MS.Artist", portable=False),
    FieldDef(name="bpm", ui_header="BPM", db_column="S.TempoBPM", required=True)
]
'''

@pytest.fixture
def mock_yellberus_file(tmp_path):
    path = tmp_path / "yellberus_mock.py"
    path.write_text(MOCK_YELLBERUS_CONTENT, encoding="utf-8")
    return path

class TestParsingLogic:
    """Tests for parsing functionality."""

    def test_parse_yellberus_fields(self, mock_yellberus_file):
        fields = parse_yellberus(mock_yellberus_file)
        assert len(fields) == 3
        assert fields[0].name == "title"
        assert fields[1].name == "artist"
        assert fields[1].portable is False
        assert fields[2].required is True

    def test_extract_class_defaults(self, mock_yellberus_file):
        defaults = extract_class_defaults(mock_yellberus_file)
        assert defaults["visible"] is True
        assert defaults["filterable"] is False
        assert defaults["portable"] is True

class TestWritingLogic:
    """Tests for writing functionality (Logic Layer)."""

    def test_write_yellberus_roundtrip(self, mock_yellberus_file):
        """Verify Load -> Modify -> Save -> Load consistency."""
        fields = parse_yellberus(mock_yellberus_file)
        fields[0].ui_header = "Song Title"
        
        success = write_yellberus(mock_yellberus_file, fields)
        assert success is True
        
        # Reload and verify
        reloaded = parse_yellberus(mock_yellberus_file)
        assert reloaded[0].ui_header == "Song Title"
        assert reloaded[1].name == "artist" # Still there

    def test_sparse_writing_respects_defaults(self, mock_yellberus_file):
        """Verify that default values are NOT explicitly written (Sparse Write)."""
        # Create field with visible=True explicitly in its __dict__
        f = DynamicFieldSpec(name="test", ui_header="Test", db_column="T.T")
        setattr(f, "visible", True)
        fields = [f]
        
        # If default is also True, it should be OMITTED from output
        defaults = {"visible": True}
        write_yellberus(mock_yellberus_file, fields, defaults=defaults)
        
        content = mock_yellberus_file.read_text(encoding="utf-8")
        assert 'name=' + repr("test") in content
        assert "visible=True" not in content # Should be sparse

    def test_write_preserves_complex_attributes(self, mock_yellberus_file):
        """Verify that extra attributes like query_expression survive."""
        fields = parse_yellberus(mock_yellberus_file)
        fields[0].query_expression = "COALESCE(title, 'Unknown')"
        
        write_yellberus(mock_yellberus_file, fields)
        
        content = mock_yellberus_file.read_text(encoding="utf-8")
        assert "query_expression=" in content
        assert "COALESCE" in content

class TestMarkdownLogic:
    """Tests for FIELD_REGISTRY.md generation."""

    def test_write_field_registry_md(self, tmp_path, monkeypatch):
        md_file = tmp_path / "design" / "FIELD_REGISTRY.md"
        md_file.parent.mkdir()
        
        # Seed with 12 columns including Strategy
        header = "| Name | UI Header | DB Column | Type | Strategy | Visible | Editable | Filterable | Searchable | Required | Portable | ID3 Tag |"
        sep = "|---|---|---|---|---|---|---|---|---|---|---|---|"
        md_file.write_text(f"# Registry\n\n{header}\n{sep}\n\n**Total: 0 fields**", encoding="utf-8")
        
        # Mock id3_frames in the structure the parser expects relative to the root
        # Parser does: id3_path = Path(__file__).parent.parent / "src" / "resources" / "id3_frames.json"
        # We need to monkeypatch the lookup or satisfy it.
        # Actually, let's just Satisfy the Path lookup by mocking Path.parent if needed, 
        # or better: monkeypatch the json loading inside the function.
        
        import tools.yellberus_parser
        id3_data = {"TIT2": {"field": "title"}}
        monkeypatch.setattr(tools.yellberus_parser, "_load_id3_frames", lambda path: id3_data)
        
        fields = [
            DynamicFieldSpec(name="title", ui_header="Title", db_column="MS.Name")
        ]
        fields[0].portable = True
        fields[0].field_type = "TEXT"
        fields[0].strategy = "list"
        fields[0].visible = True
        fields[0].editable = True
        fields[0].filterable = False
        fields[0].searchable = True
        fields[0].required = False
        
        success = write_field_registry_md(md_file, fields)
        
        assert success is True
        content = md_file.read_text(encoding="utf-8")
        # Check that TIT2 was looked up
        assert "TIT2" in content
        assert "**Total: 1 fields**" in content

    def test_parse_registry_md_table(self, tmp_path):
        md_file = tmp_path / "registry.md"
        content = "| Name | UI Header | DB Column | Type | Strategy | Visible | Editable | Filterable | Searchable | Required | Portable | ID3 Tag |\n"
        content += "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        content += "| `title` | Title | MS.Name | TEXT | list | Yes | Yes | No | Yes | No | Yes | TIT2 |\n"
        md_file.write_text(content, encoding="utf-8")
        
        fields = parse_field_registry_md(md_file)
        assert len(fields) == 1
        assert fields[0].name == "title"
        assert fields[0].ui_header == "Title"
        assert fields[0].portable is True
