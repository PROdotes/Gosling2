import sqlite3
from uuid import UUID

from src.data.song_repository import SongRepository
from src.engine.routers.mutation_models import UpdateSongItem


class SongMutator:
    def __init__(self, db_path: str):
        self._repo = SongRepository(db_path)

    def apply_within(self, action: str, item: UpdateSongItem, conn: sqlite3.Connection, batch_id: UUID) -> None:
        if action != "update":
            raise ValueError(f"SongMutator does not support action '{action}'")

        fields = item.model_dump(exclude={"type", "id"}, exclude_unset=True)
        if not fields:
            return

        updated = self._repo.update_scalars(item.id, fields, conn)
        if updated == 0:
            raise LookupError(f"Song {item.id} not found")
