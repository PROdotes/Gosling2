"""ArtistName Repository Module"""
from typing import List, Optional, Any
import sqlite3
from .generic_repository import GenericRepository
from ..models.artist_name import ArtistName


class ArtistNameRepository(GenericRepository[ArtistName]):
    """
    Repository for ArtistName data access.
    Handles stage names and aliases with Audit Logging.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path, "ArtistNames", "name_id")

    def get_by_id(self, record_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[ArtistName]:
        """Fetch a single artist name by ID."""
        if conn:
            return self._get_by_id_logic(record_id, conn)
        
        try:
            with self.get_connection() as conn:
                return self._get_by_id_logic(record_id, conn)
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching artist name by id {record_id}: {e}")
            return None

    def _get_by_id_logic(self, name_id: int, conn: sqlite3.Connection) -> Optional[ArtistName]:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT NameID, OwnerIdentityID, DisplayName, SortName, IsPrimaryName, DisambiguationNote
            FROM ArtistNames WHERE NameID = ?
        """, (name_id,))
        row = cursor.fetchone()
        return ArtistName.from_row(row) if row else None

    def _insert_db(self, cursor: sqlite3.Cursor, entity: ArtistName, **kwargs) -> int:
        """Execute INSERT statement."""
        cursor.execute("""
            INSERT INTO ArtistNames (
                OwnerIdentityID, DisplayName, SortName, IsPrimaryName, DisambiguationNote
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            entity.owner_identity_id, entity.display_name, entity.sort_name, 
            int(entity.is_primary_name), entity.disambiguation_note
        ))
        return cursor.lastrowid

    def _update_db(self, cursor: sqlite3.Cursor, entity: ArtistName, **kwargs) -> None:
        """Execute UPDATE statement."""
        cursor.execute("""
            UPDATE ArtistNames SET 
                OwnerIdentityID = ?, DisplayName = ?, SortName = ?, 
                IsPrimaryName = ?, DisambiguationNote = ?
            WHERE NameID = ?
        """, (
            entity.owner_identity_id, entity.display_name, entity.sort_name, 
            int(entity.is_primary_name), entity.disambiguation_note, entity.name_id
        ))

    def _delete_db(self, cursor: sqlite3.Cursor, record_id: int, **kwargs) -> None:
        """Execute DELETE statement. Clean up credits first."""
        cursor.execute("DELETE FROM SongCredits WHERE CreditedNameID = ?", (record_id,))
        cursor.execute("DELETE FROM AlbumCredits WHERE CreditedNameID = ?", (record_id,))
        cursor.execute("DELETE FROM ArtistNames WHERE NameID = ?", (record_id,))

    def merge(self, source_id: int, target_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Merge source name piece into target name piece.
        Redirects all SongCredits and AlbumCredits.
        """
        from src.core.audit_logger import AuditLogger
        
        def _execute(target_conn):
            auditor = AuditLogger(target_conn)
            
            # 1. Update SongCredits
            # PK is (SourceID, CreditedNameID, RoleID). 
            # If target already has that role for that song, we just delete the source link.
            target_conn.execute("""
                INSERT OR IGNORE INTO SongCredits (SourceID, CreditedNameID, RoleID)
                SELECT SourceID, ?, RoleID FROM SongCredits WHERE CreditedNameID = ?
            """, (target_id, source_id))
            target_conn.execute("DELETE FROM SongCredits WHERE CreditedNameID = ?", (source_id,))
            
            # 2. Update AlbumCredits
            target_conn.execute("""
                INSERT OR IGNORE INTO AlbumCredits (AlbumID, CreditedNameID, RoleID)
                SELECT AlbumID, ?, RoleID FROM AlbumCredits WHERE CreditedNameID = ?
            """, (target_id, source_id))
            target_conn.execute("DELETE FROM AlbumCredits WHERE CreditedNameID = ?", (source_id,))
            
            # 3. Delete Source Piece
            target_conn.execute("DELETE FROM ArtistNames WHERE NameID = ?", (source_id,))
            return True

        if conn:
            return _execute(conn)
        with self.get_connection() as conn:
            success = _execute(conn)
            if success:
                conn.commit()
            return success

    def get_by_owner(self, identity_id: int) -> List[ArtistName]:
        """Fetch all names owned by a specific identity."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT NameID, OwnerIdentityID, DisplayName, SortName, IsPrimaryName, DisambiguationNote
                    FROM ArtistNames WHERE OwnerIdentityID = ?
                    ORDER BY IsPrimaryName DESC, DisplayName ASC
                """, (identity_id,))
                return [ArtistName.from_row(row) for row in cursor.fetchall()]
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching names for identity {identity_id}: {e}")
            return []

    def search(self, query: str) -> List[ArtistName]:
        """Search for artist names by display name."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT NameID, OwnerIdentityID, DisplayName, SortName, IsPrimaryName, DisambiguationNote
                    FROM ArtistNames 
                    WHERE DisplayName COLLATE UTF8_NOCASE LIKE ?
                    ORDER BY DisplayName ASC
                """, (f"%{query}%",))
                return [ArtistName.from_row(row) for row in cursor.fetchall()]
        except Exception as e:
            from src.core import logger
            logger.error(f"Error searching artist names with query '{query}': {e}")
            return []

    def find_exact(self, name: str) -> List[ArtistName]:
        """Find names matching exactly (using strict UTF8 collation)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT NameID, OwnerIdentityID, DisplayName, SortName, IsPrimaryName, DisambiguationNote
                    FROM ArtistNames 
                    WHERE DisplayName = ? COLLATE UTF8_NOCASE
                """, (name,))
                return [ArtistName.from_row(row) for row in cursor.fetchall()]
        except Exception as e:
            from src.core import logger
            logger.error(f"Error finding exact name '{name}': {e}")
            return []

    def create(self, entity: ArtistName, batch_id: Optional[str] = None) -> int:
        """Alias for insert() to maintain consistency."""
        return self.insert(entity, batch_id=batch_id)
