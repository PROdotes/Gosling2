from typing import List, Tuple, Any, Optional
import sqlite3
from ...core import logger
from ...data.database import BaseRepository

class AuditRepository(BaseRepository):
    """Repository for managing audit records (ChangeLog, DeletedRecords, ActionLog)."""

    def __init__(self, db_path: Optional[str] = None, connection: Optional[sqlite3.Connection] = None):
        """
        Initialize AuditRepository.
        If connection is provided, it will be used for inserts (transactional).
        If not, super().__init__ will set up connection management for reads.
        """
        if connection:
            self.conn = connection
            # Skip _ensure_schema if we have a raw connection, 
            # as it's likely already handled or we are in a tight loop.
            self.db_path = None 
        else:
            super().__init__(db_path)

    def insert_change_logs(self, rows: List[Tuple[Any, ...]]) -> None:
        """
        Bulk insert change log entries.
        rows: List of (TableName, RecordID, FieldName, OldValue, NewValue, BatchID)
        Raises: Exception (propagates DB errors for rollback)
        """
        if not rows:
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.executemany("""
                INSERT INTO ChangeLog 
                (LogTableName, RecordID, LogFieldName, OldValue, NewValue, BatchID) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, rows)
        except Exception as e:
            logger.error(f"AuditRepository CRITICAL: Failed to write ChangeLog: {e}")
            raise  # Fail-Secure

    def insert_deleted_record(self, table_name: str, record_id: int, snapshot: str, batch_id: str) -> None:
        """Archive a deleted record."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO DeletedRecords 
                (DeletedFromTable, RecordID, FullSnapshot, BatchID)
                VALUES (?, ?, ?, ?)
            """, (table_name, record_id, snapshot, batch_id))
        except Exception as e:
            logger.error(f"AuditRepository CRITICAL: Failed to write DeletedRecord: {e}")
            raise  # Fail-Secure

    def insert_action_log(self, action_type: str, target_table: Optional[str], target_id: Optional[int], details_json: Optional[str], user_id: Optional[str], batch_id: Optional[str] = None) -> None:
        """Log a high-level action."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO ActionLog 
                (ActionLogType, TargetTable, ActionTargetID, ActionDetails, UserID, BatchID)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (action_type, target_table, target_id, details_json, user_id, batch_id))
        except Exception as e:
            logger.error(f"AuditRepository CRITICAL: Failed to write ActionLog: {e}")
            raise  # Fail-Secure

    def get_change_log(self, limit: int = 1000) -> List[dict]:
        """Retrieve recent field-level changes."""
        try:
            # Handle both raw connection and BaseRepository lifecycle
            if hasattr(self, 'conn') and self.conn:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT LogID, LogTableName, RecordID, LogFieldName, OldValue, NewValue, LogTimestamp, BatchID
                    FROM ChangeLog
                    ORDER BY LogTimestamp DESC
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
            else:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT LogID, LogTableName, RecordID, LogFieldName, OldValue, NewValue, LogTimestamp, BatchID
                        FROM ChangeLog
                        ORDER BY LogTimestamp DESC
                        LIMIT ?
                    """, (limit,))
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch ChangeLog: {e}")
            return []

    def get_action_log(self, limit: int = 1000) -> List[dict]:
        """Retrieve recent high-level actions."""
        try:
            if hasattr(self, 'conn') and self.conn:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT ActionID, ActionLogType, TargetTable, ActionTargetID, ActionDetails, ActionTimestamp, UserID
                    FROM ActionLog
                    ORDER BY ActionTimestamp DESC
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
            else:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT ActionID, ActionLogType, TargetTable, ActionTargetID, ActionDetails, ActionTimestamp, UserID
                        FROM ActionLog
                        ORDER BY ActionTimestamp DESC
                        LIMIT ?
                    """, (limit,))
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch ActionLog: {e}")
            return []

    def get_unified_log(self, limit: int = 1000) -> List[dict]:
        """Retrieve a merged view of ChangeLog and ActionLog."""
        query = """
            SELECT 
                LogTimestamp as Time, 
                'CHANGE' as EntryType, 
                LogTableName as TableName, 
                LogFieldName as FieldName, 
                RecordID, 
                OldValue, 
                NewValue,
                BatchID
            FROM ChangeLog
            UNION ALL
            SELECT 
                ActionTimestamp as Time, 
                ActionLogType as EntryType, 
                TargetTable as TableName, 
                'Action' as FieldName, 
                ActionTargetID as RecordID, 
                NULL as OldValue, 
                ActionDetails as NewValue,
                BatchID
            FROM ActionLog
            ORDER BY Time DESC
            LIMIT ?
        """
        try:
            if hasattr(self, 'conn') and self.conn:
                cursor = self.conn.cursor()
                cursor.execute(query, (limit,))
                return [dict(row) for row in cursor.fetchall()]
            else:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (limit,))
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch UnifiedLog: {e}")
            return []
