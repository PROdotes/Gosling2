import sqlite3
from typing import Optional, List
from ..models.domain import Song

class SongRepository:
    """Repository for loading Song domain models from the SQLite database."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_by_id(self, song_id: int) -> Optional[Song]:
        """Fetch a single Song by its SourceID."""
        results = self.get_by_ids([song_id])
        return results[0] if results else None

    def get_by_ids(self, ids: List[int]) -> List[Song]:
        """Batch-fetch multiple Songs by their IDs."""
        if not ids:
            return []
            
        placeholders = ",".join(["?" for _ in ids])
        query = f"""
            SELECT 
                m.SourceID, m.TypeID, m.SourcePath, m.SourceDuration, m.AudioHash, 
                m.ProcessingStatus, m.IsActive, m.SourceNotes, m.MediaName,
                s.TempoBPM, s.RecordingYear, s.ISRC
            FROM MediaSources m
            JOIN Songs s ON m.SourceID = s.SourceID
            WHERE m.SourceID IN ({placeholders})
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, ids).fetchall()
            return [self._row_to_song(row) for row in rows]

    def _row_to_song(self, row: sqlite3.Row) -> Song:
        """Map a database row to a Song Pydantic model."""
        return Song(
            id=row["SourceID"],
            type_id=row["TypeID"],
            source_path=row["SourcePath"],
            duration_ms=int(row["SourceDuration"] * 1000),  # Convert seconds to ms
            audio_hash=row["AudioHash"],
            processing_status=row["ProcessingStatus"],
            is_active=bool(row["IsActive"]),
            notes=row["SourceNotes"],
            title=row["MediaName"],
            bpm=row["TempoBPM"],
            year=row["RecordingYear"],
            isrc=row["ISRC"],
            album_id=None  # Refinement: Add album linking later
        )
