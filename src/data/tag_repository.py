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

    def get_all(self) -> List[Tag]:
        """Fetch all tags."""
        logger.debug("[TagRepository] -> get_all()")
        query = "SELECT TagID, TagName, TagCategory FROM Tags ORDER BY TagName COLLATE NOCASE"
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(query).fetchall()
                results = [self._row_to_tag(row) for row in rows]
                logger.debug(f"[TagRepository] <- get_all() count={len(results)}")
                return results
        except Exception as e:
            logger.error(f"[TagRepository] ERROR: Failed to fetch all tags: {e}")
            raise

    def search(self, query: str) -> List[Tag]:
        """Search tags by name."""
        logger.debug(f"[TagRepository] -> search(q='{query}')")
        sql = """
            SELECT TagID, TagName, TagCategory
            FROM Tags
            WHERE TagName LIKE ? COLLATE NOCASE
            ORDER BY TagName COLLATE NOCASE
        """
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, (f"%{query}%",)).fetchall()
                results = [self._row_to_tag(row) for row in rows]
                logger.debug(
                    f"[TagRepository] <- search(q='{query}') count={len(results)}"
                )
                return results
        except Exception as e:
            logger.error(f"[TagRepository] ERROR: Failed to search tags: {e}")
            raise

    def get_by_id(self, tag_id: int) -> Tag | None:
        """Fetch a single tag by ID."""
        logger.debug(f"[TagRepository] -> get_by_id(id={tag_id})")
        query = "SELECT TagID, TagName, TagCategory FROM Tags WHERE TagID = ?"
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(query, (tag_id,)).fetchone()
                if not row:
                    logger.debug(f"[TagRepository] <- get_by_id(id={tag_id}) NOT_FOUND")
                    return None
                result = self._row_to_tag(row)
                logger.debug(
                    f"[TagRepository] <- get_by_id(id={tag_id}) '{result.name}'"
                )
                return result
        except Exception as e:
            logger.error(f"[TagRepository] ERROR: Failed to fetch tag by ID: {e}")
            raise

    def get_song_ids_by_tag(self, tag_id: int) -> List[int]:
        """Get all song IDs linked to this tag."""
        logger.debug(f"[TagRepository] -> get_song_ids_by_tag(tag_id={tag_id})")
        query = "SELECT SourceID FROM MediaSourceTags WHERE TagID = ?"
        try:
            with self._get_connection() as conn:
                rows = conn.execute(query, (tag_id,)).fetchall()
                song_ids = [row[0] for row in rows]
                logger.debug(
                    f"[TagRepository] <- get_song_ids_by_tag(tag_id={tag_id}) count={len(song_ids)}"
                )
                return song_ids
        except Exception as e:
            logger.error(f"[TagRepository] ERROR: Failed to fetch song IDs by tag: {e}")
            raise

    def _row_to_tag(self, row: Mapping[str, Any]) -> Tag:
        """Map a database row to a Tag Pydantic model."""
        return Tag(
            id=row["TagID"],
            name=row["TagName"],
            category=row["TagCategory"],
            is_primary=bool(row["IsPrimary"]) if "IsPrimary" in row.keys() else False,
        )
