"""
Generic Repository Module
Defines the abstract base class for repositories with audit logging support.
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Any
import sqlite3

from src.data.database import BaseRepository
from src.core import logger

T = TypeVar('T')

class GenericRepository(BaseRepository, Generic[T], ABC):
    """
    Abstract Base Repository implementing Audit Logging (Fail-Secure).
    
    This class wraps standard CRUD operations with automated hooks into the
    Audit Logging system. It enforces a "Fail-Secure" policy where database writes
    are bundled with audit writes in a single atomic transaction.
    
    Type Vars:
        T: The Model class (e.g. Song, Album) this repository manages.
    """
    
    def __init__(self, db_path: Optional[str] = None, table_name: str = "Unknown", id_attr: str = "id") -> None:
        """
        Initialize the repository.
        
        Args:
            db_path: Path to SQLite database.
            table_name: Database table name for Audit Logging (e.g. 'Songs').
            id_attr: The Python attribute name of the ID on the model (e.g. 'source_id').
        """
        super().__init__(db_path)
        self.table_name = table_name
        self.id_attr = id_attr

    # --- ABSTRACT IMPLEMENTATION HOOKS ---
    
    @abstractmethod
    def get_by_id(self, record_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[T]:
        """
        Fetch a single record by ID.
        REQUIRED for Audit Logging to calculate diffs (Old vs New).
        """
        pass

    @abstractmethod
    def _insert_db(self, cursor: sqlite3.Cursor, entity: T, **kwargs) -> int:
        """
        Execute the SQL INSERT statement.
        Must return the new Record ID.
        """
        pass
        
    @abstractmethod
    def _update_db(self, cursor: sqlite3.Cursor, entity: T, **kwargs) -> None:
        """
        Execute the SQL UPDATE statement.
        Should raise sqlite3.Error on failure.
        """
        pass

    @abstractmethod
    def _delete_db(self, cursor: sqlite3.Cursor, record_id: int, **kwargs) -> None:
        """
        Execute the SQL DELETE statement.
        Should raise sqlite3.Error on failure.
        """
        pass

    # --- PUBLIC TRANSACTIONAL METHODS ---

    def insert(self, entity: T, batch_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
        """
        Transactional Insert with Audit.
        Returns: New ID on success, None on failure.
        """
        if conn:
            return self._insert_logic(entity, conn, batch_id)
            
        try:
            with self.get_connection() as conn:
                return self._insert_logic(entity, conn, batch_id)
        except Exception as e:
            logger.error(f"GenericRepository Insert Failed ({self.table_name}): {e}")
            return None

    def _insert_logic(self, entity: T, conn: sqlite3.Connection, batch_id: Optional[str]) -> Optional[int]:
        """Internal logic for insert, allowing connection sharing."""
        from src.core.audit_logger import AuditLogger
        cursor = conn.cursor()
        auditor = AuditLogger(conn, batch_id=batch_id)
        
        new_id = self._insert_db(cursor, entity, auditor=auditor)
        
        if hasattr(entity, 'to_dict') and new_id:
            auditor.log_insert(self.table_name, new_id, entity.to_dict())
        
        return new_id

    def update(self, entity: T, batch_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Transactional Update with Audit (Diffing).
        Returns: True on success, False on failure.
        """
        if conn:
            return self._update_logic(entity, conn, batch_id)
            
        try:
            with self.get_connection() as conn:
                return self._update_logic(entity, conn, batch_id)
        except Exception as e:
            logger.error(f"GenericRepository Update Failed ({self.table_name}): {e}")
            raise e

    def _update_logic(self, entity: T, conn: sqlite3.Connection, batch_id: Optional[str]) -> bool:
        """Internal logic for update, allowing connection sharing."""
        from src.core.audit_logger import AuditLogger
        
        record_id = getattr(entity, self.id_attr, None)
        if not record_id: 
            raise ValueError(f"Entity missing ID attribute '{self.id_attr}'")
        
        # NOTE: get_by_id still creates its own connection unless overridden
        # For full transaction support, get_by_id should also support conn
        old_entity = self.get_by_id(record_id, conn=conn)
        if not old_entity:
            logger.warning(f"Update failed: Record {record_id} not found in {self.table_name}")
            return False
            
        old_snapshot = old_entity.to_dict() if hasattr(old_entity, 'to_dict') else {}

        cursor = conn.cursor()
        auditor = AuditLogger(conn, batch_id=batch_id)
        
        self._update_db(cursor, entity, auditor=auditor)
        
        if hasattr(entity, 'to_dict'):
            auditor.log_update(self.table_name, record_id, old_snapshot, entity.to_dict())
        
        return True

    def delete(self, record_id: int, batch_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Transactional Delete with Audit (Recycle Bin).
        Returns: True on success, False on failure.
        """
        if conn:
            return self._delete_logic(record_id, conn, batch_id)
            
        try:
            with self.get_connection() as conn:
                return self._delete_logic(record_id, conn, batch_id)
        except Exception as e:
            logger.error(f"GenericRepository Delete Failed ({self.table_name}): {e}")
            return False

    def _delete_logic(self, record_id: int, conn: sqlite3.Connection, batch_id: Optional[str]) -> bool:
        """Internal logic for delete, allowing connection sharing."""
        from src.core.audit_logger import AuditLogger
        
        old_entity = self.get_by_id(record_id, conn=conn)
        if not old_entity:
            return False 

        old_snapshot = old_entity.to_dict() if hasattr(old_entity, 'to_dict') else {}

        cursor = conn.cursor()
        auditor = AuditLogger(conn, batch_id=batch_id)
        
        self._delete_db(cursor, record_id, auditor=auditor)
        
        auditor.log_delete(self.table_name, record_id, old_snapshot)
        
        return True
