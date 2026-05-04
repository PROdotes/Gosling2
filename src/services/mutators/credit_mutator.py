import sqlite3
from uuid import UUID

from src.data.song_credit_repository import SongCreditRepository
from src.engine.routers.mutation_models import (
    AddCreditItem,
    RemoveCreditItem,
    UpdateCreditEntityItem,
)


class CreditMutator:
    def __init__(self, db_path: str):
        self._repo = SongCreditRepository(db_path)

    def apply_within(self, action: str, item, conn: sqlite3.Connection, batch_id: UUID) -> None:
        if action == "add":
            self._add(item, conn)
        elif action == "remove":
            self._remove(item, conn)
        elif action == "update":
            self._update(item, conn)
        else:
            raise ValueError(f"CreditMutator does not support action '{action}'")

    def _add(self, item: AddCreditItem, conn: sqlite3.Connection) -> None:
        self._repo.add_credit(item.song_id, item.name, item.role, conn, identity_id=item.id)

    def _remove(self, item: RemoveCreditItem, conn: sqlite3.Connection) -> None:
        self._repo.remove_credit(item.id, conn)

    def _update(self, item: UpdateCreditEntityItem, conn: sqlite3.Connection) -> None:
        if item.display_name is None:
            return
        self._repo.update_credit_name(item.id, item.display_name, conn)
