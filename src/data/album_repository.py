import sqlite3
from typing import List, Optional

from src.data.base_repository import BaseRepository
from src.models.domain import Album
from src.services.logger import logger


class AlbumRepository(BaseRepository):
    """Repository for loading first-class Album records."""

    _COLUMNS = "AlbumID, AlbumTitle, AlbumType, ReleaseYear"

    def get_all(self) -> List[Album]:
        """Fetch the full album directory."""
        logger.info("[AlbumRepository] Entry: get_all()")
        query = f"SELECT {self._COLUMNS} FROM Albums ORDER BY AlbumTitle COLLATE NOCASE ASC"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
            result = [self._row_to_album(row) for row in rows]
            logger.info(f"[AlbumRepository] Exit: Found {len(result)} albums.")
            return result

    def search(self, query: str) -> List[Album]:
        """Search albums by title."""
        logger.info(f"[AlbumRepository] Entry: search(query='{query}')")
        sql = f"SELECT {self._COLUMNS} FROM Albums WHERE AlbumTitle LIKE ? ORDER BY AlbumTitle COLLATE NOCASE ASC"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, (f"%{query}%",)).fetchall()
            result = [self._row_to_album(row) for row in rows]
            logger.info(f"[AlbumRepository] Exit: Found {len(result)} albums.")
            return result

    def get_by_id(self, album_id: int) -> Optional[Album]:
        """Fetch a single album by ID."""
        logger.info(f"[AlbumRepository] Entry: get_by_id(id={album_id})")
        query = f"SELECT {self._COLUMNS} FROM Albums WHERE AlbumID = ?"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(query, (album_id,)).fetchone()
            if row is None:
                logger.warning(f"[AlbumRepository] Exit: ID {album_id} NOT_FOUND")
                return None
            result = self._row_to_album(row)
            logger.info(f"[AlbumRepository] Exit: Found '{result.title}'")
            return result

    def get_song_ids_by_album(self, album_id: int) -> List[int]:
        """Fetch all song IDs linked to an album."""
        logger.info(f"[AlbumRepository] Entry: get_song_ids_by_album(id={album_id})")
        query = "SELECT SourceID FROM SongAlbums WHERE AlbumID = ? ORDER BY DiscNumber, TrackNumber, SourceID"
        with self._get_connection() as conn:
            rows = conn.execute(query, (album_id,)).fetchall()
            result = [row[0] for row in rows]
            logger.info(f"[AlbumRepository] Exit: Found {len(result)} song IDs.")
            return result

    def _row_to_album(self, row: sqlite3.Row) -> Album:
        return Album(
            id=row["AlbumID"],
            title=row["AlbumTitle"],
            album_type=row["AlbumType"],
            release_year=row["ReleaseYear"],
        )
