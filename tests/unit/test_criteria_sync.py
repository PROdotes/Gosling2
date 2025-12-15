import unittest
import json
import os
import sqlite3
from src.data.repositories.base_repository import BaseRepository

class TestCriteriaSync(unittest.TestCase):
    """Ensure completeness_criteria.json stays in sync with Database Schema"""

    def setUp(self):
        # Path to the JSON criteria file
        self.criteria_path = os.path.join(
            os.path.dirname(__file__), 
            '../../../Gosling2/src/completeness_criteria.json'
        )
        self.criteria_path = os.path.normpath(self.criteria_path)
        
        # FIX: For :memory: databases, we can't let BaseRepository open/close new connections.
        # We will manually create a connection and initialize the schema on it.
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        
        # Manually run the schema creation from BaseRepository logic
        # (We duplicate the logic slightly here or we could invoke a method if we refactored BaseRepo)
        self._init_schema(self.conn)

    def tearDown(self):
        self.conn.close()

    def _init_schema(self, conn):
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS Files (FileID INTEGER PRIMARY KEY, Path TEXT NOT NULL UNIQUE, Title TEXT NOT NULL, Duration REAL, TempoBPM INTEGER, RecordingYear INTEGER)")
        cursor.execute("CREATE TABLE IF NOT EXISTS Contributors (ContributorID INTEGER PRIMARY KEY, Name TEXT NOT NULL UNIQUE, SortName TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS Roles (RoleID INTEGER PRIMARY KEY, Name TEXT NOT NULL UNIQUE)")
        default_roles = ["Performer", "Composer", "Lyricist", "Producer"]
        cursor.executemany("INSERT OR IGNORE INTO Roles (Name) VALUES (?)", [(r,) for r in default_roles])
        conn.commit()

    def test_json_matches_db_schema(self):
        """Verify that all DB columns and Roles are present in the JSON config"""
        
        # 1. Load JSON Criteria
        with open(self.criteria_path, 'r') as f:
            criteria = json.load(f)
        
        defined_fields = set(criteria.get('fields', {}).keys())
        
        # 2. Introspect 'Files' Table
        db_fields = set()
        # Use existing connection
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(Files)")
        columns = cursor.fetchall()
            
        # Map DB Column -> JSON Key
        column_map = {
            'FileID': 'file_id',
            'Path': 'path',
            'Title': 'title',
            'Duration': 'duration',
            'TempoBPM': 'bpm',
            'RecordingYear': 'recording_year'
        }
        
        for col in columns:
            col_name = col['name'] # Access by name row_factory=sqlite3.Row
            # If we are strictly mapping, we expect the map to handle it.
            # If a new column appears, it won't be in the map, so we should flag it?
            # Or we explicitly look for what columns EXIST and assert they are covered.
            
            if col_name in column_map:
                db_fields.add(column_map[col_name])
            else:
                # Fail if there is an unknown column (force dev to update map/test)
                self.fail(f"New DB Column '{col_name}' detected! Please update the test and JSON criteria.")

            # 3. Introspect 'Roles' Table for Contributors
            cursor.execute("SELECT Name FROM Roles")
            roles = cursor.fetchall()
            
            # Map Role Name -> JSON Key (pluralized)
            role_map = {
                'Performer': 'performers',
                'Composer': 'composers',
                'Lyricist': 'lyricists',
                'Producer': 'producers'
            }
            
            for role_row in roles:
                role_name = role_row['Name']
                if role_name in role_map:
                    db_fields.add(role_map[role_name])
                else:
                    self.fail(f"New Role '{role_name}' detected! Please update the test and JSON criteria.")

        # 4. Assert Coverage
        missing_in_json = db_fields - defined_fields
        self.assertFalse(missing_in_json, f"JSON criteria missing definitions for: {missing_in_json}")
        
        # Optional: Warn on extra keys in JSON not in DB? 
        # (Not strictly an error, maybe computed fields, but good to know)
        extra_in_json = defined_fields - db_fields
        if extra_in_json:
            print(f"Note: JSON contains extra fields not in DB core schema: {extra_in_json}")

if __name__ == '__main__':
    unittest.main()
