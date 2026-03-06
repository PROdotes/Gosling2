import sqlite3
from typing import Optional, List
from src.models.domain import Song
from src.data.base_repository import BaseRepository
from src.services.logger import logger


class SongRepository(BaseRepository):
    """Repository for loading Song domain models from the SQLite database."""

    # The Golden Truth: All song queries MUST fetch these columns.
    _COLUMNS = """
        m.SourceID, m.TypeID, m.SourcePath, m.SourceDuration, m.AudioHash,
        m.ProcessingStatus, m.IsActive, m.SourceNotes, m.MediaName,
        s.TempoBPM, s.RecordingYear, s.ISRC
    """
    _JOIN = "FROM MediaSources m JOIN Songs s ON m.SourceID = s.SourceID"

    def get_by_id(self, song_id: int) -> Optional[Song]:
        """Fetch a single Song by its SourceID."""
        results = self.get_by_ids([song_id])
        return results[0] if results else None

    def get_by_ids(self, ids: List[int]) -> List[Song]:
        """Batch-fetch multiple Songs by their IDs."""
        if not ids:
            return []

        logger.debug(f"[SongRepository] Batch-fetching {len(ids)} songs.")
        placeholders = ",".join(["?" for _ in ids])
        query = (
            f"SELECT {self._COLUMNS} {self._JOIN} WHERE m.SourceID IN ({placeholders})"
        )

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, ids).fetchall()
            logger.debug(
                f"[SongRepository] Found {len(rows)} out of {len(ids)} requested songs."
            )
            return [self._row_to_song(row) for row in rows]

    def get_by_title(self, query: str, limit: int = 50) -> List[Song]:
        """Find songs by title match."""
        logger.debug(f"[SongRepository] Searching for songs with title LIKE: {query}")
        query_sql = (
            f"SELECT {self._COLUMNS} {self._JOIN} WHERE m.MediaName LIKE ? LIMIT ?"
        )

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            # Basic SQLite LIKE is case-insensitive by default for ASCII
            rows = conn.execute(query_sql, (f"%{query}%", limit)).fetchall()
            logger.debug(
                f"[SongRepository] Found {len(rows)} matches for query: '{query}'"
            )
            return [self._row_to_song(row) for row in rows]

    def _row_to_song(self, row: sqlite3.Row) -> Song:
        """Map a database row to a Song Pydantic model."""
        return Song(
            id=row["SourceID"],
            type_id=row["TypeID"],
            source_path=row["SourcePath"],
            duration_ms=int(row["SourceDuration"] * 1000),  # Convert seconds to ms
            audio_hash=row["AudioHash"],
            processing_status=(
                row["ProcessingStatus"] if row["ProcessingStatus"] is not None else 0
            ),
            is_active=bool(row["IsActive"]) if row["IsActive"] is not None else True,
            notes=row["SourceNotes"],
            title=row["MediaName"],
            bpm=row["TempoBPM"],
            year=row["RecordingYear"],
            isrc=row["ISRC"],
            album_id=None,
        )
