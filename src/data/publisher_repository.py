import sqlite3
from typing import List, Dict, Tuple
from src.data.base_repository import BaseRepository
from src.models.domain import Publisher
from src.services.logger import logger


class PublisherRepository(BaseRepository):
    """Repository for loading Publisher metadata for Albums and Tracks."""

    def get_publishers_for_albums(
        self, album_ids: List[int]
    ) -> List[Tuple[int, Publisher]]:
        """Batch-fetch publisher objects for a list of Albums (M2M)."""
        if not album_ids:
            return []

        logger.debug(
            f"[PublisherRepository] Batch-fetching publishers for {len(album_ids)} albums."
        )
        placeholders = ",".join(["?" for _ in album_ids])
        query = f"""
            SELECT ap.AlbumID, p.PublisherID, p.PublisherName, p.ParentPublisherID
            FROM AlbumPublishers ap
            JOIN Publishers p ON ap.PublisherID = p.PublisherID
            WHERE ap.AlbumID IN ({placeholders})
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, album_ids).fetchall()
            logger.debug(
                f"[PublisherRepository] Found {len(rows)} album-publisher associations."
            )
            return [(row["AlbumID"], self._row_to_publisher(row)) for row in rows]

    def get_publishers_for_songs(
        self, song_ids: List[int]
    ) -> List[Tuple[int, Publisher]]:
        """Batch-fetch master publishers for a list of Songs (M2M through RecordingPublishers)."""
        if not song_ids:
            return []

        logger.debug(
            f"[PublisherRepository] Batch-fetching recording publishers for {len(song_ids)} songs."
        )
        placeholders = ",".join(["?" for _ in song_ids])
        query = f"""
            SELECT rp.SourceID, p.PublisherID, p.PublisherName, p.ParentPublisherID
            FROM RecordingPublishers rp
            JOIN Publishers p ON rp.PublisherID = p.PublisherID
            WHERE rp.SourceID IN ({placeholders})
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, song_ids).fetchall()
            logger.debug(
                f"[PublisherRepository] Found {len(rows)} recording-publisher associations."
            )
            return [(row["SourceID"], self._row_to_publisher(row)) for row in rows]

    def get_publishers(self, publisher_ids: List[int]) -> Dict[int, Publisher]:
        """Resolve a flat list of IDs to Publisher objects."""
        if not publisher_ids:
            return {}

        logger.debug(
            f"[PublisherRepository] Resolving {len(publisher_ids)} publisher names."
        )
        placeholders = ",".join(["?" for _ in publisher_ids])
        query = f"SELECT PublisherID, PublisherName, ParentPublisherID FROM Publishers WHERE PublisherID IN ({placeholders})"

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, publisher_ids).fetchall()
            return {row["PublisherID"]: self._row_to_publisher(row) for row in rows}

    def _row_to_publisher(self, row: sqlite3.Row) -> Publisher:
        """Map a database row to a Publisher Pydantic model."""
        return Publisher(
            id=row["PublisherID"],
            name=row["PublisherName"],
            parent_id=row["ParentPublisherID"],
        )
