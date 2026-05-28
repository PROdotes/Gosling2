import sqlite3

from src.data.base_repository import BaseRepository


class AuditRepository(BaseRepository):
    def flush_batch(self, batch_id: str, conn: sqlite3.Connection) -> None:
        # TODO: UPDATE ChangeLog SET batch_id = ? WHERE batch_id IS NULL
        pass
