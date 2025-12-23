import pytest
import dataclasses
from src.data.models.song import Song

def test_song_model_schema_stability():
    """
    Model Integrity Test:
    Ensures that the Song data model has exactly the expected fields.
    If a developer adds 'genre' to the Song class, this test will fail,
    forcing them to explicitly update this test (and hopefully recall to check DB/Repo).
    """
    expected_fields = {
        "source_id",
        "type_id",
        "name",
        "source",
        "duration",
        "notes",
        "is_active",
        "is_done",
        "isrc",
        "bpm",
        "recording_year",
        "performers",
        "composers",
        "lyricists",
        "producers",
        "groups",
        "unified_artist",
        "album_artist",
        "album",
        "publisher",
        "genre"
    }
    
    actual_fields = {f.name for f in dataclasses.fields(Song)}
    
    missing = expected_fields - actual_fields
    extra = actual_fields - expected_fields
    
    assert not missing, f"Song Model missing expected fields: {missing}"
    assert not extra, f"Song Model has unexpected extra fields: {extra}. Update this test AND DB schema tests."

def test_strict_column_mapping():
    """
    STRICT Column Mapping:
    Ensures that every column in the 'Files' table defines a corresponding field in the 
    Song data model (or is explicitly ignored with a reason).
    """
    import sqlite3
    from src.data.database import BaseRepository
    
    # 1. Spin up a temporary DB to get the TRUE schema
    # We use :memory: and the actual BaseRepository caching logic might interfere if not handled,
    # but BaseRepository usually takes db_path.
    
    conn = sqlite3.connect(":memory:")
    # We must manually inject the schema or use a subclass, because BaseRepository 
    # might try to close the connection or we want to inspect exactly what BaseRepository creates.
    # Actually, let's use a temp file to be safe with BaseRepository.
    import tempfile
    import os
    
    fd, path = tempfile.mkstemp()
    os.close(fd)
    
    try:
        repo = BaseRepository(path) # This creates the schema
        
        with sqlite3.connect(path) as conn:
            cursor = conn.cursor()
            
            # 1. MediaSources
            cursor.execute("PRAGMA table_info(MediaSources)")
            ms_cols = {row[1] for row in cursor.fetchall()}
            
            # 2. Songs
            cursor.execute("PRAGMA table_info(Songs)")
            song_cols = {row[1] for row in cursor.fetchall()}
            
            db_columns = ms_cols | song_cols
            
        # 2. Get Model Fields
        model_fields = {f.name for f in dataclasses.fields(Song)}
        
        # 3. Define Mapping (DB -> Model)
        mapping = {
            "SourceID": "source_id",
            "TypeID": "type_id",
            "Name": "name",
            "Source": "source",
            "Duration": "duration",
            "Notes": "notes",
            "IsActive": "is_active",
            
            "TempoBPM": "bpm",
            "RecordingYear": "recording_year",
            "ISRC": "isrc",
            "IsDone": "is_done",
            "Groups": "groups",
            "AlbumArtist": "album_artist"
        }
        
        # 4. Strict Check
        for col in db_columns:
            if col in mapping:
                target_field = mapping[col]
                if target_field not in model_fields:
                     pytest.fail(f"DB Column '{col}' maps to field '{target_field}', but Song model is missing '{target_field}'.")
                continue
            
            pytest.fail(f"Strict Check: DB Column '{col}' is not mapped to any Song model field! "
                        f"Update the mapping in this test and the Song dataclass.")
            
    finally:
        # Ensure garbage collection releases any handles
        import gc
        gc.collect()
        
        # Retry removal a few times to handle Windows file locking delays
        if os.path.exists(path):
            import time
            for _ in range(3):
                try:
                    os.remove(path)
                    break
                except PermissionError:
                    time.sleep(0.1)
