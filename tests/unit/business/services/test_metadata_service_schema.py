import pytest
from unittest.mock import MagicMock, patch
from src.business.services.metadata_service import MetadataService
import sqlite3
import tempfile
import os
from src.data.repositories.base_repository import BaseRepository

def test_strict_extraction_coverage():
    """
    STRICT Metadata Extraction:
    Ensures that MetadataService has extraction logic for EVERY relevant column in the 'Files' table.
    
    If 'Genre' is added to the DB, this test will fail until you:
    1. Update the 'SCHEMA_TAG_MAP' in this test (defining what ID3 tag maps to Genre).
    2. Update 'MetadataService.extract_from_mp3' to actually read that tag.
    """
    
    # 1. Get DB Schema (Truth)
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        repo = BaseRepository(path)
        with sqlite3.connect(path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(Files)")
            db_columns = {row[1] for row in cursor.fetchall()}
    finally:
        import gc
        gc.collect()
        if os.path.exists(path):
            import time
            for _ in range(3):
                try:
                    os.remove(path)
                    break 
                except PermissionError:
                    time.sleep(0.1)
                    
    # 2. Define Expected ID3 Mappings for DB Columns
    # This is the "Contract".
    # Column Name -> (Expected Song Field, ID3 Tag to Mock, Expected Value)
    schema_tag_map = {
        "Title": ("title", "TIT2", "Test Title"),
        "TempoBPM": ("bpm", "TBPM", ["120"]), # text list
        "RecordingYear": ("recording_year", "TDRC", ["2023"]),
        # Duration is special (audio.info)
        "Duration": ("duration", None, 123.45),
        # Path/FileID are args
        "Path": ("path", None, "/test/path.mp3"),
        "FileID": ("file_id", None, 1),
    }
    
    # 3. Verify Coverage
    missing_map = db_columns - set(schema_tag_map.keys())
    assert not missing_map, f"DB Columns {missing_map} are not accounted for in Schema Tag Map! Update test."
    
    # 4. Execute Service Logic with Mocks
    with patch("src.business.services.metadata_service.MP3") as MockMP3, \
         patch("src.business.services.metadata_service.ID3") as MockID3:
        
        # Setup MP3 info
        mock_audio = MagicMock()
        mock_audio.info.length = 123.45
        MockMP3.return_value = mock_audio
        
        # Setup ID3 Tags
        mock_tags = MagicMock()
        
        # Helper to simulate getall behavior
        def getall_side_effect(key):
            if key in ["TIT2", "TBPM", "TDRC", "TPE1", "TCOM", "TIT1", "TOLY", "TEXT", "TXXX:PRODUCER", "TIPL"]:
                # Map specific keys to our schema map values if present
                for col, info in schema_tag_map.items():
                    if info[1] == key:
                        val = info[2]
                        # Wrap in object with .text?
                        # Service: for f in frame: if hasattr(f, 'text')...
                        obj = MagicMock()
                        obj.text = [val] if not isinstance(val, list) else val
                        return [obj]
                return []
            return []
            
        # Also need exact dictionary access `if frame_id not in tags`
        # Service logic uses `if frame_id not in tags` then `tags.getall`.
        # So we must mock __contains__.
        
        mock_tags.__contains__.side_effect = lambda key: True # Claim everything exists
        mock_tags.getall.side_effect = getall_side_effect
        
        MockID3.return_value = mock_tags
        
        # Run SUT
        song = MetadataService.extract_from_mp3("/test/path.mp3", file_id=1)
        
        # 5. Assertions
        for col in db_columns:
            field_name, tag, expected_val = schema_tag_map[col]
            
            actual_val = getattr(song, field_name)
            
            # Type conversions (Service returns int for bpm/year)
            if col == "TempoBPM":
                assert actual_val == 120
            elif col == "RecordingYear":
                assert actual_val == 2023
            elif col == "Duration":
                assert actual_val == 123.45
            elif col == "Title":
                assert actual_val == "Test Title"
            # Path/FileID
            elif col == "Path":
                assert actual_val == "/test/path.mp3"
            elif col == "FileID":
                assert actual_val == 1
                
            # If we reached here, the service effectively extracted the value we wanted!
