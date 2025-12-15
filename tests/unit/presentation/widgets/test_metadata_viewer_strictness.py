import pytest
from unittest.mock import MagicMock
from src.presentation.widgets.metadata_viewer_dialog import MetadataViewerDialog

def test_metadata_viewer_strict_mapping(qtbot):
    """
    STRICT Metadata Viewer Mapping:
    Ensures that MetadataViewerDialog contains a mapping for EVERY column in the 'Files' table.
    
    If 'Genre' is added to the database, this test will fail until it's added to 
    MetadataViewerDialog.mapped_fields (ensuring users can see the discrepancy).
    """
    import sqlite3
    import tempfile
    import os
    from src.data.repositories.base_repository import BaseRepository
    
    # 1. Get DB Schema
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
    
    # 3. Inspect MetadataViewerDialog Schema Logic
    # We create a dummy dialog to inspect its schema rules
    mock_file = MagicMock()
    mock_db = MagicMock()
    
    # We patch the ID3 loading parts to avoid IO if possible, or just let it run (it handles errors).
    dlg = MetadataViewerDialog(mock_file, mock_db)
    
    # Extract the set of SONG ATTRIBUTES it maps to.
    # mapped_fields format: (Label, SongAttribute, ID3Tags)
    mapped_attributes = {entry[1] for entry in dlg.mapped_fields}
    
    # 4. Define Expected Attributes for Files Table Columns
    # Map DB Column Name -> Song Attribute Name
    # This Mapping MUST exactly match what the dialog EXPECTS to display.
    # If DB has "TempoBPM", Dialog must map "bpm".
    
    db_to_attribute = {
        "FileID": None, # Ignored
        "Path": None,   # Handled by Header/Layout, not table mapping
        "Title": "title",
        "Duration": "formatted_duration", # Dialog calculates this from Duration? No, Song model property.
        "TempoBPM": "bpm",
        "RecordingYear": "recording_year"
    }
    
    # Join on Contributors? 
    # The Tables Contributors/Roles etc mean we have 'performers', 'composers' etc.
    # But strictly speaking, those aren't COLUMNS in 'Files'.
    # This test enforces that 'Files' table columns are covered.
    
    with open("debug_test_output.txt", "w") as f:
        f.write(f"DB Columns: {db_columns}\n")
        f.write(f"Mapped Attributes: {mapped_attributes}\n")

    for col in db_columns:
        if col not in db_to_attribute:
            with open("debug_test_output.txt", "a") as f:
                f.write(f"FAIL: Unknown DB Column '{col}'\n")
            pytest.fail(f"Strict Check: DB Column '{col}' is unknown to test logic! Update test mapping.")
            
        attr = db_to_attribute[col]
        if attr:
            if attr not in mapped_attributes:
                with open("debug_test_output.txt", "a") as f:
                    f.write(f"FAIL: Missing mapping for '{col}' -> '{attr}'\n")
                pytest.fail(f"MetadataViewerDialog is missing mapping for DB Column '{col}' (Attribute '{attr}'). "
                            f"Update MetadataViewerDialog.mapped_fields.")
                            
    # Optional: ensure we don't have broken mappings?
    # (Checked by other tests)

