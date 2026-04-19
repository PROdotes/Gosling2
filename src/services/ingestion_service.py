import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.data.song_repository import SongRepository
from src.data.album_repository import AlbumRepository
from src.data.song_credit_repository import SongCreditRepository
from src.data.song_album_repository import SongAlbumRepository
from src.data.publisher_repository import PublisherRepository
from src.data.tag_repository import TagRepository
from src.data.identity_repository import IdentityRepository
from src.models.exceptions import ReingestionConflictError
from src.services.logger import logger
from src.utils.audio_hash import calculate_audio_hash
from src.services.metadata_service import MetadataService
from src.services.metadata_parser import MetadataParser
from src.services.filing_service import FilingService
from src.services.metadata_writer import MetadataWriter
from src.services.library_service import LibraryService
from src.engine.config import (
    RENAME_RULES_PATH,
    get_db_path,
    ProcessingStatus,
)


class IngestionService:
    """Specialized orchestrator for checking, writing, and batching audio file ingestion."""

    # Class-level state to ensure persistence across CatalogService re-instantiation
    _active_tasks: Dict[str, Dict[str, Any]] = {}
    _session_success: int = 0
    _session_action: int = 0

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

        # Cross-service dependencies
        self._library_service = library_service or LibraryService(db_path)

        # Ingestion Helpers
        self._metadata_service = MetadataService()
        self._metadata_parser = MetadataParser()
        self._filing_service = FilingService(RENAME_RULES_PATH)
        self._metadata_writer = MetadataWriter()

    def get_session_status(self) -> Dict[str, int]:
        """Return the 'Whole Model' for the UI: {pending, success, action}."""
        pending = sum(
            t["total"] - t["processed"] for t in IngestionService._active_tasks.values()
        )
        return {
            "pending": max(0, pending),
            "success": IngestionService._session_success,
            "action": IngestionService._session_action,
        }

    def register_task(self, task_id: str, total: int) -> None:
        """Register a new ingestion batch task."""
        IngestionService._active_tasks[task_id] = {
            "total": total,
            "processed": 0,
            "ingested": 0,
            "duplicates": 0,
            "conflicts": 0,
            "errors": 0,
            "results": [],
        }

    def _update_task(self, task_id: str, status_delta: str):
        """Update the internal counters."""
        if task_id not in IngestionService._active_tasks:
            return

        task = IngestionService._active_tasks[task_id]
        if status_delta == "INGESTED":
            task["ingested"] += 1
            IngestionService._session_success += 1
        elif status_delta == "ALREADY_EXISTS":
            task["duplicates"] += 1
            IngestionService._session_action += 1
        elif status_delta == "CONFLICT":
            task["conflicts"] += 1
            IngestionService._session_action += 1
        elif status_delta == "ERROR":
            task["errors"] += 1
            IngestionService._session_action += 1
        elif status_delta == "PENDING_CONVERT":
            IngestionService._session_action += 1

        task["processed"] += 1
        if task["processed"] >= task["total"]:
            logger.info(f"[IngestionService] Task {task_id} completed: {task}")
            del IngestionService._active_tasks[task_id]

    @classmethod
    def reset_session_status(cls):
        """Reset the session counters."""
        cls._session_success = 0
        cls._session_action = 0

    def check_ingestion(self, file_path: str) -> Dict[str, Any]:
        """
        Dry-run ingestion check.
        1. Source Path collision.
        2. Audio Hash collision.
        3. Metadata (Artist, Title, Year) collision.
        """
        logger.debug(f"[IngestionService] -> check_ingestion(file_path='{file_path}')")

        if not os.path.exists(file_path):
            logger.warning(
                f"[IngestionService] <- check_ingestion(file_path='{file_path}') NOT_FOUND"
            )
            return {"status": "ERROR", "message": "File not found"}

        # 1. Path Check (Fastest)
        existing_by_path = self._song_repo.get_by_path(file_path)
        if existing_by_path:
            logger.info(
                f"[IngestionService] <- check_ingestion(file_path='{file_path}') PATH_COLLISION"
            )
            # Use LibraryService for hydration to maintain bit-perfect domain models
            hydrated = self._library_service._hydrate_songs([existing_by_path])

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
                f"[IngestionService] <- check_ingestion(file_path='{file_path}') HASH_FAILED: {e}"
            )
            return {"status": "ERROR", "message": f"Hash failed: {str(e)}"}

        existing_by_hash = self._song_repo.get_by_hash(audio_hash)
        if existing_by_hash:
            logger.info(
                f"[IngestionService] <- check_ingestion(file_path='{file_path}') HASH_COLLISION"
            )
            hydrated = self._library_service._hydrate_songs([existing_by_hash])

            return {
                "status": "ALREADY_EXISTS",
                "match_type": "HASH",
                "message": f"Audio hash collision: {audio_hash}",
                "song": hydrated[0] if hydrated else existing_by_hash,
            }

        ghost_by_hash = self._song_repo.get_source_metadata_by_hash(audio_hash)
        if ghost_by_hash and ghost_by_hash.get("is_deleted"):
            return {
                "status": "CONFLICT",
                "match_type": "HASH",
                "ghost_id": ghost_by_hash["id"],
                "staged_path": file_path,
                "title": ghost_by_hash.get("title", "Unknown"),
                "ghost_song": ghost_by_hash,
                "new_song": None,
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
                matches = self._song_repo.find_by_metadata(title, performers, year)
                if matches:
                    logger.info(
                        f"[IngestionService] <- check_ingestion(file_path='{file_path}') METADATA_COLLISION"
                    )
                    hydrated = self._library_service._hydrate_songs(matches)

                    return {
                        "status": "ALREADY_EXISTS",
                        "match_type": "METADATA",
                        "message": f"Metadata match found: {', '.join(performers)} - {title} ({year})",
                        "song": hydrated[0],
                    }

            # Final return for NEW songs
            logger.info(
                f"[IngestionService] <- check_ingestion(file_path='{file_path}') NEW"
            )
            return {"status": "NEW", "song": parsed_song}
        except Exception as e:
            logger.error(f"[IngestionService] check_ingestion internal error: {e}")
            return {"status": "ERROR", "message": f"Metadata failed: {str(e)}"}

    def ingest_wav_as_converting(self, staged_path: str) -> Dict[str, Any]:
        """
        Ingest a WAV file immediately with processing_status=3 (Converting).
        """
        logger.debug(
            f"[IngestionService] -> ingest_wav_as_converting(path='{staged_path}')"
        )

        check = self.check_ingestion(staged_path)
        if check["status"] != "NEW":
            logger.info(
                f"[IngestionService] <- ingest_wav_as_converting(path='{staged_path}') REJECTED: {check['status']}"
            )
            if check["status"] != "CONFLICT" and os.path.exists(staged_path):
                os.remove(staged_path)
            return check

        song = check["song"]
        song = song.model_copy(update={"processing_status": ProcessingStatus.CONVERTING})
        conn = self._song_repo.get_connection()
        try:
            new_id = self._song_repo.insert(song, conn)
            hydrated_song = song.model_copy(update={"id": new_id})
            conn.commit()
            logger.info(
                f"[IngestionService] <- ingest_wav_as_converting(path='{staged_path}') INGESTED ID={new_id} (Status={ProcessingStatus.CONVERTING})"
            )
            return {"status": "CONVERTING", "song": hydrated_song}
        except Exception as e:
            conn.rollback()
            logger.error(
                f"[IngestionService] <- ingest_wav_as_converting() FAILED: {e}"
            )
            if os.path.exists(staged_path):
                os.remove(staged_path)
            return {"status": "ERROR", "message": f"Ingestion failed: {str(e)}"}
        finally:
            conn.close()

    def finalize_wav_conversion(self, song_id: int, mp3_path: str) -> int:
        """
        Called after background WAV→MP3 conversion completes.
        Updates the record and handles potential ghost reactivations.
        """
        logger.debug(
            f"[IngestionService] -> finalize_wav_conversion(id={song_id}, mp3='{mp3_path}')"
        )
        mp3_hash = calculate_audio_hash(mp3_path)

        # Check if another record already has this MP3 hash (including soft-deleted)
        existing = self._song_repo.get_source_metadata_by_hash(mp3_hash)
        if existing and existing["id"] != song_id:
            if existing["is_deleted"]:
                # Reactivate the ghost with the new MP3 path
                logger.info(
                    f"[IngestionService] <- finalize_wav_conversion(id={song_id}) GHOST: reactivating ID={existing['id']}"
                )
                conn = self._song_repo.get_connection()
                try:
                    raw_meta = self._metadata_service.extract_metadata(mp3_path)
                    parsed_song = self._metadata_parser.parse(raw_meta, mp3_path)
                    reactivated = parsed_song.model_copy(
                        update={
                            "id": existing["id"],
                            "source_path": mp3_path,
                            "audio_hash": mp3_hash,
                            "is_active": False,
                            "processing_status": ProcessingStatus.NEEDS_REVIEW,
                        }
                    )
                    self._song_repo.reactivate_ghost(existing["id"], reactivated, conn)
                    self._song_repo.hard_delete(song_id, conn)
                    conn.commit()
                    return existing["id"]
                except Exception as ex:
                    conn.rollback()
                    logger.error(
                        f"[IngestionService] <- finalize_wav_conversion() reactivate failed: {ex}"
                    )
                    return song_id
                finally:
                    conn.close()
            else:
                # Active duplicate — discard the new record
                logger.warning(
                    f"[IngestionService] <- finalize_wav_conversion(id={song_id}) DUPLICATE: MP3 hash already owned by ID={existing['id']}, deleting new record"
                )
                conn = self._song_repo.get_connection()
                try:
                    self._song_repo.hard_delete(song_id, conn)
                    conn.commit()
                except Exception as ex:
                    conn.rollback()
                    logger.error(
                        f"[IngestionService] <- finalize_wav_conversion() hard_delete failed: {ex}"
                    )
                finally:
                    conn.close()
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                return existing["id"]

        conn = self._song_repo.get_connection()
        try:
            self._song_repo.update_scalars(
                song_id,
                {
                    "source_path": mp3_path,
                    "processing_status": ProcessingStatus.PENDING_ENRICHMENT,
                    "audio_hash": mp3_hash,
                },
                conn,
            )
            self._enrich_metadata(song_id, conn)
            conn.commit()
            logger.info(
                f"[IngestionService] <- finalize_wav_conversion(id={song_id}) Status now {ProcessingStatus.NEEDS_REVIEW}"
            )
            return song_id
        except Exception as e:
            conn.rollback()
            logger.error(f"[IngestionService] <- finalize_wav_conversion() FAILED: {e}")
            return song_id
        finally:
            conn.close()

    def ingest_file(self, staged_path: str) -> Dict[str, Any]:
        """
        Write path for a staged file. Handles collisions and single transaction.
        """
        logger.debug(f"[IngestionService] -> ingest_file(path='{staged_path}')")

        # 1. Validation check
        check = self.check_ingestion(staged_path)
        if check["status"] != "NEW":
            logger.info(
                f"[IngestionService] <- ingest_file(path='{staged_path}') REJECTED: {check['status']}"
            )

            if check["status"] == "CONFLICT":
                raise ReingestionConflictError(
                    ghost_id=check["ghost_id"],
                    title=check["ghost_song"]["title"],
                    duration_s=check["ghost_song"]["duration_s"],
                    year=check["ghost_song"].get("year"),
                    isrc=check["ghost_song"].get("isrc"),
                )

            if os.path.exists(staged_path) and check["status"] not in (
                "CONFLICT",
                "PENDING_CONVERT",
            ):
                os.remove(staged_path)
            return check

        # 2. Atomic Write
        song = check["song"]
        conn = self._song_repo.get_connection()
        try:
            new_id = self._song_repo.insert(song, conn)
            hydrated_song = song.model_copy(update={"id": new_id})
            self._enrich_metadata(new_id, conn)
            hydrated_song = hydrated_song.model_copy(update={"processing_status": ProcessingStatus.NEEDS_REVIEW})
            conn.commit()
            logger.info(
                f"[IngestionService] <- ingest_file(path='{staged_path}') INGESTED ID={new_id}"
            )
            return {"status": "INGESTED", "song": hydrated_song}
        except Exception as e:
            conn.rollback()
            # Catch hash conflict with ghost
            ghost_meta = self._song_repo.get_source_metadata_by_hash(song.audio_hash)
            if ghost_meta and ghost_meta["is_deleted"]:
                raise ReingestionConflictError(
                    ghost_id=ghost_meta["id"],
                    title=ghost_meta["title"],
                    duration_s=ghost_meta["duration_s"],
                    year=ghost_meta.get("year"),
                    isrc=ghost_meta.get("isrc"),
                )

            if os.path.exists(staged_path):
                os.remove(staged_path)
            return {
                "status": "ERROR",
                "message": f"Ingestion failed: {str(e)}",
                "staged_path": staged_path,
            }
        finally:
            conn.close()

    def resolve_conflict(self, ghost_id: int, staged_path: str) -> Dict[str, Any]:
        """
        Resolve a ghost conflict by re-activating the soft-deleted record.
        """
        logger.info(
            f"[IngestionService] -> resolve_conflict(ghost={ghost_id}, path='{staged_path}')"
        )

        if not os.path.exists(staged_path):
            logger.error(
                f"[IngestionService] <- resolve_conflict FAILED: File not found: {staged_path}"
            )
            return {"status": "ERROR", "message": "Staged file not found"}

        is_wav = Path(staged_path).suffix.lower() == ".wav"
        target_status = ProcessingStatus.CONVERTING if is_wav else ProcessingStatus.NEEDS_REVIEW

        conn = self._song_repo.get_connection()
        try:
            audio_hash = calculate_audio_hash(staged_path)
            raw_meta = self._metadata_service.extract_metadata(staged_path)
            parsed_song = self._metadata_parser.parse(raw_meta, staged_path)

            reactivated = parsed_song.model_copy(
                update={
                    "id": ghost_id,
                    "source_path": staged_path,
                    "audio_hash": audio_hash,
                    "is_active": False,
                    "processing_status": target_status,
                }
            )
            self._song_repo.reactivate_ghost(ghost_id, reactivated, conn)
            conn.commit()

            status_label = "PENDING_CONVERT" if is_wav else "INGESTED"
            logger.info(f"[IngestionService] <- resolve_conflict OK ({status_label})")
            return {"status": status_label, "song": reactivated}

        except Exception as e:
            conn.rollback()
            logger.error(f"[IngestionService] <- resolve_conflict FAILED: {e}")
            return {"status": "ERROR", "message": str(e)}
        finally:
            conn.close()

    def scan_folder(self, folder_path: str, recursive: bool = True) -> List[str]:
        """
        Scan a folder for audio files.
        """
        logger.debug(f"[IngestionService] -> scan_folder(path='{folder_path}')")
        if not os.path.exists(folder_path):
            return []

        from src.engine.config import ACCEPTED_EXTENSIONS

        audio_files = []
        if recursive:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if Path(file).suffix.lower() in ACCEPTED_EXTENSIONS:
                        audio_files.append(os.path.join(root, file))
        else:
            for entry in os.listdir(folder_path):
                file_path = os.path.join(folder_path, entry)
                if os.path.isfile(file_path):
                    if Path(entry).suffix.lower() in ACCEPTED_EXTENSIONS:
                        audio_files.append(file_path)
        return audio_files

    def ingest_batch(
        self, file_paths: List[str], max_workers: int = 10
    ) -> Dict[str, Any]:
        """
        Ingest multiple files in parallel.
        """
        logger.info(f"[IngestionService] -> ingest_batch(count={len(file_paths)})")
        results = []
        stats = {"INGESTED": 0, "ALREADY_EXISTS": 0, "CONFLICT": 0, "ERROR": 0}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self._ingest_single, p): p for p in file_paths
            }
            for future in as_completed(future_to_path):
                try:
                    report = future.result()
                    status = report["status"]
                    stats[status if status in stats else "ERROR"] += 1
                    results.append(report)
                except Exception as e:
                    stats["ERROR"] += 1
                    results.append({"status": "ERROR", "message": str(e)})

        return {
            "total_files": len(file_paths),
            "ingested": stats["INGESTED"],
            "duplicates": stats["ALREADY_EXISTS"],
            "conflicts": stats["CONFLICT"],
            "errors": stats["ERROR"],
            "results": results,
        }

    def _ingest_single(self, file_path: str) -> Dict[str, Any]:
        """Thread-safe single file ingestion wrapper."""
        try:
            return self.ingest_file(file_path)
        except ReingestionConflictError as e:
            return {
                "status": "CONFLICT",
                "match_type": "HASH",
                "ghost_id": e.ghost_id,
                "title": e.title,
                "duration_s": e.duration_s,
                "year": e.year,
                "isrc": e.isrc,
                "staged_path": file_path,
                "song": None,
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "message": str(e),
                "song": None,
                "staged_path": file_path,
            }

    def _enrich_metadata(self, song_id: int, conn: sqlite3.Connection) -> None:
        """Internal sink for metadata enrichment (SIMULATED)."""
        logger.debug(f"[IngestionService] -> _enrich_metadata(id={song_id})")
        self._song_repo.update_scalars(song_id, {"processing_status": ProcessingStatus.NEEDS_REVIEW}, conn)
