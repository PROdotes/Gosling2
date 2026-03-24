from typing import Optional, Mapping, Any
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
                model.processing_status if model.processing_status is not None else 1,
            ),
        )

        source_id = cursor.lastrowid
        if not source_id:
            logger.error(
                "[MediaSourceRepository] Failed to retrieve lastrowid during insert."
            )
            raise sqlite3.Error("Failed to retrieve SourceID after insert.")

        return source_id

    def get_by_path(self, path: str) -> Optional[MediaSource]:
        """Universal lookup by SourcePath. Returns base MediaSource or None."""
        logger.debug(f"[MediaSourceRepository] -> get_by_path(path='{path}')")
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT SourceID, TypeID, MediaName, SourcePath, SourceDuration, AudioHash, IsActive, ProcessingStatus
                FROM MediaSources
                WHERE SourcePath = ?
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

            logger.info(f"[MediaSourceRepository] <- get_by_path(path='{path}') NOT_FOUND")
            return None

    def get_by_hash(self, audio_hash: str) -> Optional[MediaSource]:
        """Universal lookup by AudioHash. Returns base MediaSource or None."""
        logger.debug(f"[MediaSourceRepository] -> get_by_hash(hash='{audio_hash}')")
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT SourceID, TypeID, MediaName, SourcePath, SourceDuration, AudioHash, IsActive, ProcessingStatus
                FROM MediaSources
                WHERE AudioHash = ?
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

    def delete(self, source_id: int, conn: sqlite3.Connection) -> bool:
        """
        Universal hard delete for any MediaSource by ID.
        Triggers CASCADE deletes into extension tables (Songs, etc.).
        Returns True if a record was removed.
        """
        logger.debug(f"[MediaSourceRepository] -> delete(id={source_id})")
        cursor = conn.cursor()

        # Hard Delete from the parent MediaSources table
        cursor.execute("DELETE FROM MediaSources WHERE SourceID = ?", (source_id,))
        count = cursor.rowcount

        if count > 0:
            logger.info(f"[MediaSourceRepository] <- delete(id={source_id}) DELETED")
            return True

        logger.warning(f"[MediaSourceRepository] <- delete(id={source_id}) NOT_FOUND")
        return False
