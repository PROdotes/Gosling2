from typing import Optional, Mapping, Any, Dict
import sqlite3
from src.models.domain import MediaSource
from src.data.base_repository import BaseRepository
from src.services.logger import logger


class MediaSourceRepository(BaseRepository):
    """The universal repository for any MediaSource record."""

    def insert_source(
        self, model: MediaSource, type_name: str, conn: sqlite3.Connection
    ) -> int:
        """
        Inserts the core record into MediaSources table.
        type_name: "Song", "Podcast", etc.
        Returns the new SourceID.
        """
        logger.debug(
            f"[MediaSourceRepository] -> insert_source(name='{model.media_name}', type='{type_name}')"
        )
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO MediaSources 
                (TypeID, MediaName, SourcePath, SourceDuration, AudioHash, IsActive, ProcessingStatus)
            VALUES 
                ((SELECT TypeID FROM Types WHERE TypeName = ?), ?, ?, ?, ?, ?, ?)
            """,
            (
                type_name,
                model.media_name,
                model.source_path,
                model.duration_s,
                model.audio_hash,
                1 if model.is_active else 0,
                model.processing_status if model.processing_status is not None else 2,
            ),
        )

        source_id = cursor.lastrowid
        if not source_id:
            logger.error("[MediaSourceRepository] <- insert_source() FAILED_TO_GET_ID")
            raise sqlite3.Error("Failed to retrieve SourceID after insert.")

        logger.debug(
            f"[MediaSourceRepository] <- insert_source() SourceID={source_id} (Virgin=2)"
        )
        return int(source_id)

    def get_by_path(self, path: str) -> Optional[MediaSource]:
        """Universal lookup by SourcePath. Returns base MediaSource or None."""
        logger.debug(f"[MediaSourceRepository] -> get_by_path(path='{path}')")
        conn = self.get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT SourceID, TypeID, MediaName, SourcePath, SourceDuration, AudioHash, IsActive, ProcessingStatus
                FROM MediaSources
                WHERE SourcePath = ? AND IsDeleted = 0
            """,
                (path,),
            )
            row = cursor.fetchone()

            if row:
                source = self._row_to_source(row)
                logger.info(
                    f"[MediaSourceRepository] <- get_by_path(path='{path}') FOUND id={source.id}"
                )
                return source

            logger.info(
                f"[MediaSourceRepository] <- get_by_path(path='{path}') NOT_FOUND"
            )
            return None
        finally:
            conn.close()

    def get_by_hash(self, audio_hash: str) -> Optional[MediaSource]:
        """Universal lookup by AudioHash. Returns base MediaSource or None."""
        logger.debug(f"[MediaSourceRepository] -> get_by_hash(hash='{audio_hash}')")
        conn = self.get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT SourceID, TypeID, MediaName, SourcePath, SourceDuration, AudioHash, IsActive, ProcessingStatus
                FROM MediaSources
                WHERE AudioHash = ? AND IsDeleted = 0
            """,
                (audio_hash,),
            )
            row = cursor.fetchone()

            if row:
                source = self._row_to_source(row)
                logger.info(
                    f"[MediaSourceRepository] <- get_by_hash(hash='{audio_hash}') FOUND id={source.id}"
                )
                return source

            logger.info(
                f"[MediaSourceRepository] <- get_by_hash(hash='{audio_hash}') NOT_FOUND"
            )
            return None
        finally:
            conn.close()

    def get_source_metadata_by_hash(self, audio_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves basic metadata for a source by its hash, regardless of its deleted status.
        Used for re-ingestion conflict resolution.
        """
        logger.debug(
            f"[MediaSourceRepository] -> get_source_metadata_by_hash(hash='{audio_hash}')"
        )
        conn = self.get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    ms.SourceID,
                    ms.MediaName,
                    ms.SourceDuration,
                    ms.IsDeleted,
                    s.RecordingYear,
                    s.ISRC
                FROM MediaSources ms
                LEFT JOIN Songs s ON ms.SourceID = s.SourceID
                WHERE ms.AudioHash = ?
            """,
                (audio_hash,),
            )
            row = cursor.fetchone()

            if row:
                return {
                    "id": row["SourceID"],
                    "title": row["MediaName"],
                    "duration_s": float(row["SourceDuration"] or 0),
                    "is_deleted": bool(row["IsDeleted"]),
                    "year": row["RecordingYear"],
                    "isrc": row["ISRC"],
                }

            return None
        finally:
            conn.close()

    def _row_to_source(self, row: Mapping[str, Any]) -> MediaSource:
        """Hydrates a base MediaSource from a raw MediaSources row."""
        return MediaSource(
            id=row["SourceID"],
            type_id=row["TypeID"],
            media_name=row["MediaName"],
            source_path=row["SourcePath"],
            duration_s=float(row["SourceDuration"] or 0),
            audio_hash=row["AudioHash"],
            is_active=bool(row["IsActive"]) if row["IsActive"] is not None else False,
            processing_status=row["ProcessingStatus"],
            notes=None,  # Not in core MediaSources table currently
        )

    def soft_delete(self, source_id: int, conn: sqlite3.Connection) -> bool:
        """
        Soft-delete a MediaSource by setting IsDeleted = 1.
        Returns True if a record was updated, False if not found or already deleted.
        """
        logger.debug(f"[MediaSourceRepository] -> soft_delete(id={source_id})")
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE MediaSources SET IsDeleted = 1 WHERE SourceID = ? AND IsDeleted = 0",
            (source_id,),
        )
        count = cursor.rowcount

        if count > 0:
            logger.info(
                f"[MediaSourceRepository] <- soft_delete(id={source_id}) SOFT_DELETED"
            )
            return True

        logger.warning(
            f"[MediaSourceRepository] <- soft_delete(id={source_id}) NOT_FOUND_OR_ALREADY_DELETED"
        )
        return False

    def delete_song_links(self, source_id: int, conn: sqlite3.Connection) -> None:
        """
        Hard-delete all junction/link rows for a song.
        Must be called before soft_delete since CASCADE won't fire on UPDATE.
        """
        logger.debug(f"[MediaSourceRepository] -> delete_song_links(id={source_id})")
        cursor = conn.cursor()

        link_tables = [
            "SongCredits",
            "SongAlbums",
            "MediaSourceTags",
            "RecordingPublishers",
        ]
        for table in link_tables:
            cursor.execute(f"DELETE FROM {table} WHERE SourceID = ?", (source_id,))
            logger.debug(
                f"[MediaSourceRepository] Deleted {cursor.rowcount} rows from {table}"
            )

        logger.debug(
            f"[MediaSourceRepository] <- delete_song_links(id={source_id}) DONE"
        )

    def hard_delete(self, source_id: int, conn: sqlite3.Connection) -> None:
        """Hard-delete a MediaSource and its Songs row. Use for records that should never have existed."""
        logger.debug(f"[MediaSourceRepository] -> hard_delete(id={source_id})")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Songs WHERE SourceID = ?", (source_id,))
        cursor.execute("DELETE FROM MediaSources WHERE SourceID = ?", (source_id,))
        logger.info(f"[MediaSourceRepository] <- hard_delete(id={source_id}) DONE")

    def reactivate_source(
        self, source_id: int, model: MediaSource, conn: sqlite3.Connection
    ) -> None:
        """
        Reactivate a soft-deleted MediaSource record with new metadata.
        Updates MediaSources table and sets IsDeleted=0.
        """
        logger.debug(
            f"[MediaSourceRepository] -> reactivate_source(id={source_id}, name='{model.media_name}')"
        )
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE MediaSources
            SET MediaName = ?,
                SourcePath = ?,
                SourceDuration = ?,
                AudioHash = ?,
                IsActive = ?,
                ProcessingStatus = ?,
                IsDeleted = 0
            WHERE SourceID = ?
            """,
            (
                model.media_name,
                model.source_path,
                model.duration_s,
                model.audio_hash,
                1 if model.is_active else 0,
                model.processing_status if model.processing_status is not None else 1,
                source_id,
            ),
        )

        logger.debug(
            f"[MediaSourceRepository] <- reactivate_source(id={source_id}) UPDATED"
        )
