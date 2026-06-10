from typing import Any, Dict, List, Optional, Tuple

from src.data.song_repository import SongRepository
from src.engine.config import get_db_path
from src.models.domain import Song, SongCredit
from src.models.view_models import SongAlbumView, SongView
from src.services.library_service import LibraryService

# Editable scalar fields collapsed across the selection.
COLLAPSED_SCALARS = ("media_name", "bpm", "year", "isrc", "notes")


class MultiEditService:
    """Collapses a selection of songs into one virtual SongView (read) and
    expands single-song-shaped ops into per-song mutation items (write)."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = str(get_db_path())
        self._db_path = db_path
        self._song_repo = SongRepository(db_path)
        self._library = LibraryService(db_path)

    def get_multi_view(self, song_ids: List[int]) -> SongView:
        unique_ids = list(dict.fromkeys(song_ids))
        songs = self._song_repo.get_by_ids(unique_ids)
        if len(songs) != len(unique_ids):
            found = {s.id for s in songs}
            missing = [i for i in unique_ids if i not in found]
            raise LookupError(f"Songs not found: {missing}")
        songs = self._library.hydrate_songs(songs)

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
