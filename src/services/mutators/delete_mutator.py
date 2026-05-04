import sqlite3
from uuid import UUID

from src.data.album_repository import AlbumRepository
from src.data.identity_repository import IdentityRepository
from src.data.media_source_repository import MediaSourceRepository
from src.data.publisher_repository import PublisherRepository
from src.data.tag_repository import TagRepository
from src.engine.routers.mutation_models import (
    DeleteAlbumItem,
    DeleteIdentityItem,
    DeletePublisherItem,
    DeleteSongItem,
    DeleteTagItem,
)


class DeleteMutator:
    def __init__(self, db_path: str):
        self._media_repo = MediaSourceRepository(db_path)
        self._tag_repo = TagRepository(db_path)
        self._publisher_repo = PublisherRepository(db_path)
        self._album_repo = AlbumRepository(db_path)
        self._identity_repo = IdentityRepository(db_path)

    def apply_within(self, action: str, item, conn: sqlite3.Connection, batch_id: UUID) -> None:
        if action != "delete":
            raise ValueError(f"DeleteMutator does not support action '{action}'")
        t = item.type
        if t == "song":
            self._delete_song(item, conn)
        elif t == "tag":
            self._delete_tag(item, conn)
        elif t == "publisher":
            self._delete_publisher(item, conn)
        elif t == "album":
            self._delete_album(item, conn)
        elif t == "identity":
            self._delete_identity(item, conn)
        else:
            raise ValueError(f"DeleteMutator: unknown type '{t}'")

    def _delete_song(self, item: DeleteSongItem, conn: sqlite3.Connection) -> None:
        self._media_repo.delete_song_links(item.id, conn)
        deleted = self._media_repo.soft_delete(item.id, conn)
        if not deleted:
            raise LookupError(f"Song {item.id} not found")

    def _delete_tag(self, item: DeleteTagItem, conn: sqlite3.Connection) -> None:
        if item.unlinked:
            for tag in self._tag_repo.get_all(conn):
                if not self._tag_repo.get_song_ids_by_tag(tag.id, conn):
                    self._tag_repo.soft_delete(tag.id, conn)
            return
        linked = self._tag_repo.get_song_ids_by_tag(item.id, conn)
        if linked:
            raise ValueError(f"Tag {item.id} is still linked to {len(linked)} song(s)")
        deleted = self._tag_repo.soft_delete(item.id, conn)
        if not deleted:
            raise LookupError(f"Tag {item.id} not found")

    def _delete_publisher(self, item: DeletePublisherItem, conn: sqlite3.Connection) -> None:
        if item.unlinked:
            for pub in self._publisher_repo.get_all(conn):
                if not self._publisher_repo.get_song_ids_by_publisher(pub.id, conn):
                    self._publisher_repo.soft_delete(pub.id, conn)
            return
        linked = self._publisher_repo.get_song_ids_by_publisher(item.id, conn)
        if linked:
            raise ValueError(f"Publisher {item.id} is still linked to {len(linked)} song(s)")
        deleted = self._publisher_repo.soft_delete(item.id, conn)
        if not deleted:
            raise LookupError(f"Publisher {item.id} not found")

    def _delete_album(self, item: DeleteAlbumItem, conn: sqlite3.Connection) -> None:
        if item.unlinked:
            for album in self._album_repo.get_all(conn):
                if not self._album_repo.get_song_ids_by_album(album.id, conn):
                    self._album_repo.delete_album_links(album.id, conn)
                    self._album_repo.soft_delete(album.id, conn)
            return
        linked = self._album_repo.get_song_ids_by_album(item.id, conn)
        if linked:
            raise ValueError(f"Album {item.id} is still linked to {len(linked)} song(s)")
        self._album_repo.delete_album_links(item.id, conn)
        deleted = self._album_repo.soft_delete(item.id, conn)
        if not deleted:
            raise LookupError(f"Album {item.id} not found")

    def _delete_identity(self, item: DeleteIdentityItem, conn: sqlite3.Connection) -> None:
        if item.unlinked:
            for identity in self._identity_repo.get_all_identities(conn):
                if not self._identity_repo.get_song_ids_by_identity(identity.id, conn):
                    self._identity_repo.soft_delete(identity.id, conn)
            return
        linked = self._identity_repo.get_song_ids_by_identity(item.id, conn)
        if linked:
            raise ValueError(f"Identity {item.id} is still linked to {len(linked)} song(s)")
        deleted = self._identity_repo.soft_delete(item.id, conn)
        if not deleted:
            raise LookupError(f"Identity {item.id} not found")
