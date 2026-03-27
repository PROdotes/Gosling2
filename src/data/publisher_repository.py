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
        logger.debug(
            f"[PublisherRepository] -> get_publishers_for_albums(count={len(album_ids)})"
        )
        if not album_ids:
            return []

        placeholders = ",".join(["?" for _ in album_ids])
        query = f"""
            SELECT ap.AlbumID, {self._COLUMNS}
            FROM AlbumPublishers ap
            JOIN Publishers p ON ap.PublisherID = p.PublisherID
            WHERE ap.AlbumID IN ({placeholders}) AND p.IsDeleted = 0
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, album_ids).fetchall()
            result = [(row["AlbumID"], self._row_to_publisher(row)) for row in rows]
            logger.debug(
                f"[PublisherRepository] <- get_publishers_for_albums() count={len(result)}"
            )
            return result

    def get_publishers_for_songs(
        self, song_ids: List[int]
    ) -> List[Tuple[int, Publisher]]:
        """Batch-fetch master publishers for a list of Songs (M2M)."""
        logger.debug(
            f"[PublisherRepository] -> get_publishers_for_songs(count={len(song_ids)})"
        )
        if not song_ids:
            return []

        placeholders = ",".join(["?" for _ in song_ids])
        query = f"""
            SELECT rp.SourceID, {self._COLUMNS}
            FROM RecordingPublishers rp
            JOIN Publishers p ON rp.PublisherID = p.PublisherID
            WHERE rp.SourceID IN ({placeholders}) AND p.IsDeleted = 0
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, song_ids).fetchall()
            result = [(row["SourceID"], self._row_to_publisher(row)) for row in rows]
            logger.debug(
                f"[PublisherRepository] <- get_publishers_for_songs() count={len(result)}"
            )
            return result

    def get_publishers(self, publisher_ids: List[int]) -> Dict[int, Publisher]:
        """Resolve a flat list of ID -> Publisher objects."""
        logger.debug(
            f"[PublisherRepository] -> get_publishers(count={len(publisher_ids)})"
        )
        if not publisher_ids:
            return {}

        placeholders = ",".join(["?" for _ in publisher_ids])
        query = f"SELECT {self._COLUMNS_NO_ALIAS} FROM Publishers WHERE PublisherID IN ({placeholders}) AND IsDeleted = 0"

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, publisher_ids).fetchall()
            result = {row["PublisherID"]: self._row_to_publisher(row) for row in rows}
            logger.debug(
                f"[PublisherRepository] <- get_publishers() resolved={len(result)}"
            )
            return result

    def get_all(self) -> List[Publisher]:
        """Fetch the full directory of active publishers."""
        logger.debug("[PublisherRepository] -> get_all()")
        query = f"SELECT {self._COLUMNS_NO_ALIAS} FROM Publishers WHERE IsDeleted = 0 ORDER BY PublisherName"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
            result = [self._row_to_publisher(row) for row in rows]
            logger.debug(f"[PublisherRepository] <- get_all() count={len(result)}")
            return result

    def search(self, query: str) -> List[Publisher]:
        """Surface search for publishers by name match only."""
        logger.debug(f"[PublisherRepository] -> search(q='{query}')")
        query_sql = f"SELECT {self._COLUMNS_NO_ALIAS} FROM Publishers WHERE PublisherName LIKE ? AND IsDeleted = 0 ORDER BY PublisherName"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, (f"%{query}%",)).fetchall()
            result = [self._row_to_publisher(row) for row in rows]
            logger.debug(
                f"[PublisherRepository] <- search(q='{query}') found {len(result)}"
            )
            return result

    def search_deep(self, query: str) -> List[Publisher]:
        """
        Deep search for publishers by name match, including all descendants.
        Used by the deep song search expansion leg only.
        Uses a recursive CTE to find the corporate tree for any matching seeds.
        """
        logger.debug(f"[PublisherRepository] -> search_deep(q='{query}')")
        query_sql = f"""
            WITH RECURSIVE Descendants({self._COLUMNS_NO_ALIAS}) AS (
                SELECT {self._COLUMNS_NO_ALIAS}
                FROM Publishers
                WHERE PublisherName LIKE ? AND IsDeleted = 0
                UNION
                SELECT {self._COLUMNS}
                FROM Publishers p
                JOIN Descendants d ON p.ParentPublisherID = d.PublisherID
                WHERE p.IsDeleted = 0
            )
            SELECT DISTINCT {self._COLUMNS_NO_ALIAS} FROM Descendants ORDER BY PublisherName;
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, (f"%{query}%",)).fetchall()
            result = [self._row_to_publisher(row) for row in rows]
            logger.debug(
                f"[PublisherRepository] <- search_deep(q='{query}') found {len(result)} total"
            )
            return result

    def get_by_id(self, publisher_id: int) -> Optional[Publisher]:
        """Fetch a single publisher by its ID."""
        logger.debug(f"[PublisherRepository] -> get_by_id(id={publisher_id})")
        results = self.get_by_ids([publisher_id])
        if results:
            res = results[0]
            logger.debug(
                f"[PublisherRepository] <- get_by_id(id={publisher_id}) '{res.name}'"
            )
            return res
        logger.warning(
            f"[PublisherRepository] <- get_by_id(id={publisher_id}) NOT_FOUND"
        )
        return None

    def get_by_ids(self, ids: List[int]) -> List[Publisher]:
        """Batch-fetch multiple publishers by ID."""
        logger.debug(f"[PublisherRepository] -> get_by_ids(count={len(ids)})")
        if not ids:
            return []
        placeholders = ",".join(["?" for _ in ids])
        query = f"SELECT {self._COLUMNS_NO_ALIAS} FROM Publishers WHERE PublisherID IN ({placeholders}) AND IsDeleted = 0"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, ids).fetchall()
            result = [self._row_to_publisher(row) for row in rows]
            logger.debug(f"[PublisherRepository] <- get_by_ids() count={len(result)}")
            return result

    def get_hierarchy_batch(self, publisher_ids: List[int]) -> Dict[int, Publisher]:
        """
        RESOLVER: Fetches the entire ancestry chain for a list of publishers in a SINGLE query.
        Uses a recursive Common Table Expression (CTE).
        """
        logger.debug(
            f"[PublisherRepository] -> get_hierarchy_batch(count={len(publisher_ids)})"
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
                WHERE p.IsDeleted = 0
            )
            SELECT * FROM Ancestry;
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, publisher_ids).fetchall()
            result = {row["PublisherID"]: self._row_to_publisher(row) for row in rows}
            logger.debug(
                f"[PublisherRepository] <- get_hierarchy_batch() resolved={len(result)} ancestors"
            )
            return result

    def get_children(self, parent_id: int) -> List[Publisher]:
        """Fetch all sub-publishers for a given parent."""
        logger.debug(f"[PublisherRepository] -> get_children(parent_id={parent_id})")
        query = f"SELECT {self._COLUMNS_NO_ALIAS} FROM Publishers WHERE ParentPublisherID = ? AND IsDeleted = 0"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, (parent_id,)).fetchall()
            result = [self._row_to_publisher(row) for row in rows]
            logger.debug(f"[PublisherRepository] <- get_children() count={len(result)}")
            return result

    def get_song_ids_by_publisher(self, publisher_id: int) -> List[int]:
        """Find all song IDs explicitly linked to this publisher (Master)."""
        logger.debug(
            f"[PublisherRepository] -> get_song_ids_by_publisher(id={publisher_id})"
        )
        query = "SELECT SourceID FROM RecordingPublishers WHERE PublisherID = ?"
        with self._get_connection() as conn:
            rows = conn.execute(query, (publisher_id,)).fetchall()
            result = [row[0] for row in rows]
            logger.debug(
                f"[PublisherRepository] <- get_song_ids_by_publisher() count={len(result)}"
            )
            return result

    def get_song_ids_by_publisher_batch(self, publisher_ids: List[int]) -> List[int]:
        """Find all song IDs explicitly linked to any of these publishers."""
        logger.debug(
            f"[PublisherRepository] -> get_song_ids_by_publisher_batch(count={len(publisher_ids)})"
        )
        if not publisher_ids:
            return []

        placeholders = ",".join(["?" for _ in publisher_ids])
        query = f"SELECT DISTINCT SourceID FROM RecordingPublishers WHERE PublisherID IN ({placeholders})"
        with self._get_connection() as conn:
            rows = conn.execute(query, publisher_ids).fetchall()
            result = [row[0] for row in rows]
            logger.debug(
                f"[PublisherRepository] <- get_song_ids_by_publisher_batch() count={len(result)}"
            )
            return result

    def insert_song_publishers(
        self, source_id: int, publishers: List[Publisher], conn: sqlite3.Connection
    ) -> None:
        """Get-or-create Publishers rows (case-insensitive), then insert RecordingPublishers links."""
        logger.debug(
            f"[PublisherRepository] -> insert_song_publishers(source_id={source_id}, count={len(publishers)})"
        )
        if not publishers:
            logger.debug(
                "[PublisherRepository] <- insert_song_publishers() empty list, no-op"
            )
            return

        cursor = conn.cursor()
        for pub in publishers:
            pub_id = self.get_or_create_publisher(pub.name, cursor)
            cursor.execute(
                "INSERT INTO RecordingPublishers (SourceID, PublisherID) VALUES (?, ?)",
                (source_id, pub_id),
            )

        logger.info(
            f"[PublisherRepository] <- insert_song_publishers(source_id={source_id}) wrote {len(publishers)} publishers"
        )

    def get_or_create_publisher(self, name: str, cursor) -> int:
        """Get-or-create a Publisher by name. Reactivates soft-deleted. Returns publisher_id."""
        row = cursor.execute(
            "SELECT PublisherID, IsDeleted FROM Publishers WHERE PublisherName = ? COLLATE UTF8_NOCASE",
            (name,),
        ).fetchone()
        if row:
            pub_id = row[0]
            if row[1]:
                cursor.execute(
                    "UPDATE Publishers SET IsDeleted = 0 WHERE PublisherID = ?",
                    (pub_id,),
                )
            return pub_id
        cursor.execute("INSERT INTO Publishers (PublisherName) VALUES (?)", (name,))
        return cursor.lastrowid

    def add_song_publisher(
        self, source_id: int, name: str, conn: sqlite3.Connection
    ) -> Publisher:
        """
        Add a publisher link to a song. Get-or-creates the Publisher record.
        Returns the Publisher. Does NOT commit.
        """
        logger.debug(
            f"[PublisherRepository] -> add_song_publisher(source_id={source_id}, name='{name}')"
        )
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        pub_id = self.get_or_create_publisher(name, cursor)
        cursor.execute(
            "INSERT OR IGNORE INTO RecordingPublishers (SourceID, PublisherID) VALUES (?, ?)",
            (source_id, pub_id),
        )
        row = cursor.execute(
            "SELECT PublisherID, PublisherName, ParentPublisherID FROM Publishers WHERE PublisherID = ?",
            (pub_id,),
        ).fetchone()
        logger.debug(f"[PublisherRepository] <- add_song_publisher() pub_id={pub_id}")
        return self._row_to_publisher(row)

    def remove_song_publisher(
        self, source_id: int, publisher_id: int, conn: sqlite3.Connection
    ) -> None:
        """
        Remove a publisher link from a song. Keeps Publisher record.
        Does NOT commit.
        """
        logger.debug(
            f"[PublisherRepository] -> remove_song_publisher(source_id={source_id}, publisher_id={publisher_id})"
        )
        conn.cursor().execute(
            "DELETE FROM RecordingPublishers WHERE SourceID = ? AND PublisherID = ?",
            (source_id, publisher_id),
        )
        logger.debug("[PublisherRepository] <- remove_song_publisher() done")

    def update_publisher(
        self, publisher_id: int, name: str, conn: sqlite3.Connection
    ) -> None:
        """
        Update a Publisher's name globally. Affects all songs linked to this publisher.
        Does NOT commit.
        """
        logger.debug(
            f"[PublisherRepository] -> update_publisher(publisher_id={publisher_id}, name='{name}')"
        )
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Publishers SET PublisherName = ? WHERE PublisherID = ?",
            (name, publisher_id),
        )
        if cursor.rowcount == 0:
            logger.warning(
                f"[PublisherRepository] update_publisher(id={publisher_id}) NOT_FOUND"
            )
            raise LookupError(f"Publisher {publisher_id} not found")
        logger.debug("[PublisherRepository] <- update_publisher() done")

    def _row_to_publisher(self, row: Mapping[str, Any]) -> Publisher:
        """Map a database row to a Publisher Pydantic model."""
        return Publisher(
            id=row["PublisherID"],
            name=row["PublisherName"],
            parent_id=row["ParentPublisherID"],
        )
