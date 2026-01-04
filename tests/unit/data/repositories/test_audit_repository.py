"""
Logic tests for AuditRepository (Level 1: Happy Path & Polite Failures).
Per TESTING.md: Tests for audit logging infrastructure and fail-secure behavior.
"""
import pytest
import sqlite3
import json
from src.data.database import BaseRepository
from src.data.repositories.audit_repository import AuditRepository


class TestAuditRepository:
    """Unit tests for AuditRepository audit logging operations."""
    
    @pytest.fixture
    def db_connection(self, tmp_path):
        """Fixture providing a database connection with schema."""
        db_path = tmp_path / "test_audit.db"
        # Initialize schema
        BaseRepository(str(db_path))
        
        # Return a connection for AuditRepository
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        yield conn
        conn.close()
    
    @pytest.fixture
    def repo(self, db_connection):
        """Fixture providing AuditRepository instance."""
        return AuditRepository(connection=db_connection)
    
    class TestChangeLogOperations:
        """Tests for ChangeLog table operations."""
        
        def test_insert_single_change_log(self, repo, db_connection):
            """Test inserting a single change log entry."""
            rows = [
                ("Songs", 1, "Title", "Old Title", "New Title", "batch-001")
            ]
            
            # Should not raise
            repo.insert_change_logs(rows)
            
            # Verify insertion
            cursor = db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM ChangeLog WHERE BatchID = 'batch-001'")
            count = cursor.fetchone()[0]
            assert count == 1
            
            # Verify content
            cursor.execute("""
                SELECT LogTableName, RecordID, LogFieldName, OldValue, NewValue 
                FROM ChangeLog WHERE BatchID = 'batch-001'
            """)
            row = cursor.fetchone()
            assert row[0] == "Songs"
            assert row[1] == 1
            assert row[2] == "Title"
            assert row[3] == "Old Title"
            assert row[4] == "New Title"
        
        def test_insert_bulk_change_logs(self, repo, db_connection):
            """Test bulk inserting multiple change log entries."""
            rows = [
                ("Songs", 1, "Title", "Old1", "New1", "batch-002"),
                ("Songs", 1, "Artist", "OldArtist", "NewArtist", "batch-002"),
                ("Songs", 2, "BPM", "120", "140", "batch-002"),
            ]
            
            repo.insert_change_logs(rows)
            
            # Verify all inserted
            cursor = db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM ChangeLog WHERE BatchID = 'batch-002'")
            count = cursor.fetchone()[0]
            assert count == 3
        
        def test_insert_empty_change_logs(self, repo, db_connection):
            """Test that empty list doesn't cause errors."""
            # Should not raise
            repo.insert_change_logs([])
            
            # Verify nothing inserted
            cursor = db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM ChangeLog")
            count = cursor.fetchone()[0]
            assert count == 0
        
        def test_insert_change_log_with_null_values(self, repo, db_connection):
            """Test inserting change logs with NULL old/new values."""
            rows = [
                ("Albums", 5, "Publisher", None, "Sony Music", "batch-003"),
                ("Albums", 6, "ReleaseYear", "2020", None, "batch-003"),
            ]
            
            repo.insert_change_logs(rows)
            
            cursor = db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM ChangeLog WHERE BatchID = 'batch-003'")
            count = cursor.fetchone()[0]
            assert count == 2

        def test_get_change_log(self, repo, db_connection):
            """Test retrieving recent change log entries."""
            rows = [
                ("Songs", 1, "Title", "Old1", "New1", "batch-get-1"),
                ("Songs", 2, "Artist", "Old2", "New2", "batch-get-1")
            ]
            repo.insert_change_logs(rows)
            
            logs = repo.get_change_log(limit=10)
            assert len(logs) == 2
            assert logs[0]['LogTableName'] == "Songs"
            assert logs[0]['BatchID'] == "batch-get-1"
            assert 'LogTimestamp' in logs[0]
    
    class TestDeletedRecordOperations:
        """Tests for DeletedRecords table operations."""
        
        def test_insert_deleted_record(self, repo, db_connection):
            """Test archiving a deleted record."""
            snapshot = json.dumps({
                "song_id": 42,
                "title": "Deleted Song",
                "artist": "Test Artist"
            })
            
            repo.insert_deleted_record("Songs", 42, snapshot, "batch-del-001")
            
            # Verify insertion
            cursor = db_connection.cursor()
            cursor.execute("""
                SELECT DeletedFromTable, RecordID, FullSnapshot, BatchID 
                FROM DeletedRecords WHERE BatchID = 'batch-del-001'
            """)
            row = cursor.fetchone()
            assert row[0] == "Songs"
            assert row[1] == 42
            assert row[2] == snapshot
            assert row[3] == "batch-del-001"
        
        def test_insert_multiple_deleted_records(self, repo, db_connection):
            """Test archiving multiple deleted records."""
            snapshot1 = json.dumps({"id": 1, "name": "Record 1"})
            snapshot2 = json.dumps({"id": 2, "name": "Record 2"})
            
            repo.insert_deleted_record("Albums", 1, snapshot1, "batch-del-002")
            repo.insert_deleted_record("Albums", 2, snapshot2, "batch-del-002")
            
            cursor = db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM DeletedRecords WHERE BatchID = 'batch-del-002'")
            count = cursor.fetchone()[0]
            assert count == 2
        
        def test_deleted_record_preserves_snapshot(self, repo, db_connection):
            """Test that complex JSON snapshots are preserved correctly."""
            complex_snapshot = json.dumps({
                "album_id": 99,
                "title": "Test Album",
                "tracks": [
                    {"track_num": 1, "title": "Song 1"},
                    {"track_num": 2, "title": "Song 2"}
                ],
                "metadata": {
                    "year": 2024,
                    "label": "Indie Records"
                }
            })
            
            repo.insert_deleted_record("Albums", 99, complex_snapshot, "batch-del-003")
            
            cursor = db_connection.cursor()
            cursor.execute("SELECT FullSnapshot FROM DeletedRecords WHERE RecordID = 99")
            retrieved = cursor.fetchone()[0]
            
            # Verify JSON round-trip
            assert json.loads(retrieved) == json.loads(complex_snapshot)
    
    class TestActionLogOperations:
        """Tests for ActionLog table operations."""
        
        def test_insert_action_log_full_params(self, repo, db_connection):
            """Test logging an action with all parameters."""
            details = json.dumps({"reason": "User requested", "notes": "Bulk operation"})
            
            repo.insert_action_log(
                action_type="BULK_DELETE",
                target_table="Songs",
                target_id=100,
                details_json=details,
                user_id="admin@example.com"
            )
            
            cursor = db_connection.cursor()
            cursor.execute("""
                SELECT ActionLogType, TargetTable, ActionTargetID, ActionDetails, UserID 
                FROM ActionLog WHERE ActionLogType = 'BULK_DELETE'
            """)
            row = cursor.fetchone()
            assert row[0] == "BULK_DELETE"
            assert row[1] == "Songs"
            assert row[2] == 100
            assert row[3] == details
            assert row[4] == "admin@example.com"
        
        def test_insert_action_log_minimal_params(self, repo, db_connection):
            """Test logging an action with minimal parameters (NULLs)."""
            repo.insert_action_log(
                action_type="SYSTEM_STARTUP",
                target_table=None,
                target_id=None,
                details_json=None,
                user_id=None
            )
            
            cursor = db_connection.cursor()
            cursor.execute("""
                SELECT ActionLogType, TargetTable, ActionTargetID, ActionDetails, UserID 
                FROM ActionLog WHERE ActionLogType = 'SYSTEM_STARTUP'
            """)
            row = cursor.fetchone()
            assert row[0] == "SYSTEM_STARTUP"
            assert row[1] is None
            assert row[2] is None
            assert row[3] is None
            assert row[4] is None
        
        def test_insert_multiple_action_logs(self, repo, db_connection):
            """Test logging multiple actions."""
            repo.insert_action_log("IMPORT_START", "MediaSources", None, None, "user1")
            repo.insert_action_log("IMPORT_COMPLETE", "MediaSources", None, '{"count": 50}', "user1")
            repo.insert_action_log("EXPORT_START", "Songs", None, None, "user2")
            
            cursor = db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM ActionLog")
            count = cursor.fetchone()[0]
            assert count == 3

        def test_get_action_log(self, repo, db_connection):
            """Test retrieving recent action log entries."""
            repo.insert_action_log("TEST_ACTION", "Table", 1, '{"key": "val"}', "user")
            
            logs = repo.get_action_log(limit=5)
            assert len(logs) == 1
            assert logs[0]['ActionLogType'] == "TEST_ACTION"
            assert logs[0]['UserID'] == "user"
            assert json.loads(logs[0]['ActionDetails'])['key'] == "val"
    
    class TestFailSecureBehavior:
        """Tests for fail-secure error handling."""
        
        def test_change_log_propagates_errors(self, repo, db_connection):
            """Test that ChangeLog errors are propagated (fail-secure)."""
            # Close the connection to force an error
            db_connection.close()
            
            rows = [("Songs", 1, "Title", "Old", "New", "batch-fail")]
            
            # Should raise an exception
            with pytest.raises(Exception):
                repo.insert_change_logs(rows)
        
        def test_deleted_record_propagates_errors(self, repo, db_connection):
            """Test that DeletedRecords errors are propagated (fail-secure)."""
            db_connection.close()
            
            with pytest.raises(Exception):
                repo.insert_deleted_record("Songs", 1, "{}", "batch-fail")
        
        def test_action_log_propagates_errors(self, repo, db_connection):
            """Test that ActionLog errors are propagated (fail-secure)."""
            db_connection.close()
            
            with pytest.raises(Exception):
                repo.insert_action_log("TEST", None, None, None, None)
    
    class TestTransactionalIntegrity:
        """Tests for transactional behavior with audit operations."""
        
        def test_change_logs_in_transaction(self, repo, db_connection):
            """Test that change logs can be part of a larger transaction."""
            cursor = db_connection.cursor()
            
            # Start a transaction
            cursor.execute("BEGIN")
            
            try:
                # Insert some data
                cursor.execute("INSERT INTO MediaSources (SourcePath, MediaName, IsActive, TypeID) VALUES ('test.mp3', 'Test', 1, 1)")
                source_id = cursor.lastrowid
                
                # Log the change
                repo.insert_change_logs([
                    ("MediaSources", source_id, "SourcePath", None, "test.mp3", "batch-tx-001")
                ])
                
                # Commit
                db_connection.commit()
                
                # Verify both operations succeeded
                cursor.execute("SELECT COUNT(*) FROM MediaSources WHERE SourcePath = 'test.mp3'")
                assert cursor.fetchone()[0] == 1
                
                cursor.execute("SELECT COUNT(*) FROM ChangeLog WHERE BatchID = 'batch-tx-001'")
                assert cursor.fetchone()[0] == 1
                
            except Exception:
                db_connection.rollback()
                raise
        
        def test_rollback_includes_audit_logs(self, repo, db_connection):
            """Test that rolling back a transaction also rolls back audit logs."""
            cursor = db_connection.cursor()
            
            cursor.execute("BEGIN")
            
            try:
                # Insert data
                cursor.execute("INSERT INTO MediaSources (SourcePath, MediaName, IsActive, TypeID) VALUES ('rollback.mp3', 'Test', 1, 1)")
                source_id = cursor.lastrowid
                
                # Log the change
                repo.insert_change_logs([
                    ("MediaSources", source_id, "SourcePath", None, "rollback.mp3", "batch-rollback")
                ])
                
                # Force a rollback
                db_connection.rollback()
                
                # Verify both operations were rolled back
                cursor.execute("SELECT COUNT(*) FROM MediaSources WHERE SourcePath = 'rollback.mp3'")
                assert cursor.fetchone()[0] == 0
                
                cursor.execute("SELECT COUNT(*) FROM ChangeLog WHERE BatchID = 'batch-rollback'")
                assert cursor.fetchone()[0] == 0
                
            except Exception:
                db_connection.rollback()
                raise
