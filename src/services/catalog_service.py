import sqlite3
from typing import Optional, List, Dict, Any
from src.data.album_repository import AlbumRepository
from src.data.song_repository import SongRepository
from src.data.song_credit_repository import SongCreditRepository
from src.data.song_album_repository import SongAlbumRepository
from src.data.publisher_repository import PublisherRepository
from src.data.album_credit_repository import AlbumCreditRepository
from src.data.tag_repository import TagRepository
from src.data.identity_repository import IdentityRepository
from src.data.staging_repository import StagingRepository
from src.models.domain import (
    Song,
    Album,
    Identity,
    Publisher,
    Tag,
)

from src.engine.config import (
    get_db_path,
)
from src.services.identity_service import IdentityService
from src.services.library_service import LibraryService
from src.services.ingestion_service import IngestionService


class CatalogService:
    """Entry point for song access. Stateless orchestrator."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = get_db_path()
        self._db_path = db_path
        self._song_repo = SongRepository(db_path)
        self._album_repo_dir = AlbumRepository(db_path)
        self._credit_repo = SongCreditRepository(db_path)
        self._album_repo = SongAlbumRepository(db_path)
        self._album_credit_repo = AlbumCreditRepository(db_path)
        self._pub_repo = PublisherRepository(db_path)
        self._tag_repo = TagRepository(db_path)
        self._identity_repo = IdentityRepository(db_path)
        self._staging_repo = StagingRepository(db_path)
        self._identity_service = IdentityService(
            db_path, identity_repo=self._identity_repo
        )
        self._library_service = LibraryService(db_path)
        self._ingestion_service = IngestionService(
            db_path,
            self._library_service,
            song_repo=self._song_repo,
            album_repo_dir=self._album_repo_dir,
            credit_repo=self._credit_repo,
            album_repo=self._album_repo,
            pub_repo=self._pub_repo,
            tag_repo=self._tag_repo,
            identity_repo=self._identity_repo,
        )

    def check_ingestion(self, file_path: str) -> Dict[str, Any]:
        """Dry-run ingestion check for path, hash, and metadata collisions."""
        return self._ingestion_service.check_ingestion(file_path)

    def ingest_wav_as_converting(
        self, staged_path: str, original_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ingest a WAV file immediately with processing_status=3 (Converting)."""
        return self._ingestion_service.ingest_wav_as_converting(
            staged_path, original_path
        )

    def finalize_wav_conversion(self, song_id: int, mp3_path: str) -> int:
        """Called after WAV→MP3 conversion completes to update the DB record."""
        return self._ingestion_service.finalize_wav_conversion(song_id, mp3_path)

    def ingest_file(
        self, staged_path: str, original_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Write path for a staged file. Handles collisions and reingestion errors."""
        return self._ingestion_service.ingest_file(staged_path, original_path)

    def enrich_metadata(self, song_id: int, conn: sqlite3.Connection) -> None:
        """Internal sink for metadata enrichment (Delegated)."""
        return self._ingestion_service.enrich_metadata(song_id, conn)

    def scan_folder(self, folder_path: str, recursive: bool = True) -> List[str]:
        """Scan a folder for audio files and return their paths."""
        return self._ingestion_service.scan_folder(folder_path, recursive)

    def ingest_single(
        self, file_path: str, original_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Internal wrapper for thread-safe single file ingestion (Delegated)."""
        return self._ingestion_service.ingest_single(file_path, original_path)

    def resolve_conflict(
        self, ghost_id: int, staged_path: str, original_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve a ghost conflict by re-activating the soft-deleted record."""
        return self._ingestion_service.resolve_conflict(
            ghost_id, staged_path, original_path
        )

    def get_song(self, song_id: int) -> Optional[Song]:
        """Fetch a single song and all its credits by ID."""
        return self._library_service.get_song(song_id)

    def get_identity(self, identity_id: int) -> Optional[Identity]:
        """Fetch a full identity tree (Aliases/Members/Groups)."""
        return self._identity_service.get_identity(identity_id)

    def get_all_identities_slim(self) -> List[dict]:
        """Slim list-view rows for all active identities (no hydration)."""
        return self._identity_service.get_all_slim()

    def resolve_identity_by_name(self, display_name: str) -> Optional[int]:
        """Return the IdentityID for an ArtistName (Truth-First resolution)."""
        return self._identity_service.resolve_identity_by_name(display_name)

    def publisher_exists(self, name: str) -> bool:
        """Return True if a Publisher with this exact name exists."""
        return self._pub_repo.find_by_name(name) is not None

    def search_identities_slim(
        self, query: str, exclude_groups: bool = False
    ) -> List[dict]:
        """Slim list-view search (no hydration)."""
        return self._identity_service.search_slim(
            query, exclude_groups=exclude_groups
        )

    def search_artist_names(self, query: str, exclude_groups: bool = False):
        """Search ArtistNames for picker results (one row per name)."""
        return self._identity_service.search_artist_names(
            query, exclude_groups=exclude_groups
        )

    def get_publisher_link_counts(self, publisher_ids: List[int]) -> dict:
        """Batch song+album counts for publishers."""
        return self._pub_repo.get_link_counts_batch(publisher_ids)

    def get_all_publishers(self) -> List[Publisher]:
        """Fetch the full directory of publishers."""
        return self._library_service.get_all_publishers()

    def get_all_albums(self) -> List[Album]:
        """Fetch the full album directory."""
        return self._library_service.get_all_albums()

    def search_albums_slim(self, query: str) -> List[dict]:
        """Slim list-view album search."""
        return self._library_service.search_albums_slim(query)

    def get_album(self, album_id: int) -> Optional[Album]:
        """Fetch a single album by ID."""
        return self._library_service.get_album(album_id)

    def search_publishers(self, query: str) -> List[Publisher]:
        """Search for publishers."""
        return self._library_service.search_publishers(query)

    def get_publisher(self, publisher_id: int) -> Optional[Publisher]:
        """Fetch a single publisher by ID."""
        return self._library_service.get_publisher(publisher_id)

    def get_songs_slim_by_publisher(self, publisher_id: int) -> List[dict]:
        """Fetch slim song rows for a publisher."""
        return self._library_service.get_songs_slim_by_publisher(publisher_id)

    def get_all_tags(self) -> List[Tag]:
        """Fetch the full directory of tags."""
        return self._library_service.get_all_tags()

    def get_tag_categories(self) -> List[str]:
        """Fetch all distinct tag categories."""
        return self._library_service.get_tag_categories()

    def search_tags(self, query: str) -> List[Tag]:
        """Search for tags."""
        return self._library_service.search_tags(query)

    def get_tag(self, tag_id: int) -> Optional[Tag]:
        """Fetch a single tag by ID."""
        return self._library_service.get_tag(tag_id)

    def get_songs_slim_by_tag(self, tag_id: int) -> List[dict]:
        """Fetch slim song rows for a tag."""
        return self._library_service.get_songs_slim_by_tag(tag_id)

    def get_songs_slim_by_identity(self, identity_id: int) -> List[dict]:
        """Slim reversed credit lookup from identity."""
        return self._library_service.get_songs_slim_by_identity(identity_id)

    def get_albums_slim_by_identity(self, identity_id: int) -> List[dict]:
        """Slim reversed album-credit lookup from identity."""
        return self._library_service.get_albums_slim_by_identity(identity_id)

    def get_filter_values(self, q: str = "") -> dict:
        """Returns all distinct filter sidebar values, optionally filtered by query."""
        return self._library_service.get_filter_values(q=q)

    def filter_songs_slim(
        self,
        artists: Optional[List[str]] = None,
        contributors: Optional[List[str]] = None,
        years: Optional[List[int]] = None,
        decades: Optional[List[int]] = None,
        genres: Optional[List[str]] = None,
        albums: Optional[List[str]] = None,
        publishers: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        live_only: bool = False,
        has_original: bool = False,
        mode: str = "ALL",
        q: Optional[str] = None,
    ) -> List[dict]:
        """Filter songs by sidebar criteria."""
        return self._library_service.filter_songs_slim(
            artists=artists,
            contributors=contributors,
            years=years,
            decades=decades,
            genres=genres,
            albums=albums,
            publishers=publishers,
            statuses=statuses,
            tags=tags,
            live_only=live_only,
            has_original=has_original,
            mode=mode,
            q=q,
        )

    def search_songs_slim(self, query: str) -> List[dict]:
        """Slim list-view search."""
        return self._library_service.search_songs_slim(query)

    def find_duplicate_songs(self) -> List[List[int]]:
        """Groups of song IDs sharing MediaName + performer identity set."""
        return self._library_service.find_duplicate_groups()

    def search_songs_deep_slim(self, query: str) -> List[dict]:
        """Deep slim search."""
        return self._library_service.search_songs_deep_slim(query)

    def get_all_roles(self) -> list[str]:
        return self._credit_repo.get_all_roles()

    def get_staging_origin(self, song_id: int) -> Optional[str]:
        """Fetch the original birth-path for this staged song."""
        return self._staging_repo.get_origin(song_id)
