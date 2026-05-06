import sqlite3
from typing import Union

from src.data.tag_repository import TagRepository
from src.engine.routers.mutation_models import (
    AddTagItem,
    RemoveTagItem,
    UpdateTagEntityItem,
    UpdateSongTagItem,
)


class TagMutator:
    def __init__(self, db_path: str):
        self._repo = TagRepository(db_path)

    def apply_within(
        self,
        action: str,
        item: Union[AddTagItem, RemoveTagItem, UpdateTagEntityItem, UpdateSongTagItem],
        conn: sqlite3.Connection,
    ) -> None:
        if action == "add":
            self._add(item, conn)
        elif action == "remove":
            self._remove(item, conn)
        elif action == "update":
            self._update(item, conn)
        else:
            raise ValueError(f"TagMutator does not support action '{action}'")

    def _add(self, item: AddTagItem, conn: sqlite3.Connection) -> None:
        if item.id is not None:
            existing_tag = self._repo.get_by_id(item.id, conn)
            if not existing_tag:
                raise LookupError(f"Tag {item.id} not found")
            name = existing_tag.name
            category = existing_tag.category
        else:
            name = item.name.strip()
            category = item.category.strip().title()

        is_primary = 0
        if category == "Genre":
            existing_links = self._repo.get_tags_for_songs([item.song_id], conn)
            has_primary = any(
                t.is_primary
                for sid, t in existing_links
                if sid == item.song_id and t.category == "Genre"
            )
            if item.make_primary or not has_primary:
                is_primary = 1

        self._repo.add_tag(
            item.song_id, name, category, conn, is_primary=is_primary, tag_id=item.id
        )

    def _remove(self, item: RemoveTagItem, conn: sqlite3.Connection) -> None:
        links = self._repo.get_tags_for_songs([item.song_id], conn)
        removed_link = next(
            (t for sid, t in links if sid == item.song_id and t.id == item.id), None
        )
        was_primary_genre = (
            removed_link
            and removed_link.is_primary
            and removed_link.category == "Genre"
        )
        removed = self._repo.remove_tag(item.song_id, item.id, conn)
        if removed == 0:
            raise LookupError(f"Tag {item.id} not linked to song {item.song_id}")
        if was_primary_genre:
            next_genre = next(
                (
                    t
                    for sid, t in links
                    if sid == item.song_id and t.category == "Genre" and t.id != item.id
                ),
                None,
            )
            if next_genre:
                self._repo.set_primary_tag(item.song_id, next_genre.id, conn)

    def _update(
        self,
        item: Union[UpdateSongTagItem, UpdateTagEntityItem],
        conn: sqlite3.Connection,
    ) -> None:
        if isinstance(item, UpdateSongTagItem):
            if item.is_primary:
                updated = self._repo.set_primary_tag(item.song_id, item.tag_id, conn)
                if updated == 0:
                    raise LookupError(
                        f"Tag {item.tag_id} not linked to song {item.song_id}"
                    )
        elif isinstance(item, UpdateTagEntityItem):
            existing = self._repo.get_by_id(item.id, conn)
            if existing is None:
                raise LookupError(f"Tag {item.id} not found")
            name = item.name if item.name is not None else existing.name
            category = item.category if item.category is not None else existing.category
            updated = self._repo.update_tag(item.id, name, category, conn)
            if updated == 0:
                raise LookupError(f"Tag {item.id} not found")
        else:
            raise ValueError(
                f"TagMutator: unexpected update type '{getattr(item, 'type', '?')}'"
            )
