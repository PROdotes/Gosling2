# TODO: Split this class into IngestionService, QueryService, EditService — it's 1594 lines
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
from src.data.audit_repository import AuditRepository
from src.models.domain import (
    Song,
    Album,
    SongAlbum,
    Identity,
    Publisher,
    SongCredit,
    Tag,
)

from src.services.metadata_parser import MetadataParser
from src.engine.config import (
    STAGING_DIR,
    SCALAR_VALIDATION,
    LIBRARY_ROOT,
    get_db_path,
)
from src.services.identity_service import IdentityService
from src.services.library_service import LibraryService
from src.services.ingestion_service import IngestionService
from src.services.edit_service import EditService
from src.engine.models.spotify import SpotifyCredit


class CatalogService:
    """Entry point for song access. Stateless orchestrator."""

    _SCALAR_ALLOWED = {
        "media_name",
        "year",
        "bpm",
        "isrc",
        "is_active",
        "processing_status",
        "mood",
        "energy",
        "comment",
    }
    _METADATA_ALLOWED = _SCALAR_ALLOWED | {"credits", "albums", "tags", "publishers"}

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
        self._audit_repo = AuditRepository(db_path)
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
        self._edit_service = EditService(
            db_path,
            self._library_service,
            song_repo=self._song_repo,
            album_repo_dir=self._album_repo_dir,
            credit_repo=self._credit_repo,
            album_repo=self._album_repo,
            pub_repo=self._pub_repo,
            tag_repo=self._tag_repo,
            identity_repo=self._identity_repo,
            album_credit_repo=self._album_credit_repo,
        )

        self._metadata_parser = MetadataParser()

    def _sync_id3_if_enabled(self, song_id: int) -> None:
        """Internal trigger for persistent ID3 writing (Delegated)."""
        return self._edit_service._sync_id3_if_enabled(song_id)

    def check_ingestion(self, file_path: str) -> Dict[str, Any]:
        """Dry-run ingestion check for path, hash, and metadata collisions."""
        return self._ingestion_service.check_ingestion(file_path)

    def ingest_wav_as_converting(self, staged_path: str) -> Dict[str, Any]:
        """Ingest a WAV file immediately with processing_status=3 (Converting)."""
        return self._ingestion_service.ingest_wav_as_converting(staged_path)

    def finalize_wav_conversion(self, song_id: int, mp3_path: str) -> int:
        """Called after WAV→MP3 conversion completes to update the DB record."""
        return self._ingestion_service.finalize_wav_conversion(song_id, mp3_path)

    def ingest_file(self, staged_path: str) -> Dict[str, Any]:
        """Write path for a staged file. Handles collisions and reingestion errors."""
        return self._ingestion_service.ingest_file(staged_path)

    def _enrich_metadata(self, song_id: int, conn: sqlite3.Connection) -> None:
        """Internal sink for metadata enrichment (Delegated)."""
        return self._ingestion_service._enrich_metadata(song_id, conn)

    def scan_folder(self, folder_path: str, recursive: bool = True) -> List[str]:
        """Scan a folder for audio files and return their paths."""
        return self._ingestion_service.scan_folder(folder_path, recursive)

    def ingest_batch(
        self, file_paths: List[str], max_workers: int = 10
    ) -> Dict[str, Any]:
        """Ingest multiple already-staged files in parallel."""
        return self._ingestion_service.ingest_batch(file_paths, max_workers)

    def _ingest_single(self, file_path: str) -> Dict[str, Any]:
        """Internal wrapper for thread-safe single file ingestion (Delegated)."""
        return self._ingestion_service._ingest_single(file_path)

    def delete_song(self, song_id: int) -> bool:
        """Soft-delete a single song. Handles physical cleanup if in staging."""
        return self._edit_service.delete_song(song_id, staging_dir=STAGING_DIR)

    def resolve_conflict(self, ghost_id: int, staged_path: str) -> Dict[str, Any]:
        """Resolve a ghost conflict by re-activating the soft-deleted record."""
        return self._ingestion_service.resolve_conflict(ghost_id, staged_path)

    def get_song(self, song_id: int) -> Optional[Song]:
        """Fetch a single song and all its credits by ID."""
        return self._library_service.get_song(song_id)

    def get_identity(self, identity_id: int) -> Optional[Identity]:
        """Fetch a full identity tree (Aliases/Members/Groups)."""
        return self._identity_service.get_identity(identity_id)

    def get_all_identities(self) -> List[Identity]:
        """Fetch a list of all active identities."""
        return self._identity_service.get_all_identities()

    def resolve_identity_by_name(self, display_name: str) -> Optional[int]:
        """Return the IdentityID for an ArtistName (Truth-First resolution)."""
        return self._identity_service.resolve_identity_by_name(display_name)

    def add_identity_alias(
        self, identity_id: int, display_name: str, name_id: Optional[int] = None
    ) -> int:
        """Link a new or existing alias name to an identity (Truth-First mapping)."""
        return self._identity_service.add_identity_alias(
            identity_id, display_name, name_id
        )

    def remove_identity_alias(self, name_id: int) -> None:
        """Remove an alias from an identity."""
        return self._identity_service.remove_identity_alias(name_id)

    def update_identity_legal_name(
        self, identity_id: int, legal_name: Optional[str]
    ) -> None:
        """Update the LegalName on an Identity."""
        return self._identity_service.update_identity_legal_name(
            identity_id, legal_name
        )

    def publisher_exists(self, name: str) -> bool:
        """Return True if a Publisher with this exact name exists."""
        return self._pub_repo.find_by_name(name) is not None

    def search_identities(self, query: str) -> List[Identity]:
        """Search for identities by name or alias."""
        return self._identity_service.search_identities(query)

    def get_publisher_link_counts(self, publisher_ids: List[int]) -> dict:
        """Batch song+album counts for publishers."""
        return self._pub_repo.get_link_counts_batch(publisher_ids)

    def get_identity_song_counts(self, identity_ids: List[int]) -> dict:
        """Batch active song counts for identities."""
        return self._identity_service.get_identity_song_counts(identity_ids)

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

    def get_songs_by_publisher(self, publisher_id: int) -> List[Song]:
        """Fetch song repertoire for a publisher."""
        return self._library_service.get_songs_by_publisher(publisher_id)

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

    def get_songs_by_tag(self, tag_id: int) -> List[Song]:
        """Fetch all songs linked to this tag."""
        return self._library_service.get_songs_by_tag(tag_id)

    def get_songs_by_identity(self, identity_id: int) -> List[Song]:
        """Reversed credit lookup from identity."""
        return self._library_service.get_songs_by_identity(identity_id)

    def get_filter_values(self) -> dict:
        """Returns all distinct filter sidebar values."""
        return self._library_service.get_filter_values()

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
        mode: str = "ALL",
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
            mode=mode,
        )

    def search_songs_slim(self, query: str) -> List[dict]:
        """Slim list-view search."""
        return self._library_service.search_songs_slim(query)

    def search_songs_deep_slim(self, query: str) -> List[dict]:
        """Deep slim search."""
        return self._library_service.search_songs_deep_slim(query)

    def format_entity_field(
        self, entity_type: str, entity_id: int, field: str, format_type: str
    ) -> Any:
        """Standardizes casing for any entity field via EditService."""
        current_value = None
        if entity_type == "song":
            entity = self.get_song(entity_id)
            current_value = getattr(entity, field, None)
        elif entity_type == "album":
            entity = self.get_album(entity_id)
            current_value = getattr(entity, field, None)
        elif entity_type == "publisher":
            entity = self.get_publisher(entity_id)
            current_value = entity.name if entity else None
            field = "name"
        elif entity_type == "credit":
            identity = self._identity_repo.get_by_id(entity_id)
            current_value = identity.display_name if identity else None
            field = "name"
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

        if current_value is None:
            raise LookupError(f"{entity_type} {entity_id} not found")

        new_value = self._edit_service.format_entity_field(field, current_value)

        if new_value != current_value:
            if entity_type == "song":
                self.update_song_scalars(entity_id, {field: new_value})
            elif entity_type == "album":
                self.update_album(entity_id, {field: new_value})
            elif entity_type == "publisher":
                self.update_publisher(entity_id, new_value)
            elif entity_type == "credit":
                self.update_credit_name(entity_id, new_value)

        return new_value

    def update_song_scalars(self, song_id: int, fields: Dict[str, Any]) -> Song:
        """Delegate scalar updates to EditService."""
        self._edit_service.update_song_scalars(
            song_id, fields, scalar_rules=SCALAR_VALIDATION
        )
        return self.get_song(song_id)

    def get_all_roles(self) -> list[str]:
        return self._credit_repo.get_all_roles()

    def add_song_credit(
        self,
        song_id: int,
        display_name: str,
        role_name: str = "Performer",
        identity_id: Optional[int] = None,
    ) -> SongCredit:
        """Add artist credit via EditService."""
        return self._edit_service.add_song_credit(
            song_id, display_name, role_name, identity_id
        )

    def remove_song_credit(self, song_id: int, credit_id: int) -> None:
        """Remove a credit link via EditService."""
        return self._edit_service.remove_song_credit(song_id, credit_id)

    def update_credit_name(self, name_id: int, new_name: str) -> None:
        """Update artist display name globally via EditService."""
        return self._edit_service.update_credit_name(name_id, new_name)

    def merge_identity_into(self, source_name_id: int, target_name_id: int) -> None:
        """Merges a solo identity via IdentityService."""
        return self._identity_service.merge_identity_into(
            source_name_id, target_name_id
        )

    def set_identity_type(self, identity_id: int, type_: str) -> None:
        """Convert an identity between person and group."""
        return self._identity_service.set_identity_type(identity_id, type_)

    def add_identity_member(self, group_id: int, member_id: int) -> None:
        """Add a person identity as a member of a group."""
        return self._identity_service.add_identity_member(group_id, member_id)

    def remove_identity_member(self, group_id: int, member_id: int) -> None:
        """Remove a member from a group."""
        return self._identity_service.remove_identity_member(group_id, member_id)

    def add_song_album(
        self,
        song_id: int,
        album_id: int,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
    ) -> SongAlbum:
        """Link an existing album via EditService."""
        return self._edit_service.add_song_album(
            song_id, album_id, track_number, disc_number
        )

    def create_and_link_album(
        self,
        song_id: int,
        album_data: dict,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
    ) -> SongAlbum:
        """Create and link album via EditService."""
        return self._edit_service.create_and_link_album(
            song_id, album_data, track_number, disc_number
        )

    def remove_song_album(self, song_id: int, album_id: int) -> None:
        """Unlink album via EditService."""
        return self._edit_service.remove_song_album(song_id, album_id)

    def update_song_album_link(
        self,
        song_id: int,
        album_id: int,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
    ) -> None:
        """Update link metadata via EditService."""
        return self._edit_service.update_song_album_link(
            song_id, album_id, track_number, disc_number
        )

    def update_album(self, album_id: int, album_data: dict) -> Album:
        """Update album record via EditService."""
        return self._edit_service.update_album(album_id, album_data)

    def add_album_credit(
        self,
        album_id: int,
        display_name: str,
        role_name: str = "Performer",
        identity_id: Optional[int] = None,
    ) -> int:
        """Add album credit via EditService."""
        return self._edit_service.add_album_credit(
            album_id, display_name, role_name, identity_id
        )

    def remove_album_credit(self, album_id: int, artist_name_id: int) -> None:
        """Remove album credit via EditService."""
        return self._edit_service.remove_album_credit(album_id, artist_name_id)

    def add_album_publisher(
        self,
        album_id: int,
        publisher_name: Optional[str],
        publisher_id: Optional[int] = None,
    ) -> Publisher:
        """Add album publisher via EditService."""
        return self._edit_service.add_album_publisher(
            album_id, publisher_name, publisher_id
        )

    def remove_album_publisher(self, album_id: int, publisher_id: int) -> None:
        """Remove album publisher via EditService."""
        return self._edit_service.remove_album_publisher(album_id, publisher_id)

    def add_song_tag(
        self,
        song_id: int,
        tag_name: Optional[str] = None,
        category: Optional[str] = None,
        tag_id: Optional[int] = None,
    ) -> Tag:
        """Add song tag via EditService."""
        return self._edit_service.add_song_tag(song_id, tag_name, category, tag_id)

    def remove_song_tag(self, song_id: int, tag_id: int) -> None:
        """Remove song tag via EditService."""
        return self._edit_service.remove_song_tag(song_id, tag_id)

    def update_tag(self, tag_id: int, new_name: str, new_category: str) -> None:
        """Update tag via EditService."""
        return self._edit_service.update_tag(tag_id, new_name, new_category)

    def delete_unlinked_albums(self, album_ids: List[int]) -> int:
        """Clean up unlinked albums via EditService."""
        return self._edit_service.delete_unlinked_albums(album_ids)

    def delete_unlinked_publishers(self, publisher_ids: List[int]) -> int:
        """Clean up unlinked publishers via EditService."""
        return self._edit_service.delete_unlinked_publishers(publisher_ids)

    def delete_unlinked_identities(self, identity_ids: List[int]) -> int:
        """Clean up unlinked identities via IdentityService."""
        return self._identity_service.delete_unlinked_identities(identity_ids)

    def delete_unlinked_tags(self, tag_ids: List[int]) -> int:
        """Clean up unlinked tags via EditService."""
        return self._edit_service.delete_unlinked_tags(tag_ids)

    def set_primary_song_tag(self, song_id: int, tag_id: int) -> Tag:
        """Set primary tag via EditService."""
        return self._edit_service.set_primary_song_tag(song_id, tag_id)

    def add_song_publisher(
        self,
        song_id: int,
        publisher_name: Optional[str],
        publisher_id: Optional[int] = None,
    ) -> Publisher:
        """Add song publisher via EditService."""
        return self._edit_service.add_song_publisher(
            song_id, publisher_name, publisher_id
        )

    def remove_song_publisher(self, song_id: int, publisher_id: int) -> None:
        """Remove song publisher via EditService."""
        return self._edit_service.remove_song_publisher(song_id, publisher_id)

    def import_credits_bulk(
        self, song_id: int, credits: List[SpotifyCredit], publishers: List[str]
    ) -> None:
        """Bulk import via EditService."""
        return self._edit_service.import_credits_bulk(song_id, credits, publishers)

    def update_publisher(self, publisher_id: int, new_name: str) -> None:
        """Update publisher via EditService."""
        return self._edit_service.update_publisher(publisher_id, new_name)

    def set_publisher_parent(self, publisher_id: int, parent_id: Optional[int]) -> None:
        """Update hierarchy via EditService."""
        return self._edit_service.set_publisher_parent(publisher_id, parent_id)

    def get_id3_frames_config(self) -> Dict[str, Any]:
        """Returns the ID3 frame configuration."""
        return self._metadata_parser.config

    def move_song_to_library(self, song_id: int) -> str:
        """Organize library via EditService."""
        return self._edit_service.move_song_to_library(
            song_id, library_root_path=LIBRARY_ROOT
        )
