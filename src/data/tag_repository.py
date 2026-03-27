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
            WHERE mst.SourceID IN ({placeholders}) AND t.IsDeleted = 0
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
            tag_id = self.get_or_create_tag(tag.name, tag.category, cursor)
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
        query = "SELECT TagID, TagName, TagCategory FROM Tags WHERE IsDeleted = 0 ORDER BY TagName COLLATE NOCASE"
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
            WHERE TagName LIKE ? COLLATE NOCASE AND IsDeleted = 0
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
        query = "SELECT TagID, TagName, TagCategory FROM Tags WHERE TagID = ? AND IsDeleted = 0"
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

    def get_or_create_tag(self, name: str, category: str, cursor) -> int:
        """Get-or-create a Tag by name+category. Reactivates soft-deleted. Returns tag_id."""
        row = cursor.execute(
            "SELECT TagID, IsDeleted FROM Tags WHERE TagName = ? COLLATE UTF8_NOCASE AND TagCategory IS ?",
            (name, category),
        ).fetchone()
        if row:
            tag_id = row[0]
            if row[1]:
                cursor.execute("UPDATE Tags SET IsDeleted = 0 WHERE TagID = ?", (tag_id,))
            return tag_id
        cursor.execute("INSERT INTO Tags (TagName, TagCategory) VALUES (?, ?)", (name, category))
        return cursor.lastrowid

    def add_tag(self, source_id: int, name: str, category: str, conn: sqlite3.Connection) -> Tag:
        """
        Add a tag to a song. Get-or-creates the Tag record.
        Returns the Tag. Does NOT commit.
        """
        logger.debug(f"[TagRepository] -> add_tag(source_id={source_id}, name='{name}', category='{category}')")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        tag_id = self.get_or_create_tag(name, category, cursor)
        cursor.execute(
            "INSERT OR IGNORE INTO MediaSourceTags (SourceID, TagID, IsPrimary) VALUES (?, ?, 0)",
            (source_id, tag_id),
        )
        row = cursor.execute(
            "SELECT TagID, TagName, TagCategory FROM Tags WHERE TagID = ?", (tag_id,)
        ).fetchone()
        logger.debug(f"[TagRepository] <- add_tag() tag_id={tag_id}")
        return self._row_to_tag(row)

    def remove_tag(self, source_id: int, tag_id: int, conn: sqlite3.Connection) -> None:
        """
        Remove a tag link from a song. Keeps Tag record.
        Does NOT commit.
        """
        logger.debug(f"[TagRepository] -> remove_tag(source_id={source_id}, tag_id={tag_id})")
        conn.cursor().execute(
            "DELETE FROM MediaSourceTags WHERE SourceID = ? AND TagID = ?", (source_id, tag_id)
        )
        logger.debug(f"[TagRepository] <- remove_tag() done")

    def update_tag(self, tag_id: int, name: str, category: str, conn: sqlite3.Connection) -> None:
        """
        Update a Tag's name and category globally. Affects all songs linked to this tag.
        Does NOT commit.
        """
        logger.debug(f"[TagRepository] -> update_tag(tag_id={tag_id}, name='{name}', category='{category}')")
        conn.cursor().execute(
            "UPDATE Tags SET TagName = ?, TagCategory = ? WHERE TagID = ?", (name, category, tag_id)
        )
        logger.debug(f"[TagRepository] <- update_tag() done")

    def _row_to_tag(self, row: Mapping[str, Any]) -> Tag:
        """Map a database row to a Tag Pydantic model."""
        return Tag(
            id=row["TagID"],
            name=row["TagName"],
            category=row["TagCategory"],
            is_primary=bool(row["IsPrimary"]) if "IsPrimary" in row.keys() else False,
        )
