import sqlite3

from src.data.song_repository import SongRepository
from src.engine.routers.mutation_models import UpdateSongItem
from src.utils.text import normalize_for_search


class SongMutator:
    def __init__(self, db_path: str):
        self._repo = SongRepository(db_path)

    def apply_within(
        self, action: str, item: UpdateSongItem, conn: sqlite3.Connection
    ) -> None:
        if action != "update":
            raise ValueError(f"SongMutator does not support action '{action}'")

        fields = item.model_dump(exclude={"type", "id"}, exclude_unset=True)
        if not fields:
            return

        if "media_name" in fields:
            raw = fields["media_name"]
            fields["media_name_search"] = (
                normalize_for_search(raw) if raw is not None else None
            )

        updated = self._repo.update_scalars(item.id, fields, conn)
        if updated == 0:
            raise LookupError(f"Song {item.id} not found")
