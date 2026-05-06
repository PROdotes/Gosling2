import sqlite3
from pathlib import Path
from typing import Any

from src.data.base_repository import BaseRepository
from src.data.staging_repository import StagingRepository
from src.engine.config import LIBRARY_ROOT, RENAME_RULES_PATH, STAGING_DIR
from src.engine.routers.mutation_models import (
    DeleteOriginalFileItem,
    DeleteSongItem,
    MutationRequest,
    UpdateSongItem,
)
from src.services.filing_service import FilingService
from src.services.identity_service import IdentityService
from src.services.logger import logger
from src.services.library_service import LibraryService
from src.services.metadata_writer import MetadataWriter

from src.services.mutators.album_mutator import AlbumMutator
from src.services.mutators.credit_mutator import CreditMutator
from src.services.mutators.delete_mutator import DeleteMutator
from src.services.mutators.publisher_mutator import PublisherMutator
from src.services.mutators.song_mutator import SongMutator
from src.services.mutators.tag_mutator import TagMutator

_CREDIT_TYPES = {"credit"}
_TAG_TYPES = {"tag", "song_tag"}
_PUBLISHER_TYPES = {"publisher"}
_ALBUM_TYPES = {"album", "song_album"}
_SONG_TYPES = {"song"}


class MutationCoordinator:
    def __init__(self, db_path: str, library_service: LibraryService = None):
        self._db_path = db_path
        self._conn_factory = BaseRepository(db_path)
        self._library = library_service or LibraryService(db_path)
        self._identity_service = IdentityService(db_path)
        self._song_mutator = SongMutator(db_path)
        self._credit_mutator = CreditMutator(db_path)
        self._tag_mutator = TagMutator(db_path)
        self._publisher_mutator = PublisherMutator(db_path)
        self._album_mutator = AlbumMutator(db_path)
        self._delete_mutator = DeleteMutator(db_path)
        self._staging_repo = StagingRepository(db_path)
        self._id3_writer = MetadataWriter()
        self._filing = FilingService(RENAME_RULES_PATH)

    def apply(self, body: MutationRequest) -> dict[str, Any]:
        conn = self._conn_factory.get_connection()
        copied_files: list[tuple[str, str]] = []  # (old_path, new_path)
        try:
            touched_song_ids: set[int] = set()

            deleted_songs = []
            delete_file_ids: set[int] = set()
            for item in (body.delete or []):
                if isinstance(item, DeleteOriginalFileItem):
                    origin = self._staging_repo.get_origin(item.song_id)
                    if origin and Path(origin).exists():
                        Path(origin).unlink()
                        logger.info(f"[MutationCoordinator] Deleted original source: {origin}")
                    self._staging_repo.clear_origin(item.song_id)
                    continue
                if isinstance(item, DeleteSongItem):
                    song = self._library.get_song(item.id, conn)
                    if song:
                        deleted_songs.append(song)
                    if item.delete_file and item.id:
                        delete_file_ids.add(item.id)
                self._delete_mutator.apply_within("delete", item, conn)

            for item in (body.remove or []):
                self._route(item, "remove", conn)
                self._collect_touched(item, touched_song_ids)

            for item in (body.add or []):
                self._route(item, "add", conn)
                self._collect_touched(item, touched_song_ids)

            for item in (body.update or []):
                self._route(item, "update", conn)
                self._collect_touched(item, touched_song_ids)

            songs = []
            warnings = []
            for song_id in sorted(touched_song_ids):
                post = self._library.get_song(song_id, conn)
                if not post:
                    continue
                songs.append(post)
                warnings += self._filing.write_id3_if_needed(post, self._id3_writer)
                copy_warnings, new_path = self._filing.copy_if_needed(post, LIBRARY_ROOT)
                warnings += copy_warnings
                if new_path:
                    copied_files.append((post.source_path, new_path))
                    self._song_mutator.apply_within(
                        "update",
                        UpdateSongItem(type="song", id=song_id, source_path=new_path),
                        conn,
                    )

            conn.commit()

            for song in deleted_songs:
                if song.id in delete_file_ids:
                    self._filing.delete_physical_file(song)
                else:
                    self._filing.delete_staging_file(song, Path(STAGING_DIR))

            staging = Path(STAGING_DIR)
            for old_path, _ in copied_files:
                old = Path(old_path)
                if old.is_relative_to(staging) and old.exists():
                    old.unlink()
                    logger.debug(f"[MutationCoordinator] Deleted original after move: {old}")

            return {"songs": [s.model_dump() for s in songs], "warnings": warnings}

        except Exception:
            conn.rollback()
            for _, new_path in copied_files:
                new = Path(new_path)
                if new.exists():
                    new.unlink()
                    logger.debug(f"[MutationCoordinator] Deleted copy after rollback: {new}")
            raise
        finally:
            conn.close()

    def _route(self, item, action: str, conn: sqlite3.Connection) -> None:
        t = item.type
        if t == "identity_merge":
            self._identity_service.merge_identity_into(item.source_name_id, item.target_name_id)
        elif t in _SONG_TYPES:
            self._song_mutator.apply_within(action, item, conn)
        elif t in _CREDIT_TYPES:
            self._credit_mutator.apply_within(action, item, conn)
        elif t in _TAG_TYPES:
            self._tag_mutator.apply_within(action, item, conn)
        elif t in _PUBLISHER_TYPES:
            self._publisher_mutator.apply_within(action, item, conn)
        elif t in _ALBUM_TYPES:
            self._album_mutator.apply_within(action, item, conn)
        else:
            raise ValueError(f"Unknown mutation item type: {t!r}")

    def _collect_touched(self, item, touched: set[int]) -> None:
        if isinstance(item, UpdateSongItem):
            touched.add(item.id)
        elif hasattr(item, "song_id") and item.song_id is not None:
            touched.add(item.song_id)
