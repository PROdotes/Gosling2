import pytest
from src.data.repositories.base_repository import BaseRepository

def test_database_schema_integrity(tmp_path):
    """
    Database Schema Integrity Test:
    Ensures that:
    1. The database contains exactly the expected tables.
    2. The 'Files' and 'Contributors' tables contain exactly the expected columns.
    
    If a developer adds a column (e.g., 'Genre') to 'Files' but forgets to map it,
    this test will fail, forcing them to update this test AND the object mapping tests.
    """
    db_path = tmp_path / "test_schema_integrity.db"
    repo = BaseRepository(str(db_path))
    
    expected_tables = {
        "Files",
        "Contributors",
        "Roles",
        "FileContributorRoles",
        "GroupMembers"
    }
    
    # Expected Columns per table (Name only, we could check type too but Name is sufficient trigger)
    expected_columns = {
        "Files": {"FileID", "Path", "Title", "Duration", "TempoBPM", "RecordingYear"},
        "Contributors": {"ContributorID", "Name", "SortName"},
        "Roles": {"RoleID", "Name"},
    }
    
    with repo.get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Check Tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        actual_tables = {row[0] for row in tables if row[0] != "sqlite_sequence"}
        
        missing = expected_tables - actual_tables
        extra = actual_tables - expected_tables
        assert not missing, f"Missing expected tables: {missing}"
        assert not extra, f"Unexpected extra tables: {extra}"
        
        # 2. Check Columns
        for table, expected_cols in expected_columns.items():
            cursor.execute(f"PRAGMA table_info({table})")
            columns_info = cursor.fetchall()
            # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
            actual_cols = {row[1] for row in columns_info}
            
            missing_cols = expected_cols - actual_cols
            extra_cols = actual_cols - expected_cols
            
            assert not missing_cols, f"Table '{table}' missing expected columns: {missing_cols}"
            assert not extra_cols, f"Table '{table}' has unexpected extra columns: {extra_cols}. Update tests!"
