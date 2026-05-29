from typing import Optional
import sqlite3

from src.data.media_source_repository import MediaSourceRepository
from src.models.domain import MediaSource
from src.services.logger import logger
from src.utils.text import normalize_for_search


class MediaSourceService:
    """Specialized orchestrator for MediaSource operations with normalized search fields."""

    def __init__(
        self, db_path: str, media_source_repo: Optional[MediaSourceRepository] = None
    ):
        self._db_path = db_path
        self._media_source_repo = media_source_repo or MediaSourceRepository(db_path)

    def insert_source(
        self, model: MediaSource, type_name: str, conn: sqlite3.Connection
    ) -> int:
        """
        Insert a media source with normalized MediaName_Search.
        Returns the new SourceID.
        """
        logger.debug(
            f"[MediaSourceService] -> insert_source(name='{model.media_name}', type='{type_name}')"
        )

        # Normalize MediaName for search before inserting
        media_name_search = (
            normalize_for_search(model.media_name) if model.media_name else None
        )

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO MediaSources
                (TypeID, MediaName, MediaName_Search, SourcePath, SourceDuration, AudioHash, IsActive, ProcessingStatus, SourceNotes)
            VALUES
                ((SELECT TypeID FROM Types WHERE TypeName = ?), ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                type_name,
                model.media_name,
                media_name_search,
                model.source_path,
                model.duration_s,
                model.audio_hash,
                1 if model.is_active else 0,
                model.processing_status if model.processing_status is not None else 2,
                model.notes,
            ),
        )

        source_id = cursor.lastrowid
        if not source_id:
            logger.error("[MediaSourceService] <- insert_source() FAILED_TO_GET_ID")
            raise sqlite3.Error("Failed to retrieve SourceID after insert.")

        logger.info(
            f"[MediaSourceService] <- insert_source() SourceID={source_id} '{model.media_name}'"
        )
        return int(source_id)

    def reactivate_source(
        self, source_id: int, model: MediaSource, conn: sqlite3.Connection
    ) -> None:
        """
        Reactivate a soft-deleted MediaSource record with normalized MediaName_Search.
        Delegates to repo after normalizing search field.
        """
        logger.debug(
            f"[MediaSourceService] -> reactivate_source(id={source_id}, name='{model.media_name}')"
        )

        # Normalize MediaName for search before updating
        media_name_search = (
            normalize_for_search(model.media_name) if model.media_name else None
        )

        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE MediaSources
            SET MediaName = ?,
                MediaName_Search = ?,
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
                media_name_search,
                model.source_path,
                model.duration_s,
                model.audio_hash,
                1 if model.is_active else 0,
                model.processing_status if model.processing_status is not None else 1,
                source_id,
            ),
        )

        logger.debug(
            f"[MediaSourceService] <- reactivate_source(id={source_id}) UPDATED"
        )
