import pytest
import dataclasses
import ast
import json
import os
from src.data.models.song import Song
from src.business.services.metadata_service import MetadataService

def test_metadata_extraction_coverage():
    """
    Metadata Service Integrity Test:
    Ensures that EVERY field in the Song data model is populated by the MetadataService.
    
    This test verifies two things:
    1. MetadataService uses the dynamic **song_data unpacking pattern.
    2.id3_frames.json contains mappings for all relevant Song fields.
    """
    # 1. Get Expected Fields from Song Model
    model_fields = {f.name for f in dataclasses.fields(Song)}
    
    # 2. Parse MetadataService to ensure it uses dynamic unpacking
    from pathlib import Path
    project_root = Path(__file__).resolve().parents[3]
    service_path = project_root / "src" / "business" / "services" / "metadata_service.py"

    with open(service_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
        
    extract_func = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "extract_from_mp3"), None)
    assert extract_func, "Could not find 'extract_from_mp3' function!"
    
    song_call = None
    for node in ast.walk(extract_func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Song":
            song_call = node
            break
            
    assert song_call, "Could not find 'Song(...)' instantiation!"
    
    # Ensure it uses **something (starred keyword)
    has_starred = any(kw.arg is None and isinstance(kw.value, ast.Name) for kw in song_call.keywords)
    assert has_starred, "MetadataService should use dynamic unpacking (**song_data) for future-proofing."

    # 3. Load id3_frames.json and check coverage
    json_path = project_root / "src" / "resources" / "id3_frames.json"
    with open(json_path, "r", encoding="utf-8") as f:
        id3_frames = json.load(f)
    
    # Map from JSON 'field' names to Song attribute names
    # Note: Dynamic extraction in MetadataService uses the 'field' value from JSON
    # to populate song_data keys.
    mapped_fields = set()
    for frame_info in id3_frames.values():
        if isinstance(frame_info, dict) and 'field' in frame_info:
            mapped_fields.add(frame_info['field'])

    # Fields explicitly passed as keywords in Song() call
    explicit_keywords = {kw.arg for kw in song_call.keywords if kw.arg}
    
    # Aliases (JSON field -> Song attribute)
    # MetadataService.extract_from_mp3 logic maps raw 'field' from JSON.
    # If JSON field is 'title', it ends up in song_data['title'].
    # The Song model might use 'name'. We need to account for this if
    # the model and JSON field names differ.
    
    # Gosling2 Standard: JSON 'field' should match Song attribute name OR alias.
    # Currently title -> name is handled in Song constructor or manually?
    # Actually, Song's attributes ARE name, source, source_id, etc.
    
    ignored_fields = {
        'type_id', 'notes', 'is_active', 'unified_artist',
        'is_done', # Local DB flag
        'album', 'genre', 'publisher', # Relational fields populated later
        'source', 'source_id', # Handled explicitly
        'audio_hash', # Calculated hash
    }
    
    # Account for 'title' mapping to 'name'
    if 'title' in mapped_fields: mapped_fields.add('name')
    
    missing_fields = model_fields - mapped_fields - explicit_keywords - ignored_fields
    
    assert not missing_fields, \
        f"MetadataService is failing to map these Song fields from id3_frames.json: {missing_fields}. " \
        "Ensure the field exists in Song model AND has an entry in id3_frames.json."
