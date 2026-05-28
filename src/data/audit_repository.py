import sqlite3

from src.data.base_repository import BaseRepository
from src.services.logger import logger


class AuditRepository(BaseRepository):
    def flush_batch(self, batch_id: str, label: str, conn: sqlite3.Connection) -> None:
        cursor = conn.execute(
            "UPDATE ChangeLog SET batch_id = ?, batch_label = ? WHERE batch_id IS NULL",
            (batch_id, label),
        )
        logger.debug(
            f"[AuditRepository] flush_batch label={label} batch={batch_id} rows={cursor.rowcount}"
        )
