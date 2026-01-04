"""
Audit Repository

Handles direct database operations for Audit logs (ChangeLog, DeletedRecords, ActionLog).
"""
from typing import List, Tuple, Any, Optional
from ...core import logger

class AuditRepository:
    """Repository for inserting audit records."""

    def __init__(self, connection):
        self.conn = connection

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

    def insert_action_log(self, action_type: str, target_table: Optional[str], target_id: Optional[int], details_json: Optional[str], user_id: Optional[str]) -> None:
        """Log a high-level action."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO ActionLog 
                (ActionLogType, TargetTable, ActionTargetID, ActionDetails, UserID)
                VALUES (?, ?, ?, ?, ?)
            """, (action_type, target_table, target_id, details_json, user_id))
        except Exception as e:
            logger.error(f"AuditRepository CRITICAL: Failed to write ActionLog: {e}")
            raise  # Fail-Secure
