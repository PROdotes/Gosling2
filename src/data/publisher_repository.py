import sqlite3
from typing import List, Dict, Tuple, Optional, Mapping, Any
from src.data.base_repository import BaseRepository
from src.models.domain import Publisher
from src.services.logger import logger


class PublisherRepository(BaseRepository):
    """Repository for loading Publisher metadata for Albums and Tracks."""

    _COLUMNS = "p.PublisherID, p.PublisherName, p.ParentPublisherID"
    _COLUMNS_NO_ALIAS = "PublisherID, PublisherName, ParentPublisherID"

    def get_publishers_for_albums(
        self, album_ids: List[int]
    ) -> List[Tuple[int, Publisher]]:
        """Batch-fetch publisher objects for a list of Albums (M2M)."""
        logger.info(
            f"[PublisherRepository] Entry: get_publishers_for_albums(ids={len(album_ids)})"
        )
        if not album_ids:
            return []

        placeholders = ",".join(["?" for _ in album_ids])
        query = f"""
            SELECT ap.AlbumID, {self._COLUMNS}
            FROM AlbumPublishers ap
            JOIN Publishers p ON ap.PublisherID = p.PublisherID
            WHERE ap.AlbumID IN ({placeholders})
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, album_ids).fetchall()
            result = [(row["AlbumID"], self._row_to_publisher(row)) for row in rows]
            logger.info(
                f"[PublisherRepository] Exit: Found {len(result)} associations."
            )
            return result

    def get_publishers_for_songs(
        self, song_ids: List[int]
    ) -> List[Tuple[int, Publisher]]:
        """Batch-fetch master publishers for a list of Songs (M2M)."""
        logger.info(
            f"[PublisherRepository] Entry: get_publishers_for_songs(ids={len(song_ids)})"
        )
        if not song_ids:
            return []

        placeholders = ",".join(["?" for _ in song_ids])
        query = f"""
            SELECT rp.SourceID, {self._COLUMNS}
            FROM RecordingPublishers rp
            JOIN Publishers p ON rp.PublisherID = p.PublisherID
            WHERE rp.SourceID IN ({placeholders})
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, song_ids).fetchall()
            result = [(row["SourceID"], self._row_to_publisher(row)) for row in rows]
            logger.info(
                f"[PublisherRepository] Exit: Found {len(result)} associations."
            )
            return result

    def get_publishers(self, publisher_ids: List[int]) -> Dict[int, Publisher]:
        """Resolve a flat list of ID -> Publisher objects."""
        logger.info(
            f"[PublisherRepository] Entry: get_publishers(ids={len(publisher_ids)})"
        )
        if not publisher_ids:
            return {}

        placeholders = ",".join(["?" for _ in publisher_ids])
        query = f"SELECT {self._COLUMNS_NO_ALIAS} FROM Publishers WHERE PublisherID IN ({placeholders})"

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, publisher_ids).fetchall()
            result = {row["PublisherID"]: self._row_to_publisher(row) for row in rows}
            logger.info(
                f"[PublisherRepository] Exit: Resolved {len(result)} publishers."
            )
            return result

    def get_all(self) -> List[Publisher]:
        """Fetch the full directory of active publishers."""
        logger.info("[PublisherRepository] Entry: get_all()")
        query = (
            f"SELECT {self._COLUMNS_NO_ALIAS} FROM Publishers ORDER BY PublisherName"
        )
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
            result = [self._row_to_publisher(row) for row in rows]
            logger.info(f"[PublisherRepository] Exit: Found {len(result)} publishers.")
            return result

    def search(self, query: str) -> List[Publisher]:
        """Search for publishers by name match."""
        logger.info(f"[PublisherRepository] Entry: search(query='{query}')")
        sql = f"SELECT {self._COLUMNS_NO_ALIAS} FROM Publishers WHERE PublisherName LIKE ? ORDER BY PublisherName"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, (f"%{query}%",)).fetchall()
            result = [self._row_to_publisher(row) for row in rows]
            logger.info(f"[PublisherRepository] Exit: Found {len(result)} results.")
            return result

    def get_by_id(self, publisher_id: int) -> Optional[Publisher]:
        """Fetch a single publisher by its ID."""
        logger.info(f"[PublisherRepository] Entry: get_by_id(id={publisher_id})")
        results = self.get_by_ids([publisher_id])
        if results:
            res = results[0]
            logger.debug(f"[PublisherRepository] Exit: Found '{res.name}'")
            return res
        logger.warning(f"[PublisherRepository] Exit: ID {publisher_id} NOT_FOUND")
        return None

    def get_by_ids(self, ids: List[int]) -> List[Publisher]:
        """Batch-fetch multiple publishers by ID."""
        logger.info(f"[PublisherRepository] Entry: get_by_ids(count={len(ids)})")
        if not ids:
            return []
        placeholders = ",".join(["?" for _ in ids])
        query = f"SELECT {self._COLUMNS_NO_ALIAS} FROM Publishers WHERE PublisherID IN ({placeholders})"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, ids).fetchall()
            result = [self._row_to_publisher(row) for row in rows]
            logger.debug(f"[PublisherRepository] Exit: Found {len(result)} matches.")
            return result

    def get_hierarchy_batch(self, publisher_ids: List[int]) -> Dict[int, Publisher]:
        """
        RESOLVER: Fetches the entire ancestry chain for a list of publishers in a SINGLE query.
        Uses a recursive Common Table Expression (CTE).
        """
        logger.info(
            f"[PublisherRepository] Entry: get_hierarchy_batch(ids={len(publisher_ids)})"
        )
        if not publisher_ids:
            return {}

        placeholders = ",".join(["?" for _ in publisher_ids])
        query = f"""
            WITH RECURSIVE Ancestry({self._COLUMNS_NO_ALIAS}) AS (
                -- Base Case (Seeds)
                SELECT {self._COLUMNS_NO_ALIAS}
                FROM Publishers
                WHERE PublisherID IN ({placeholders})
                
                UNION
                
                -- Recursive Step
                SELECT {self._COLUMNS}
                FROM Publishers p
                JOIN Ancestry a ON p.PublisherID = a.ParentPublisherID
            )
            SELECT * FROM Ancestry;
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, publisher_ids).fetchall()
            result = {row["PublisherID"]: self._row_to_publisher(row) for row in rows}
            logger.info(
                f"[PublisherRepository] Exit: Resolved {len(result)} ancestors."
            )
            return result

    def get_children(self, parent_id: int) -> List[Publisher]:
        """Fetch all sub-publishers for a given parent."""
        logger.info(f"[PublisherRepository] Entry: get_children(id={parent_id})")
        query = f"SELECT {self._COLUMNS_NO_ALIAS} FROM Publishers WHERE ParentPublisherID = ?"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, (parent_id,)).fetchall()
            result = [self._row_to_publisher(row) for row in rows]
            logger.info(f"[PublisherRepository] Exit: Found {len(result)} children.")
            return result

    def get_song_ids_by_publisher(self, publisher_id: int) -> List[int]:
        """Find all song IDs explicitly linked to this publisher (Master)."""
        logger.info(
            f"[PublisherRepository] Entry: get_song_ids_by_publisher(id={publisher_id})"
        )
        query = "SELECT SourceID FROM RecordingPublishers WHERE PublisherID = ?"
        with self._get_connection() as conn:
            rows = conn.execute(query, (publisher_id,)).fetchall()
            result = [row[0] for row in rows]
            logger.info(f"[PublisherRepository] Exit: Found {len(result)} songs.")
            return result

    def _row_to_publisher(self, row: Mapping[str, Any]) -> Publisher:
        """Map a database row to a Publisher Pydantic model."""
        return Publisher(
            id=row["PublisherID"],
            name=row["PublisherName"],
            parent_id=row["ParentPublisherID"],
        )
