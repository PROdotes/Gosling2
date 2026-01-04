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
    def get_by_id(self, record_id: int) -> Optional[T]:
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

    def insert(self, entity: T) -> Optional[int]:
        """
        Transactional Insert with Audit.
        Returns: New ID on success, None on failure.
        """
        # AuditLogger imported locally to handle dependency resolution
        from src.core.audit_logger import AuditLogger
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                auditor = AuditLogger(conn)
                
                # 1. Write Data
                new_id = self._insert_db(cursor, entity, auditor=auditor)
                
                # 2. Write Audit (Snapshots the entity as provided)
                if hasattr(entity, 'to_dict') and new_id:
                    auditor.log_insert(self.table_name, new_id, entity.to_dict())
                
                return new_id
                
        except Exception as e:
            # BaseRepository context manager handles Rollback.
            # We log and return failure.
            logger.error(f"GenericRepository Insert Failed ({self.table_name}): {e}")
            return None

    def update(self, entity: T) -> bool:
        """
        Transactional Update with Audit (Diffing).
        Returns: True on success, False on failure.
        """
        from src.core.audit_logger import AuditLogger
        
        try:
            # 1. Fetch Old State (Snapshot T0)
            record_id = getattr(entity, self.id_attr, None)
            if not record_id: 
                raise ValueError(f"Entity missing ID attribute '{self.id_attr}'")
            
            old_entity = self.get_by_id(record_id)
            if not old_entity:
                logger.warning(f"Update failed: Record {record_id} not found in {self.table_name}")
                return False
                
            old_snapshot = old_entity.to_dict() if hasattr(old_entity, 'to_dict') else {}

            # 2. Write Data & Audit (Snapshot T1)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                auditor = AuditLogger(conn)
                
                self._update_db(cursor, entity, auditor=auditor)
                
                if hasattr(entity, 'to_dict'):
                    auditor.log_update(self.table_name, record_id, old_snapshot, entity.to_dict())
                
                return True
                
        except Exception as e:
            logger.error(f"GenericRepository Update Failed ({self.table_name}): {e}")
            return False

    def delete(self, record_id: int) -> bool:
        """
        Transactional Delete with Audit (Recycle Bin).
        Returns: True on success, False on failure.
        """
        from src.core.audit_logger import AuditLogger
        
        try:
            # 1. Fetch Old State (Snapshot T0) for Recycle Bin
            old_entity = self.get_by_id(record_id)
            if not old_entity:
                return False # Idempotent-ish failure (Record already gone)

            old_snapshot = old_entity.to_dict() if hasattr(old_entity, 'to_dict') else {}

            # 2. Delete Data & Audit
            with self.get_connection() as conn:
                cursor = conn.cursor()
                auditor = AuditLogger(conn)
                
                self._delete_db(cursor, record_id, auditor=auditor)
                
                auditor.log_delete(self.table_name, record_id, old_snapshot)
                
                return True
                
        except Exception as e:
            logger.error(f"GenericRepository Delete Failed ({self.table_name}): {e}")
            return False
