import os
import re
import threading
from src.services.metadata_frames_reader import (
    register_tag_category,
    unregister_tag_category,
    load_tag_categories,
)
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
from src.data.staging_repository import StagingRepository
from src.models.domain import (
    Album,
    SongAlbum,
    Publisher,
    SongCredit,
    Tag,
)
from src.services.logger import logger
from src.services.metadata_writer import MetadataWriter
from src.services.casing_service import CasingService
from src.services.filing_service import FilingService
from src.services.library_service import LibraryService
from src.services.identity_service import IdentityService
from src.engine.config import (
    get_db_path,
    RENAME_RULES_PATH,
    LIBRARY_ROOT,
    STAGING_DIR,
    SCALAR_VALIDATION,
    SCALAR_ALLOWED,
    METADATA_ALLOWED,
    AUTO_SAVE_ID3,
    ProcessingStatus,
)
from src.engine.models.spotify import SpotifyCredit


class EditService:
    """Specialized orchestrator for modifying metadata, credits, links, and library organization."""

    _SCALAR_ALLOWED = SCALAR_ALLOWED
    _METADATA_ALLOWED = METADATA_ALLOWED

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
        album_credit_repo: Optional[AlbumCreditRepository] = None,
        rules_path: Optional[Path] = None,
        library_root: Optional[Path] = None,
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
        self._staging_repo = StagingRepository(db_path)

        # Cross-service dependencies
        self._library_service = library_service or LibraryService(
            db_path, rules_path=rules_path, library_root=library_root
        )

        # Edit Helpers
        self._metadata_writer = MetadataWriter()
        self._casing_service = CasingService()
        actual_rules_path = rules_path or RENAME_RULES_PATH
        self._filing_service = FilingService(actual_rules_path)

    def update_song_scalars(
        self,
        song_id: int,
        fields: Dict[str, Any],
        scalar_rules: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Partial update of core song metadata with validation."""
        logger.debug(
            f"[EditService] -> update_song_scalars(id={song_id}, fields={fields})"
        )

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
        if (
            fields.get("is_active") is True
            or fields.get("processing_status") == ProcessingStatus.REVIEWED
        ):
            if fields.get("processing_status") == ProcessingStatus.REVIEWED:
                from src.models.view_models import SongView

                view = SongView.from_domain(song)
                blockers = view.review_blockers
                if blockers:
                    raise ValueError(
                        f"Cannot mark as reviewed, missing: {', '.join(blockers)}"
                    )

            if fields.get("is_active") is True:
                status = fields.get("processing_status", song.processing_status)
                if status != ProcessingStatus.REVIEWED:
                    raise ValueError(
                        f"Cannot activate song unless processing_status is {ProcessingStatus.REVIEWED} (Reviewed)"
                    )

        # 3. Scalar Validation
        import datetime

        if "media_name" in fields and (
            not fields["media_name"] or not str(fields["media_name"]).strip()
        ):
            raise ValueError("media_name cannot be empty")

        if "year" in fields and fields["year"] is not None:
            year = int(fields["year"])
            year_rules = rules["year"]
            max_year = datetime.date.today().year + year_rules["max_offset"]
            if not (year_rules["min"] <= year <= max_year):
                raise ValueError(
                    f"year must be between {year_rules['min']} and {max_year}"
                )
            fields["year"] = year

        if "bpm" in fields and fields["bpm"] is not None:
            bpm = int(fields["bpm"])
            bpm_rules = rules["bpm"]
            if not (bpm_rules["min"] <= bpm <= bpm_rules["max"]):
                raise ValueError(
                    f"bpm must be between {bpm_rules['min']} and {bpm_rules['max']}"
                )
            fields["bpm"] = bpm

        if "isrc" in fields and fields["isrc"] is not None:
            isrc_rules = rules["isrc"]
            isrc = str(fields["isrc"]).replace(isrc_rules["strip"], "").upper().strip()
            if not re.match(isrc_rules["pattern"], isrc):
                raise ValueError(
                    "isrc must be 12 characters: 2-letter country, 3-char registrant, 2-digit year, 5-digit designation"
                )
            fields["isrc"] = isrc

        # Validate release_year if present
        if "release_year" in fields and fields["release_year"] is not None:
            release_year = int(fields["release_year"])
            ry_rules = rules.get("release_year", {"min": 1860, "max_offset": 1})
            import datetime

            max_year = datetime.date.today().year + ry_rules.get("max_offset", 1)
            if not (ry_rules["min"] <= release_year <= max_year):
                raise ValueError(
                    f"release_year must be between {ry_rules['min']} and {max_year}"
                )
            fields["release_year"] = release_year

        # 4. Persistence
        conn = self._song_repo.get_connection()
        try:
            print(f"DEBUG: update_song_scalars called for {song_id}")
            self._song_repo.update_scalars(song_id, fields, conn)
            conn.commit()
            self._sync_id3_if_enabled(song_id)

            new_status = fields.get("processing_status", song.processing_status)
            return self._library_service.get_song(song_id)
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
        logger.debug(
            f"[EditService] -> remove_song_credit(song_id={song_id}, credit_id={credit_id})"
        )
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
        logger.debug(
            f"[EditService] -> update_credit_name(name_id={name_id}, new_name='{new_name}')"
        )
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
                    raise ValueError(
                        f"UNSAFE_MERGE: '{new_name}' already exists with multiple aliases."
                    )

                source_row = cursor.execute(
                    "SELECT OwnerIdentityID FROM ArtistNames WHERE NameID = ? AND IsDeleted = 0",
                    (name_id,),
                ).fetchone()
                if not source_row:
                    raise LookupError(f"Artist name {name_id} not found")
                source_identity_id = source_row[0]
                raise ValueError(
                    f"MERGE_REQUIRED:{collision_name_id}:{source_identity_id}:{collision_identity_id}"
                )

            self._credit_repo.update_credit_name(name_id, new_name, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] <- update_credit_name FAILED: {e}")
            raise
        finally:
            conn.close()

    def _validate_album_scalars(self, fields: dict) -> dict:
        """Validate SongAlbum scalar fields. Returns cleaned fields dict."""
        rules = SCALAR_VALIDATION
        for key in ("track_number", "disc_number", "release_year"):
            value = fields.get(key)
            if value is None:
                continue
            rule = rules.get(key)
            if not rule:
                continue
            val = int(value)
            if "min" in rule and val < rule["min"]:
                raise ValueError(f"{key} must be >= {rule['min']}")
            if "max" in rule and val > rule["max"]:
                raise ValueError(f"{key} must be <= {rule['max']}")
            if key == "release_year":
                import datetime

                max_year = datetime.date.today().year + rule.get("max_offset", 1)
                if not (rule["min"] <= val <= max_year):
                    raise ValueError(
                        f"{key} must be between {rule['min']} and {max_year}"
                    )
            fields[key] = val
        return fields

    def add_song_album(
        self,
        song_id: int,
        album_id: int,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
    ) -> SongAlbum:
        """Link an existing album to a song."""
        logger.debug(
            f"[EditService] -> add_song_album(song_id={song_id}, album_id={album_id})"
        )
        if not self._song_repo.get_by_id(song_id):
            raise LookupError(f"Song {song_id} not found")
        if not self._library_service.get_album(album_id):
            raise LookupError(f"Album {album_id} not found")

        fields = {}
        if track_number is not None:
            fields["track_number"] = track_number
        if disc_number is not None:
            fields["disc_number"] = disc_number
        if fields:
            self._validate_album_scalars(fields)

        conn = self._album_repo.get_connection()
        try:
            self._album_repo.add_album(
                song_id, album_id, track_number, disc_number, conn
            )
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

        fields = {}
        if track_number is not None:
            fields["track_number"] = track_number
        if disc_number is not None:
            fields["disc_number"] = disc_number
        if "release_year" in album_data and album_data["release_year"] is not None:
            fields["release_year"] = album_data["release_year"]
        if fields:
            self._validate_album_scalars(fields)

        conn = self._album_repo_dir.get_connection()
        try:
            album_id = self._album_repo_dir.create_album(
                title,
                album_data.get("album_type"),
                album_data.get("release_year"),
                conn,
            )
            self._album_repo.add_album(
                song_id, album_id, track_number, disc_number, conn
            )
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
        fields_set: set = None,
    ) -> None:
        """Update track/disc numbers for a song-album link."""
        existing_links = self._album_repo.get_albums_for_songs([song_id])
        if not any(link.album_id == album_id for link in existing_links):
            raise LookupError(f"Song {song_id} is not linked to Album {album_id}")

        to_validate = {}
        if track_number is not None:
            to_validate["track_number"] = track_number
        if disc_number is not None:
            to_validate["disc_number"] = disc_number
        if to_validate:
            self._validate_album_scalars(to_validate)

        fields_set = fields_set or set(to_validate.keys())

        conn = self._album_repo.get_connection()
        try:
            self._album_repo.update_track_info(
                song_id,
                album_id,
                track_number if "track_number" in fields_set else ...,
                disc_number if "disc_number" in fields_set else ...,
                conn,
            )
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

        if "release_year" in album_data and album_data["release_year"] is not None:
            self._validate_album_scalars({"release_year": album_data["release_year"]})

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
            name_id = self._album_credit_repo.add_credit(
                album_id, display_name, role_name, conn, identity_id
            )
            conn.commit()
            # ID3 sync for all linked songs
            song_ids = self._album_repo_dir.get_song_ids_by_album(album_id, conn)
            for sid in song_ids:
                self._sync_id3_if_enabled(sid)
            return name_id
        except Exception as e:
            logger.error(f"[EditService] add_album_credit FAILED: {e}")
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
            logger.error(f"[EditService] remove_album_credit FAILED: {e}")
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
            publisher = self._pub_repo.add_album_publisher(
                album_id, publisher_name, conn, publisher_id=publisher_id
            )
            conn.commit()
            song_ids = self._album_repo_dir.get_song_ids_by_album(album_id, conn)
            for sid in song_ids:
                self._sync_id3_if_enabled(sid)
            return publisher
        except Exception as e:
            logger.error(f"[EditService] add_album_publisher FAILED: {e}")
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
            logger.error(f"[EditService] remove_album_publisher FAILED: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def sync_album_with_song(self, album_id: int, song_id: int) -> Album:
        """
        Sync album metadata from a song (backend implementation of CW-1).
        Syncs: release_year (if missing), Performer credits, publishers.
        Atomic operation — all-or-nothing via single connection.
        """
        logger.info(
            f"[EditService] -> sync_album_with_song(album_id={album_id}, song_id={song_id})"
        )
        song = self._library_service.get_song(song_id)
        if not song:
            raise LookupError(f"Song {song_id} not found")

        album = self._library_service.get_album(album_id)
        if not album:
            raise LookupError(f"Album {album_id} not found")

        conn = self._album_repo_dir.get_connection()
        try:
            # Sync release_year if missing on album but present on song
            if not album.release_year and song.year:
                self._album_repo_dir.update_album(
                    album_id, {"release_year": song.year}, conn
                )
                logger.debug(f"[EditService] synced release_year={song.year} to album")

            # Sync Performer credits (only role that gets synced per original logic)
            existing_credit_name_ids = {c.name_id for c in (album.credits or [])}
            for credit in song.credits or []:
                if credit.role_name != "Performer":
                    continue
                if credit.name_id not in existing_credit_name_ids:
                    name_id = self._album_credit_repo.add_credit(
                        album_id,
                        credit.display_name,
                        credit.role_name,
                        conn,
                        identity_id=credit.identity_id or None,
                    )
                    existing_credit_name_ids.add(name_id)
                    logger.debug(
                        f"[EditService] added credit '{credit.display_name}' to album"
                    )

            # Sync publishers
            existing_pub_ids = {p.id for p in (album.publishers or [])}
            for pub in song.publishers or []:
                if pub.id not in existing_pub_ids:
                    self._pub_repo.add_album_publisher(
                        album_id, pub.name, conn, publisher_id=pub.id
                    )
                    existing_pub_ids.add(pub.id)
                    logger.debug(f"[EditService] added publisher '{pub.name}' to album")

            conn.commit()
            # ID3 sync for all linked songs
            song_ids = self._album_repo_dir.get_song_ids_by_album(album_id, conn)
            for sid in song_ids:
                self._sync_id3_if_enabled(sid)

            result = self._library_service.get_album(album_id)
            logger.info(f"[EditService] <- sync_album_with_song() OK '{result.title}'")
            return result
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] sync_album_with_song FAILED: {e}")
            raise
        finally:
            conn.close()

    def quick_create_album_for_song(
        self, song_id: int, title: Optional[str] = None
    ) -> SongAlbum:
        """
        Quick-create an album from a song (backend implementation of CW-2).
        Creates album with song's media_name, defaults disc=1, track=1,
        then syncs metadata from song atomically.
        """
        logger.info(
            f"[EditService] -> quick_create_album_for_song(song_id={song_id}, title='{title}')"
        )
        song = self._library_service.get_song(song_id)
        if not song:
            raise LookupError(f"Song {song_id} not found")

        album_title = (title or song.media_name or "Unknown Album").strip()
        if not album_title:
            raise ValueError("Album title cannot be empty")

        conn = self._album_repo_dir.get_connection()
        try:
            # Create album
            album_id = self._album_repo_dir.create_album(
                album_title, "Album", song.year, conn
            )
            # Link to song with defaults
            self._album_repo.add_album(song_id, album_id, 1, 1, conn)
            logger.debug(
                f"[EditService] created album_id={album_id}, linked to song_id={song_id}"
            )

            # Sync metadata (Performer credits + publishers) using already-fetched data
            # We need to re-fetch album within this transaction to get credits/publishers
            # For simplicity, just sync the album we just created
            # Sync Performer credits
            existing_credit_name_ids = set()
            for credit in song.credits or []:
                if credit.role_name != "Performer":
                    continue
                name_id = self._album_credit_repo.add_credit(
                    album_id,
                    credit.display_name,
                    credit.role_name,
                    conn,
                    identity_id=credit.identity_id or None,
                )
                existing_credit_name_ids.add(name_id)

            # Sync publishers
            for pub in song.publishers or []:
                self._pub_repo.add_album_publisher(
                    album_id, pub.name, conn, publisher_id=pub.id
                )

            conn.commit()
            # ID3 sync
            self._sync_id3_if_enabled(song_id)

            # Return the link info
            links = self._album_repo.get_albums_for_songs([song_id], conn)
            result = next((link for link in links if link.album_id == album_id), None)
            logger.info(
                f"[EditService] <- quick_create_album_for_song() OK album_id={album_id}"
            )
            return result
        except Exception as e:
            conn.rollback()
            logger.error(f"[EditService] quick_create_album_for_song FAILED: {e}")
            raise
        finally:
            conn.close()

    def _parse_raw_tag(self, raw: str) -> dict:
        """
        Parse a raw tag input string into {name, category}.
        Uses TAG_CATEGORY_DELIMITER and TAG_INPUT_FORMAT from config.
        """
        delimiter = "::"  # config.TAG_CATEGORY_DELIMITER
        default_category = "Genre"  # config.TAG_DEFAULT_CATEGORY
        format_ = "tag:category"  # config.TAG_INPUT_FORMAT
        name_first = format_.lower().startswith("tag")

        raw = raw.strip()
        if not raw:
            raise ValueError("Tag name cannot be empty")

        if delimiter not in raw:
            return {"name": raw, "category": default_category}

        idx = raw.find(delimiter)
        a = raw[:idx].strip()
        b = raw[idx + len(delimiter) :].strip()
        if name_first:
            return {"name": a, "category": b}
        else:
            return {"name": b, "category": a}

    def add_song_tag(
        self,
        song_id: int,
        tag_name: Optional[str] = None,
        category: Optional[str] = None,
        tag_id: Optional[int] = None,
        raw_tag: Optional[str] = None,
    ) -> Tag:
        """Add a tag to a song. Supports raw_tag parsing (DT-1, DT-2)."""
        # Parse raw_tag if provided (backend tag parsing)
        if raw_tag is not None:
            parsed = self._parse_raw_tag(raw_tag)
            tag_name = parsed["name"]
            category = parsed["category"]

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
            if not any(
                t.is_primary
                for sid, t in existing_links
                if sid == song_id and t.category == "Genre"
            ):
                is_primary = 1

        conn = self._tag_repo.get_connection()
        try:
            tag = self._tag_repo.add_tag(
                song_id, tag_name, category, conn, is_primary=is_primary, tag_id=tag_id
            )
            conn.commit()
            if category not in load_tag_categories():
                register_tag_category(category)
            self._sync_id3_if_enabled(song_id)
            return tag
        except Exception as e:
            logger.error(f"[EditService] add_song_tag FAILED: {e}")
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
                    (category,),
                ).fetchone()[0]
                if remaining == 0:
                    unregister_tag_category(category)
            self._sync_id3_if_enabled(song_id)
        except Exception as e:
            logger.error(f"[EditService] remove_song_tag FAILED: {e}")
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
            logger.error(f"[EditService] update_tag FAILED: {e}")
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
            logger.error(f"[EditService] set_primary_song_tag FAILED: {e}")
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
            publisher = self._pub_repo.add_song_publisher(
                song_id, publisher_name, conn, publisher_id=publisher_id
            )
            conn.commit()
            self._sync_id3_if_enabled(song_id)
            return publisher
        except Exception as e:
            logger.error(f"[EditService] add_song_publisher FAILED: {e}")
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
            logger.error(f"[EditService] remove_song_publisher FAILED: {e}")
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
            logger.error(f"[EditService] update_publisher FAILED: {e}")
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
            logger.error(f"[EditService] set_publisher_parent FAILED: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def import_credits_bulk(
        self, song_id: int, credits: List[SpotifyCredit], publishers: List[str]
    ) -> None:
        """Atomic bulk import for Spotify credits and publishers (backend CW-3)."""
        if not self._song_repo.get_by_id(song_id):
            raise LookupError(f"Song {song_id} not found")

        # Backend identity resolution (moved from frontend CW-3)
        # Only resolve if identity_id not already provided (Truth-First)
        identity_service = IdentityService(self._db_path)
        resolved_credits = []
        for c in credits:
            identity_id = c.identity_id or identity_service.resolve_identity_by_name(
                c.name
            )
            resolved_credits.append(
                SpotifyCredit(name=c.name, role=c.role, identity_id=identity_id)
            )

        conn = self._song_repo.get_connection()
        try:
            domain_credits = [
                SongCredit(
                    display_name=c.name, role_name=c.role, identity_id=c.identity_id
                )
                for c in resolved_credits
            ]
            if domain_credits:
                self._credit_repo.insert_credits(song_id, domain_credits, conn=conn)

            domain_pubs = [Publisher(name=p) for p in publishers]
            if domain_pubs:
                self._pub_repo.insert_song_publishers(song_id, domain_pubs, conn=conn)

            conn.commit()
            self._sync_id3_if_enabled(song_id)
        except Exception as e:
            logger.error(f"[EditService] import_credits_bulk FAILED: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def format_entity_field(
        self, field_name: str, value: str, format_type: str = "title"
    ) -> str:
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
        if not song:
            return False

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

            # 4. Cleanup transient staging origin link
            self._staging_repo.clear_origin(song_id, conn)

            return True
        except Exception as e:
            logger.error(f"[EditService] delete_song FAILED: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def move_song_to_library(
        self, song_id: int, library_root_path: Optional[Path] = None
    ) -> str:
        """Orchestrates organization and organization of a song into the library folder."""
        song = self._library_service.get_song(song_id)
        if not song or song.processing_status != ProcessingStatus.REVIEWED:
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

            # Unlink ONLY if there was an actual physical move (bypasses in-place ingestion logic safely)
            try:
                is_same_file = (
                    source_abs_path.resolve() == new_abs_path.resolve()
                    or source_abs_path.samefile(new_abs_path)
                )
            except Exception as e:
                logger.debug(
                    f"[EditService] move_song_to_library file compare failed: {e}"
                )
                is_same_file = False

            if source_abs_path.exists() and not is_same_file:
                source_abs_path.unlink()

            # Origin stays until user confirms deletion OR it's been handled manually.
            # Actually, user wants a reminder. If we clear it here, the reminder is gone.
            # So we keep it.

            return str(new_abs_path.relative_to(library_root))
        except Exception as e:
            logger.error(f"[EditService] move_song_to_library FAILED: {e}")
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
        except Exception as e:
            logger.error(f"[EditService] delete_unlinked_albums FAILED: {e}")
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
                if not self._pub_repo.get_song_ids_by_publisher(
                    pub_id, conn
                ) and not self._pub_repo.get_album_ids_by_publisher(pub_id, conn):
                    if self._pub_repo.soft_delete(pub_id, conn):
                        deleted += 1
            conn.commit()
            return deleted
        except Exception as e:
            logger.error(f"[EditService] delete_unlinked_publishers FAILED: {e}")
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
        except Exception as e:
            logger.error(f"[EditService] delete_unlinked_tags FAILED: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def _sync_id3_if_enabled(self, song_id: int) -> None:
        """Internal trigger for persistent ID3 writing."""
        if not AUTO_SAVE_ID3:
            return
        def _write():
            try:
                song = self._library_service.get_song(song_id)
                if song:
                    self._metadata_writer.write_metadata(song)
            except Exception as e:
                logger.error(f"[EditService] ID3 sync failed: {e}")
        threading.Thread(target=_write, daemon=True).start()

    def delete_original_source(self, song_id: int) -> bool:
        """Physical deletion of the original file linked to this song (e.g. in Downloads)."""
        origin_path = self._staging_repo.get_origin(song_id)
        if not origin_path:
            return False

        if os.path.exists(origin_path):
            try:
                os.remove(origin_path)
                self._staging_repo.clear_origin(song_id)
                logger.info(f"[EditService] Deleted original source: {origin_path}")
                return True
            except Exception as e:
                logger.error(
                    f"[EditService] Failed to delete original source {origin_path}: {e}"
                )
                return False
        else:
            # Path is dead, clear it anyway
            self._staging_repo.clear_origin(song_id)
            return False
