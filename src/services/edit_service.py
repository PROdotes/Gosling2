import os
import re
import sqlite3
from src.services.metadata_frames_reader import register_tag_category, unregister_tag_category, load_tag_categories
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.data.song_repository import SongRepository
from src.data.album_repository import AlbumRepository
from src.data.song_credit_repository import SongCreditRepository
from src.data.song_album_repository import SongAlbumRepository
from src.data.publisher_repository import PublisherRepository
from src.data.tag_repository import TagRepository
from src.data.identity_repository import IdentityRepository
from src.data.album_credit_repository import AlbumCreditRepository
from src.models.domain import (
    Song,
    Album,
    SongAlbum,
    Identity,
    Publisher,
    SongCredit,
    Tag,
)
from src.services.logger import logger
from src.services.metadata_writer import MetadataWriter
from src.services.casing_service import CasingService
from src.services.filing_service import FilingService
from src.services.library_service import LibraryService
from src.engine.config import (
    RENAME_RULES_PATH,
    LIBRARY_ROOT,
    get_db_path,
    AUTO_SAVE_ID3,
    STAGING_DIR,
    SCALAR_VALIDATION,
)
from src.engine.models.spotify import SpotifyCredit

class EditService:
    """Specialized orchestrator for modifying metadata, credits, links, and library organization."""

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

    def __init__(
        self, 
        db_path: Optional[str] = None, 
        library_service: Optional[LibraryService] = None,
        song_repo: Optional[SongRepository] = None,
        album_repo_dir: Optional[AlbumRepository] = None,
        credit_repo: Optional[SongCreditRepository] = None,
        album_repo: Optional[SongAlbumRepository] = None,
        pub_repo: Optional[PublisherRepository] = None,
        tag_repo: Optional[TagRepository] = None,
        identity_repo: Optional[IdentityRepository] = None,
        album_credit_repo: Optional[AlbumCreditRepository] = None
    ):
        if db_path is None:
            db_path = get_db_path()
        self._db_path = db_path
        self._song_repo = song_repo or SongRepository(db_path)
        self._album_repo_dir = album_repo_dir or AlbumRepository(db_path)
        self._credit_repo = credit_repo or SongCreditRepository(db_path)
        self._album_repo = album_repo or SongAlbumRepository(db_path)
        self._pub_repo = pub_repo or PublisherRepository(db_path)
        self._tag_repo = tag_repo or TagRepository(db_path)
        self._identity_repo = identity_repo or IdentityRepository(db_path)
        self._album_credit_repo = album_credit_repo or AlbumCreditRepository(db_path)
        
        # Cross-service dependencies
        self._library_service = library_service or LibraryService(db_path)
        
        # Edit Helpers
        self._metadata_writer = MetadataWriter()
        self._casing_service = CasingService()
        self._filing_service = FilingService(RENAME_RULES_PATH)


    def update_song_scalars(
        self, 
        song_id: int, 
        fields: Dict[str, Any], 
        scalar_rules: Optional[Dict[str, Any]] = None
    ) -> None:
        """Partial update of core song metadata with validation."""
        logger.debug(f"[EditService] -> update_song_scalars(id={song_id}, fields={fields})")

        rules = scalar_rules or SCALAR_VALIDATION

        # 1. Field Authorization
        allowed = self._SCALAR_ALLOWED | {"source_path", "audio_hash"}
        if any(k not in allowed for k in fields):
            forbidden = [k for k in fields if k not in allowed]
            raise ValueError(f"Non-editable fields: {forbidden}")

        # 2. Existence check
        song = self._library_service.get_song(song_id)
        if not song:
            raise LookupError(f"Song {song_id} not found")

        # 3. Workflow Validation (Review/Activation)
        if fields.get("is_active") is True or fields.get("processing_status") == 0:
            if fields.get("processing_status") == 0:
                from src.models.view_models import SongView
                view = SongView.from_domain(song)
                blockers = view.review_blockers
                if blockers:
                    raise ValueError(f"Cannot mark as reviewed, missing: {', '.join(blockers)}")

            if fields.get("is_active") is True:
                status = fields.get("processing_status", song.processing_status)
                if status != 0:
                    raise ValueError("Cannot activate song unless processing_status is 0 (Reviewed)")

        # 3. Scalar Validation
        import datetime
        if "media_name" in fields and (not fields["media_name"] or not str(fields["media_name"]).strip()):
            raise ValueError("media_name cannot be empty")
            
        if "year" in fields and fields["year"] is not None:
            year = int(fields["year"])
            year_rules = rules["year"]
            max_year = datetime.date.today().year + year_rules["max_offset"]
            if not (year_rules["min"] <= year <= max_year):
                raise ValueError(f"year must be between {year_rules['min']} and {max_year}")
            fields["year"] = year

        if "bpm" in fields and fields["bpm"] is not None:
            bpm = int(fields["bpm"])
            bpm_rules = rules["bpm"]
            if not (bpm_rules["min"] <= bpm <= bpm_rules["max"]):
                raise ValueError(f"bpm must be between {bpm_rules['min']} and {bpm_rules['max']}")
            fields["bpm"] = bpm

        if "isrc" in fields and fields["isrc"] is not None:
            isrc_rules = rules["isrc"]
            isrc = str(fields["isrc"]).replace(isrc_rules["strip"], "").upper().strip()
            if not re.match(isrc_rules["pattern"], isrc):
                raise ValueError("isrc must be 12 characters: 2-letter country, 3-char registrant, 2-digit year, 5-digit designation")
            fields["isrc"] = isrc

        # 4. Persistence
        conn = self._song_repo.get_connection()
        try:
            self._song_repo.update_scalars(song_id, fields, conn)
            conn.commit()
            self._sync_id3_if_enabled(song_id)
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] <- update_song_scalars FAILED: {e}")
            raise
        finally:
            conn.close()

    def add_song_credit(
        self,
        song_id: int,
        display_name: str,
        role_name: str = "Performer",
        identity_id: Optional[int] = None,
    ) -> SongCredit:
        """Add a credited artist to a song."""
        logger.debug(
            f"[EditService] -> add_song_credit(song_id={song_id}, name='{display_name}', role='{role_name}')"
        )
        if not display_name or not display_name.strip():
            raise ValueError("Artist name cannot be empty")
        
        conn = self._credit_repo.get_connection()
        try:
            credit = self._credit_repo.add_credit(
                song_id, display_name, role_name, conn, identity_id
            )
            conn.commit()
            self._sync_id3_if_enabled(song_id)
            return credit
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] <- add_song_credit FAILED: {e}")
            raise
        finally:
            conn.close()

    def remove_song_credit(self, song_id: int, credit_id: int) -> None:
        """Remove a credit link from a song."""
        logger.debug(f"[EditService] -> remove_song_credit(song_id={song_id}, credit_id={credit_id})")
        conn = self._credit_repo.get_connection()
        try:
            self._credit_repo.remove_credit(credit_id, conn)
            conn.commit()
            self._sync_id3_if_enabled(song_id)
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] <- remove_song_credit FAILED: {e}")
            raise
        finally:
            conn.close()


    def update_credit_name(self, name_id: int, new_name: str) -> None:
        """Update an artist's display name globally."""
        logger.debug(f"[EditService] -> update_credit_name(name_id={name_id}, new_name='{new_name}')")
        if not new_name or not new_name.strip():
            raise ValueError("Artist name cannot be empty")
            
        conn = self._credit_repo.get_connection()
        try:
            cursor = conn.cursor()
            collision = cursor.execute(
                "SELECT NameID, OwnerIdentityID FROM ArtistNames WHERE DisplayName = ? COLLATE UTF8_NOCASE AND IsDeleted = 0",
                (new_name.strip(),),
            ).fetchone()

            if collision:
                collision_name_id, collision_identity_id = collision
                if collision_name_id == name_id:
                    return
                alias_count = cursor.execute(
                    "SELECT COUNT(*) FROM ArtistNames WHERE OwnerIdentityID = ? AND IsDeleted = 0",
                    (collision_identity_id,),
                ).fetchone()[0]
                if alias_count > 1:
                    raise ValueError(f"UNSAFE_MERGE: '{new_name}' already exists with multiple aliases.")
                
                source_row = cursor.execute(
                    "SELECT OwnerIdentityID FROM ArtistNames WHERE NameID = ? AND IsDeleted = 0",
                    (name_id,),
                ).fetchone()
                if not source_row:
                    raise LookupError(f"Artist name {name_id} not found")
                source_identity_id = source_row[0]
                raise ValueError(f"MERGE_REQUIRED:{collision_name_id}:{source_identity_id}:{collision_identity_id}")

            self._credit_repo.update_credit_name(name_id, new_name, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] <- update_credit_name FAILED: {e}")
            raise
        finally:
            conn.close()

    def add_song_album(
        self,
        song_id: int,
        album_id: int,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
    ) -> SongAlbum:
        """Link an existing album to a song."""
        logger.debug(f"[EditService] -> add_song_album(song_id={song_id}, album_id={album_id})")
        if not self._song_repo.get_by_id(song_id):
            raise LookupError(f"Song {song_id} not found")
        if not self._library_service.get_album(album_id):
            raise LookupError(f"Album {album_id} not found")
        conn = self._album_repo.get_connection()
        try:
            self._album_repo.add_album(song_id, album_id, track_number, disc_number, conn)
            conn.commit()
            self._sync_id3_if_enabled(song_id)
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] <- add_song_album FAILED: {e}")
            raise
        finally:
            conn.close()
            
        links = self._album_repo.get_albums_for_songs([song_id])
        return next((link for link in links if link.album_id == album_id), None)

    def create_and_link_album(
        self,
        song_id: int,
        album_data: dict,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
    ) -> SongAlbum:
        """Create a new album record and link it to a song."""
        title = album_data.get("title", "").strip()
        if not title:
            raise ValueError("Album title cannot be empty")
        if not self._song_repo.get_by_id(song_id):
            raise LookupError(f"Song {song_id} not found")

        conn = self._album_repo_dir.get_connection()
        try:
            album_id = self._album_repo_dir.create_album(
                title, album_data.get("album_type"), album_data.get("release_year"), conn
            )
            self._album_repo.add_album(song_id, album_id, track_number, disc_number, conn)
            conn.commit()
            self._sync_id3_if_enabled(song_id)
            
            links = self._album_repo.get_albums_for_songs([song_id])
            return next((link for link in links if link.album_id == album_id), None)
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] <- create_and_link_album FAILED: {e}")
            raise
        finally:
            conn.close()

    def remove_song_album(self, song_id: int, album_id: int) -> None:
        """Unlink a song from an album."""
        conn = self._album_repo.get_connection()
        try:
            self._album_repo.remove_album(song_id, album_id, conn)
            conn.commit()
            self._sync_id3_if_enabled(song_id)
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] <- remove_song_album FAILED: {e}")
            raise
        finally:
            conn.close()

    def update_song_album_link(
        self,
        song_id: int,
        album_id: int,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
    ) -> None:
        """Update track/disc numbers for a song-album link."""
        existing_links = self._album_repo.get_albums_for_songs([song_id])
        if not any(link.album_id == album_id for link in existing_links):
            raise LookupError(f"Song {song_id} is not linked to Album {album_id}")
        conn = self._album_repo.get_connection()
        try:
            self._album_repo.update_track_info(song_id, album_id, track_number, disc_number, conn)
            conn.commit()
            self._sync_id3_if_enabled(song_id)
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] <- update_song_album_link FAILED: {e}")
            raise
        finally:
            conn.close()

    def update_album(self, album_id: int, album_data: dict) -> Album:
        """Update album record fields globally."""
        if "title" in album_data and not album_data["title"].strip():
            raise ValueError("Album title cannot be empty")
        if not self._library_service.get_album(album_id):
            raise LookupError(f"Album {album_id} not found")
        conn = self._album_repo_dir.get_connection()
        try:
            self._album_repo_dir.update_album(album_id, album_data, conn)
            conn.commit()
            # ID3 sync for all linked songs
            song_ids = self._album_repo_dir.get_song_ids_by_album(album_id, conn)
            for sid in song_ids:
                self._sync_id3_if_enabled(sid)
            return self._library_service.get_album(album_id)
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] <- update_album FAILED: {e}")
            raise
        finally:
            conn.close()

    def add_album_credit(
        self,
        album_id: int,
        display_name: str,
        role_name: str = "Performer",
        identity_id: Optional[int] = None,
    ) -> int:
        """Add a credited artist to an album."""
        if not self._library_service.get_album(album_id):
            raise LookupError(f"Album {album_id} not found")
        conn = self._album_credit_repo.get_connection()
        try:
            name_id = self._album_credit_repo.add_credit(album_id, display_name, role_name, conn, identity_id)
            conn.commit()
            # ID3 sync for all linked songs
            song_ids = self._album_repo_dir.get_song_ids_by_album(album_id, conn)
            for sid in song_ids:
                self._sync_id3_if_enabled(sid)
            return name_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def remove_album_credit(self, album_id: int, artist_name_id: int) -> None:
        """Remove a credited artist from an album."""
        conn = self._album_credit_repo.get_connection()
        try:
            self._album_credit_repo.remove_credit(album_id, artist_name_id, conn)
            conn.commit()
            song_ids = self._album_repo_dir.get_song_ids_by_album(album_id, conn)
            for sid in song_ids:
                self._sync_id3_if_enabled(sid)
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def add_album_publisher(
        self,
        album_id: int,
        publisher_name: Optional[str],
        publisher_id: Optional[int] = None,
    ) -> Publisher:
        """Add a publisher link for an album."""
        if not self._library_service.get_album(album_id):
            raise LookupError(f"Album {album_id} not found")
        if publisher_id is not None:
            existing = self._pub_repo.get_by_id(publisher_id)
            publisher_name = existing.name
        else:
            publisher_name = publisher_name.strip()
            
        conn = self._pub_repo.get_connection()
        try:
            publisher = self._pub_repo.add_album_publisher(album_id, publisher_name, conn)
            conn.commit()
            song_ids = self._album_repo_dir.get_song_ids_by_album(album_id, conn)
            for sid in song_ids:
                self._sync_id3_if_enabled(sid)
            return publisher
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def remove_album_publisher(self, album_id: int, publisher_id: int) -> None:
        """Remove a publisher link from an album."""
        conn = self._pub_repo.get_connection()
        try:
            self._pub_repo.remove_album_publisher(album_id, publisher_id, conn)
            conn.commit()
            song_ids = self._album_repo_dir.get_song_ids_by_album(album_id, conn)
            for sid in song_ids:
                self._sync_id3_if_enabled(sid)
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def add_song_tag(
        self,
        song_id: int,
        tag_name: Optional[str] = None,
        category: Optional[str] = None,
        tag_id: Optional[int] = None,
    ) -> Tag:
        """Add a tag to a song."""
        if tag_id is not None:
            existing = self._tag_repo.get_by_id(tag_id)
            if not existing:
                raise LookupError(f"Tag {tag_id} not found")
            tag_name = existing.name
            category = existing.category
        else:
            if not tag_name or not tag_name.strip():
                raise ValueError("Tag name cannot be empty")
            if not category or not category.strip():
                raise ValueError("Tag category cannot be empty")
            tag_name = tag_name.strip()
            category = category.strip().title()

        is_primary = 0
        if category == "Genre":
            existing_links = self._tag_repo.get_tags_for_songs([song_id])
            if not any(t.is_primary for sid, t in existing_links if sid == song_id and t.category == "Genre"):
                is_primary = 1

        conn = self._tag_repo.get_connection()
        try:
            tag = self._tag_repo.add_tag(song_id, tag_name, category, conn, is_primary=is_primary)
            conn.commit()
            if category not in load_tag_categories():
                register_tag_category(category)
            self._sync_id3_if_enabled(song_id)
            return tag
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def remove_song_tag(self, song_id: int, tag_id: int) -> None:
        """Remove a tag link from a song."""
        existing = self._tag_repo.get_by_id(tag_id)
        category = existing.category if existing else None

        conn = self._tag_repo.get_connection()
        try:
            self._tag_repo.remove_tag(song_id, tag_id, conn)
            conn.commit()
            if category:
                remaining = conn.execute(
                    """SELECT COUNT(*) FROM MediaSourceTags st
                       JOIN Tags t ON t.TagID = st.TagID
                       WHERE t.TagCategory = ? AND t.IsDeleted = 0""",
                    (category,)
                ).fetchone()[0]
                if remaining == 0:
                    unregister_tag_category(category)
            self._sync_id3_if_enabled(song_id)
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_tag(self, tag_id: int, new_name: str, new_category: str) -> None:
        """Update tag name/category globally."""
        if not new_name or not new_name.strip():
            raise ValueError("Tag name cannot be empty")
        new_category = new_category.strip().title() if new_category else new_category
        conn = self._tag_repo.get_connection()
        try:
            self._tag_repo.update_tag(tag_id, new_name, new_category, conn)
            conn.commit()
            song_ids = self._tag_repo.get_song_ids_by_tag(tag_id, conn)
            for sid in song_ids:
                self._sync_id3_if_enabled(sid)
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def set_primary_song_tag(self, song_id: int, tag_id: int) -> Tag:
        """Promote a specific tag to primary (Genre only)."""
        tag = self._tag_repo.get_by_id(tag_id)
        if not tag or tag.category != "Genre":
            raise ValueError("Only Genre tags can be primary")
        
        conn = self._tag_repo.get_connection()
        try:
            self._tag_repo.set_primary_tag(song_id, tag_id, conn)
            conn.commit()
            self._sync_id3_if_enabled(song_id)
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
        
        song = self._library_service.get_song(song_id)
        return next((t for t in song.tags if t.id == tag_id), None)

    def add_song_publisher(
        self,
        song_id: int,
        publisher_name: Optional[str],
        publisher_id: Optional[int] = None,
    ) -> Publisher:
        """Add a publisher link to a song."""
        if publisher_id is not None:
            existing = self._pub_repo.get_by_id(publisher_id)
            if not existing:
                raise LookupError(f"Publisher {publisher_id} not found")
            publisher_name = existing.name
        else:
            if not publisher_name or not str(publisher_name).strip():
                raise ValueError("Publisher name cannot be empty")
            publisher_name = str(publisher_name).strip()


        conn = self._pub_repo.get_connection()
        try:
            publisher = self._pub_repo.add_song_publisher(song_id, publisher_name, conn)
            conn.commit()
            self._sync_id3_if_enabled(song_id)
            return publisher
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def remove_song_publisher(self, song_id: int, publisher_id: int) -> None:
        """Remove a publisher link from a song."""
        conn = self._pub_repo.get_connection()
        try:
            self._pub_repo.remove_song_publisher(song_id, publisher_id, conn)
            conn.commit()
            self._sync_id3_if_enabled(song_id)
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_publisher(self, publisher_id: int, new_name: str) -> None:
        """Update publisher name globally."""
        if not new_name or not new_name.strip():
            raise ValueError("Publisher name cannot be empty")
        conn = self._pub_repo.get_connection()
        try:
            self._pub_repo.update_publisher(publisher_id, new_name, conn)
            conn.commit()
            song_ids = self._pub_repo.get_song_ids_by_publisher(publisher_id, conn)
            for sid in song_ids:
                self._sync_id3_if_enabled(sid)
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def set_publisher_parent(self, publisher_id: int, parent_id: Optional[int]) -> None:
        """Set or clear the parent of a publisher."""
        conn = self._pub_repo.get_connection()
        try:
            self._pub_repo.set_parent(publisher_id, parent_id, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def import_credits_bulk(
        self, song_id: int, credits: List[SpotifyCredit], publishers: List[str]
    ) -> None:
        """Atomic bulk import for Spotify credits and publishers."""
        if not self._song_repo.get_by_id(song_id):
            raise LookupError(f"Song {song_id} not found")
        conn = self._song_repo.get_connection()
        try:
            for credit in credits:
                self._credit_repo.add_credit(song_id, credit.name, credit.role, conn=conn, identity_id=credit.identity_id)
            for pub_name in publishers:
                self._pub_repo.add_song_publisher(song_id, pub_name, conn=conn)
            conn.commit()
            self._sync_id3_if_enabled(song_id)
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def format_entity_field(self, field_name: str, value: str, format_type: str = "title") -> str:
        """Standardizes casing for any entity field."""
        if not value:
            return value
            
        if format_type == "title":
            return CasingService.to_title_case(value)
        elif format_type == "sentence":
            return CasingService.to_sentence_case(value)
        return value.strip()


    def delete_song(self, song_id: int, staging_dir: Optional[Path] = None) -> bool:
        """Soft-delete a single song. Handles physical cleanup if in staging."""
        song = self._song_repo.get_by_id(song_id)
        if not song: return False
        
        source_path = song.source_path
        staging = staging_dir or STAGING_DIR
        conn = self._song_repo.get_connection()
        try:
            self._song_repo.delete_song_links(song_id, conn)
            success = self._song_repo.soft_delete(song_id, conn)
            if not success:
                conn.rollback()
                return False
            conn.commit()
            
            if source_path.startswith(str(staging)):
                if os.path.exists(source_path):
                    os.remove(source_path)
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()


    def move_song_to_library(self, song_id: int, library_root_path: Optional[Path] = None) -> str:
        """Orchestrates organization and organization of a song into the library folder."""
        song = self._library_service.get_song(song_id)
        if not song or song.processing_status != 0:
            raise ValueError("Song not found or not in Reviewed state")
            
        library_root = library_root_path or LIBRARY_ROOT
        source_abs_path = Path(song.source_path)
        try:
            new_abs_path = self._filing_service.copy_to_library(song, library_root)
            updates = {"source_path": str(new_abs_path)}
            self.update_song_scalars(song_id, updates)
            # Mandatory ID3 write
            shipped_song = self._library_service.get_song(song_id)
            if shipped_song:
                self._metadata_writer.write_metadata(shipped_song)
            if source_abs_path.exists():
                source_abs_path.unlink()
            return str(new_abs_path.relative_to(library_root))
        except Exception:
            raise


    def delete_unlinked_albums(self, album_ids: List[int]) -> int:
        """Soft-delete albums with zero active song links."""
        conn = self._album_repo_dir.get_connection()
        try:
            deleted = 0
            for album_id in album_ids:
                if not self._album_repo_dir.get_song_ids_by_album(album_id, conn):
                    self._album_repo_dir.delete_album_links(album_id, conn)
                    if self._album_repo_dir.soft_delete(album_id, conn):
                        deleted += 1
            conn.commit()
            return deleted
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_unlinked_publishers(self, publisher_ids: List[int]) -> int:
        """Soft-delete publishers with zero active links."""
        conn = self._pub_repo.get_connection()
        try:
            deleted = 0
            for pub_id in publisher_ids:
                if not self._pub_repo.get_song_ids_by_publisher(pub_id, conn) and not self._pub_repo.get_album_ids_by_publisher(pub_id, conn):
                    if self._pub_repo.soft_delete(pub_id, conn):
                        deleted += 1
            conn.commit()
            return deleted
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_unlinked_tags(self, tag_ids: List[int]) -> int:
        """Soft-delete tags with zero active song links."""
        conn = self._tag_repo.get_connection()
        try:
            deleted = 0
            for tag_id in tag_ids:
                if not self._tag_repo.get_song_ids_by_tag(tag_id, conn):
                    if self._tag_repo.soft_delete(tag_id, conn):
                        deleted += 1
            conn.commit()
            return deleted
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _sync_id3_if_enabled(self, song_id: int) -> None:
        """Internal trigger for persistent ID3 writing."""
        if not AUTO_SAVE_ID3:
            return
        try:
            song = self._library_service.get_song(song_id)
            if song:
                self._metadata_writer.write_metadata(song)
        except Exception as e:
            logger.error(f"[EditService] ID3 sync failed: {e}")
