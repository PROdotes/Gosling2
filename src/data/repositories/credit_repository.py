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

    def get_song_credits(self, source_id: int) -> List[Dict[str, Any]]:
        """Fetch all credits for a song with display names and role names."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT sc.CreditID, sc.SourceID, sc.CreditedNameID, sc.RoleID, sc.CreditPosition,
                           an.DisplayName, r.RoleName
                    FROM SongCredits sc
                    JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
                    JOIN Roles r ON sc.RoleID = r.RoleID
                    WHERE sc.SourceID = ?
                    ORDER BY sc.CreditPosition ASC
                """, (source_id,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "credit_id": row[0],
                        "source_id": row[1],
                        "name_id": row[2],
                        "role_id": row[3],
                        "position": row[4],
                        "display_name": row[5],
                        "role_name": row[6]
                    })
                return results
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching song credits for {source_id}: {e}")
            return []

    def add_album_credit(self, album_id: int, name_id: int, role_id: int, batch_id: Optional[str] = None) -> int:
        """Add a credit record to an album."""
        from src.core.audit_logger import AuditLogger
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO AlbumCredits (AlbumID, CreditedNameID, RoleID)
                    VALUES (?, ?, ?)
                """, (album_id, name_id, role_id))
                new_id = cursor.lastrowid
                
                if new_id:
                    AuditLogger(conn, batch_id=batch_id).log_insert("AlbumCredits", f"{album_id}-{name_id}-{role_id}", {
                        "AlbumID": album_id, "CreditedNameID": name_id, "RoleID": role_id
                    })
                return new_id
        except sqlite3.IntegrityError:
            return 0
        except Exception as e:
            from src.core import logger
            logger.error(f"Error adding album credit: {e}")
            return 0

    def remove_album_credit(self, album_id: int, name_id: int, role_id: int, batch_id: Optional[str] = None) -> bool:
        """Remove a credit record from an album."""
        from src.core.audit_logger import AuditLogger
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Snapshot for audit
                snapshot = {"AlbumID": album_id, "CreditedNameID": name_id, "RoleID": role_id}
                
                cursor.execute("""
                    DELETE FROM AlbumCredits 
                    WHERE AlbumID = ? AND CreditedNameID = ? AND RoleID = ?
                """, (album_id, name_id, role_id))
                
                if cursor.rowcount > 0:
                    AuditLogger(conn, batch_id=batch_id).log_delete("AlbumCredits", f"{album_id}-{name_id}-{role_id}", snapshot)
                return cursor.rowcount > 0
        except Exception as e:
            from src.core import logger
            logger.error(f"Error removing album credit: {e}")
            return False

    def get_album_credits(self, album_id: int) -> List[Dict[str, Any]]:
        """Fetch all credits for an album."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ac.CreditID, ac.AlbumID, ac.CreditedNameID, ac.RoleID,
                           an.DisplayName, r.RoleName
                    FROM AlbumCredits ac
                    JOIN ArtistNames an ON ac.CreditedNameID = an.NameID
                    JOIN Roles r ON ac.RoleID = r.RoleID
                    WHERE ac.AlbumID = ?
                """, (album_id,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "credit_id": row[0],
                        "album_id": row[1],
                        "name_id": row[2],
                        "role_id": row[3],
                        "display_name": row[4],
                        "role_name": row[5]
                    })
                return results
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching album credits for {album_id}: {e}")
            return []
