import pytest
import dataclasses
import ast
import inspect
from src.data.models.song import Song
from src.business.services.metadata_service import MetadataService

def test_metadata_extraction_coverage():
    """
    Metadata Service Integrity Test:
    Ensures that EVERY field in the Song data model is populated by the MetadataService.
    
    If a developer adds 'ReleaseYear' to Song, this test checks if MetadataService
    actually extracts logic for it.
    
    This uses AST (Abstract Syntax Tree) inspection to verify that the `Song` constructor
    call within `extract_from_mp3` includes all the fields.
    """
    # 1. Get Expected Fields from Song Model
    model_fields = {f.name for f in dataclasses.fields(Song)}
    
    # 1. Get Expected Fields from Song Model
    model_fields = {f.name for f in dataclasses.fields(Song)}
    
    # 2. Parse the File Directly (Robust path resolution)
    from pathlib import Path
    # Resolve project root relative to this test file:
    # tests/unit/services/test_metadata_service_coverage.py -> ... -> src/
    # parents[0]=services, [1]=unit, [2]=tests, [3]=ProjectRoot
    project_root = Path(__file__).resolve().parents[3]
    service_path = project_root / "src" / "business" / "services" / "metadata_service.py"
    
    with open(service_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
        
    # 3. Find extract_from_mp3 function
    extract_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "extract_from_mp3":
            extract_func = node
            break
            
    assert extract_func, "Could not find 'extract_from_mp3' function in MetadataService file!"
    
    # 4. Find return Song(...)
    song_instantiation = None
    for node in ast.walk(extract_func):
        if isinstance(node, ast.Return):
            # Check for Song(...) or Song(request=...)
            if isinstance(node.value, ast.Call):
                func = node.value.func
                # func could be Name(id='Song')
                if isinstance(func, ast.Name) and func.id == "Song":
                    song_instantiation = node.value
                    break
    
    assert song_instantiation, "Could not find 'return Song(...)' in extract_from_mp3!"

    # 5. Get Extracted Fields
    extracted_fields = {kw.arg for kw in song_instantiation.keywords}
    
    # 6. Compare
    missing_fields = model_fields - extracted_fields
    
    assert not missing_fields, \
        f"MetadataService is failing to populate these Song fields: {missing_fields}. " \
        "Did you add a field to the Model but forget to extract the ID3 tag for it?"
