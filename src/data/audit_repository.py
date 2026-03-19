import sqlite3
from typing import List, Optional
from src.data.base_repository import BaseRepository
from src.models.domain import AuditAction, AuditChange, DeletedRecord
from src.services.logger import logger


class AuditRepository(BaseRepository):
    """Low-level database access for Audit tables (ActionLog, ChangeLog, DeletedRecords)."""

    def get_actions_for_target(self, target_id: int, table: str) -> List[AuditAction]:
        """Fetch high-level events (IMPORT, DELETE) for a specific record."""
        logger.debug(
            f"[AuditRepository] Entry: get_actions_for_target(id={target_id}, table='{table}')"
        )
        query = """
            SELECT ActionID, ActionLogType, TargetTable, ActionTargetID, ActionDetails, ActionTimestamp, UserID, BatchID
            FROM ActionLog
            WHERE ActionTargetID = ? AND TargetTable = ?
            ORDER BY ActionTimestamp DESC
        """
        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (target_id, table))
            rows = cursor.fetchall()
            results = [self._row_to_action(row) for row in rows]
            logger.debug(f"[AuditRepository] Exit: Found {len(results)} actions.")
            return results
        finally:
            conn.close()

    def get_changes_for_record(self, record_id: int, table: str) -> List[AuditChange]:
        """Fetch field-level modifications for a specific record."""
        logger.debug(
            f"[AuditRepository] Entry: get_changes_for_record(id={record_id}, table='{table}')"
        )
        valid_tables = [table]
        if table == "Songs":
            valid_tables.extend(
                [
                    "SongCredits",
                    "SongAlbums",
                    "RecordingPublishers",
                    "MediaSourceTags",
                    "MediaSources",
                ]
            )
        elif table == "Identities":
            valid_tables.extend(["ArtistNames", "GroupMemberships"])
        elif table == "Albums":
            valid_tables.extend(["AlbumCredits", "AlbumPublishers", "SongAlbums"])
        elif table == "Publishers":
            valid_tables.extend(["AlbumPublishers", "RecordingPublishers"])

        placeholders = ",".join(["?"] * len(valid_tables))

        query = f"""
            SELECT LogID, LogTableName, RecordID, LogFieldName, OldValue, NewValue, LogTimestamp, BatchID
            FROM ChangeLog
            WHERE (RecordID = ? OR RecordID LIKE ?)
            AND LogTableName IN ({placeholders})
            ORDER BY LogTimestamp DESC
        """
        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            params = [str(record_id), f"{record_id}-%"] + valid_tables
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            results = [self._row_to_change(row) for row in rows]
            logger.debug(f"[AuditRepository] Exit: Found {len(results)} changes.")
            return results
        finally:
            conn.close()

    def get_deleted_snapshot(
        self, record_id: int, table: str
    ) -> Optional[DeletedRecord]:
        """Fetch the last JSON snapshot of a deleted record."""
        logger.debug(
            f"[AuditRepository] Entry: get_deleted_snapshot(id={record_id}, table='{table}')"
        )
        query = """
            SELECT DeleteID, DeletedFromTable, RecordID, FullSnapshot, DeletedAt, RestoredAt, BatchID
            FROM DeletedRecords
            WHERE RecordID = ? AND DeletedFromTable = ?
            ORDER BY DeletedAt DESC LIMIT 1
        """
        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (record_id, table))
            row = cursor.fetchone()
            if not row:
                logger.debug(
                    f"[AuditRepository] Exit: No snapshot found for ID {record_id} in {table}"
                )
                return None
            result = self._row_to_deleted(row)
            logger.debug(
                f"[AuditRepository] Exit: Returning snapshot from {result.deleted_at}"
            )
            return result
        finally:
            conn.close()

    def _row_to_action(self, row: sqlite3.Row) -> AuditAction:
        return AuditAction(
            id=row["ActionID"],
            action_type=row["ActionLogType"],
            target_table=row["TargetTable"],
            target_id=(
                str(row["ActionTargetID"])
                if row["ActionTargetID"] is not None
                else None
            ),
            details=row["ActionDetails"],
            timestamp=row["ActionTimestamp"],
            user_id=row["UserID"],
            batch_id=row["BatchID"],
        )

    def _row_to_change(self, row: sqlite3.Row) -> AuditChange:
        return AuditChange(
            id=row["LogID"],
            table_name=row["LogTableName"],
            record_id=str(row["RecordID"]),
            field_name=row["LogFieldName"],
            old_value=row["OldValue"],
            new_value=row["NewValue"],
            timestamp=row["LogTimestamp"],
            batch_id=row["BatchID"],
        )

    def _row_to_deleted(self, row: sqlite3.Row) -> DeletedRecord:
        return DeletedRecord(
            id=row["DeleteID"],
            table_name=row["DeletedFromTable"],
            record_id=str(row["RecordID"]),
            snapshot=row["FullSnapshot"],
            deleted_at=row["DeletedAt"],
            restored_at=row["RestoredAt"],
            batch_id=row["BatchID"],
        )
