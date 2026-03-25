import os
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
from src.services.logger import logger
from src.utils.audio_hash import calculate_audio_hash
from src.services.metadata_service import MetadataService
from src.services.metadata_parser import MetadataParser
from src.engine.config import STAGING_DIR


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
                        "song": hydrated[0] if hydrated else matches[0],
                    }

            logger.info(
                f"[CatalogService] <- check_ingestion(file_path='{file_path}') NEW"
            )
            return {"status": "NEW", "song": parsed_song}
        except Exception as e:
            logger.error(
                f"[CatalogService] <- check_ingestion(file_path='{file_path}') EXTRACTION_FAILED: {e}"
            )
            return {"status": "ERROR", "message": f"Metadata failed: {str(e)}"}

    def ingest_file(self, staged_path: str) -> Dict[str, Any]:
        """
        Write path for a staged file.
        1. Check (Hash/Path/Meta collisions).
        2. If NEW, insert into both tables.
        3. Commit single transaction.
        4. Rollback on failure + cleanup.
        """
        logger.debug(f"[CatalogService] -> ingest_file(path='{staged_path}')")

        # 1. Validation check
        check = self.check_ingestion(staged_path)
        if check["status"] != "NEW":
            logger.info(
                f"[CatalogService] <- ingest_file(path='{staged_path}') REJECTED: {check['status']}"
            )
            # Cleanup staging file for rejected duplicates
            if os.path.exists(staged_path):
                os.remove(staged_path)
                logger.debug(
                    f"[CatalogService] Deleted rejected staged file: {staged_path}"
                )
            return check

        # 2. Atomic Write
        song = check["song"]
        conn = self._song_repo.get_connection()
        try:
            new_id = self._song_repo.insert(song, conn)
            # Update the returned song object with the new db ID
            hydrated_song = song.model_copy(update={"id": new_id})

            conn.commit()
            logger.info(
                f"[CatalogService] <- ingest_file(path='{staged_path}') INGESTED ID={new_id}"
            )
            return {"status": "INGESTED", "song": hydrated_song}

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
            f"duplicates={duplicate_count} errors={error_count}"
        )

        return {
            "total_files": len(file_paths),
            "ingested": ingested_count,
            "duplicates": duplicate_count,
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

    def search_albums(self, query: str) -> List[Album]:
        """Search for albums by title."""
        logger.debug(f"[CatalogService] -> search_albums(q='{query}')")
        albums = self._album_repo_dir.search(query)
        result = self._hydrate_albums(albums)
        logger.debug(
            f"[CatalogService] <- search_albums(q='{query}') count={len(result)}"
        )
        return result

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

    def search_songs(self, query: str) -> List[Song]:
        """
        The Jazler-Debounce Hybrid:
        1. Surface Discovery (Title/Album match).
        2. Deep Resolution (Identity/Group expansion) via Fast Batching (4 Query method).
        """
        logger.debug(f"[CatalogService] -> search_songs(q='{query}')")

        songs = self._song_repo.search_surface(query)
        seen_ids = {s.id for s in songs}

        seeds = self._identity_repo.search_identities(query)
        identity_ids = {seed.id for seed in seeds}

        if identity_ids:
            group_ids = self._identity_repo.get_group_ids_for_members(
                list(identity_ids)
            )
            identity_ids.update(group_ids)

            deep_songs = self._song_repo.get_by_identity_ids(list(identity_ids))
            for s in deep_songs:
                if s.id not in seen_ids:
                    songs.append(s)
                    seen_ids.add(s.id)

        results = self._hydrate_songs(songs)
        logger.debug(
            f"[CatalogService] <- search_songs(q='{query}') count={len(results)}"
        )
        return results

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
