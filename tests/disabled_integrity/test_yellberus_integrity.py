"""
Phase 5: Database ↔ Yellberus Integrity Tests

These tests ensure the database schema matches what Yellberus expects.
Any mismatch means either:
1. DB schema is out of sync (run migration)
2. Yellberus definition is wrong (fix the registry)
"""
import pytest
import sqlite3
import tempfile
import os
from src.core import yellberus
from src.data.repositories.base_repository import BaseRepository


class TestDatabaseSchemaIntegrity:
    """Tests that verify DB schema matches Yellberus registry."""
    
    @pytest.fixture
    def db_connection(self):
        """Create a temp database with schema and return connection."""
        fd, path = tempfile.mkstemp()
        os.close(fd)
        try:
            # BaseRepository creates the schema
            repo = BaseRepository(path)
            conn = sqlite3.connect(path)
            yield conn
            conn.close()
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
    
    def test_yellberus_query_executes_without_error(self, db_connection):
        """Test that BASE_QUERY can execute against the actual schema."""
        cursor = db_connection.cursor()
        try:
            cursor.execute(yellberus.BASE_QUERY)
            # Just check it doesn't crash
            _ = cursor.fetchall()
        except sqlite3.OperationalError as e:
            pytest.fail(f"Yellberus BASE_QUERY failed: {e}")
    
    def test_yellberus_query_returns_correct_column_count(self, db_connection):
        """Test that query returns same number of columns as FIELDS."""
        cursor = db_connection.cursor()
        cursor.execute(yellberus.BASE_QUERY)
        
        # Get column count from query
        column_count = len(cursor.description)
        field_count = len(yellberus.FIELDS)
        
        assert column_count == field_count, \
            f"Query returns {column_count} columns but FIELDS has {field_count} entries"
    
    def test_all_db_columns_in_yellberus(self, db_connection):
        """Test that DB columns are accounted for in Yellberus."""
        cursor = db_connection.cursor()
        
        # Get MediaSources columns
        cursor.execute("PRAGMA table_info(MediaSources)")
        ms_columns = {row[1] for row in cursor.fetchall()}
        
        # Get Songs columns
        cursor.execute("PRAGMA table_info(Songs)")
        songs_columns = {row[1] for row in cursor.fetchall()}
        
        # Yellberus db_columns (extract table.column -> column)
        yellberus_columns = set()
        for field in yellberus.FIELDS:
            # Handle "MS.Name", "S.RecordingYear", etc.
            if '.' in field.db_column:
                col = field.db_column.split('.')[1]
            else:
                col = field.db_column
            yellberus_columns.add(col)
        
        # Columns that are intentionally not in Yellberus (yet)
        ignored_columns = {
            'IsActive',  # Filter condition, not exposed as field
            'Notes',     # Future field
            'Groups',    # Temporarily removed - deciding on implementation
        }
        
        # Check MediaSources
        missing_ms = ms_columns - yellberus_columns - ignored_columns
        assert not missing_ms, \
            f"MediaSources columns not in Yellberus: {missing_ms}"
        
        # Check Songs
        missing_songs = songs_columns - yellberus_columns - ignored_columns
        assert not missing_songs, \
            f"Songs columns not in Yellberus: {missing_songs}"


class TestYellberusFieldsIntegrity:
    """Tests that verify FIELDS list is internally consistent."""
    
    def test_field_names_are_unique(self):
        """Each field must have a unique name."""
        names = [f.name for f in yellberus.FIELDS]
        assert len(names) == len(set(names)), \
            f"Duplicate field names found: {[n for n in names if names.count(n) > 1]}"
    
    def test_db_columns_are_valid(self):
        """Each field's db_column should be properly formatted."""
        for field in yellberus.FIELDS:
            # Must not be empty
            assert field.db_column, f"Field '{field.name}' has empty db_column"
            
            # Should be either "TABLE.Column" or just "Column" (for GROUP_CONCAT aliases)
            # GROUP_CONCAT results like "Performers" are valid without table prefix
            if '.' in field.db_column:
                parts = field.db_column.split('.')
                assert len(parts) == 2, \
                    f"Field '{field.name}' has invalid db_column format: {field.db_column}"
    
    def test_portable_fields_have_json_mapping(self):
        """Portable fields must have frame mapping in id3_frames.json."""
        import json
        import os
        
        # Load id3_frames.json
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, '..', '..', '..', 'src', 'resources', 'id3_frames.json')
        
        with open(json_path, 'r', encoding='utf-8') as f:
            id3_frames = json.load(f)
        
        # Build reverse lookup: field_name -> frame_code
        field_to_frame = {}
        for frame_code, frame_info in id3_frames.items():
            if isinstance(frame_info, dict) and 'field' in frame_info:
                field_to_frame[frame_info['field']] = frame_code
        
        for field in yellberus.FIELDS:
            if field.portable:
                assert field.name in field_to_frame, \
                    f"Portable field '{field.name}' missing from id3_frames.json"
    
    def test_local_fields_marked_correctly(self):
        """Local fields should have portable=False."""
        local_fields = ['file_id', 'type_id', 'is_done', 'duration', 'path']
        for field in yellberus.FIELDS:
            if field.name in local_fields:
                assert not field.portable, \
                    f"Field '{field.name}' should be marked as local (portable=False)"
