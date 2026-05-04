import sqlite3
from uuid import UUID

from src.data.publisher_repository import PublisherRepository
from src.engine.routers.mutation_models import (
    AddPublisherItem,
    RemovePublisherItem,
    UpdatePublisherEntityItem,
)


class PublisherMutator:
    def __init__(self, db_path: str):
        self._repo = PublisherRepository(db_path)

    def apply_within(self, action: str, item, conn: sqlite3.Connection, batch_id: UUID) -> None:
        if action == "add":
            self._add(item, conn)
        elif action == "remove":
            self._remove(item, conn)
        elif action == "update":
            self._update(item, conn)
        else:
            raise ValueError(f"PublisherMutator does not support action '{action}'")

    def _add(self, item: AddPublisherItem, conn: sqlite3.Connection) -> None:
        if item.song_id is not None:
            self._repo.add_song_publisher(item.song_id, item.name, conn, publisher_id=item.id)
        else:
            self._repo.add_album_publisher(item.album_id, item.name, conn, publisher_id=item.id)

    def _remove(self, item: RemovePublisherItem, conn: sqlite3.Connection) -> None:
        if item.song_id is not None:
            self._repo.remove_song_publisher(item.song_id, item.id, conn)
        else:
            self._repo.remove_album_publisher(item.album_id, item.id, conn)

    def _update(self, item: UpdatePublisherEntityItem, conn: sqlite3.Connection) -> None:
        if item.name is not None:
            self._repo.update_publisher(item.id, item.name, conn)
        if item.parent_id is not None or (item.model_fields_set and "parent_id" in item.model_fields_set):
            self._repo.set_parent(item.id, item.parent_id, conn)
