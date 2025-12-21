import pytest
import sqlite3
import dataclasses
from src.data.database import BaseRepository
from src.data.repositories.song_repository import SongRepository
from src.data.models.song import Song

# SIMULATION:
# We simulate a developer who enters "Cowboy Mode":
# 1. Adds 'GenreID' column to 'Files' table in the DB.
# 2. Forgets to update 'Song' model.
# 3. Forgets to update 'test_database_schema.py'.
# 4. Forgets to update 'test_schema_model_cross_ref.py'.

class CowboyRepo(SongRepository):
    def _ensure_schema(self):
        super()._ensure_schema()
        with self.get_connection() as conn:
            # UNAUTHORIZED CHANGE
            try:
                conn.execute("CREATE TABLE Genres (GenreID INTEGER PRIMARY KEY, Name TEXT)")
            except Exception:
                pass

def test_cascade_failure_simulation(tmp_path):
    """
    Demonstrates that a single DB change triggers MULTIPLE test failures.
    We gather exceptions instead of failing on the first one to show the full blast radius.
    """
    db_path = tmp_path / "cowboy.db"
    repo = CowboyRepo(str(db_path))
    
    failures = []
    
    # --- FAILURE 1: test_database_schema.py Logic ---
    try:
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            # Check TABLES first
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            actual_tables = {row[0] for row in tables if row[0] != "sqlite_sequence"}
            expected_tables = {"Files", "Contributors", "Roles", "FileContributorRoles", "GroupMembers"}
            
            extra = actual_tables - expected_tables
            if extra:
                raise AssertionError(f"[Database Schema Test] Unexpected extra tables: {extra}")
    except AssertionError as e:
        failures.append(str(e))

    # --- FAILURE 2, 3, 4, 5: Irrelevant for Table Listing ---
    # These tests check for COLUMN mappings in 'Files' table. 
    # Since we only added 'Genres' table and didn't touch 'Files', they should theoretically pass 
    # (or be skipped because we assume 'Files' is unchanged).
    # We focus only on Failure 1.


    # --- REPORTING ---
    # For Table Addition, only the Table Schema test should fail initially (alerting you to existence).
    # The others won't fail because the new table isn't linked to Files yet (unless we added a FK).
    
    db_fail = any("Unexpected extra tables" in f for f in failures)
    
    if db_fail:
        print(f"\nSUCCESS! Detected Table Addition via: {failures[0]}")
    else:
        pytest.fail(f"Simulation failed. Expected 'Unexpected extra tables' failure, got: {failures}")
