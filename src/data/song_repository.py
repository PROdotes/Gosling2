import sqlite3
from typing import List, Optional, Mapping, Any
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
    _JOIN = "FROM MediaSources m JOIN Songs s ON m.SourceID = s.SourceID AND m.TypeID = (SELECT TypeID FROM Types WHERE TypeName = 'Song')"

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

    def get_by_title(self, query: str) -> List[Song]:
        """Find songs by title match."""
        logger.debug(f"[SongRepository] Searching for songs with title LIKE: {query}")
        query_sql = f"SELECT {self._COLUMNS} {self._JOIN} WHERE m.MediaName LIKE ?"

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, (f"%{query}%",)).fetchall()
            logger.debug(
                f"[SongRepository] Found {len(rows)} matches for query: '{query}'"
            )
            return [self._row_to_song(row) for row in rows]

    def search_surface(self, query: str) -> List[Song]:
        """Discovery path on titles and albums. Fastest search."""
        fmt_q = f"%{query}%"
        query_sql = f"""
            SELECT {self._COLUMNS} {self._JOIN}
            WHERE m.MediaName LIKE ?
               OR m.SourceID IN (
                   SELECT sa.SourceID FROM SongAlbums sa
                   JOIN Albums a ON sa.AlbumID = a.AlbumID
                   WHERE a.AlbumTitle LIKE ?
               )
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, (fmt_q, fmt_q)).fetchall()
            return [self._row_to_song(row) for row in rows]

    def get_by_identity_ids(self, identity_ids: List[int]) -> List[Song]:
        """Retrieves songs where any given Identity ID is credited (The Grohlton Check base)."""
        if not identity_ids:
            return []

        logger.debug(f"[SongRepository] get_by_identity_ids entry: ids={identity_ids}")
        placeholders = ",".join(["?" for _ in identity_ids])
        query_sql = f"""
            SELECT {self._COLUMNS} {self._JOIN}
            WHERE m.SourceID IN (
                SELECT sc.SourceID FROM SongCredits sc
                JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
                WHERE an.OwnerIdentityID IN ({placeholders})
            )
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, identity_ids).fetchall()
            return [self._row_to_song(row) for row in rows]

    def _row_to_song(self, row: Mapping[str, Any]) -> Song:
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
            is_active=bool(row["IsActive"]) if row["IsActive"] is not None else False,
            notes=row["SourceNotes"],
            media_name=row["MediaName"],
            bpm=row["TempoBPM"],
            year=row["RecordingYear"],
            isrc=row["ISRC"],
        )
