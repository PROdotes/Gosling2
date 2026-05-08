import sqlite3
from typing import Union

from src.data.album_credit_repository import AlbumCreditRepository
from src.data.song_credit_repository import SongCreditRepository
from src.engine.routers.mutation_models import (
    AddCreditItem,
    RemoveCreditItem,
    UpdateCreditEntityItem,
)


class CreditMutator:
    def __init__(self, db_path: str):
        self._song_repo = SongCreditRepository(db_path)
        self._album_repo = AlbumCreditRepository(db_path)

    def apply_within(
        self,
        action: str,
        item: Union[AddCreditItem, RemoveCreditItem, UpdateCreditEntityItem],
        conn: sqlite3.Connection,
    ) -> None:
        if action == "add":
            self._add(item, conn)
        elif action == "remove":
            self._remove(item, conn)
        elif action == "update":
            self._update(item, conn)
        else:
            raise ValueError(f"CreditMutator does not support action '{action}'")

    def _add(self, item: AddCreditItem, conn: sqlite3.Connection) -> None:
        if item.song_id is not None:
            self._song_repo.add_credit(
                item.song_id, item.name, item.role, conn, identity_id=item.id
            )
        else:
            self._album_repo.add_credit(
                item.album_id, item.name, item.role, conn, identity_id=item.id
            )

    def _remove(self, item: RemoveCreditItem, conn: sqlite3.Connection) -> None:
        if item.song_id is not None:
            removed = self._song_repo.remove_credit(item.id, conn)
        else:
            removed = self._album_repo.remove_credit(item.album_id, item.id, conn)
        if removed == 0:
            raise LookupError(f"Credit {item.id} not found")

    def _update(self, item: UpdateCreditEntityItem, conn: sqlite3.Connection) -> None:
        if item.display_name is None:
            return
        existing_id = self._song_repo.get_name_id_by_display_name(
            item.display_name, conn
        )
        if existing_id is not None and existing_id != item.id:
            raise ValueError(f"MERGE_REQUIRED:credit:{existing_id}")
        updated = self._song_repo.update_credit_name(item.id, item.display_name, conn)
        if updated == 0:
            raise LookupError(f"ArtistName {item.id} not found")
