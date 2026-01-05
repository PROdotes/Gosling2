
import pytest
from typing import Optional
import sqlite3
from src.data.database import BaseRepository
from src.data.repositories.generic_repository import GenericRepository

# --- Stub Implementation for Testing ---
class MockEntity:
    def __init__(self, id_val: Optional[int], name: str):
        self.id = id_val
        self.name = name

    def to_dict(self):
        return {"id": self.id, "name": self.name}
    
    @classmethod
    def from_row(cls, row):
        return cls(row[0], row[1])

class MockRepository(GenericRepository[MockEntity]):
    def __init__(self, db_path):
        super().__init__(db_path, "MockTable", "id")
        with self.get_connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS MockTable (id INTEGER PRIMARY KEY, name TEXT)")
            # Initialize Audit Tables (Schema Dependency based on src/data/audit_repository.py)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ChangeLog (
                    LogID INTEGER PRIMARY KEY AUTOINCREMENT,
                    LogTableName TEXT NOT NULL,
                    RecordID TEXT NOT NULL,
                    LogFieldName TEXT NOT NULL,
                    OldValue TEXT,
                    NewValue TEXT,
                    LogTimestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    BatchID TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS DeletedRecords (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    DeletedFromTable TEXT NOT NULL,
                    RecordID INTEGER NOT NULL,
                    FullSnapshot TEXT NOT NULL,
                    DeletedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                    BatchID TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ActionLog (
                    ActionID INTEGER PRIMARY KEY AUTOINCREMENT,
                    ActionLogType TEXT NOT NULL,
                    TargetTable TEXT,
                    ActionTargetID TEXT,
                    ActionDetails TEXT,
                    ActionTimestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UserID TEXT,
                    BatchID TEXT
                )
            """)

    def get_by_id(self, record_id: int) -> Optional[MockEntity]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT id, name FROM MockTable WHERE id = ?", (record_id,))
            row = cur.fetchone()
            return MockEntity.from_row(row) if row else None

    def _insert_db(self, cursor: sqlite3.Cursor, entity: MockEntity, **kwargs) -> int:
        cursor.execute("INSERT INTO MockTable (name) VALUES (?)", (entity.name,))
        return cursor.lastrowid

    def _update_db(self, cursor: sqlite3.Cursor, entity: MockEntity, **kwargs) -> None:
        cursor.execute("UPDATE MockTable SET name = ? WHERE id = ?", (entity.name, entity.id))

    def _delete_db(self, cursor: sqlite3.Cursor, record_id: int, **kwargs) -> None:
        cursor.execute("DELETE FROM MockTable WHERE id = ?", (record_id,))


@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test_generic.db"
    return MockRepository(str(db_path))

class TestGenericRepository:
    """
    Test the Audit Logging orchestration logic of GenericRepository.
    We assume actual AuditLogger works (tested elsewhere), 
    we primarily test that GenericRepo calls it correctly during transactions.
    """

    def test_insert_creates_audit_log(self, repo):
        # 1. Insert
        entity = MockEntity(None, "Test Item")
        new_id = repo.insert(entity)
        assert new_id is not None
        
        # 2. Verify Data
        saved = repo.get_by_id(new_id)
        assert saved.name == "Test Item"
        
        # 3. Verify Audit Log (ChangeLog table)
        # We need to manually check the DB because AuditRepo isn't injected here
        with repo.get_connection() as conn:
            # ChangeLog structure: LogTableName, RecordID, LogFieldName, OldValue, NewValue
            cur = conn.execute("SELECT LogTableName, RecordID, LogFieldName, NewValue FROM ChangeLog WHERE RecordID = ?", (str(new_id),))
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "MockTable"
            assert str(row[1]) == str(new_id)
            # Normalization might sort/convert, but NewValue usually matches
            assert row[3] == "Test Item"

    def test_update_creates_audit_log(self, repo):
        # Setup
        entity = MockEntity(None, "Original")
        oid = repo.insert(entity)
        entity.id = oid
        
        # Update
        entity.name = "Updated"
        success = repo.update(entity)
        assert success is True
        
        # Verify Audit
        with repo.get_connection() as conn:
            # Should have INSERT then UPDATE
            cur = conn.execute("SELECT LogFieldName, OldValue, NewValue FROM ChangeLog WHERE RecordID = ? ORDER BY LogTimestamp", (str(oid),))
            rows = cur.fetchall()
            # Rows could be multiple if multiple fields, but here only 'name' changes
            # But the first INSERT creates logs too.
            # 1. INSERT: New=Original
            # 2. UPDATE: Old=Original, New=Updated
            # Let's filter for just the Update diff
            cur = conn.execute("SELECT OldValue, NewValue FROM ChangeLog WHERE RecordID = ? AND OldValue = 'Original'", (str(oid),))
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "Original"
            assert row[1] == "Updated"

    def test_delete_creates_audit_log_and_recycle_bin(self, repo):
        # Setup
        entity = MockEntity(None, "To Delete")
        oid = repo.insert(entity)
        
        # Delete
        success = repo.delete(oid)
        assert success is True
        
        # Verify Data Gone
        assert repo.get_by_id(oid) is None
        
        # Verify Audit (DeletedRecords)
        with repo.get_connection() as conn:
            cur = conn.execute("SELECT FullSnapshot FROM DeletedRecords WHERE DeletedFromTable = 'MockTable' AND RecordID = ?", (oid,))
            row = cur.fetchone()
            assert row is not None
            assert "To Delete" in row[0]

    def test_transaction_rollback_on_error(self, repo):
        """Verify that DB write failure rollback prevents Audit Log write (Atomicity)."""
        
        # Force a failure in _insert_db by monkeypatching the instance method
        
        def failing_insert(cursor, entity, **kwargs):
            raise Exception("Force Fail")
        
        repo._insert_db = failing_insert
        
        # Attempt Insert
        entity = MockEntity(None, "Fail")
        res = repo.insert(entity)
        
        assert res is None
        
        # Verify NO Audit Log created
        with repo.get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM ChangeLog")
            assert cur.fetchone()[0] == 0
