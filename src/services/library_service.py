import sqlite3
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.data.song_repository import SongRepository
from src.data.album_repository import AlbumRepository
from src.data.song_album_repository import SongAlbumRepository
from src.data.song_credit_repository import SongCreditRepository
from src.data.album_credit_repository import AlbumCreditRepository
from src.data.publisher_repository import PublisherRepository
from src.data.tag_repository import TagRepository
from src.data.identity_repository import IdentityRepository
from src.data.staging_repository import StagingRepository
from src.models.domain import (
    Song,
    Album,
    SongAlbum,
    Publisher,
    SongCredit,
    AlbumCredit,
    Tag,
)
from src.services.logger import logger
from src.services.filing_service import FilingService
from src.engine import config


class LibraryService:
    """Specialized orchestrator for Reading and Hydrating the music catalog."""

    def __init__(
        self,
        db_path: str,
        rules_path: Optional[Path] = None,
        library_root: Optional[Path] = None,
    ):
        self._db_path = db_path
        self._library_root = library_root or config.LIBRARY_ROOT
        self._song_repo = SongRepository(db_path)
        self._album_repo_dir = AlbumRepository(db_path)
        self._album_repo = SongAlbumRepository(db_path)
        self._credit_repo = SongCreditRepository(db_path)
        self._album_credit_repo = AlbumCreditRepository(db_path)
        self._pub_repo = PublisherRepository(db_path)
        self._tag_repo = TagRepository(db_path)
        self._identity_repo = IdentityRepository(db_path)
        self._staging_repo = StagingRepository(db_path)

        # Determine rules path
        actual_rules_path = rules_path or config.RENAME_RULES_PATH
        self._filing_service = FilingService(actual_rules_path)

    def get_song(self, song_id: int) -> Optional[Song]:
        """Fetch a single song and all its credits by ID."""
        logger.debug(f"[LibraryService] -> get_song(id={song_id})")
        with self._song_repo.get_connection() as conn:
            song = self._song_repo.get_by_id(song_id, conn)
            if not song:
                logger.warning(f"[LibraryService] <- get_song(id={song_id}) NOT_FOUND")
                return None

            hydrated = self._hydrate_songs([song], conn=conn)
            if not hydrated:
                return None

            result = hydrated[0]
            logger.debug(f"[LibraryService] <- get_song(id={song_id}) '{result.title}'")
            return result

    def get_all_albums(self) -> List[Album]:
        """Fetch the full album directory with hydrated publishers, credits, and songs."""
        logger.debug("[LibraryService] -> get_all_albums()")
        with self._album_repo_dir.get_connection() as conn:
            albums = self._album_repo_dir.get_all(conn=conn)
            result = self._hydrate_albums(albums, conn=conn)
            logger.debug(f"[LibraryService] <- get_all_albums() count={len(result)}")
            return result

    def get_album(self, album_id: int) -> Optional[Album]:
        """Fetch a single album by ID with hydrated publishers, credits, and songs."""
        logger.debug(f"[LibraryService] -> get_album(id={album_id})")
        with self._album_repo_dir.get_connection() as conn:
            album = self._album_repo_dir.get_by_id(album_id, conn=conn)
            if not album:
                logger.warning(
                    f"[LibraryService] <- get_album(id={album_id}) NOT_FOUND"
                )
                return None

            hydrated = self._hydrate_albums([album], conn=conn)
            if not hydrated:
                return None

            result = hydrated[0]
            logger.debug(
                f"[LibraryService] <- get_album(id={album_id}) '{result.title}'"
            )
            return result

    def search_albums_slim(self, query: str) -> List[dict]:
        """Slim list-view album search. No tracklist hydration."""
        logger.debug(f"[LibraryService] -> search_albums_slim(q='{query}')")
        rows = self._album_repo_dir.search_slim(query)
        logger.debug(f"[LibraryService] <- search_albums_slim count={len(rows)}")
        return rows

    def get_all_publishers(self) -> List[Publisher]:
        """Fetch the full directory of publishers with resolved hierarchies."""
        logger.debug("[LibraryService] -> get_all_publishers()")
        with self._pub_repo.get_connection() as conn:
            pubs = self._pub_repo.get_all(conn=conn)
            result = self._hydrate_publishers(pubs, conn=conn)
            logger.debug(
                f"[LibraryService] <- get_all_publishers() count={len(result)}"
            )
            return result

    def search_publishers(self, query: str) -> List[Publisher]:
        """Search for publishers by name match with resolved hierarchies."""
        logger.debug(f"[LibraryService] -> search_publishers(q='{query}')")
        with self._pub_repo.get_connection() as conn:
            pubs = self._pub_repo.search(query, conn=conn)
            result = self._hydrate_publishers(pubs, conn=conn)
            logger.debug(
                f"[LibraryService] <- search_publishers(q='{query}') count={len(result)}"
            )
            return result

    def get_publisher(self, publisher_id: int) -> Optional[Publisher]:
        """Fetch a single publisher by ID and resolve its full hierarchy."""
        logger.debug(f"[LibraryService] -> get_publisher(id={publisher_id})")
        with self._pub_repo.get_connection() as conn:
            publisher = self._pub_repo.get_by_id(publisher_id, conn=conn)
            if not publisher:
                logger.warning(
                    f"[LibraryService] <- get_publisher(id={publisher_id}) NOT_FOUND"
                )
                return None

            children = self._pub_repo.get_children(publisher_id, conn=conn)
            hydrated_list = self._hydrate_publishers([publisher], conn=conn)
            if not hydrated_list:
                return None

            hydrated = hydrated_list[0]
            result = hydrated.model_copy(update={"sub_publishers": children})
            logger.debug(
                f"[LibraryService] <- get_publisher(id={publisher_id}) '{result.name}'"
            )
            return result

    def get_songs_by_publisher(self, publisher_id: int) -> List[Song]:
        """Fetch the full song repertoire for a given publisher."""
        logger.debug(f"[LibraryService] -> get_songs_by_publisher(id={publisher_id})")
        with self._pub_repo.get_connection() as conn:
            song_ids = self._pub_repo.get_song_ids_by_publisher(publisher_id, conn=conn)
            if not song_ids:
                logger.debug(
                    f"[LibraryService] <- get_songs_by_publisher(id={publisher_id}) NO_REPERTOIRE"
                )
                return []

            songs = self._song_repo.get_by_ids(song_ids, conn=conn)
            result = self._hydrate_songs(songs, conn=conn)
            logger.debug(f"[LibraryService] <- Return count={len(result)}")
            return result

    def get_all_tags(self) -> List[Tag]:
        """Fetch the full directory of tags."""
        logger.debug("[LibraryService] -> get_all_tags()")
        tags = self._tag_repo.get_all()
        logger.debug(f"[LibraryService] <- get_all_tags() count={len(tags)}")
        return tags

    def get_tag_categories(self) -> List[str]:
        """Fetch all distinct tag categories."""
        logger.debug("[LibraryService] -> get_tag_categories()")
        return self._tag_repo.get_categories()

    def search_tags(self, query: str) -> List[Tag]:
        """Search for tags by name match."""
        logger.debug(f"[LibraryService] -> search_tags(q='{query}')")
        tags = self._tag_repo.search(query)
        logger.debug(f"[LibraryService] <- search_tags(q='{query}') count={len(tags)}")
        return tags

    def get_tag(self, tag_id: int) -> Optional[Tag]:
        """Fetch a single tag by ID."""
        logger.debug(f"[LibraryService] -> get_tag(id={tag_id})")
        tag = self._tag_repo.get_by_id(tag_id)
        if not tag:
            logger.warning(f"[LibraryService] <- get_tag(id={tag_id}) NOT_FOUND")
            return None
        logger.debug(f"[LibraryService] <- get_tag(id={tag_id}) '{tag.name}'")
        return tag

    def get_songs_by_tag(self, tag_id: int) -> List[Song]:
        """Fetch all songs linked to this tag."""
        logger.debug(f"[LibraryService] -> get_songs_by_tag(id={tag_id})")
        with self._tag_repo.get_connection() as conn:
            song_ids = self._tag_repo.get_song_ids_by_tag(tag_id, conn=conn)
            if not song_ids:
                logger.debug(
                    f"[LibraryService] <- get_songs_by_tag(id={tag_id}) NO_SONGS"
                )
                return []

            songs = self._song_repo.get_by_ids(song_ids, conn=conn)
            result = self._hydrate_songs(songs, conn=conn)
            logger.debug(f"[LibraryService] <- Return count={len(result)}")
            return result

    def get_songs_by_identity(self, identity_id: int) -> List[Song]:
        """
        Reverse Credit lookup: find all related IDs (aliases + members/groups)
        and return all songs where any of those IDs are credited.
        """
        logger.debug(f"[LibraryService] -> get_songs_by_identity(id={identity_id})")
        with self._identity_repo.get_connection() as conn:
            identity = self._identity_repo.get_by_id(identity_id, conn=conn)
            if not identity:
                logger.warning(
                    f"[LibraryService] Exit: Identity {identity_id} not found."
                )
                return []

            related_ids = {identity.id}
            members_by_id = self._identity_repo.get_members_batch(
                [identity.id], conn=conn
            )
            groups_by_id = self._identity_repo.get_groups_batch(
                [identity.id], conn=conn
            )

            for member in members_by_id.get(identity.id, []):
                related_ids.add(member.id)
            for group in groups_by_id.get(identity.id, []):
                related_ids.add(group.id)

            songs = self._song_repo.get_by_identity_ids(list(related_ids), conn=conn)
            result = self._hydrate_songs(songs, conn=conn)
            logger.debug(f"[LibraryService] <- Return count={len(result)}")
            return result

    def get_filter_values(self) -> dict:
        """Returns all distinct filter sidebar values."""
        return self._song_repo.get_filter_values()

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
        """Filter songs by sidebar criteria. Returns slim list-view rows."""
        return self._song_repo.filter_slim(
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
        """Slim list-view search. Returns raw dicts for SongSlimView — no hydration."""
        logger.debug(f"[LibraryService] -> search_songs_slim(q='{query}')")
        rows = self._song_repo.search_slim(query)
        logger.debug(f"[LibraryService] <- search_songs_slim count={len(rows)}")
        return rows

    def search_songs_deep_slim(self, query: str) -> List[dict]:
        """
        Deep slim search. Base matches + identity/publisher expansion, no hydration.
        """
        logger.debug(f"[LibraryService] -> search_songs_deep_slim(q='{query}')")
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
            f"[LibraryService] <- search_songs_deep_slim count={len(base_rows)}"
        )
        return base_rows

    def _hydrate_songs(
        self,
        songs: List[Song],
        pre_albums: Optional[Dict[int, List[SongAlbum]]] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Song]:
        """Centralized batch hydration for songs and their relations."""
        if not songs:
            return []

        song_ids = [s.id for s in songs if s.id is not None]
        logger.debug(f"[LibraryService] -> _hydrate_songs(count={len(song_ids)})")

        credits_by_song = self._get_credits_by_song(song_ids, conn=conn)
        if pre_albums is not None:
            assocs_by_song = pre_albums
        else:
            assocs_by_song = self._get_albums_by_song(song_ids, conn=conn)

        pubs_by_song = self._get_publishers_by_song(song_ids, conn=conn)
        tags_by_song = self._get_tags_by_songs(song_ids, conn=conn)

        hydrated_songs = []
        for song in songs:
            if song.id is None:
                continue

            # Origin check
            origin_path = self._staging_repo.get_origin(song.id, conn)

            # --- 1. Hydrate full domain object ---
            song = song.model_copy(
                update={
                    "credits": credits_by_song.get(song.id, []),
                    "albums": assocs_by_song.get(song.id, []),
                    "publishers": pubs_by_song.get(song.id, []),
                    "tags": tags_by_song.get(song.id, []),
                    "estimated_original_path": origin_path,
                    "original_exists": bool(
                        origin_path and os.path.exists(origin_path)
                    ),
                }
            )

            # --- 2. Desired State Sync (Declarative Physical Move) ---
            projected_path = None
            needs_organization = False

            # Optimization: Only calculate paths and check moves if song is Reviewed
            # This prevents 500+ exists() checks during a simple library search
            if song.processing_status == config.ProcessingStatus.REVIEWED:
                try:
                    projected_path = str(
                        self._library_root / self._filing_service.evaluate_routing(song)
                    )
                    if song.source_path and os.path.normpath(
                        song.source_path
                    ) != os.path.normpath(projected_path):
                        needs_organization = True
                        if config.AUTO_MOVE_ON_APPROVE:
                            new_path = self._filing_service.move_to_library(
                                song, self._library_root
                            )
                            self._song_repo.update_scalars(
                                song.id, {"source_path": str(new_path)}, conn
                            )
                            # Re-sync path on the object
                            song = song.model_copy(
                                update={"source_path": str(new_path)}
                            )
                            needs_organization = False
                except Exception as e:
                    logger.error(
                        f"[LibraryService] Desired State Sync failed for {song.id}: {e}"
                    )

            hydrated_songs.append(
                song.model_copy(
                    update={
                        "projected_path": projected_path,
                        "needs_organization": needs_organization,
                    }
                )
            )

        logger.debug(f"[LibraryService] <- hydrated {len(hydrated_songs)} songs.")
        return hydrated_songs

    def _hydrate_publishers(
        self,
        pubs: List[Publisher],
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Publisher]:
        """Batch-resolve full parent chains for publishers."""
        if not pubs:
            return []

        seed_ids = [p.id for p in pubs if p.id is not None]
        logger.debug(f"[LibraryService] -> _hydrate_publishers(count={len(seed_ids)})")

        full_parent_map = self._pub_repo.get_hierarchy_batch(seed_ids, conn=conn)

        hydrated = []
        for pub in pubs:
            chain = []
            current_id = pub.parent_id
            visited = set()
            while current_id is not None and current_id in full_parent_map:
                if current_id in visited:
                    break
                visited.add(current_id)
                parent = full_parent_map[current_id]
                chain.append(parent)
                current_id = parent.parent_id

            hydrated.append(
                pub.model_copy(update={"parent_name": chain[0].name if chain else None})
            )

        logger.debug(f"[LibraryService] <- _hydrate_publishers(count={len(hydrated)})")
        return hydrated

    def _hydrate_albums(
        self, albums: List[Album], conn: Optional[sqlite3.Connection] = None
    ) -> List[Album]:
        """Centralized batch hydration for albums and their related songs."""
        if not albums:
            return []

        album_ids = [album.id for album in albums if album.id is not None]
        logger.debug(f"[LibraryService] -> _hydrate_albums(count={len(album_ids)})")

        pubs_by_album = self._get_publishers_by_album(album_ids, conn=conn)
        credits_by_album = self._get_credits_by_album(album_ids, conn=conn)
        songs_by_album = self._get_songs_by_album(album_ids, conn=conn)

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

        logger.debug(f"[LibraryService] <- _hydrate_albums(count={len(hydrated)})")
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

    def _get_credits_by_song(
        self, song_ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> Dict[int, List[SongCredit]]:
        all_credits = self._credit_repo.get_credits_for_songs(song_ids, conn=conn)
        return self._batch_group_by_id(all_credits, "source_id")

    def _resolve_publisher_associations(
        self,
        raw_assocs: List[tuple],
        entity_label: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[int, List[Publisher]]:
        if not raw_assocs:
            return {}

        all_found_pubs = [pub for _, pub in raw_assocs]
        hydrated_map: Dict[int, Publisher] = {}
        for p in self._hydrate_publishers(all_found_pubs, conn=conn):
            if p.id is not None:
                hydrated_map[p.id] = p

        results: Dict[int, List[Publisher]] = {}
        for entity_id, pub in raw_assocs:
            if entity_id is not None:
                if pub.id is not None and pub.id in hydrated_map:
                    results.setdefault(entity_id, []).append(hydrated_map[pub.id])
                else:
                    results.setdefault(entity_id, []).append(pub)
        return results

    def _get_publishers_by_song(
        self, song_ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> Dict[int, List[Publisher]]:
        raw_assocs = self._pub_repo.get_publishers_for_songs(song_ids, conn=conn)
        return self._resolve_publisher_associations(raw_assocs, "songs", conn=conn)

    def _get_tags_by_songs(
        self, song_ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> Dict[int, List[Tag]]:
        all_tags_tuples = self._tag_repo.get_tags_for_songs(song_ids, conn=conn)
        tags_by_song: Dict[int, List[Tag]] = {}
        for song_id, tag in all_tags_tuples:
            if song_id is not None:
                tags_by_song.setdefault(song_id, []).append(tag)
        return tags_by_song

    def _get_albums_by_song(
        self, song_ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> Dict[int, List[SongAlbum]]:
        all_assocs = self._album_repo.get_albums_for_songs(song_ids, conn=conn)
        album_ids = [a.album_id for a in all_assocs if a.album_id is not None]

        pubs_by_album = self._get_publishers_by_album(album_ids, conn=conn)
        credits_by_album = self._get_credits_by_album(album_ids, conn=conn)

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
        return assocs_by_song

    def _get_publishers_by_album(
        self, album_ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> Dict[int, List[Publisher]]:
        if not album_ids:
            return {}
        raw_assocs = self._pub_repo.get_publishers_for_albums(album_ids, conn=conn)
        return self._resolve_publisher_associations(raw_assocs, "albums", conn=conn)

    def _get_credits_by_album(
        self, album_ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> Dict[int, List[AlbumCredit]]:
        if not album_ids:
            return {}
        all_credits = self._album_credit_repo.get_credits_for_albums(
            album_ids, conn=conn
        )
        return self._batch_group_by_id(all_credits, "album_id")

    def _get_songs_by_album(
        self, album_ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> Dict[int, List[Song]]:
        if not album_ids:
            return {}

        all_assocs = self._album_repo.get_albums_for_songs_reverse(album_ids, conn=conn)
        if not all_assocs:
            return {}

        unique_song_ids = list(
            dict.fromkeys(a.source_id for a in all_assocs if a.source_id)
        )
        pre_mapped_assocs: Dict[int, List[SongAlbum]] = {}
        for a in all_assocs:
            if a.source_id:
                pre_mapped_assocs.setdefault(a.source_id, []).append(a)

        all_songs = self._song_repo.get_by_ids(unique_song_ids, conn=conn)
        hydrated_songs = self._hydrate_songs(
            all_songs, pre_albums=pre_mapped_assocs, conn=conn
        )

        song_lookup = {s.id: s for s in hydrated_songs if s.id is not None}
        results: Dict[int, List[Song]] = {}
        for a in all_assocs:
            if a.album_id and a.source_id in song_lookup:
                results.setdefault(a.album_id, []).append(song_lookup[a.source_id])
        return results
