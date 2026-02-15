"""Credit Repository Module"""
from typing import List, Optional, Dict, Any
import sqlite3
from src.data.database import BaseRepository


class CreditRepository(BaseRepository):
    """
    Repository for managing song and album credits.
    """

    def add_song_credit(self, source_id: int, name_id: int, role_id: int, position: int = 0, batch_id: Optional[str] = None) -> int:
        """Add a credit record to a song."""
        from src.core.audit_logger import AuditLogger
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID, CreditPosition)
                    VALUES (?, ?, ?, ?)
                """, (source_id, name_id, role_id, position))
                new_id = cursor.lastrowid
                
                if new_id:
                    AuditLogger(conn, batch_id=batch_id).log_insert("SongCredits", f"{source_id}-{name_id}-{role_id}", {
                        "SourceID": source_id, "CreditedNameID": name_id, 
                        "RoleID": role_id, "CreditPosition": position
                    })
                return new_id
        except sqlite3.IntegrityError:
            # Credit already exists (UNIQUE constraint)
            return 0
        except Exception as e:
            from src.core import logger
            logger.error(f"Error adding song credit: {e}")
            return 0

    def remove_song_credit(self, source_id: int, name_id: int, role_id: int, batch_id: Optional[str] = None) -> bool:
        """Remove a credit record from a song."""
        from src.core.audit_logger import AuditLogger
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Snapshot for audit
                snapshot = {"SourceID": source_id, "CreditedNameID": name_id, "RoleID": role_id}
                
                cursor.execute("""
                    DELETE FROM SongCredits 
                    WHERE SourceID = ? AND CreditedNameID = ? AND RoleID = ?
                """, (source_id, name_id, role_id))
                
                if cursor.rowcount > 0:
                    AuditLogger(conn, batch_id=batch_id).log_delete("SongCredits", f"{source_id}-{name_id}-{role_id}", snapshot)
                return cursor.rowcount > 0
        except Exception as e:
            from src.core import logger
            logger.error(f"Error removing song credit: {e}")
            return False
