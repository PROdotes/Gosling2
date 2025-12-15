import pytest
import sqlite3
import tempfile
import os
from unittest.mock import MagicMock
from src.presentation.widgets.filter_widget import FilterWidget
from src.data.repositories.base_repository import BaseRepository

def test_strict_filter_coverage():
    """
    STRICT Filter Coverage:
    Ensures that FilterWidget accounts for EVERY column in the 'Files' table.
    
    Logic:
    1. Get actual DB columns from 'Files'.
    2. Subtract columns explicitly IGNORED by FilterWidget (`IGNORED_DB_COLUMNS`).
    3. Subtract columns KNOWN to be USED by FilterWidget (e.g. 'RecordingYear').
    4. Assert remainder is EMPTY.
    
    If 'Genre' is added to DB, checking this test will FAIL because 'Genre' 
    is neither ignored nor in the known used list.
    """
    
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

    # 2. Get FilterWidget Config
    # We inspect the class constant we added
    ignored = FilterWidget.IGNORED_DB_COLUMNS
    
    # 3. Define Known Used Columns
    # We assert "RecordingYear" is used because we know `_add_years_to_tree` exists.
    # Ideally we'd inspect the code, but verifying via a known list is acceptable strictness 
    # as long as we maintain it.
    used = {
        "RecordingYear"
    }
    
    # "Contributors" etc are not columns in Files (they are Foreign Keys usually, but linked via tables).
    # If Files had 'GenreID', we'd expect 'GenreID' to be in USED (if we filter by it) or IGNORED.
    
    # 4. Strict Check
    remainder = db_columns - ignored - used
    
    assert not remainder, \
        f"FilterWidget is not handling the following DB columns: {remainder}. "\
        f"You must implementation filtering for them OR add them to FilterWidget.IGNORED_DB_COLUMNS."

    # Optional: Check for stale ignored fields?
    stale_ignored = ignored - db_columns
    assert not stale_ignored, \
        f"FilterWidget ignores columns that don't exist in DB: {stale_ignored}. Clean up IGNORED_DB_COLUMNS."
        
    # Optional: Check for stale used fields?
    stale_used = used - db_columns
    assert not stale_used, \
        f"Test expects FilterWidget to use columns that don't exist: {stale_used}"
