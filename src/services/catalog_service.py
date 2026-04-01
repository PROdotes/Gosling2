# TODO: Split this class into IngestionService, QueryService, EditService — it's 1594 lines
import os
import re
from pathlib import Path
import sqlite3
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.data.album_repository import AlbumRepository
from src.data.song_repository import SongRepository
from src.data.song_credit_repository import SongCreditRepository
from src.data.song_album_repository import SongAlbumRepository
from src.data.publisher_repository import PublisherRepository
from src.data.album_credit_repository import AlbumCreditRepository
from src.data.tag_repository import TagRepository
from src.data.identity_repository import IdentityRepository
from src.models.domain import (
    Song,
    Album,
    SongAlbum,
    Identity,
    Publisher,
    SongCredit,
    AlbumCredit,
    Tag,
)
from src.models.exceptions import ReingestionConflictError
from src.services.logger import logger
from src.utils.audio_hash import calculate_audio_hash
from src.services.metadata_service import MetadataService
from src.services.metadata_parser import MetadataParser
from src.engine.config import (
    STAGING_DIR,
    SCALAR_VALIDATION,
    RENAME_RULES_PATH,
    get_library_root,
)
from src.services.filing_service import FilingService


class CatalogService:
    """Entry point for song access. Stateless orchestrator."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._song_repo = SongRepository(db_path)
        self._album_repo_dir = AlbumRepository(db_path)
        self._credit_repo = SongCreditRepository(db_path)
        self._album_repo = SongAlbumRepository(db_path)
        self._album_credit_repo = AlbumCreditRepository(db_path)
        self._pub_repo = PublisherRepository(db_path)
        self._tag_repo = TagRepository(db_path)
        self._identity_repo = IdentityRepository(db_path)

        # Ingestion Helpers
        self._metadata_service = MetadataService()
        self._metadata_parser = MetadataParser()
        self._filing_service = FilingService(RENAME_RULES_PATH)

    def check_ingestion(self, file_path: str) -> Dict[str, Any]:
        """
        Dry-run ingestion check.
        1. Source Path collision.
        2. Audio Hash collision.
        3. Metadata (Artist, Title, Year) collision.
        """
        logger.debug(f"[CatalogService] -> check_ingestion(file_path='{file_path}')")

        if not os.path.exists(file_path):
            logger.warning(
                f"[CatalogService] <- check_ingestion(file_path='{file_path}') NOT_FOUND"
            )
            return {"status": "ERROR", "message": "File not found"}

        # 1. Path Check (Fastest)
        existing_by_path = self._song_repo.get_by_path(file_path)
        if existing_by_path:
            logger.info(
                f"[CatalogService] <- check_ingestion(file_path='{file_path}') PATH_COLLISION"
            )
            hydrated = self._hydrate_songs([existing_by_path])
            return {
                "status": "ALREADY_EXISTS",
                "match_type": "PATH",
                "message": f"Source path collision: {file_path}",
                "song": hydrated[0] if hydrated else existing_by_path,
            }

        # 2. Hash Check (Requires reading file)
        try:
            audio_hash = calculate_audio_hash(file_path)
        except Exception as e:
            logger.error(
                f"[CatalogService] <- check_ingestion(file_path='{file_path}') HASH_FAILED: {e}"
            )
            return {"status": "ERROR", "message": f"Hash failed: {str(e)}"}

        existing_by_hash = self._song_repo.get_by_hash(audio_hash)
        if existing_by_hash:
            logger.info(
                f"[CatalogService] <- check_ingestion(file_path='{file_path}') HASH_COLLISION"
            )
            hydrated = self._hydrate_songs([existing_by_hash])
            return {
                "status": "ALREADY_EXISTS",
                "match_type": "HASH",
                "message": f"Audio hash collision: {audio_hash}",
                "song": hydrated[0] if hydrated else existing_by_hash,
            }

        # 3. Metadata Extraction & Metadata Collision Check
        try:
            raw_meta = self._metadata_service.extract_metadata(file_path)
            parsed_song = self._metadata_parser.parse(raw_meta, file_path)
            # Ensure the hash is attached for the "potential" record
            parsed_song = parsed_song.model_copy(update={"audio_hash": audio_hash})

            # Extract ALL performer names
            title = parsed_song.title
            performers = []
            if parsed_song.credits:
                performers = [
                    c.display_name
                    for c in parsed_song.credits
                    if c.role_name == "Performer"
                ]

            year = parsed_song.year

            if title and performers:
                # find_by_metadata now handles multiple artists to avoid "Single-Match" false duplicates
                matches = self._song_repo.find_by_metadata(title, performers, year)
                if matches:
                    logger.info(
                        f"[CatalogService] <- check_ingestion(file_path='{file_path}') METADATA_COLLISION"
                    )
                    hydrated = self._hydrate_songs(matches)
                    return {
                        "status": "ALREADY_EXISTS",
                        "match_type": "METADATA",
                        "message": f"Metadata match found: {', '.join(performers)} - {title} ({year})",
                        "song": hydrated[0],
                    }

            # Final return for NEW songs
            logger.info(
                f"[CatalogService] <- check_ingestion(file_path='{file_path}') NEW"
            )
            return {"status": "NEW", "song": parsed_song}
        except Exception as e:
            # Re-signal 409 CONFLICT if the error is a collision that happened during write
            # (Ensures the UI sees the specific Ghost that blocked the commit)
            if "UNIQUE constraint failed" in str(
                e
            ) or "ReingestionConflictError" in str(e):
                from src.engine.exceptions import ReingestionConflictError

                if isinstance(e, ReingestionConflictError):
                    ghost_id = e.ghost_id
                    ghost_data = self._song_repo.get_by_id_including_deleted(ghost_id)
                    return {
                        "status": "CONFLICT",
                        "match_type": "HASH" if "audio_hash" in str(e) else "METADATA",
                        "ghost_id": ghost_id,
                        "staged_path": file_path,
                        "ghost_song": ghost_data,
                        "new_song": parsed_song,  # Show the metadata of the file we dropped
                    }

            logger.error(
                f"[CatalogService] <- check_ingestion(file_path='{file_path}') ERROR: {e}"
            )
            return {"status": "ERROR", "message": f"Metadata failed: {str(e)}"}

    def ingest_file(self, staged_path: str) -> Dict[str, Any]:
        """
        Write path for a staged file.
        1. Check (Hash/Path/Meta collisions).
        2. If NEW, try insertion.
        3. Catch collisions and throw specific errors for Reingestion.
        4. Commit single transaction.
        5. Rollback on failure + cleanup.
        """
        logger.debug(f"[CatalogService] -> ingest_file(path='{staged_path}')")

        # 1. Validation check
        check = self.check_ingestion(staged_path)
        if check["status"] != "NEW":
            logger.info(
                f"[CatalogService] <- ingest_file(path='{staged_path}') REJECTED: {check['status']}"
            )
            # Cleanup staging file for rejected ACTIVE duplicates
            if os.path.exists(staged_path):
                os.remove(staged_path)
                logger.debug(
                    f"[CatalogService] Deleted duplicate staged file: {staged_path}"
                )
            return check

        # 2. Atomic Write
        song = check["song"]
        conn = self._song_repo.get_connection()
        try:
            new_id = self._song_repo.insert(song, conn)
            # Update the returned song object with the new db ID
            hydrated_song = song.model_copy(update={"id": new_id})

            # 3. Simulate enrichment (Virgin 2 -> Enriched 1)
            # This represents the future MusicBrainz background task.
            self._enrich_metadata(new_id, conn)
            hydrated_song = hydrated_song.model_copy(update={"processing_status": 1})

            conn.commit()
            logger.info(
                f"[CatalogService] <- ingest_file(path='{staged_path}') INGESTED ID={new_id} (Status=1)"
            )
            return {"status": "INGESTED", "song": hydrated_song}

        except sqlite3.IntegrityError as e:
            logger.error(f"[CatalogService] IntegrityError during ingestion: {e}")
            conn.rollback()
            # 3. Reactive Conflict Resolution
            # Check if this mismatch was with a ghost Musical Record
            # Truth Discovery: Check hash even if IsDeleted=1
            ghost_meta = self._song_repo.get_source_metadata_by_hash(song.audio_hash)
            if ghost_meta and ghost_meta["is_deleted"]:
                logger.warning(
                    f"[CatalogService] <- Conflict with GHOST ID={ghost_meta['id']}: {ghost_meta['title']}"
                )
                # THROW 409 Exception (Musical sense - "Records" not "records")
                # We do NOT delete the staged file here so it's ready for Phase 2 resolution
                raise ReingestionConflictError(
                    ghost_id=ghost_meta["id"],
                    title=ghost_meta["title"],
                    duration_s=ghost_meta["duration_s"],
                    year=ghost_meta.get("year"),
                    isrc=ghost_meta.get("isrc"),
                )

            # Standard integrity error handling (re-trace existing check)
            logger.error(f"[CatalogService] <- ingest_file() IntegrityError: {e}")
            if os.path.exists(staged_path):
                os.remove(staged_path)
            return {"status": "ERROR", "message": f"Ingestion failed: {str(e)}"}

        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- ingest_file() FAILED: {e}")

            # Prevent orphans: delete staged file on failed ingestion
            if os.path.exists(staged_path):
                os.remove(staged_path)
                logger.warning(
                    f"[CatalogService] Deleted failed staged file: {staged_path}"
                )

            return {"status": "ERROR", "message": f"Ingestion failed: {str(e)}"}
        finally:
            conn.close()

    def _enrich_metadata(self, song_id: int, conn: sqlite3.Connection) -> None:
        """
        Internal sink for metadata enrichment.
        Moves status from 2 (Virgin) -> 1 (Enriched/Ready for Review).
        """
        logger.info(
            f"[CatalogService] -> _enrich_metadata(id={song_id}) [SIMULATED SUCCESS: 2 -> 1]"
        )
        self._song_repo.update_scalars(song_id, {"processing_status": 1}, conn)
        logger.debug(
            f"[CatalogService] <- _enrich_metadata(id={song_id}) Status is now 1"
        )

    def scan_folder(self, folder_path: str, recursive: bool = True) -> List[str]:
        """
        Scan a folder for audio files and return their paths.
        Pure file discovery - no staging or ingestion.

        Args:
            folder_path: Directory to scan
            recursive: Include subdirectories

        Returns:
            List of absolute paths to audio files
        """
        logger.debug(
            f"[CatalogService] -> scan_folder(path='{folder_path}', recursive={recursive})"
        )

        if not os.path.exists(folder_path):
            logger.warning(
                f"[CatalogService] <- scan_folder() FOLDER_NOT_FOUND: {folder_path}"
            )
            return []

        from pathlib import Path
        from src.engine.config import ACCEPTED_EXTENSIONS

        audio_files = []

        if recursive:
            # Walk entire directory tree
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if Path(file).suffix.lower() in ACCEPTED_EXTENSIONS:
                        audio_files.append(os.path.join(root, file))
        else:
            # Only scan top level
            for entry in os.listdir(folder_path):
                file_path = os.path.join(folder_path, entry)
                if os.path.isfile(file_path):
                    if Path(entry).suffix.lower() in ACCEPTED_EXTENSIONS:
                        audio_files.append(file_path)

        logger.debug(
            f"[CatalogService] <- scan_folder() found {len(audio_files)} audio files"
        )
        return audio_files

    def ingest_batch(
        self, file_paths: List[str], max_workers: int = 10
    ) -> Dict[str, Any]:
        """
        Ingest multiple already-staged files in parallel.
        Each file gets its own transaction (one failure doesn't block others).

        Uses ThreadPoolExecutor for concurrent processing (works in web and desktop apps).

        Args:
            file_paths: List of absolute paths to staged files
            max_workers: Maximum number of parallel threads (default: 10)

        Returns:
            BatchIngestReport with aggregate stats and per-file results
        """
        logger.info(
            f"[CatalogService] -> ingest_batch(count={len(file_paths)}, workers={max_workers})"
        )

        results = []
        ingested_count = 0
        duplicate_count = 0
        conflict_count = 0
        error_count = 0

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files for processing
            future_to_path = {
                executor.submit(self._ingest_single, file_path): file_path
                for file_path in file_paths
            }

            # Collect results as they complete
            for future in as_completed(future_to_path):
                file_path = future_to_path[future]
                try:
                    report = future.result()

                    # Track aggregate stats
                    if report["status"] == "INGESTED":
                        ingested_count += 1
                    elif report["status"] == "ALREADY_EXISTS":
                        duplicate_count += 1
                    elif report["status"] == "CONFLICT":
                        conflict_count += 1
                    else:  # ERROR
                        error_count += 1

                    results.append(report)

                except Exception as e:
                    logger.error(
                        f"[CatalogService] Batch item failed: {file_path} - {e}"
                    )
                    error_count += 1
                    results.append(
                        {
                            "status": "ERROR",
                            "message": f"Unexpected error: {str(e)}",
                            "song": None,
                        }
                    )

        logger.info(
            f"[CatalogService] <- ingest_batch() "
            f"total={len(file_paths)} ingested={ingested_count} "
            f"duplicates={duplicate_count} conflicts={conflict_count} errors={error_count}"
        )

        return {
            "total_files": len(file_paths),
            "ingested": ingested_count,
            "duplicates": duplicate_count,
            "conflicts": conflict_count,
            "errors": error_count,
            "results": results,
        }

    def _ingest_single(self, file_path: str) -> Dict[str, Any]:
        """
        Internal wrapper for thread-safe single file ingestion.
        Each thread gets its own database connection.
        """
        try:
            return self.ingest_file(file_path)
        except ReingestionConflictError as e:
            logger.warning(f"[CatalogService] Conflict detected in batch: {file_path}")
            return {
                "status": "CONFLICT",
                "match_type": "HASH",  # Conflicts are always hash-based
                "ghost_id": e.ghost_id,
                "title": e.title,
                "duration_s": e.duration_s,
                "year": e.year,
                "isrc": e.isrc,
                "staged_path": file_path,
                "song": None,
            }
        except Exception as e:
            logger.error(f"[CatalogService] Thread error processing {file_path}: {e}")
            return {
                "status": "ERROR",
                "message": f"Thread error: {str(e)}",
                "song": None,
            }

    def delete_song(self, song_id: int) -> bool:
        """
        Soft-delete a single song by SourceID.
        1. Fetch metadata (need path).
        2. Hard-delete junction/link rows (CASCADE won't fire on UPDATE).
        3. Soft-delete the MediaSources row (IsDeleted = 1).
        4. Physical cleanup ONLY if in staging.
        """
        logger.debug(f"[CatalogService] -> delete_song(id={song_id})")

        # 1. Fetch current info (need path for cleanup)
        song = self._song_repo.get_by_id(song_id)
        if not song:
            logger.warning(f"[CatalogService] <- delete_song(id={song_id}) NOT_FOUND")
            return False

        source_path = song.source_path

        # 2. Database Soft-Delete
        conn = self._song_repo.get_connection()
        try:
            # Hard-delete junction rows first (links die, entities stay)
            self._song_repo.delete_song_links(song_id, conn)

            # Soft-delete the song itself
            success = self._song_repo.soft_delete(song_id, conn)
            if not success:
                logger.warning(
                    f"[CatalogService] <- delete_song(id={song_id}) SOFT_DELETE_FALSE"
                )
                conn.rollback()
                return False

            conn.commit()
            logger.info(f"[CatalogService] <- delete_song(id={song_id}) SOFT_DELETED")

            # 3. Physical File Cleanup (Only after successful DB commit)
            # If path is in staging area, delete the physical file
            if source_path.startswith(str(STAGING_DIR)):
                if os.path.exists(source_path):
                    os.remove(source_path)
                    logger.info(
                        f"[CatalogService] Physical file deleted from staging: {source_path}"
                    )

            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- delete_song(id={song_id}) FAILED: {e}")
            return False
        finally:
            conn.close()

    def resolve_conflict(self, ghost_id: int, staged_path: str) -> Dict[str, Any]:
        """
        Resolve a ghost conflict by re-activating the soft-deleted record with new file metadata.

        1. Extract metadata from the staged file
        2. Update the ghost record (IsDeleted=0, new metadata, keep staged path)
        3. Return the reactivated song

        Note: File stays in staging - no move operation (user moves files manually later).
        """
        logger.info(
            f"[CatalogService] -> resolve_conflict(ghost_id={ghost_id}, staged_path='{staged_path}')"
        )

        if not os.path.exists(staged_path):
            logger.error(f"[CatalogService] Staged file not found: {staged_path}")
            return {"status": "ERROR", "message": "Staged file not found"}

        conn = self._song_repo.get_connection()
        try:
            # 1. Extract metadata from staged file
            raw_meta = self._metadata_service.extract_metadata(staged_path)
            parsed_song = self._metadata_parser.parse(raw_meta, staged_path)
            audio_hash = calculate_audio_hash(staged_path)

            # 2. Create updated song model with ghost_id and staged path
            reactivated_song = parsed_song.model_copy(
                update={
                    "id": ghost_id,
                    "source_path": staged_path,
                    "audio_hash": audio_hash,
                    "is_active": False,  # Stay inactive until library move/publish
                    "processing_status": 1,  # Ready for Review
                }
            )

            # 3. Update the ghost record
            self._song_repo.reactivate_ghost(ghost_id, reactivated_song, conn)

            # 4. Enrich metadata (Simulated enrichment moves 2 -> 1 in DB)
            self._enrich_metadata(ghost_id, conn)

            conn.commit()
            logger.info(
                f"[CatalogService] <- resolve_conflict() REACTIVATED ID={ghost_id} (Status=1)"
            )

            # 4. Return the reactivated song with full hydration
            hydrated_songs = self._hydrate_songs([reactivated_song])
            return {
                "status": "INGESTED",
                "message": "Ghost record reactivated with new metadata",
                "song": hydrated_songs[0] if hydrated_songs else reactivated_song,
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- resolve_conflict() FAILED: {e}")
            return {
                "status": "ERROR",
                "message": f"Conflict resolution failed: {str(e)}",
            }
        finally:
            conn.close()

    def get_song(self, song_id: int) -> Optional[Song]:
        """Fetch a single song and all its credits by ID."""
        logger.debug(f"[CatalogService] -> get_song(id={song_id})")
        song = self._song_repo.get_by_id(song_id)
        if not song:
            logger.warning(f"[CatalogService] <- get_song(id={song_id}) NOT_FOUND")
            return None

        hydrated = self._hydrate_songs([song])
        if not hydrated:
            return None

        result = hydrated[0]
        logger.debug(f"[CatalogService] <- get_song(id={song_id}) '{result.title}'")
        return result

    def get_identity(self, identity_id: int) -> Optional[Identity]:
        """Fetch a full identity tree (Aliases/Members/Groups)."""
        logger.debug(f"[CatalogService] -> get_identity(id={identity_id})")
        identity = self._identity_repo.get_by_id(identity_id)
        if not identity:
            logger.warning(f"[CatalogService] Exit: Identity {identity_id} not found.")
            return None

        hydrated_list = self._hydrate_identities([identity])
        if not hydrated_list:
            return None

        result = hydrated_list[0]
        logger.debug(
            f"[CatalogService] <- get_identity(id={identity_id}) '{result.display_name}'"
        )
        return result

    def get_all_identities(self) -> List[Identity]:
        """Fetch a list of all active identities."""
        logger.debug("[CatalogService] -> get_all_identities()")
        identities = self._identity_repo.get_all_identities()
        result = self._hydrate_identities(identities)
        logger.debug(f"[CatalogService] <- get_all_identities() count={len(result)}")
        return result

    def search_identities(self, query: str) -> List[Identity]:
        """Search for identities by name or alias."""
        logger.debug(f"[CatalogService] -> search_identities(q='{query}')")
        identities = self._identity_repo.search_identities(query)
        result = self._hydrate_identities(identities)
        logger.debug(
            f"[CatalogService] <- search_identities(q='{query}') count={len(result)}"
        )
        return result

    def get_all_publishers(self) -> List[Publisher]:
        """Fetch the full directory of publishers with resolved hierarchies."""
        logger.debug("[CatalogService] -> get_all_publishers()")
        pubs = self._pub_repo.get_all()
        result = self._hydrate_publishers(pubs)
        logger.debug(f"[CatalogService] <- get_all_publishers() count={len(result)}")
        return result

    def get_all_albums(self) -> List[Album]:
        """Fetch the full album directory with hydrated publishers, credits, and songs."""
        logger.debug("[CatalogService] -> get_all_albums()")
        albums = self._album_repo_dir.get_all()
        result = self._hydrate_albums(albums)
        logger.debug(f"[CatalogService] <- get_all_albums() count={len(result)}")
        return result

    def search_albums_slim(self, query: str) -> List[dict]:
        """Slim list-view album search. No tracklist hydration."""
        logger.debug(f"[CatalogService] -> search_albums_slim(q='{query}')")
        rows = self._album_repo_dir.search_slim(query)
        logger.debug(f"[CatalogService] <- search_albums_slim count={len(rows)}")
        return rows

    def get_album(self, album_id: int) -> Optional[Album]:
        """Fetch a single album by ID with hydrated publishers, credits, and songs."""
        logger.debug(f"[CatalogService] -> get_album(id={album_id})")
        album = self._album_repo_dir.get_by_id(album_id)
        if not album:
            logger.warning(f"[CatalogService] <- get_album(id={album_id}) NOT_FOUND")
            return None

        hydrated = self._hydrate_albums([album])
        if not hydrated:
            return None

        result = hydrated[0]
        logger.debug(f"[CatalogService] <- get_album(id={album_id}) '{result.title}'")
        return result

    def search_publishers(self, query: str) -> List[Publisher]:
        """Search for publishers by name match with resolved hierarchies."""
        logger.debug(f"[CatalogService] -> search_publishers(q='{query}')")
        pubs = self._pub_repo.search(query)
        result = self._hydrate_publishers(pubs)
        logger.debug(
            f"[CatalogService] <- search_publishers(q='{query}') count={len(result)}"
        )
        return result

    def get_publisher(self, publisher_id: int) -> Optional[Publisher]:
        """Fetch a single publisher by ID and resolve its full hierarchy."""
        logger.debug(f"[CatalogService] -> get_publisher(id={publisher_id})")
        publisher = self._pub_repo.get_by_id(publisher_id)
        if not publisher:
            logger.warning(
                f"[CatalogService] <- get_publisher(id={publisher_id}) NOT_FOUND"
            )
            return None

        children = self._pub_repo.get_children(publisher_id)
        hydrated_list = self._hydrate_publishers([publisher])
        if not hydrated_list:
            return None

        hydrated = hydrated_list[0]
        result = hydrated.model_copy(update={"sub_publishers": children})
        logger.debug(
            f"[CatalogService] <- get_publisher(id={publisher_id}) '{result.name}'"
        )
        return result

    def get_publisher_songs(self, publisher_id: int) -> List[Song]:
        """Fetch the full song repertoire for a given publisher."""
        logger.debug(f"[CatalogService] -> get_publisher_songs(id={publisher_id})")
        song_ids = self._pub_repo.get_song_ids_by_publisher(publisher_id)
        if not song_ids:
            logger.debug(
                f"[CatalogService] <- get_publisher_songs(id={publisher_id}) NO_REPERTOIRE"
            )
            return []

        songs = self._song_repo.get_by_ids(song_ids)
        result = self._hydrate_songs(songs)
        logger.debug(f"[CatalogService] <- Return count={len(result)}")
        return result

    def get_all_tags(self) -> List[Tag]:
        """Fetch the full directory of tags."""
        logger.debug("[CatalogService] -> get_all_tags()")
        tags = self._tag_repo.get_all()
        logger.debug(f"[CatalogService] <- get_all_tags() count={len(tags)}")
        return tags

    def get_tag_categories(self) -> List[str]:
        """Fetch all distinct tag categories."""
        logger.debug("[CatalogService] -> get_tag_categories()")
        return self._tag_repo.get_categories()

    def search_tags(self, query: str) -> List[Tag]:
        """Search for tags by name match."""
        logger.debug(f"[CatalogService] -> search_tags(q='{query}')")
        tags = self._tag_repo.search(query)
        logger.debug(f"[CatalogService] <- search_tags(q='{query}') count={len(tags)}")
        return tags

    def get_tag(self, tag_id: int) -> Optional[Tag]:
        """Fetch a single tag by ID."""
        logger.debug(f"[CatalogService] -> get_tag(id={tag_id})")
        tag = self._tag_repo.get_by_id(tag_id)
        if not tag:
            logger.warning(f"[CatalogService] <- get_tag(id={tag_id}) NOT_FOUND")
            return None
        logger.debug(f"[CatalogService] <- get_tag(id={tag_id}) '{tag.name}'")
        return tag

    def get_tag_songs(self, tag_id: int) -> List[Song]:
        """Fetch all songs linked to this tag."""
        logger.debug(f"[CatalogService] -> get_tag_songs(id={tag_id})")
        song_ids = self._tag_repo.get_song_ids_by_tag(tag_id)
        if not song_ids:
            logger.debug(f"[CatalogService] <- get_tag_songs(id={tag_id}) NO_SONGS")
            return []

        songs = self._song_repo.get_by_ids(song_ids)
        result = self._hydrate_songs(songs)
        logger.debug(f"[CatalogService] <- Return count={len(result)}")
        return result

    def get_songs_by_identity(self, identity_id: int) -> List[Song]:
        """
        Reverse Credit lookup: Given a seed identity_id, find all related IDs (its aliases + members/groups)
        and return all songs where any of those IDs are credited.
        """
        logger.debug(f"[CatalogService] -> get_songs_by_identity(id={identity_id})")
        identity = self._identity_repo.get_by_id(identity_id)
        if not identity:
            logger.warning(f"[CatalogService] Exit: Identity {identity_id} not found.")
            return []

        related_ids = {identity.id}
        members_by_id = self._identity_repo.get_members_batch([identity.id])
        groups_by_id = self._identity_repo.get_groups_batch([identity.id])

        for member in members_by_id.get(identity.id, []):
            related_ids.add(member.id)
        for group in groups_by_id.get(identity.id, []):
            related_ids.add(group.id)

        songs = self._song_repo.get_by_identity_ids(list(related_ids))
        result = self._hydrate_songs(songs)
        logger.debug(f"[CatalogService] <- Return count={len(result)}")
        return result

    def search_songs_slim(self, query: str) -> List[dict]:
        """Slim list-view search. Returns raw dicts for SongSlimView — no hydration."""
        logger.debug(f"[CatalogService] -> search_songs_slim(q='{query}')")
        rows = self._song_repo.search_slim(query)
        logger.debug(f"[CatalogService] <- search_songs_slim count={len(rows)}")
        return rows

    def search_songs_deep_slim(self, query: str) -> List[dict]:
        """
        Deep slim search. Base matches + identity/publisher expansion, no hydration.
        """
        logger.debug(f"[CatalogService] -> search_songs_deep_slim(q='{query}')")
        base_rows = self._song_repo.search_slim(query)
        seen_ids = {r["SourceID"] for r in base_rows}

        # Identity expansion (Mel B → Spice Girls)
        seeds = self._identity_repo.search_identities(query)
        if seeds:
            identity_ids = {s.id for s in seeds}
            group_ids = self._identity_repo.get_group_ids_for_members(
                list(identity_ids)
            )
            identity_ids.update(group_ids)
            identity_songs = self._song_repo.get_by_identity_ids(list(identity_ids))
            extra_ids = [s.id for s in identity_songs if s.id not in seen_ids]
            if extra_ids:
                extra_rows = self._song_repo.search_slim_by_ids(extra_ids)
                seen_ids.update(r["SourceID"] for r in extra_rows)
                base_rows.extend(extra_rows)

        # Publisher expansion (parent → all sub-labels)
        expanded_pubs = self._pub_repo.search_deep(query)
        if expanded_pubs:
            pub_ids = [p.id for p in expanded_pubs if p.id is not None]
            song_ids = self._pub_repo.get_song_ids_by_publisher_batch(pub_ids)
            extra_ids = [sid for sid in song_ids if sid not in seen_ids]
            if extra_ids:
                extra_rows = self._song_repo.search_slim_by_ids(extra_ids)
                base_rows.extend(extra_rows)

        logger.debug(
            f"[CatalogService] <- search_songs_deep_slim count={len(base_rows)}"
        )
        return base_rows

    def _search_songs_composed(
        self, query: str, initial_songs: List[Song]
    ) -> List[Song]:
        """Internal orchestrator that adds expanded discovery legs to an initial set."""
        seen_ids = {s.id for s in initial_songs}
        songs = list(initial_songs)

        # 1. Identity Expansion (Member -> Group / The Grohlton Check)
        identity_songs = self._expand_identity_songs(query)
        for s in identity_songs:
            if s.id not in seen_ids:
                songs.append(s)
                seen_ids.add(s.id)

        # 2. Publisher Expansion (Parent -> Child / The Corporate Umbrella)
        publisher_songs = self._expand_publisher_songs(query)
        for s in publisher_songs:
            if s.id not in seen_ids:
                songs.append(s)
                seen_ids.add(s.id)

        result = self._hydrate_songs(songs)
        logger.debug(f"[CatalogService] <- composed search results count={len(result)}")
        return result

    def _expand_identity_songs(self, query: str) -> List[Song]:
        """Resolves all songs for identities matching the query, including group memberships."""
        seeds = self._identity_repo.search_identities(query)
        identity_ids = {seed.id for seed in seeds}
        if not identity_ids:
            return []

        # Find encompassing groups (The Upward Leg)
        group_ids = self._identity_repo.get_group_ids_for_members(list(identity_ids))
        identity_ids.update(group_ids)

        return self._song_repo.get_by_identity_ids(list(identity_ids))

    def _expand_publisher_songs(self, query: str) -> List[Song]:
        """Resolves all songs for publishers matching the query, including corporate sub-labels."""
        expanded_publishers = self._pub_repo.search_deep(query)
        if not expanded_publishers:
            return []

        pub_ids = [p.id for p in expanded_publishers if p.id is not None]
        song_ids = self._pub_repo.get_song_ids_by_publisher_batch(pub_ids)
        if not song_ids:
            return []

        return self._song_repo.get_by_ids(song_ids)

    def _hydrate_songs(
        self,
        songs: List[Song],
        pre_albums: Optional[Dict[int, List[SongAlbum]]] = None,
    ) -> List[Song]:
        """Centralized batch hydration for songs and their relations."""
        if not songs:
            return []

        song_ids = [s.id for s in songs if s.id is not None]
        logger.debug(f"[CatalogService] -> _hydrate_songs(count={len(song_ids)})")

        credits_by_song = self._get_credits_by_song(song_ids)
        # OPTIMIZATION: If we already have the album links (e.g. coming from an album view),
        # use them instead of re-querying the DB.
        if pre_albums is not None:
            assocs_by_song = pre_albums
        else:
            assocs_by_song = self._get_albums_by_song(song_ids)

        pubs_by_song = self._get_publishers_by_song(song_ids)
        tags_by_song = self._get_tags_by_song(song_ids)

        hydrated_songs = []
        for song in songs:
            if song.id is None:
                continue
            hydrated_songs.append(
                song.model_copy(
                    update={
                        "credits": credits_by_song.get(song.id, []),
                        "albums": assocs_by_song.get(song.id, []),
                        "publishers": pubs_by_song.get(song.id, []),
                        "tags": tags_by_song.get(song.id, []),
                    }
                )
            )

        logger.debug(f"[CatalogService] <- hydrated {len(hydrated_songs)} songs.")
        return hydrated_songs

    def _hydrate_identities(self, identities: List[Identity]) -> List[Identity]:
        """Centralized batch hydration for identities and their relations."""
        identities = [i for i in identities if i is not None]
        if not identities:
            return []

        identity_ids = [i.id for i in identities]
        logger.debug(
            f"[CatalogService] -> _hydrate_identities(count={len(identity_ids)})"
        )

        aliases_by_id = self._identity_repo.get_aliases_batch(identity_ids)
        members_by_id = self._identity_repo.get_members_batch(identity_ids)
        groups_by_id = self._identity_repo.get_groups_batch(identity_ids)

        hydrated = []
        for identity in identities:
            hydrated.append(
                identity.model_copy(
                    update={
                        "aliases": aliases_by_id.get(identity.id, []),
                        "members": members_by_id.get(identity.id, []),
                        "groups": groups_by_id.get(identity.id, []),
                    }
                )
            )
        logger.debug(f"[CatalogService] <- _hydrate_identities(count={len(hydrated)})")
        return hydrated

    def _hydrate_publishers(self, pubs: List[Publisher]) -> List[Publisher]:
        """Batch-resolve full parent chains for publishers."""
        if not pubs:
            return []

        # Collect all unique seed publisher IDs
        seed_ids = [p.id for p in pubs if p.id is not None]
        logger.debug(f"[CatalogService] -> _hydrate_publishers(count={len(seed_ids)})")

        # FETCH ENTIRE ANCESTRY IN ONE QUERY (CTE)
        full_parent_map = self._pub_repo.get_hierarchy_batch(seed_ids)

        hydrated = []
        for pub in pubs:
            chain = []
            current_id = pub.parent_id
            # Resolve the chain locally from the pre-fetched map
            visited = set()
            while current_id is not None and current_id in full_parent_map:
                if current_id in visited:  # Break cycles just in case
                    break
                visited.add(current_id)
                parent = full_parent_map[current_id]
                chain.append(parent)
                current_id = parent.parent_id

            # The immediate parent is chain[0] if exists
            hydrated.append(
                pub.model_copy(update={"parent_name": chain[0].name if chain else None})
            )

        logger.debug(f"[CatalogService] <- _hydrate_publishers(count={len(hydrated)})")
        return hydrated

    def _hydrate_albums(self, albums: List[Album]) -> List[Album]:
        """Centralized batch hydration for albums and their related songs."""
        if not albums:
            return []

        album_ids = [album.id for album in albums if album.id is not None]
        logger.debug(f"[CatalogService] -> _hydrate_albums(count={len(album_ids)})")

        pubs_by_album = self._get_publishers_by_album(album_ids)
        credits_by_album = self._get_album_credits_by_album(album_ids)
        songs_by_album = self._get_songs_by_album(album_ids)

        hydrated = []
        for album in albums:
            if album.id is None:
                continue
            hydrated.append(
                album.model_copy(
                    update={
                        "publishers": pubs_by_album.get(album.id, []),
                        "credits": credits_by_album.get(album.id, []),
                        "songs": songs_by_album.get(album.id, []),
                    }
                )
            )

        logger.debug(f"[CatalogService] <- _hydrate_albums(count={len(hydrated)})")
        return hydrated

    def _batch_group_by_id(
        self, items: List[Any], id_attr: str
    ) -> Dict[int, List[Any]]:
        """Generic helper to group a list of objects by a specific attribute ID."""
        results: Dict[int, List[Any]] = {}
        for item in items:
            val = getattr(item, id_attr, None)
            if val is not None:
                results.setdefault(val, []).append(item)
        return results

    def _get_credits_by_song(self, song_ids: List[int]) -> Dict[int, List[SongCredit]]:
        """Fetch and group credits by song ID."""
        logger.debug(f"[CatalogService] -> _get_credits_by_song(count={len(song_ids)})")
        all_credits = self._credit_repo.get_credits_for_songs(song_ids)
        results = self._batch_group_by_id(all_credits, "source_id")
        logger.debug(f"[CatalogService] <- _get_credits_by_song(count={len(results)})")
        return results

    def _resolve_publisher_associations(
        self, raw_assocs: List[tuple], entity_label: str
    ) -> Dict[int, List[Publisher]]:
        """Generic helper to hydrate and group publishers for any entity type."""
        if not raw_assocs:
            logger.debug(
                f"[CatalogService] Exit: No publishers found for {entity_label}."
            )
            return {}

        all_found_pubs = [pub for _, pub in raw_assocs]
        hydrated_map: Dict[int, Publisher] = {}
        for p in self._hydrate_publishers(all_found_pubs):
            if p.id is not None:
                hydrated_map[p.id] = p

        results: Dict[int, List[Publisher]] = {}
        for entity_id, pub in raw_assocs:
            if entity_id is not None:
                if pub.id is not None and pub.id in hydrated_map:
                    results.setdefault(entity_id, []).append(hydrated_map[pub.id])
                else:
                    results.setdefault(entity_id, []).append(pub)

        logger.debug(
            f"[CatalogService] <- _resolve_pubs_for_{entity_label}(count={len(results)})"
        )
        return results

    def _get_publishers_by_song(
        self, song_ids: List[int]
    ) -> Dict[int, List[Publisher]]:
        """Fetch and group master publishers by song ID, then resolve hierarchies."""
        logger.debug(
            f"[CatalogService] -> _get_publishers_by_song(count={len(song_ids)})"
        )
        raw_assocs = self._pub_repo.get_publishers_for_songs(song_ids)
        return self._resolve_publisher_associations(raw_assocs, "songs")

    def _get_tags_by_song(self, song_ids: List[int]) -> Dict[int, List[Tag]]:
        """Fetch and group tags by song ID."""
        logger.debug(f"[CatalogService] -> _get_tags_by_song(count={len(song_ids)})")
        all_tags_tuples = self._tag_repo.get_tags_for_songs(song_ids)
        tags_by_song: Dict[int, List[Tag]] = {}
        for song_id, tag in all_tags_tuples:
            if song_id is not None:
                tags_by_song.setdefault(song_id, []).append(tag)
        logger.debug(
            f"[CatalogService] <- _get_tags_by_song(count={len(tags_by_song)})"
        )
        return tags_by_song

    def _get_albums_by_song(self, song_ids: List[int]) -> Dict[int, List[SongAlbum]]:
        """Fetch album associations and hydrate with publishers and credits."""
        logger.debug(f"[CatalogService] -> _get_albums_by_song(count={len(song_ids)})")
        all_assocs = self._album_repo.get_albums_for_songs(song_ids)
        album_ids = [a.album_id for a in all_assocs if a.album_id is not None]

        pubs_by_album = self._get_publishers_by_album(album_ids)
        credits_by_album = self._get_album_credits_by_album(album_ids)

        assocs_by_song: Dict[int, List[SongAlbum]] = {}
        for a in all_assocs:
            if a.source_id is None or a.album_id is None:
                continue
            hydrated_assoc = a.model_copy(
                update={
                    "album_publishers": pubs_by_album.get(a.album_id, []),
                    "credits": credits_by_album.get(a.album_id, []),
                }
            )
            assocs_by_song.setdefault(a.source_id, []).append(hydrated_assoc)

        logger.debug(
            f"[CatalogService] <- _get_albums_by_song(count={len(assocs_by_song)})"
        )
        return assocs_by_song

    def _get_publishers_by_album(
        self, album_ids: List[int]
    ) -> Dict[int, List[Publisher]]:
        """Batch-fetch and hydrate publishers for albums."""
        logger.debug(
            f"[CatalogService] -> _get_publishers_by_album(count={len(album_ids)})"
        )
        if not album_ids:
            return {}
        raw_assocs = self._pub_repo.get_publishers_for_albums(album_ids)
        return self._resolve_publisher_associations(raw_assocs, "albums")

    def _get_album_credits_by_album(
        self, album_ids: List[int]
    ) -> Dict[int, List[AlbumCredit]]:
        """Batch-fetch album credits grouped by album ID."""
        logger.debug(
            f"[CatalogService] -> _get_album_credits_by_album(count={len(album_ids)})"
        )
        if not album_ids:
            return {}
        all_credits = self._album_credit_repo.get_credits_for_albums(album_ids)
        results = self._batch_group_by_id(all_credits, "album_id")
        logger.debug(
            f"[CatalogService] <- _get_album_credits_by_album(count={len(results)})"
        )
        return results

    def _get_songs_by_album(self, album_ids: List[int]) -> Dict[int, List[Song]]:
        """
        RESOLVER: Fetches and hydrates all songs for multiple albums in a single BATCH flow.
        Prevents the N+1 trap where each album individually triggers _hydrate_songs.
        """
        logger.debug(f"[CatalogService] -> _get_songs_by_album(count={len(album_ids)})")
        if not album_ids:
            return {}

        # 1. Fetch all Song/Album associations (Single Repository Query)
        # Using SongAlbumRepository instead of AlbumRepository to get full SongAlbum objects for pre-seeding
        all_assocs = self._album_repo.get_albums_for_songs_reverse(album_ids)
        if not all_assocs:
            return {}

        # 2. Collect unique song IDs and pre-map assocs by song
        unique_song_ids = list(
            dict.fromkeys(a.source_id for a in all_assocs if a.source_id)
        )
        pre_mapped_assocs: Dict[int, List[SongAlbum]] = {}
        for a in all_assocs:
            if a.source_id:
                pre_mapped_assocs.setdefault(a.source_id, []).append(a)

        # 3. Batch Fetch and Hydrate ALL songs in one orchestrator call
        # We pass pre_mapped_assocs to skip the redundant album link query in _hydrate_songs
        all_songs = self._song_repo.get_by_ids(unique_song_ids)
        hydrated_songs = self._hydrate_songs(all_songs, pre_albums=pre_mapped_assocs)

        # 4. Map back to albums
        song_lookup = {s.id: s for s in hydrated_songs if s.id is not None}
        results: Dict[int, List[Song]] = {}
        for a in all_assocs:
            if a.album_id and a.source_id in song_lookup:
                results.setdefault(a.album_id, []).append(song_lookup[a.source_id])

        logger.debug(f"[CatalogService] <- _get_songs_by_album(count={len(results)})")
        return results

    # -------------------------------------------------------------------------
    # CRUD Update Methods
    # -------------------------------------------------------------------------

    _SCALAR_ALLOWED = {
        "media_name",
        "year",
        "bpm",
        "isrc",
        "is_active",
        "processing_status",
        "notes",
    }

    def update_song_scalars(
        self, song_id: int, fields: dict, conn: Optional[sqlite3.Connection] = None
    ) -> Song:
        """
        Update editable scalar fields for a song.
        Validates values per spec rules, then delegates to SongRepository.
        Returns the fully hydrated Song.
        Raises ValueError on validation failure, LookupError if song not found.
        """
        logger.debug(
            f"[CatalogService] -> update_song_scalars(id={song_id}, fields={fields})"
        )

        # source_path is privileged — allowed only for internal filing operations
        allowed = self._SCALAR_ALLOWED | {"source_path"}
        unknown = set(fields) - allowed
        if unknown:
            logger.warning(
                f"[CatalogService] <- update_song_scalars(id={song_id}) INVALID_FIELDS {unknown}"
            )
            raise ValueError(f"Non-editable fields: {unknown}")

        # --- Workflow Validation ---
        needs_song = (
            fields.get("is_active") is True or fields.get("processing_status") == 0
        )
        if needs_song:
            song = self.get_song(song_id)
            if not song:
                logger.warning(
                    f"[CatalogService] <- update_song_scalars(id={song_id}) NOT_FOUND"
                )
                raise LookupError(f"Song {song_id} not found")

            if fields.get("processing_status") == 0:
                from src.models.view_models import SongView

                view = SongView.from_domain(song)
                blockers = view.review_blockers
                if blockers:
                    logger.info(
                        f"[CatalogService] Branch: Blocked review approval - Song {song_id} missing: {blockers}"
                    )
                    raise ValueError(
                        f"Cannot mark as reviewed, missing: {', '.join(blockers)}"
                    )
                logger.debug(
                    f"[CatalogService] Branch: Song {song_id} passes review checks. Approval allowed."
                )

            if fields.get("is_active") is True:
                status = fields.get("processing_status", song.processing_status)
                if status != 0:
                    logger.info(
                        f"[CatalogService] Branch: Blocked activation - Song {song_id} status is {status}"
                    )
                    raise ValueError(
                        "Cannot activate song unless processing_status is 0 (Reviewed)"
                    )
                logger.debug(
                    f"[CatalogService] Branch: Song {song_id} is reviewed (Status 0). Activation allowed."
                )

        # Validate
        import datetime

        if "media_name" in fields:
            if not fields["media_name"] or not str(fields["media_name"]).strip():
                raise ValueError("media_name cannot be empty")
        if "year" in fields and fields["year"] is not None:
            year = int(fields["year"])
            year_rules = SCALAR_VALIDATION["year"]
            max_year = datetime.date.today().year + year_rules["max_offset"]
            if not (year_rules["min"] <= year <= max_year):
                raise ValueError(
                    f"year must be between {year_rules['min']} and {max_year}"
                )
            fields = {**fields, "year": year}
        if "bpm" in fields and fields["bpm"] is not None:
            bpm = int(fields["bpm"])
            bpm_rules = SCALAR_VALIDATION["bpm"]
            if not (bpm_rules["min"] <= bpm <= bpm_rules["max"]):
                raise ValueError(
                    f"bpm must be between {bpm_rules['min']} and {bpm_rules['max']}"
                )
            fields = {**fields, "bpm": bpm}
        if "isrc" in fields and fields["isrc"] is not None:
            isrc_rules = SCALAR_VALIDATION["isrc"]
            isrc = str(fields["isrc"]).replace(isrc_rules["strip"], "").upper().strip()
            if not re.match(isrc_rules["pattern"], isrc):
                raise ValueError(
                    "isrc must be 12 characters: 2-letter country, 3-char registrant, 2-digit year, 5-digit designation"
                )
            fields = {**fields, "isrc": isrc}

        conn = self._song_repo.get_connection()
        try:
            self._song_repo.update_scalars(song_id, fields, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(
                f"[CatalogService] <- update_song_scalars(id={song_id}) FAILED: {e}"
            )
            raise
        finally:
            conn.close()

        song = self.get_song(song_id)
        if not song:
            raise LookupError(f"Song {song_id} not found after update")
        logger.debug(f"[CatalogService] <- update_song_scalars(id={song_id}) OK")
        return song

    # --- Credits ---

    def get_all_roles(self) -> list[str]:
        return self._credit_repo.get_all_roles()

    def add_song_credit(
        self,
        song_id: int,
        display_name: str,
        role_name: str,
        identity_id: Optional[int] = None,
    ) -> SongCredit:
        """
        Add artist credit to a song. Get-or-create artist name and role.
        Supports explicit identity_id for Truth-First linking.
        """
        logger.debug(
            f"[CatalogService] -> add_song_credit(song_id={song_id}, name='{display_name}', role='{role_name}', identity_id={identity_id})"
        )
        conn = self._credit_repo.get_connection()
        try:
            credit = self._credit_repo.add_credit(
                song_id, display_name, role_name, conn, identity_id=identity_id
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- add_song_credit FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug(
            f"[CatalogService] <- add_song_credit OK credit_id={credit.credit_id}"
        )
        return credit

    def remove_song_credit(self, song_id: int, credit_id: int) -> None:
        """Remove a credit link from a song. Keeps the artist name record."""
        logger.debug(
            f"[CatalogService] -> remove_song_credit(song_id={song_id}, credit_id={credit_id})"
        )
        conn = self._credit_repo.get_connection()
        try:
            self._credit_repo.remove_credit(credit_id, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- remove_song_credit FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug("[CatalogService] <- remove_song_credit OK")

    def update_credit_name(self, name_id: int, new_name: str) -> None:
        """Update an artist's display name globally (affects all linked songs)."""
        logger.debug(
            f"[CatalogService] -> update_credit_name(name_id={name_id}, new_name='{new_name}')"
        )
        if not new_name or not new_name.strip():
            raise ValueError("Artist name cannot be empty")
        conn = self._credit_repo.get_connection()
        try:
            self._credit_repo.update_credit_name(name_id, new_name, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- update_credit_name FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug("[CatalogService] <- update_credit_name OK")

    # --- Albums ---

    def add_song_album(
        self,
        song_id: int,
        album_id: int,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
    ) -> SongAlbum:
        """Link an existing album to a song."""
        logger.debug(
            f"[CatalogService] -> add_song_album(song_id={song_id}, album_id={album_id})"
        )
        
        # 1. Existence Checks
        if not self._song_repo.get_by_id(song_id):
            raise LookupError(f"Song {song_id} not found")
        if not self._album_repo_dir.get_by_id(album_id):
            raise LookupError(f"Album {album_id} not found")

        conn = self._album_repo.get_connection()
        try:
            self._album_repo.add_album(
                song_id, album_id, track_number, disc_number, conn
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback() # Assume duplicate or conflict
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- add_song_album FAILED: {e}")
            raise
        finally:
            conn.close()
            
        links = self._album_repo.get_albums_for_songs([song_id])
        song_album = next((link for link in links if link.album_id == album_id), None)
        return song_album

    def create_and_link_album(
        self,
        song_id: int,
        album_data: dict,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
    ) -> SongAlbum:
        """Create a new album record and link it to a song (single transaction)."""
        logger.debug(f"[CatalogService] -> create_and_link_album(song_id={song_id})")
        
        # 1. Validation
        title = album_data.get("title", "").strip()
        if not title:
            raise ValueError("Album title cannot be empty")
            
        # 2. Existence Check (Fail Loudly with LookupError)
        song = self._song_repo.get_by_id(song_id)
        if not song:
            raise LookupError(f"Song {song_id} not found")

        # 3. Atomic Write
        conn = self._album_repo_dir.get_connection()
        try:
            # create_album handles reactivation internally
            album_id = self._album_repo_dir.create_album(
                title,
                album_data.get("album_type"),
                album_data.get("release_year"),
                conn,
            )
            # Link the album
            self._album_repo.add_album(
                song_id, album_id, track_number, disc_number, conn
            )
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- create_and_link_album FAILED: {e}")
            raise LookupError(f"Persistence failure: {e}")
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

        # 4. Hydration & Return
        links = self._album_repo.get_albums_for_songs([song_id])
        song_album = next((link for link in links if link.album_id == album_id), None)
        if not song_album:
             raise LookupError(f"Failed to retrieve link for song {song_id} after creation")
             
        logger.debug(f"[CatalogService] <- create_and_link_album OK album_id={album_id}")
        return song_album

    def remove_song_album(self, song_id: int, album_id: int) -> None:
        """Unlink a song from an album. Keeps the album record."""
        logger.debug(
            f"[CatalogService] -> remove_song_album(song_id={song_id}, album_id={album_id})"
        )
        conn = self._album_repo.get_connection()
        try:
            self._album_repo.remove_album(song_id, album_id, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- remove_song_album FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug("[CatalogService] <- remove_song_album OK")

    def update_song_album_link(
        self,
        song_id: int,
        album_id: int,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
    ) -> None:
        """Update track/disc numbers for a song-album link."""
        logger.debug(
            f"[CatalogService] -> update_song_album_link(song_id={song_id}, album_id={album_id})"
        )
        
        # 1. Existence Check
        links = self._album_repo.get_albums_for_songs([song_id])
        if not any(link.album_id == album_id for link in links):
            raise LookupError(f"Link between song {song_id} and album {album_id} not found")

        conn = self._album_repo.get_connection()
        try:
            self._album_repo.update_track_info(
                song_id, album_id, track_number, disc_number, conn
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- update_song_album_link FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug("[CatalogService] <- update_song_album_link OK")

    def update_album(self, album_id: int, album_data: dict) -> Album:
        """Update album record fields. Affects all linked songs globally."""
        logger.debug(f"[CatalogService] -> update_album(album_id={album_id})")
        
        # 1. Validation
        if "title" in album_data and not album_data["title"].strip():
             raise ValueError("Album title cannot be empty")
             
        # 2. Existence Check
        if not self._album_repo_dir.get_by_id(album_id):
            raise LookupError(f"Album {album_id} not found")

        conn = self._album_repo_dir.get_connection()
        try:
            self._album_repo_dir.update_album(album_id, album_data, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- update_album FAILED: {e}")
            raise
        finally:
            conn.close()
        return self.get_album(album_id)

    def add_album_credit(
        self,
        album_id: int,
        display_name: str,
        role_name: str = "Performer",
        identity_id: Optional[int] = None,
    ) -> int:
        """Add a credited artist to an album. Get-or-create artist name. Returns name_id."""
        logger.debug(
            f"[CatalogService] -> add_album_credit(album_id={album_id}, name='{display_name}', role='{role_name}', identity_id={identity_id})"
        )
        
        # 1. Existence Check
        if not self._album_repo_dir.get_by_id(album_id):
             raise LookupError(f"Album {album_id} not found")
        if identity_id and not self._identity_repo.get_by_id(identity_id):
             raise LookupError(f"Identity {identity_id} not found")

        conn = self._album_credit_repo.get_connection()
        try:
            name_id = self._album_credit_repo.add_credit(
                album_id, display_name, role_name, conn, identity_id
            )
            conn.commit()
            return name_id
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- add_album_credit FAILED: {e}")
            raise
        finally:
            conn.close()

    def remove_album_credit(self, album_id: int, artist_name_id: int) -> None:
        """Remove a credited artist from an album."""
        logger.debug(
            f"[CatalogService] -> remove_album_credit(album_id={album_id}, name_id={artist_name_id})"
        )
        conn = self._album_credit_repo.get_connection()
        try:
            self._album_credit_repo.remove_credit(album_id, artist_name_id, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- remove_album_credit FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug("[CatalogService] <- remove_album_credit OK")

    def add_album_publisher(
        self,
        album_id: int,
        publisher_name: Optional[str],
        publisher_id: Optional[int] = None,
    ) -> Publisher:
        """Add a publisher link for an album. Links by ID if publisher_id provided, otherwise get-or-creates by name."""
        logger.debug(
            f"[CatalogService] -> add_album_publisher(album_id={album_id}, publisher='{publisher_name or publisher_id}')"
        )
        
        # 1. Existence Check
        if not self._album_repo_dir.get_by_id(album_id):
            raise LookupError(f"Album {album_id} not found")

        if publisher_id is not None:
            existing = self._pub_repo.get_by_id(publisher_id)
            if not existing:
                raise LookupError(f"Publisher {publisher_id} not found")
            publisher_name = existing.name
        else:
            if not publisher_name:
                raise ValueError(
                    "publisher_name is required when publisher_id is not provided"
                )
            publisher_name = publisher_name.strip()
        conn = self._pub_repo.get_connection()
        try:
            publisher = self._pub_repo.add_album_publisher(
                album_id, publisher_name, conn
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- add_album_publisher FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug(
            f"[CatalogService] <- add_album_publisher OK pub_id={publisher.id}"
        )
        return publisher

    def remove_album_publisher(self, album_id: int, publisher_id: int) -> None:
        """Remove a publisher link from an album. Keeps the publisher record."""
        logger.debug(
            f"[CatalogService] -> remove_album_publisher(album_id={album_id}, pub_id={publisher_id})"
        )
        conn = self._pub_repo.get_connection()
        try:
            self._pub_repo.remove_album_publisher(album_id, publisher_id, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- remove_album_publisher FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug("[CatalogService] <- remove_album_publisher OK")

    # --- Tags ---

    def add_song_tag(
        self,
        song_id: int,
        tag_name: Optional[str],
        category: Optional[str],
        tag_id: Optional[int] = None,
    ) -> Tag:
        """Add a tag to a song. Links by ID if tag_id provided, otherwise get-or-creates by name+category."""
        if tag_id is not None:
            existing = self._tag_repo.get_by_id(tag_id)
            if not existing:
                raise LookupError(f"Tag {tag_id} not found")
            tag_name = existing.name
            category = existing.category
        else:
            if not tag_name or not category:
                raise ValueError(
                    "tag_name and category are required when tag_id is not provided"
                )
            tag_name = tag_name.strip()
            category = category.strip()

        logger.debug(
            f"[CatalogService] -> add_song_tag(song_id={song_id}, tag='{tag_name}', cat='{category}')"
        )
        conn = self._tag_repo.get_connection()
        try:
            tag = self._tag_repo.add_tag(song_id, tag_name, category, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- add_song_tag FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug(f"[CatalogService] <- add_song_tag OK tag_id={tag.id}")
        return tag

    def remove_song_tag(self, song_id: int, tag_id: int) -> None:
        """Remove a tag link from a song. Keeps the tag record."""
        logger.debug(
            f"[CatalogService] -> remove_song_tag(song_id={song_id}, tag_id={tag_id})"
        )
        conn = self._tag_repo.get_connection()
        try:
            self._tag_repo.remove_tag(song_id, tag_id, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- remove_song_tag FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug("[CatalogService] <- remove_song_tag OK")

    def update_tag(self, tag_id: int, new_name: str, new_category: str) -> None:
        """Update tag name/category globally (affects all linked songs)."""
        logger.debug(f"[CatalogService] -> update_tag(tag_id={tag_id})")
        if not new_name or not new_name.strip():
            raise ValueError("Tag name cannot be empty")
        conn = self._tag_repo.get_connection()
        try:
            self._tag_repo.update_tag(tag_id, new_name, new_category, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- update_tag FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug("[CatalogService] <- update_tag OK")

    # --- Publishers ---

    def add_song_publisher(
        self,
        song_id: int,
        publisher_name: Optional[str],
        publisher_id: Optional[int] = None,
    ) -> Publisher:
        """Add a publisher link to a song. Links by ID if publisher_id provided, otherwise get-or-creates by name."""
        if publisher_id is not None:
            existing = self._pub_repo.get_by_id(publisher_id)
            if not existing:
                raise LookupError(f"Publisher {publisher_id} not found")
            publisher_name = existing.name
        else:
            if not publisher_name:
                raise ValueError(
                    "publisher_name is required when publisher_id is not provided"
                )
            publisher_name = publisher_name.strip()

        logger.debug(
            f"[CatalogService] -> add_song_publisher(song_id={song_id}, publisher='{publisher_name}')"
        )
        conn = self._pub_repo.get_connection()
        try:
            publisher = self._pub_repo.add_song_publisher(song_id, publisher_name, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- add_song_publisher FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug(f"[CatalogService] <- add_song_publisher OK pub_id={publisher.id}")
        return publisher

    def remove_song_publisher(self, song_id: int, publisher_id: int) -> None:
        """Remove a publisher link from a song. Keeps the publisher record."""
        logger.debug(
            f"[CatalogService] -> remove_song_publisher(song_id={song_id}, pub_id={publisher_id})"
        )
        conn = self._pub_repo.get_connection()
        try:
            self._pub_repo.remove_song_publisher(song_id, publisher_id, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- remove_song_publisher FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug("[CatalogService] <- remove_song_publisher OK")

    def update_publisher(self, publisher_id: int, new_name: str) -> None:
        """Update publisher name globally (affects all linked songs)."""
        logger.debug(f"[CatalogService] -> update_publisher(pub_id={publisher_id})")
        if not new_name or not new_name.strip():
            raise ValueError("Publisher name cannot be empty")
        conn = self._pub_repo.get_connection()
        try:
            self._pub_repo.update_publisher(publisher_id, new_name, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- update_publisher FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug("[CatalogService] <- update_publisher OK")

    def set_publisher_parent(self, publisher_id: int, parent_id: Optional[int]) -> None:
        """Set or clear the parent of a publisher."""
        logger.debug(
            f"[CatalogService] -> set_publisher_parent(pub_id={publisher_id}, parent_id={parent_id})"
        )
        conn = self._pub_repo.get_connection()
        try:
            self._pub_repo.set_parent(publisher_id, parent_id, conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CatalogService] <- set_publisher_parent FAILED: {e}")
            raise
        finally:
            conn.close()
        logger.debug("[CatalogService] <- set_publisher_parent OK")

    def get_id3_frames_config(self) -> Dict[str, Any]:
        """Returns the ID3 frame configuration from the parser (Single Source of Truth)."""
        return self._metadata_parser.config

    def move_song_to_library(self, song_id: int) -> str:
        """
        Orchestrates the move of a song from staging (or anywhere) to the organized library.
        Updates the SourcePath in the database to the new absolute path.
        Returns the new relative path for UI display.
        """
        logger.info(f"[CatalogService] -> move_song_to_library(id={song_id})")

        # 1. Fetch hydrated song
        song = self.get_song(song_id)
        if not song:
            logger.warning(
                f"[CatalogService] <- move_song_to_library(id={song_id}) NOT_FOUND"
            )
            raise LookupError(f"Song {song_id} not found")

        # 0. State Guard: Only Reviewed songs can be moved
        if song.processing_status != 0:
            logger.warning(
                f"[CatalogService] <- move_song_to_library(id={song_id}) REJECTED: Not in Reviewed state (Status {song.processing_status})"
            )
            raise ValueError(
                f"Cannot move song {song_id}: Must be in 'Reviewed' state (Status 0) first."
            )

        # 2. Stage 1: Copy to Library (Preserve source for safety)
        library_root = Path(get_library_root())
        source_abs_path = Path(song.source_path)
        try:
            # We copy first, original remains in staging as backup
            new_abs_path = self._filing_service.copy_to_library(song, library_root)
        except Exception as e:
            logger.error(f"[CatalogService] Copy phase failed: {e}")
            raise e

        # 3. Stage 2: Commit to Database
        try:
            updates = {"source_path": str(new_abs_path)}
            self.update_song_scalars(song_id, updates)
        except Exception as db_err:
            # ROLLBACK: If DB update fails, delete the LIBRARY CLONE.
            # Staging source remains untouched.
            logger.critical(
                f"[CatalogService] DB Update failed! PURGING library clone: {new_abs_path}"
            )
            try:
                if new_abs_path.exists():
                    new_abs_path.unlink()
            except Exception as unlink_err:
                logger.critical(
                    f"[CatalogService] COULD NOT PURGE CLONE at {new_abs_path}: {unlink_err}"
                )
            raise db_err

        # 4. Stage 3: Cleanup (Remove source from staging now that DB is committed)
        try:
            if source_abs_path.exists():
                source_abs_path.unlink()
                logger.info(
                    f"[CatalogService] Successfully unlinked staging source: {source_abs_path}"
                )
        except Exception as cleanup_err:
            # This is non-fatal to the workflow, but we should log it.
            # The file is moved, indexed, but an orphan remains in staging.
            logger.warning(
                f"[CatalogService] Cleanup failed! Source orphan remains in staging: {cleanup_err}"
            )

        # 4. Calculate relative path for UI
        relative = os.path.relpath(new_abs_path, library_root)

        logger.info(
            f"[CatalogService] <- move_song_to_library(id={song_id}) OK -> {relative}"
        )
        return relative
