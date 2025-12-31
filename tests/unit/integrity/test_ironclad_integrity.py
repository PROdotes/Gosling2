import pytest
import dataclasses
import json
import sqlite3
import os
from src.core import yellberus
from src.data.models.song import Song
from src.data.database import BaseRepository

def test_yellberus_schema_internal():
    """
    Law of Derivation: Integrity check built into Yellberus itself.
    Ensures that FIELDS, id3_frames.json, and Song model attributes are aligned.
    """
    try:
        yellberus.validate_schema()
    except yellberus.SchemaError as e:
        pytest.fail(str(e))

def test_song_model_field_alignment():
    """
    Law of Mirroring: Every field in yellberus.FIELDS must exist in the Song model.
    Exceptions are covered by aliases or model_attr.
    """
    model_fields = {f.name for f in dataclasses.fields(Song)}
    # Add known properties/aliases that Song defines (not just dataclass fields)
    model_fields.add('source_id')
    model_fields.add('source')
    model_fields.add('unified_artist') # Computed
    model_fields.add('title') # Alias
    model_fields.add('path') # Alias
    model_fields.add('file_id') # Alias
    model_fields.add('year') # Alias
    
    # Map from Yellberus name to Song attribute if they differ
    attr_map = {
        'file_id': 'source_id',
        'path': 'source',
        'title': 'name',
    }
    
    for field in yellberus.FIELDS:
        attr = attr_map.get(field.name, field.name)
        # Check dataclass fields OR hasattr (for properties)
        assert attr in model_fields or hasattr(Song, attr), \
            f"Yellberus field '{field.name}' has no matching attribute '{attr}' in Song model."

def test_database_schema_alignment():
    """
    Law of Mirroring: Every column in the core DB tables should be represented in yellberus.FIELDS.
    Or be explicitly ignored if it's internal housekeeping.
    """
    # 1. Setup temp DB to get schema
    import tempfile
    fd, path = tempfile.mkstemp()
    os.close(fd)
    
    try:
        repo = BaseRepository(path)
        with sqlite3.connect(path) as conn:
            cursor = conn.cursor()
            
            # Gather all columns from core tables
            cursor.execute("PRAGMA table_info(MediaSources)")
            ms_cols = {row[1] for row in cursor.fetchall()}
            
            cursor.execute("PRAGMA table_info(Songs)")
            song_cols = {row[1] for row in cursor.fetchall()}
            
            db_cols = ms_cols | song_cols
            
        # 2. Gather columns from Yellberus
        yell_cols = set()
        for f in yellberus.FIELDS:
            # DB column might be 'MS.Name' or 'Producers' or 'S.BPM'
            col = f.db_column
            if '.' in col:
                col = col.split('.')[1]
            yell_cols.add(col)
            
        # 3. Known system columns that don't need UI mapping
        ignored_cols = {
            'Notes', # Partially implemented in some widgets, but in MS table
            'SourceID', # Handled via ID mapping
            'TypeID', # Internal categorization
        }
        
        # 4. Check for orphans (Columns in DB but not in Yellberus)
        orphans = db_cols - yell_cols - ignored_cols
        # Actually, let's be strict: everything in DB should be in Yellberus if it's a "Field"
        # But SourceID etc are keys.
        assert not orphans, f"Database has orphan columns not registered in Yellberus: {orphans}"
        
        # 5. Check for missing (Fields in Yellberus but not in DB)
        # Note: Some Yellberus fields are virtual (computed), they don't have direct columns.
        for f in yellberus.FIELDS:
            # Skip virtual fields or fields in joined tables (Albums etc)
            if f.query_expression and any(x in f.query_expression for x in ("GROUP_CONCAT", "COALESCE", "CASE")):
                continue 
            
            # If it explicitly targets MS or S table, it must exist
            if f.db_column.startswith(('MS.', 'S.')):
                col = f.db_column.split('.')[1]
                assert col in db_cols, f"Yellberus field '{f.name}' references DB column '{f.db_column}', but it was not found in schema!"

    finally:
        if os.path.exists(path):
            try: os.remove(path)
            except: pass

def test_id3_mapping_integrity():
    """
    Ensures that every 'portable' field in Yellberus is actually present in id3_frames.json
    and maps to a valid frame that MetadataService can handle.
    """
    import json
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    json_path = os.path.join(project_root, 'src', 'resources', 'id3_frames.json')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        id3_frames = json.load(f)
        
    mapped_fields = set()
    for frame_code, frame_info in id3_frames.items():
        if isinstance(frame_info, dict) and 'field' in frame_info:
            mapped_fields.add(frame_info['field'])
    
    for f in yellberus.FIELDS:
        if f.portable:
            # The name in Yellberus must match the 'field' name in id3_frames.json
            assert f.name in mapped_fields or f.id3_tag in id3_frames, \
                f"Portable field '{f.name}' (Tag: {f.id3_tag}) is not mapped to any frame in id3_frames.json."

def test_filter_widget_strategies():
    """
    Ensures every filterable field has a valid strategy and grouper.
    """
    for f in yellberus.FIELDS:
        if f.filterable:
            assert f.strategy is not None, f"Filterable field '{f.name}' must have a strategy!"
            if f.strategy in ("decade_grouper", "first_letter_grouper"):
                 assert f.strategy in yellberus.GROUPERS, f"Field '{f.name}' uses unknown strategy '{f.strategy}'"
