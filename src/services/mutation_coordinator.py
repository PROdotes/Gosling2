import sqlite3
from typing import Any
from uuid import uuid4

from src.engine.routers.mutation_models import (
    MutationRequest,
    UpdateSongItem,
)
from src.services.library_service import LibraryService

from src.services.mutators.album_mutator import AlbumMutator
from src.services.mutators.credit_mutator import CreditMutator
from src.services.mutators.delete_mutator import DeleteMutator
from src.services.mutators.publisher_mutator import PublisherMutator
from src.services.mutators.song_mutator import SongMutator
from src.services.mutators.tag_mutator import TagMutator

# Maps item type string to the mutator that handles it
_CREDIT_TYPES = {"credit"}
_TAG_TYPES = {"tag", "song_tag"}
_PUBLISHER_TYPES = {"publisher"}
_ALBUM_TYPES = {"album", "song_album"}
_SONG_TYPES = {"song"}


class MutationCoordinator:
    def __init__(self, db_path: str, library_service: LibraryService = None):
        self._db_path = db_path
        self._library = library_service or LibraryService(db_path)
        self._song_mutator = SongMutator(db_path)
        self._credit_mutator = CreditMutator(db_path)
        self._tag_mutator = TagMutator()
        self._publisher_mutator = PublisherMutator()
        self._album_mutator = AlbumMutator(db_path)
        self._delete_mutator = DeleteMutator(db_path)

    def apply(self, body: MutationRequest) -> dict[str, Any]:
        conn = self._get_connection()
        batch_id = uuid4()
        try:
            touched_song_ids: set[int] = set()

            for item in (body.delete or []):
                self._delete_mutator.apply_within("delete", item, conn, batch_id)

            for item in (body.remove or []):
                self._route(item, "remove", conn, batch_id)
                if hasattr(item, "song_id") and item.song_id is not None:
                    touched_song_ids.add(item.song_id)

            for item in (body.add or []):
                self._route(item, "add", conn, batch_id)
                if hasattr(item, "song_id") and item.song_id is not None:
                    touched_song_ids.add(item.song_id)

            for item in (body.update or []):
                self._route(item, "update", conn, batch_id)
                if isinstance(item, UpdateSongItem):
                    touched_song_ids.add(item.id)
                elif hasattr(item, "song_id"):
                    touched_song_ids.add(item.song_id)

            conn.commit()

            songs = []
            warnings = []
            for song_id in sorted(touched_song_ids):
                post = self._library.get_song(song_id, conn)
                if post:
                    songs.append(post)

            return {"songs": [s.model_dump() for s in songs], "warnings": warnings}

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _route(self, item, action: str, conn: sqlite3.Connection, batch_id) -> None:
        t = item.type
        if t in _SONG_TYPES:
            self._song_mutator.apply_within(action, item, conn, batch_id)
        elif t in _CREDIT_TYPES:
            self._credit_mutator.apply_within(action, item, conn, batch_id)
        elif t in _TAG_TYPES:
            self._tag_mutator.apply_within(action, item, conn, batch_id)
        elif t in _PUBLISHER_TYPES:
            self._publisher_mutator.apply_within(action, item, conn, batch_id)
        elif t in _ALBUM_TYPES:
            self._album_mutator.apply_within(action, item, conn, batch_id)
        else:
            raise ValueError(f"Unknown mutation item type: {t!r}")

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.create_collation(
            "UTF8_NOCASE",
            lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
        )
        return conn
