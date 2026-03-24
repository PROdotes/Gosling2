import sqlite3
from typing import Any, List, Mapping, Tuple
from src.data.base_repository import BaseRepository
from src.models.domain import Tag
from src.services.logger import logger


class TagRepository(BaseRepository):
    """Repository for loading Tags associated with MediaSources."""

    def get_tags_for_songs(self, song_ids: List[int]) -> List[Tuple[int, Tag]]:
        """Batch-fetch all tags for a list of songs (M2M)."""
        logger.debug(f"[TagRepository] -> get_tags_for_songs(count={len(song_ids)})")
        if not song_ids:
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
                logger.debug(
                    f"[TagRepository] <- get_tags_for_songs() count={len(results)}"
                )
                return results
        except Exception as e:
            logger.error(f"[TagRepository] ERROR: Failed to fetch tags: {e}")
            raise

    def insert_tags(
        self, source_id: int, tags: List[Tag], conn: sqlite3.Connection
    ) -> None:
        """Get-or-create Tags rows, then insert MediaSourceTags links."""
        logger.debug(
            f"[TagRepository] -> insert_tags(source_id={source_id}, count={len(tags)})"
        )
        if not tags:
            logger.debug("[TagRepository] <- insert_tags() empty list, no-op")
            return

        cursor = conn.cursor()
        for tag in tags:
            # Get-or-create: match on name + category. Schema enforces UNIQUE(TagName, TagCategory).
            row = cursor.execute(
                "SELECT TagID FROM Tags WHERE TagName = ? COLLATE UTF8_NOCASE AND TagCategory IS ?",
                (tag.name, tag.category),
            ).fetchone()

            if row:
                tag_id = row[0]
            else:
                cursor.execute(
                    "INSERT INTO Tags (TagName, TagCategory) VALUES (?, ?)",
                    (tag.name, tag.category),
                )
                tag_id = cursor.lastrowid

            # Insert link
            cursor.execute(
                "INSERT INTO MediaSourceTags (SourceID, TagID, IsPrimary) VALUES (?, ?, ?)",
                (source_id, tag_id, 1 if tag.is_primary else 0),
            )

        logger.info(
            f"[TagRepository] <- insert_tags(source_id={source_id}) wrote {len(tags)} tags"
        )

    def _row_to_tag(self, row: Mapping[str, Any]) -> Tag:
        """Map a database row to a Tag Pydantic model."""
        return Tag(
            id=row["TagID"],
            name=row["TagName"],
            category=row["TagCategory"],
            is_primary=bool(row["IsPrimary"]) if "IsPrimary" in row.keys() else False,
        )
