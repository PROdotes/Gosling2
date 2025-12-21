import pytest
import sqlite3
from src.data.database import BaseRepository
from src.data.repositories.song_repository import SongRepository

# SIMULATION:
# We will create a "Bad" Repository that adds 'Genres' table but fails to add tests for it.
# We expect `test_database_schema_integrity` to FAIL.

class BadRepository(BaseRepository):
    def _ensure_schema(self):
        super()._ensure_schema()
        with self.get_connection() as conn:
            # ADD THE NEW TABLE FROM ISSUE #4
            conn.execute("CREATE TABLE IF NOT EXISTS Genres (GenreID INTEGER PRIMARY KEY, GenreName TEXT)")
            
def test_simulation_schema_failure(tmp_path):
    """
    Demonstrates that adding 'Genres' table without updating `test_database_schema.py`
    causes an immediate failure.
    """
    db_path = tmp_path / "bad_schema.db"
    repo = BadRepository(str(db_path))
    
    # Run the integrity check logic (copied from test_database_schema.py)
    expected_tables = {
        "Files",
        "Contributors",
        "Roles",
        "FileContributorRoles",
        "GroupMembers"
        # MISSING "Genres"
    }
    
    with repo.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        actual_tables = {row[0] for row in tables if row[0] != "sqlite_sequence"}
        
        extra = actual_tables - expected_tables
        
        # WE EXPECT FAILURE HERE
        if not extra:
            pytest.fail("Test FAILED to detect the new 'Genres' table! Safety net is broken.")
        else:
            print(f"\nSUCCESS: Detected unauthorized table: {extra}")
            
def test_simulation_column_failure(tmp_path):
    """
    Demonstrates that adding 'GenreID' to Files table without updating tests fails.
    """
    db_path = tmp_path / "bad_files_schema.db"
    repo = BaseRepository(str(db_path))
    
    with repo.get_connection() as conn:
        conn.execute("ALTER TABLE Files ADD COLUMN GenreID INTEGER")
        
    # Run column integrity check logic
    expected_cols = {"FileID", "Path", "Title", "Duration", "TempoBPM"}
    
    with repo.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Files)")
        actual_cols = {row[1] for row in cursor.fetchall()}
        
        extra = actual_cols - expected_cols
        
        if not extra:
            pytest.fail("Test FAILED to detect new column in Files!")
        else:
            print(f"\nSUCCESS: Detected unauthorized column: {extra}")
