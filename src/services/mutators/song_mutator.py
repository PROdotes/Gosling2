import sqlite3
from uuid import UUID


class SongMutator:
    def apply_within(self, action: str, item, conn: sqlite3.Connection, batch_id: UUID) -> None:
        pass
