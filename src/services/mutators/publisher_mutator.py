import sqlite3
from typing import Union

from src.data.publisher_repository import PublisherRepository
from src.engine.routers.mutation_models import (
    AddPublisherItem,
    RemovePublisherItem,
    UpdatePublisherEntityItem,
)


class PublisherMutator:
    def __init__(self, db_path: str):
        self._repo = PublisherRepository(db_path)

    def apply_within(
        self,
        action: str,
        item: Union[AddPublisherItem, RemovePublisherItem, UpdatePublisherEntityItem],
        conn: sqlite3.Connection,
    ) -> None:
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
            self._repo.add_song_publisher(
                item.song_id, item.name, conn, publisher_id=item.id
            )
        else:
            self._repo.add_album_publisher(
                item.album_id, item.name, conn, publisher_id=item.id
            )

    def _remove(self, item: RemovePublisherItem, conn: sqlite3.Connection) -> None:
        if item.song_id is not None:
            removed = self._repo.remove_song_publisher(item.song_id, item.id, conn)
        else:
            removed = self._repo.remove_album_publisher(item.album_id, item.id, conn)
        if removed == 0:
            raise LookupError(f"Publisher {item.id} not linked")

    def merge_within(
        self, source_id: int, target_id: int, conn: sqlite3.Connection
    ) -> None:
        source = self._repo.get_by_id(source_id, conn)
        if source is None:
            raise LookupError(f"Publisher {source_id} not found")
        if source.parent_id is not None:
            raise ValueError(f"Publisher {source_id} has a parent — hierarchy merge not supported yet")
        if self._repo.get_children(source_id, conn):
            raise ValueError(f"Publisher {source_id} has children — hierarchy merge not supported yet")
        self._repo.merge_into(source_id, target_id, conn)

    def _update(
        self, item: UpdatePublisherEntityItem, conn: sqlite3.Connection
    ) -> None:
        fields = item.model_dump(exclude={"type", "id"}, exclude_unset=True)
        if not fields:
            return
        if "name" in fields:
            existing_id = self._repo.find_by_name(item.name, conn)
            if existing_id is not None and existing_id != item.id:
                raise ValueError(f"MERGE_REQUIRED:publisher:{existing_id}")
            updated = self._repo.update_publisher(item.id, item.name, conn)
            if updated == 0:
                raise LookupError(f"Publisher {item.id} not found")
        if "parent_id" in fields:
            updated = self._repo.set_parent(item.id, item.parent_id, conn)
            if updated == 0:
                raise LookupError(f"Publisher {item.id} not found")
