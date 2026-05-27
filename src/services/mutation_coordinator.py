import sqlite3
from pathlib import Path
from typing import Any

from src.data.base_repository import BaseRepository
from src.data.staging_repository import StagingRepository
from src.engine.config import LIBRARY_ROOT, RENAME_RULES_PATH, STAGING_DIR
from src.engine.routers.mutation_models import (
    AddAlbumItem,
    AddCreditItem,
    AddIdentityAliasItem,
    AddIdentityMemberItem,
    AddPublisherItem,
    AddTagItem,
    DeleteOriginalFileItem,
    DeleteSongItem,
    MergeIdentityItem,
    MergePublisherItem,
    MergeTagItem,
    MutationRequest,
    RemoveAlbumItem,
    RemoveCreditItem,
    RemoveIdentityAliasItem,
    RemoveIdentityMemberItem,
    RemovePublisherItem,
    RemoveTagItem,
    UpdateAlbumEntityItem,
    UpdateCreditEntityItem,
    UpdateIdentityItem,
    UpdatePublisherEntityItem,
    UpdateSongAlbumItem,
    UpdateSongItem,
    UpdateSongTagItem,
    UpdateTagEntityItem,
)
from src.services.filing_service import FilingService
from src.services.logger import logger
from src.services.library_service import LibraryService
from src.services.metadata_writer import MetadataWriter
from src.services.waveform_service import delete_cache as delete_waveform_cache

from src.services.mutators.album_mutator import AlbumMutator
from src.services.mutators.credit_mutator import CreditMutator
from src.services.mutators.delete_mutator import DeleteMutator
from src.services.mutators.identity_mutator import IdentityMutator
from src.services.mutators.publisher_mutator import PublisherMutator
from src.services.mutators.song_mutator import SongMutator
from src.services.mutators.tag_mutator import TagMutator


class MutationCoordinator:
    def __init__(self, db_path: str, library_service: LibraryService = None):
        self._db_path = db_path
        self._conn_factory = BaseRepository(db_path)
        self._library = library_service or LibraryService(db_path)
        self._song_mutator = SongMutator(db_path)
        self._credit_mutator = CreditMutator(db_path)
        self._tag_mutator = TagMutator(db_path)
        self._publisher_mutator = PublisherMutator(db_path)
        self._album_mutator = AlbumMutator(db_path)
        self._delete_mutator = DeleteMutator(db_path)
        self._identity_mutator = IdentityMutator(db_path)
        self._staging_repo = StagingRepository(db_path)
        self._id3_writer = MetadataWriter()
        self._filing = FilingService(RENAME_RULES_PATH)

        s = self._song_mutator
        c = self._credit_mutator
        t = self._tag_mutator
        p = self._publisher_mutator
        a = self._album_mutator
        i = self._identity_mutator

        self._dispatch: dict[type, Any] = {
            UpdateSongItem: s,
            AddCreditItem: c,
            RemoveCreditItem: c,
            UpdateCreditEntityItem: c,
            AddTagItem: t,
            RemoveTagItem: t,
            UpdateTagEntityItem: t,
            UpdateSongTagItem: t,
            MergeTagItem: t,
            AddPublisherItem: p,
            RemovePublisherItem: p,
            UpdatePublisherEntityItem: p,
            MergePublisherItem: p,
            AddAlbumItem: a,
            RemoveAlbumItem: a,
            UpdateAlbumEntityItem: a,
            UpdateSongAlbumItem: a,
            AddIdentityAliasItem: i,
            RemoveIdentityAliasItem: i,
            AddIdentityMemberItem: i,
            RemoveIdentityMemberItem: i,
            UpdateIdentityItem: i,
            MergeIdentityItem: i,
        }

    def apply(self, body: MutationRequest) -> dict[str, Any]:
        conn = self._conn_factory.get_connection()
        copied_files: list[tuple[str, str]] = []
        try:
            touched_song_ids: set[int] = set()

            deleted_songs = []
            delete_file_ids: set[int] = set()
            for item in body.delete or []:
                if isinstance(item, DeleteOriginalFileItem):
                    origin = self._staging_repo.get_origin(item.song_id)
                    if origin and Path(origin).exists():
                        Path(origin).unlink()
                        logger.info(
                            f"[MutationCoordinator] Deleted original source: {origin}"
                        )
                    self._staging_repo.clear_origin(item.song_id)
                    continue
                if isinstance(item, DeleteSongItem):
                    song = self._library.get_song(item.id, conn)
                    if song:
                        deleted_songs.append(song)
                    if item.delete_file and item.id:
                        delete_file_ids.add(item.id)
                self._delete_mutator.apply_within("delete", item, conn)

            for item in body.remove or []:
                self._route(item, "remove", conn)
                self._collect_touched(item, touched_song_ids)

            for item in body.add or []:
                self._route(item, "add", conn)
                self._collect_touched(item, touched_song_ids)

            for item in body.update or []:
                self._route(item, "update", conn)
                self._collect_touched(item, touched_song_ids)

            for item in body.merge or []:
                self._route(item, "merge", conn)

            songs = []
            warnings = []
            for song_id in sorted(touched_song_ids):
                post = self._library.get_song(song_id, conn)
                if not post:
                    continue
                songs.append(post)
                warnings += self._filing.write_id3_if_needed(post, self._id3_writer)
                copy_warnings, new_path = self._filing.copy_if_needed(
                    post, LIBRARY_ROOT
                )
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
                delete_waveform_cache(song.id)

            for old_path, new_path in copied_files:
                old = Path(old_path)
                new = Path(new_path)
                if old.exists() and old.resolve() != new.resolve():
                    try:
                        old.unlink()
                        logger.debug(
                            f"[MutationCoordinator] Deleted original after move: {old}"
                        )
                    except OSError as e:
                        logger.warning(
                            f"[MutationCoordinator] Could not delete original after move (leaving in place): {old} ({e})"
                        )

            return {"songs": [s.model_dump() for s in songs], "warnings": warnings}

        except Exception:
            conn.rollback()
            for _, new_path in copied_files:
                new = Path(new_path)
                if new.exists():
                    new.unlink()
                    logger.debug(
                        f"[MutationCoordinator] Deleted copy after rollback: {new}"
                    )
            raise
        finally:
            conn.close()

    def _route(self, item, action: str, conn: sqlite3.Connection) -> None:
        mutator = self._dispatch.get(type(item))
        if mutator is None:
            raise ValueError(f"Unknown mutation item type: {item.type!r}")
        mutator.apply_within(action, item, conn)

    def _collect_touched(self, item, touched: set[int]) -> None:
        if isinstance(item, UpdateSongItem):
            touched.add(item.id)
        elif hasattr(item, "song_id") and item.song_id is not None:
            touched.add(item.song_id)
