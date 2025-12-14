import pytest
import dataclasses
from src.data.repositories.base_repository import BaseRepository
from src.data.models.song import Song

def test_cross_reference_integrity(tmp_path):
    """
    Cross-Reference Integrity Test:
    Ensures that the Database Schema (Columns in 'Files' table) and 
    The Domain Model ('Song' class) remain aligned.
    
    If you add a column to 'Files', this test fails unless you also add it to 'Song' 
    (or explicitly exclude it here).
    If you add a field to 'Song', this test fails unless you add it to 'Files' 
    (or explicitly exclude it here).
    """
    # 1. Get Database Columns
    db_path = tmp_path / "test_cross_ref.db"
    repo = BaseRepository(str(db_path))
    
    with repo.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Files)")
        columns_info = cursor.fetchall()
        db_columns = {row[1] for row in columns_info}
        
    # 2. Get Model Fields
    model_fields = {f.name for f in dataclasses.fields(Song)}
    
    # 3. Define Mapping / Expected Alignments
    # Some names differ slightly or are handled via relationships (not direct columns in Files)
    
    # Direct mappings (Name in DB -> Name in Model)
    # Note: Song model uses snake_case, DB uses PascalCase or CamelCase often.
    # We need a normalization map or manual checking.
    
    # DB Columns -> Expected Model Field
    db_to_model_map = {
        "FileID": "file_id",
        "Path": "path",
        "Title": "title",
        "Duration": "duration",
        "TempoBPM": "bpm"
    }
    
    # Model Fields -> Expected DB Column (or Relationship Check/Exclusion)
    model_to_db_map = {
        "file_id": "FileID",
        "path": "Path",
        "title": "Title",
        "duration": "Duration",
        "bpm": "TempoBPM",
        
        # Relationships (Not columns in Files, but exist in DB schema somewhere)
        # We explicitly allow these to NOT be columns in Files, but we should verify they mean something
        "performers": "RELATIONSHIP (Contributors via Performer)",
        "composers": "RELATIONSHIP (Contributors via Composer)",
        "lyricists": "RELATIONSHIP (Contributors via Lyricist)",
        "producers": "RELATIONSHIP (Contributors via Producer)",
        "groups": "RELATIONSHIP (GroupMembers)"
    }
    
    # 4. Verify DB Coverage
    # Every column in Files must map to a model field
    for col in db_columns:
        assert col in db_to_model_map, \
            f"DB Column '{col}' in Files table is NOT mapped to Song model! Update Song class."
            
        expected_field = db_to_model_map[col]
        assert expected_field in model_fields, \
            f"DB Column '{col}' maps to field '{expected_field}', but Song model is missing '{expected_field}'"
            
    # 5. Verify Model Coverage
    # Every field in Song must map to a DB column or known relationship
    for field in model_fields:
        assert field in model_to_db_map, \
            f"Song Model field '{field}' has no known DB persistence! Check mappings."
