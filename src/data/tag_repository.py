import sqlite3
from typing import List, Tuple
from src.data.base_repository import BaseRepository
from src.models.domain import Tag
from src.services.logger import logger


class TagRepository(BaseRepository):
    """Repository for loading Tags associated with MediaSources."""

    def get_tags_for_songs(self, song_ids: List[int]) -> List[Tuple[int, Tag]]:
        """Batch-fetch all tags for a list of songs (M2M)."""
        logger.info(f"[TagRepository] Entry: get_tags_for_songs(ids={song_ids})")
        if not song_ids:
            logger.info("[TagRepository] Exit: get_tags_for_songs - Empty input")
            return []

        placeholders = ",".join(["?" for _ in song_ids])
        query = f"""
            SELECT mst.SourceID, mst.IsPrimary, t.TagID, t.TagName, t.TagCategory
            FROM MediaSourceTags mst
            JOIN Tags t ON mst.TagID = t.TagID
            WHERE mst.SourceID IN ({placeholders})
        """

        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(query, song_ids).fetchall()
                results = [(row["SourceID"], self._row_to_tag(row)) for row in rows]
                logger.info(
                    f"[TagRepository] Exit: get_tags_for_songs - Found {len(results)} tags"
                )
                return results
        except Exception as e:
            logger.error(f"[TagRepository] Violation: Failed to fetch tags: {e}")
            raise

    def _row_to_tag(self, row: sqlite3.Row) -> Tag:
        """Map a database row to a Tag Pydantic model."""
        return Tag(
            id=row["TagID"],
            name=row["TagName"],
            category=row["TagCategory"],
            is_primary=bool(row["IsPrimary"]) if "IsPrimary" in row.keys() else False,
        )
