from typing import Any, Callable, Dict, List, Optional, Tuple

from src.data.song_repository import SongRepository
from src.engine.config import get_db_path
from pydantic import TypeAdapter, ValidationError

from src.engine.routers.mutation_models import (
    AddItem,
    MutationRequest,
    RemoveAlbumItem,
    RemoveCreditItem,
    RemovePublisherItem,
    RemoveTagItem,
    UpdateSongItem,
)
from src.models.domain import Song, SongCredit
from src.models.view_models import SongAlbumView, SongView
from src.services.library_service import LibraryService
from src.services.mutation_coordinator import MutationCoordinator

# Editable scalar fields collapsed across the selection.
COLLAPSED_SCALARS = ("media_name", "bpm", "year", "isrc", "notes")

# Validates a song-targeted add op dict into the discriminated AddItem union.
_ADD_ITEM: TypeAdapter = TypeAdapter(AddItem)


class MultiEditService:
    """Collapses a selection of songs into one virtual SongView (read) and
    expands single-song-shaped ops into per-song mutation items (write)."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = str(get_db_path())
        self._db_path = db_path
        self._song_repo = SongRepository(db_path)
        self._library = LibraryService(db_path)

    def _load_songs(self, song_ids: List[int]) -> List[Song]:
        unique_ids = list(dict.fromkeys(song_ids))
        songs = self._song_repo.get_by_ids(unique_ids)
        if len(songs) != len(unique_ids):
            found = {s.id for s in songs}
            missing = [i for i in unique_ids if i not in found]
            raise LookupError(f"Songs not found: {missing}")
        return self._library.hydrate_songs(songs)

    def get_multi_view(self, song_ids: List[int]) -> SongView:
        songs = self._load_songs(song_ids)

        scalars, mixed_fields = self._collapse_scalars(songs)
        return SongView(
            id=None,
            media_name=scalars["media_name"] or "",
            title=scalars["media_name"] or "",
            source_path="",
            duration_s=0,
            # Display-only fields follow the same agree -> value rule so a
            # selection of identical songs renders identically to one of them
            # (they are not in mixed_fields: not editable via multi-edit).
            processing_status=self._agreed(songs, "processing_status", None),
            is_active=self._agreed(songs, "is_active", False),
            notes=scalars["notes"],
            bpm=scalars["bpm"],
            year=scalars["year"],
            isrc=scalars["isrc"],
            mixed_fields=mixed_fields,
            credits=self._collapse_credits(songs),
            tags=self._collapse_by_id(songs, "tags"),
            publishers=self._collapse_by_id(songs, "publishers"),
            albums=self._collapse_albums(songs),
        )

    @staticmethod
    def _agreed(songs: List[Song], field: str, default):
        distinct = {getattr(s, field) for s in songs}
        return distinct.pop() if len(distinct) == 1 else default

    @staticmethod
    def _collapse_scalars(songs: List[Song]) -> Tuple[Dict, Dict[str, List]]:
        scalars: Dict = {}
        mixed: Dict[str, List] = {}
        for field in COLLAPSED_SCALARS:
            distinct = list(dict.fromkeys(getattr(s, field) for s in songs))
            if len(distinct) == 1:
                scalars[field] = distinct[0]
            else:
                scalars[field] = None
                mixed[field] = distinct
        return scalars, mixed

    @staticmethod
    def _collapse_credits(songs: List[Song]) -> List:
        # A credit is identified by (name_id, role_name); per-song row IDs
        # (credit_id, source_id) are meaningless across the selection.
        first_seen: Dict[Tuple, SongCredit] = {}
        counts: Dict[Tuple, int] = {}
        for song in songs:
            for credit in song.credits:
                key = (credit.name_id, credit.role_name)
                if key not in first_seen:
                    first_seen[key] = credit
                    counts[key] = 0
                counts[key] += 1
        return [
            entry.model_copy(update={"universal": counts[key] == len(songs)})
            for key, entry in first_seen.items()
        ]

    @staticmethod
    def _collapse_by_id(songs: List[Song], attr: str) -> List:
        first_seen: Dict[Optional[int], Any] = {}
        counts: Dict[Optional[int], int] = {}
        for song in songs:
            for entry in getattr(song, attr):
                if entry.id not in first_seen:
                    first_seen[entry.id] = entry
                    counts[entry.id] = 0
                counts[entry.id] += 1
        return [
            entry.model_copy(update={"universal": counts[key] == len(songs)})
            for key, entry in first_seen.items()
        ]

    @staticmethod
    def _collapse_albums(songs: List[Song]) -> List[SongAlbumView]:
        first_seen: Dict[Optional[int], Any] = {}
        counts: Dict[Optional[int], int] = {}
        for song in songs:
            for album in song.albums:
                if album.album_id not in first_seen:
                    first_seen[album.album_id] = album
                    counts[album.album_id] = 0
                counts[album.album_id] += 1
        return [
            SongAlbumView(**album.model_dump(), universal=counts[key] == len(songs))
            for key, album in first_seen.items()
        ]

    # ------------------------------------------------------------------
    # Packer (write)
    # ------------------------------------------------------------------

    def multi_mutate(
        self,
        song_ids: List[int],
        update: Optional[Dict] = None,
        add: Optional[List[Dict]] = None,
        remove: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Expands single-song-shaped ops into per-song mutation items and
        applies them as one MutationRequest (one transaction, full rollback).
        Ops carry no song_id; update fields use exclude_unset semantics."""
        songs = self._load_songs(song_ids)

        update_items: List[Any] = []
        if update:
            unknown = set(update) - set(COLLAPSED_SCALARS)
            if unknown:
                raise ValueError(f"Fields not multi-editable: {sorted(unknown)}")
            try:
                update_items = [
                    UpdateSongItem(type="song", id=s.id, **update) for s in songs
                ]
            except ValidationError as e:
                msgs = "; ".join(err["msg"] for err in e.errors())
                raise ValueError(msgs) from e

        # Adds are blind clones, one item per song: every mutator add path is
        # idempotent (get-or-create + INSERT OR IGNORE on the link tables).
        add_items: List[Any] = []
        for op in add or []:
            if op.get("type") not in ("credit", "tag", "publisher", "album"):
                raise ValueError(f"Op not multi-editable: {op.get('type')!r}")
            if op.get("type") == "album":
                # Album links via multi-edit are explicit 0/0, never inherited.
                op = {**op, "track_number": 0, "disc_number": 0}
            add_items.extend(
                _ADD_ITEM.validate_python({**op, "song_id": s.id}) for s in songs
            )

        remove_items: List[Any] = []
        for op in remove or []:
            remove_items.extend(self._expand_remove(op, songs))

        if not (update_items or add_items or remove_items):
            # Every add was already present on every song: a valid no-op.
            return {"songs": [], "warnings": []}

        return MutationCoordinator(self._db_path).apply(
            MutationRequest(
                add=add_items or None,
                update=update_items or None,
                remove=remove_items or None,
            )
        )

    def _expand_remove(self, op: Dict, songs: List[Song]) -> List[Any]:
        kind = op["type"]
        if kind == "credit":
            return self._expand_remove_credit(op["id"], songs)
        if kind == "tag":
            return self._remove_universal(
                op, songs, "tags", lambda t: t.id, RemoveTagItem
            )
        if kind == "publisher":
            return self._remove_universal(
                op, songs, "publishers", lambda p: p.id, RemovePublisherItem
            )
        return self._remove_universal(
            op, songs, "albums", lambda a: a.album_id, RemoveAlbumItem
        )

    @staticmethod
    def _expand_remove_credit(credit_id: int, songs: List[Song]) -> List[Any]:
        # The view carries one song's credit_id for the union entry; resolve
        # it to (name_id, role_name) and re-find each song's own row.
        key = next(
            (
                (c.name_id, c.role_name)
                for s in songs
                for c in s.credits
                if c.credit_id == credit_id
            ),
            None,
        )
        if key is None:
            raise LookupError(f"Credit {credit_id} not found in selection")
        items = []
        for song in songs:
            match = next(
                (c for c in song.credits if (c.name_id, c.role_name) == key), None
            )
            if match is None:
                raise ValueError(
                    "Credit is not universal across the selection; remove is only offered for universal entries"
                )
            items.append(
                RemoveCreditItem(type="credit", song_id=song.id, id=match.credit_id)
            )
        return items

    @staticmethod
    def _remove_universal(
        op: Dict,
        songs: List[Song],
        attr: str,
        key_fn: Callable[[Any], Optional[int]],
        item_cls,
    ) -> List[Any]:
        kind, entry_id = op["type"], op["id"]
        present = [
            s for s in songs if any(key_fn(e) == entry_id for e in getattr(s, attr))
        ]
        if not present:
            raise LookupError(f"{kind} {entry_id} not found in selection")
        if len(present) != len(songs):
            raise ValueError(
                f"{kind} {entry_id} is not universal across the selection; remove is only offered for universal entries"
            )
        return [item_cls(type=kind, song_id=s.id, id=entry_id) for s in songs]
