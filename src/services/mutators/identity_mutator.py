import sqlite3
from typing import Union

from src.data.identity_repository import IdentityRepository
from src.engine.routers.mutation_models import (
    AddIdentityAliasItem,
    AddIdentityMemberItem,
    MergeIdentityItem,
    RemoveIdentityAliasItem,
    RemoveIdentityMemberItem,
    UpdateIdentityItem,
)
from src.utils.text import normalize_for_search


class IdentityMutator:
    def __init__(self, db_path: str):
        self._repo = IdentityRepository(db_path)

    def apply_within(
        self,
        action: str,
        item: Union[
            AddIdentityAliasItem,
            AddIdentityMemberItem,
            RemoveIdentityAliasItem,
            RemoveIdentityMemberItem,
            UpdateIdentityItem,
            MergeIdentityItem,
        ],
        conn: sqlite3.Connection,
    ) -> None:
        if action == "add":
            self._add(item, conn)
        elif action == "remove":
            self._remove(item, conn)
        elif action == "update":
            self._update(item, conn)
        elif action == "merge":
            self._merge(item, conn)
        else:
            raise ValueError(f"IdentityMutator does not support action '{action}'")

    def _add(
        self,
        item: Union[AddIdentityAliasItem, AddIdentityMemberItem],
        conn: sqlite3.Connection,
    ) -> None:
        cursor = conn.cursor()
        if isinstance(item, AddIdentityAliasItem):
            display_name = item.display_name or ""
            self._repo.add_alias(
                item.identity_id,
                display_name,
                cursor,
                name_id=item.name_id,
                display_name_search=(
                    normalize_for_search(display_name) if display_name else None
                ),
            )
        elif isinstance(item, AddIdentityMemberItem):
            self._repo.add_member(item.group_id, item.member_id, cursor)
        else:
            raise ValueError(
                f"IdentityMutator: unexpected add type '{getattr(item, 'type', '?')}'"
            )

    def _remove(
        self,
        item: Union[RemoveIdentityAliasItem, RemoveIdentityMemberItem],
        conn: sqlite3.Connection,
    ) -> None:
        cursor = conn.cursor()
        if isinstance(item, RemoveIdentityAliasItem):
            owner = self._repo.get_owner_identity_id(item.name_id, cursor)
            if owner is not None and owner != item.identity_id:
                raise ValueError(
                    f"Alias {item.name_id} belongs to identity {owner}, not {item.identity_id}"
                )
            self._repo.delete_alias(item.name_id, cursor)
        elif isinstance(item, RemoveIdentityMemberItem):
            self._repo.remove_member(item.group_id, item.member_id, cursor)
        else:
            raise ValueError(
                f"IdentityMutator: unexpected remove type '{getattr(item, 'type', '?')}'"
            )

    def _update(self, item: UpdateIdentityItem, conn: sqlite3.Connection) -> None:
        if item.identity_type is not None:
            self._repo.set_type(item.id, item.identity_type, conn)

    def _merge(self, item: MergeIdentityItem, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        self._repo.merge_orphan_into(item.source_name_id, item.target_name_id, cursor)
