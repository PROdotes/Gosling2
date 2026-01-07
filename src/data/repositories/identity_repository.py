"""Identity Repository Module"""
from typing import List, Optional, Any
import sqlite3
from .generic_repository import GenericRepository
from ..models.identity import Identity


class IdentityRepository(GenericRepository[Identity]):
    """
    Repository for Identity data access.
    Handles real person/group metadata with Audit Logging.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path, "Identities", "identity_id")

    def get_by_id(self, record_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Identity]:
        """Fetch a single identity by ID."""
        if conn:
            return self._get_by_id_logic(record_id, conn)
        
        try:
            with self.get_connection() as conn:
                return self._get_by_id_logic(record_id, conn)
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching identity by id {record_id}: {e}")
            return None

    def _get_by_id_logic(self, identity_id: int, conn: sqlite3.Connection) -> Optional[Identity]:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT IdentityID, IdentityType, LegalName, DateOfBirth, DateOfDeath, 
                   Nationality, FormationDate, DisbandDate, Biography, Notes 
            FROM Identities WHERE IdentityID = ?
        """, (identity_id,))
        row = cursor.fetchone()
        return Identity.from_row(row) if row else None

    def _insert_db(self, cursor: sqlite3.Cursor, entity: Identity, **kwargs) -> int:
        """Execute INSERT statement."""
        cursor.execute("""
            INSERT INTO Identities (
                IdentityType, LegalName, DateOfBirth, DateOfDeath, 
                Nationality, FormationDate, DisbandDate, Biography, Notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity.identity_type, entity.legal_name, entity.date_of_birth, 
            entity.date_of_death, entity.nationality, entity.formation_date, 
            entity.disband_date, entity.biography, entity.notes
        ))
        return cursor.lastrowid

    def _update_db(self, cursor: sqlite3.Cursor, entity: Identity, **kwargs) -> None:
        """Execute UPDATE statement."""
        cursor.execute("""
            UPDATE Identities SET 
                IdentityType = ?, LegalName = ?, DateOfBirth = ?, DateOfDeath = ?, 
                Nationality = ?, FormationDate = ?, DisbandDate = ?, Biography = ?, Notes = ?
            WHERE IdentityID = ?
        """, (
            entity.identity_type, entity.legal_name, entity.date_of_birth, 
            entity.date_of_death, entity.nationality, entity.formation_date, 
            entity.disband_date, entity.biography, entity.notes, entity.identity_id
        ))

    def _delete_db(self, cursor: sqlite3.Cursor, record_id: int, **kwargs) -> None:
        """Execute DELETE statement."""
        cursor.execute("DELETE FROM Identities WHERE IdentityID = ?", (record_id,))

    def create(self, entity: Identity, batch_id: Optional[str] = None) -> int:
        """Alias for insert() to maintain consistency with existing repositories."""
        return self.insert(entity, batch_id=batch_id)
