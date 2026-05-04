import sqlite3
from typing import Union

from src.data.album_repository import AlbumRepository
from src.data.song_album_repository import SongAlbumRepository
from src.engine.routers.mutation_models import (
    AddAlbumItem,
    RemoveAlbumItem,
    UpdateAlbumEntityItem,
    UpdateSongAlbumItem,
)


class AlbumMutator:
    def __init__(self, db_path: str):
        self._album_repo = AlbumRepository(db_path)
        self._song_album_repo = SongAlbumRepository(db_path)

    def apply_within(
        self,
        action: str,
        item: Union[AddAlbumItem, RemoveAlbumItem, UpdateAlbumEntityItem, UpdateSongAlbumItem],
        conn: sqlite3.Connection,
    ) -> None:
        if action == "add":
            self._add(item, conn)
        elif action == "remove":
            self._remove(item, conn)
        elif action == "update":
            self._update(item, conn)
        else:
            raise ValueError(f"AlbumMutator does not support action '{action}'")

    def _add(self, item: AddAlbumItem, conn: sqlite3.Connection) -> None:
        if item.id is not None:
            album_id = item.id
        else:
            album_id = self._album_repo.create_album(item.name, None, None, conn)

        has_primary = self._song_album_repo.has_primary(item.song_id, conn)
        self._song_album_repo.add_album(item.song_id, album_id, item.track_number, item.disc_number, conn)

        if item.make_primary or not has_primary:
            self._song_album_repo.set_primary(item.song_id, album_id, conn)
        else:
            self._song_album_repo.clear_primary(item.song_id, album_id, conn)

    def _remove(self, item: RemoveAlbumItem, conn: sqlite3.Connection) -> None:
        link = self._song_album_repo.get_link(item.song_id, item.id, conn)
        was_primary = bool(link["IsPrimary"]) if link else False
        removed = self._song_album_repo.remove_album(item.song_id, item.id, conn)
        if removed == 0:
            raise LookupError(f"Album {item.id} not linked to song {item.song_id}")
        if was_primary:
            self._song_album_repo.promote_next(item.song_id, conn)

    def _update(self, item: Union[UpdateAlbumEntityItem, UpdateSongAlbumItem], conn: sqlite3.Connection) -> None:
        if isinstance(item, UpdateAlbumEntityItem):
            self._update_album_entity(item, conn)
        elif isinstance(item, UpdateSongAlbumItem):
            self._update_song_album(item, conn)
        else:
            raise ValueError(f"AlbumMutator: unexpected update type '{getattr(item, 'type', '?')}'")

    def _update_album_entity(self, item: UpdateAlbumEntityItem, conn: sqlite3.Connection) -> None:
        fields = item.model_dump(exclude={"type", "id"}, exclude_unset=True)
        if not fields:
            return
        updated = self._album_repo.update_album(item.id, fields, conn)
        if updated == 0:
            raise LookupError(f"Album {item.id} not found")

    def _update_song_album(self, item: UpdateSongAlbumItem, conn: sqlite3.Connection) -> None:
        fields = item.model_dump(exclude={"type", "song_id", "album_id", "is_primary"}, exclude_unset=True)
        if fields:
            track = item.track_number if "track_number" in item.model_fields_set else ...
            disc = item.disc_number if "disc_number" in item.model_fields_set else ...
            updated = self._song_album_repo.update_track_info(item.song_id, item.album_id, track, disc, conn)
            if updated == 0:
                raise LookupError(f"Album {item.album_id} not linked to song {item.song_id}")

        if item.is_primary is not None:
            if item.is_primary:
                updated = self._song_album_repo.set_primary(item.song_id, item.album_id, conn)
                if updated == 0:
                    raise LookupError(f"Album {item.album_id} not linked to song {item.song_id}")
            else:
                updated = self._song_album_repo.clear_primary(item.song_id, item.album_id, conn)
                if updated == 0:
                    raise LookupError(f"Album {item.album_id} not linked to song {item.song_id}")
