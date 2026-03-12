import sqlite3
from typing import List
from src.data.base_repository import BaseRepository
from src.models.domain import SongAlbum
from src.services.logger import logger


class SongAlbumRepository(BaseRepository):
    """Repository for loading Album associations for Songs."""

    _QUERY = """
        SELECT sa.SourceID, sa.AlbumID, sa.TrackNumber, sa.DiscNumber, sa.IsPrimary, sa.TrackPublisherID,
               a.AlbumTitle, a.AlbumType, a.ReleaseYear
        FROM SongAlbums sa
        JOIN Albums a ON sa.AlbumID = a.AlbumID
        WHERE sa.SourceID IN ({placeholders})
    """

    def get_albums_for_songs(self, song_ids: List[int]) -> List[SongAlbum]:
        """Batch-fetch album associations for multiple songs."""
        if not song_ids:
            return []

        logger.debug(
            f"[SongAlbumRepository] Batch-fetching albums for {len(song_ids)} songs."
        )
        placeholders = ",".join(["?" for _ in song_ids])
        query = self._QUERY.format(placeholders=placeholders)

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, song_ids).fetchall()
            logger.debug(f"[SongAlbumRepository] Found {len(rows)} album associations.")
            return [self._row_to_song_album(row) for row in rows]

    def _row_to_song_album(self, row: sqlite3.Row) -> SongAlbum:
        """Map a database row to a SongAlbum Pydantic model."""
        return SongAlbum(
            source_id=row["SourceID"],
            album_id=row["AlbumID"],
            track_number=row["TrackNumber"],
            disc_number=row["DiscNumber"],
            is_primary=bool(row["IsPrimary"]),
            track_publisher_id=row["TrackPublisherID"],
            album_title=row["AlbumTitle"],
            album_type=row["AlbumType"],
            release_year=row["ReleaseYear"],
            publishers=[],  # Hydrated later by CatalogService
        )
