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
        
        # FIX: Use Real BaseRepository with a temp file to ensure we test the ACTUAL schema
        import tempfile
        fd, self.temp_db_path = tempfile.mkstemp()
        os.close(fd)
        
        # Initialize Schema via actual Repository logic
        self.repo = BaseRepository(self.temp_db_path)
        
        # Connect for Test Introspection
        self.conn = sqlite3.connect(self.temp_db_path)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        if self.conn:
            self.conn.close()
            
        # Cleanup temp file
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except PermissionError:
                pass # Windows file locking might delay delete, permissible in test cleanup

    def test_json_matches_db_schema(self):
        """Verify that all DB columns and Roles are present in the JSON config"""
        
        # 1. Load JSON Criteria
        with open(self.criteria_path, 'r') as f:
            criteria = json.load(f)
        
        defined_fields = set(criteria.get('fields', {}).keys())
        
        # 1a. Strict Table Whitelisting
        # Ensure JSON matches DB tables exactly
        defined_tables = set(criteria.get('tables', []))
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        db_tables = {row['name'] for row in cursor.fetchall()}
        
        # Verify no unknown tables
        unknown_tables = db_tables - defined_tables
        self.assertFalse(unknown_tables, f"Unknown tables detected in DB not in JSON Criteria: {unknown_tables}")
        
        # Verify no missing tables
        missing_tables = defined_tables - db_tables
        self.assertFalse(missing_tables, f"JSON Criteria lists tables not found in DB: {missing_tables}")

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
            'RecordingYear': 'recording_year',
            'ISRC': 'isrc',
            'IsDone': 'is_done'
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
