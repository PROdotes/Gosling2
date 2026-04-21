import sqlite3
from typing import Optional
from src.data.base_repository import BaseRepository
from src.services.logger import logger

class StagingRepository(BaseRepository):
    """Temporary storage for linking staged songs back to their original source (Downloads/etc)."""

    def set_origin(self, source_id: int, origin_path: str, conn: Optional[sqlite3.Connection] = None) -> None:
        """Saves the original origin path for a song id."""
        logger.debug(f"[StagingRepository] -> set_origin(id={source_id}, path='{origin_path}')")
        query = "INSERT OR REPLACE INTO StagingOrigins (SourceID, OriginPath) VALUES (?, ?)"
        
        if conn:
            conn.execute(query, (source_id, origin_path))
            return

        with self._get_connection() as new_conn:
            new_conn.execute(query, (source_id, origin_path))
            new_conn.commit()

    def get_origin(self, source_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
        """Retrieves the original path for a song id, if it exists."""
        query = "SELECT OriginPath FROM StagingOrigins WHERE SourceID = ?"
        
        if conn:
            row = conn.execute(query, (source_id,)).fetchone()
            return row[0] if row else None

        with self._get_connection() as new_conn:
            row = new_conn.execute(query, (source_id,)).fetchone()
            return row[0] if row else None

    def clear_origin(self, source_id: int, conn: Optional[sqlite3.Connection] = None) -> None:
        """Removes the origin mapping for a song (e.g. after organization or deletion)."""
        logger.debug(f"[StagingRepository] -> clear_origin(id={source_id})")
        query = "DELETE FROM StagingOrigins WHERE SourceID = ?"
        
        if conn:
            conn.execute(query, (source_id,))
            return

        with self._get_connection() as new_conn:
            new_conn.execute(query, (source_id,))
            new_conn.commit()
