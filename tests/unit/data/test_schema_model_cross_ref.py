import pytest
import dataclasses
from src.data.repositories.base_repository import BaseRepository
from src.data.models.song import Song

def test_cross_reference_integrity(tmp_path):
    """
    Cross-Reference Integrity Test:
    Ensures that the Database Schema (MediaSources + Songs tables) and 
    The Domain Model ('Song' class) remain aligned.
    
    If you add a column, this test fails unless you also add it to 'Song' 
    (or explicitly exclude it here).
    """
    # 1. Get Database Columns from MediaSources and Songs
    db_path = tmp_path / "test_cross_ref.db"
    repo = BaseRepository(str(db_path))
    
    with repo.get_connection() as conn:
        cursor = conn.cursor()
        
        # Get MediaSources columns
        cursor.execute("PRAGMA table_info(MediaSources)")
        ms_columns = {row[1] for row in cursor.fetchall()}
        
        # Get Songs columns
        cursor.execute("PRAGMA table_info(Songs)")
        songs_columns = {row[1] for row in cursor.fetchall()}
        
    # 2. Get Model Fields (including inherited from MediaSource)
    model_fields = {f.name for f in dataclasses.fields(Song)}
    
    # 3. Define Mapping / Expected Alignments
    # DB Columns -> Expected Model Field (combined from both tables)
    db_to_model_map = {
        # MediaSources table
        "SourceID": "source_id",
        "TypeID": "type_id",
        "Name": "name",
        "Notes": "notes",
        "Source": "source",
        "Duration": "duration",
        "IsActive": "is_active",
        
        # Songs table
        "TempoBPM": "bpm",
        "RecordingYear": "recording_year",
        "ISRC": "isrc",
        "IsDone": "is_done"
    }
    
    # Model Fields -> Expected DB Column (or Relationship Check/Exclusion)
    model_to_db_map = {
        # From MediaSource (inherited)
        "source_id": "SourceID",
        "type_id": "TypeID",
        "name": "Name",
        "source": "Source",
        "duration": "Duration",
        "notes": "Notes",
        "is_active": "IsActive",
        
        # From Song
        "bpm": "TempoBPM",
        "recording_year": "RecordingYear",
        "isrc": "ISRC",
        "is_done": "IsDone",
        
        # Relationships (Not direct columns, but exist via junction tables)
        "performers": "RELATIONSHIP (Contributors via Performer)",
        "composers": "RELATIONSHIP (Contributors via Composer)",
        "lyricists": "RELATIONSHIP (Contributors via Lyricist)",
        "producers": "RELATIONSHIP (Contributors via Producer)",
        "groups": "RELATIONSHIP (GroupMembers)"
    }
    
    # 4. Verify DB Coverage
    # Every column in MediaSources/Songs should be mapped
    all_db_columns = ms_columns | songs_columns
    for col in all_db_columns:
        assert col in db_to_model_map, \
            f"DB Column '{col}' is NOT mapped! Add to db_to_model_map."
            
    # 5. Verify Model Coverage
    # Every field in Song must map to a DB column or known relationship
    for field in model_fields:
        assert field in model_to_db_map, \
            f"Song Model field '{field}' has no known DB persistence! Check mappings."
