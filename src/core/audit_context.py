import uuid
import sqlite3
from typing import Optional
from contextlib import contextmanager
from .audit_logger import AuditLogger
from ..data.database_config import DatabaseConfig

class AuditContext:
    """
    Context manager for managing a unified BatchID across multiple repository operations.
    Ensures that all actions within the context share the same transaction and audit batch.
    """

    def __init__(self, db_path: Optional[str] = None, operation_name: str = "Bulk Operation"):
        self.db_path = db_path or DatabaseConfig.get_database_path()
        self.operation_name = operation_name
        self.batch_id = str(uuid.uuid4())
        self.conn: Optional[sqlite3.Connection] = None
        self._auditor: Optional[AuditLogger] = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        
        self._auditor = AuditLogger(self.conn, batch_id=self.batch_id)
        # Log the start of the batch action
        self._auditor.log_action(f"START_BATCH: {self.operation_name}", details={"batch_id": self.batch_id})
        
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.conn.rollback()
                self._auditor.log_action(f"ROLLBACK_BATCH: {self.operation_name}", details={"error": str(exc_val)})
            else:
                self.conn.commit()
                self._auditor.log_action(f"COMMIT_BATCH: {self.operation_name}")
        finally:
            self.conn.close()

    @property
    def auditor(self) -> AuditLogger:
        if not self._auditor:
            raise RuntimeError("AuditContext not initialized. Use 'with' statement.")
        return self._auditor
