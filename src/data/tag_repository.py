import sqlite3
from typing import List, Tuple
from src.data.base_repository import BaseRepository
from src.models.domain import Tag
from src.services.logger import logger


class TagRepository(BaseRepository):
    """Repository for loading Tags associated with MediaSources."""

    def get_tags_for_songs(self, song_ids: List[int]) -> List[Tuple[int, Tag]]:
        """Batch-fetch all tags for a list of songs (M2M)."""
        if not song_ids:
            return []

        logger.debug(f"[TagRepository] Batch-fetching tags for {len(song_ids)} songs.")
        placeholders = ",".join(["?" for _ in song_ids])
        query = f"""
            SELECT mst.SourceID, t.TagID, t.TagName, t.TagCategory
            FROM MediaSourceTags mst
            JOIN Tags t ON mst.TagID = t.TagID
            WHERE mst.SourceID IN ({placeholders})
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, song_ids).fetchall()
            logger.debug(f"[TagRepository] Found {len(rows)} tag associations.")
            return [(row["SourceID"], self._row_to_tag(row)) for row in rows]

    def _row_to_tag(self, row: sqlite3.Row) -> Tag:
        """Map a database row to a Tag Pydantic model."""
        return Tag(id=row["TagID"], name=row["TagName"], category=row["TagCategory"])
