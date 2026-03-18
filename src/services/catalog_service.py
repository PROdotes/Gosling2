from typing import Optional, List, Dict
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


class CatalogService:
    """Entry point for song access. Stateless orchestrator."""

    def __init__(self, db_path: str):
        self._song_repo = SongRepository(db_path)
        self._album_repo_dir = AlbumRepository(db_path)
        self._credit_repo = SongCreditRepository(db_path)
        self._album_repo = SongAlbumRepository(db_path)
        self._album_credit_repo = AlbumCreditRepository(db_path)
        self._pub_repo = PublisherRepository(db_path)
        self._tag_repo = TagRepository(db_path)
        self._identity_repo = IdentityRepository(db_path)

    def get_song(self, song_id: int) -> Optional[Song]:
        """Fetch a single song and all its credits by ID."""
        logger.info(f"[CatalogService] Entry: get_song(id={song_id})")
        song = self._song_repo.get_by_id(song_id)
        if not song:
            logger.warning(f"[CatalogService] Exit: SongID {song_id} not found.")
            return None

        hydrated = self._hydrate_songs([song])
        result = hydrated[0] if hydrated else None
        logger.info(f"[CatalogService] Exit: Returning hydrated song '{result.title}'")
        return result

    def get_identity(self, identity_id: int) -> Optional[Identity]:
        """Fetch a full identity tree (Aliases/Members/Groups)."""
        logger.info(f"[CatalogService] Entry: get_identity(id={identity_id})")
        identity = self._identity_repo.get_by_id(identity_id)
        if not identity:
            logger.warning(f"[CatalogService] Exit: Identity {identity_id} not found.")
            return None

        result = self._hydrate_identities([identity])[0]
        logger.info(
            f"[CatalogService] Exit: Returning hydrated identity '{result.display_name}'"
        )
        return result

    def get_all_identities(self) -> List[Identity]:
        """Fetch a list of all active identities."""
        logger.info("[CatalogService] Entry: get_all_identities()")
        identities = self._identity_repo.get_all_identities()
        result = self._hydrate_identities(identities)
        logger.info(f"[CatalogService] Exit: Returning {len(result)} identities.")
        return result

    def search_identities(self, query: str) -> List[Identity]:
        """Search for identities by name or alias."""
        logger.info(f"[CatalogService] Entry: search_identities(query='{query}')")
        identities = self._identity_repo.search_identities(query)
        result = self._hydrate_identities(identities)
        logger.info(f"[CatalogService] Exit: Found {len(result)} identities.")
        return result

    def get_all_publishers(self) -> List[Publisher]:
        """Fetch the full directory of publishers with resolved hierarchies."""
        logger.info("[CatalogService] Entry: get_all_publishers()")
        pubs = self._pub_repo.get_all()
        result = self._hydrate_publishers(pubs)
        logger.info(f"[CatalogService] Exit: Returning {len(result)} publishers.")
        return result

    def get_all_albums(self) -> List[Album]:
        """Fetch the full album directory with hydrated publishers, credits, and songs."""
        logger.info("[CatalogService] Entry: get_all_albums()")
        albums = self._album_repo_dir.get_all()
        result = self._hydrate_albums(albums)
        logger.info(f"[CatalogService] Exit: Returning {len(result)} albums.")
        return result

    def search_albums(self, query: str) -> List[Album]:
        """Search for albums by title."""
        logger.info(f"[CatalogService] Entry: search_albums(query='{query}')")
        albums = self._album_repo_dir.search(query)
        result = self._hydrate_albums(albums)
        logger.info(f"[CatalogService] Exit: Found {len(result)} albums.")
        return result

    def get_album(self, album_id: int) -> Optional[Album]:
        """Fetch a single album by ID with hydrated publishers, credits, and songs."""
        logger.info(f"[CatalogService] Entry: get_album(id={album_id})")
        album = self._album_repo_dir.get_by_id(album_id)
        if not album:
            logger.warning(f"[CatalogService] Exit: AlbumID {album_id} not found.")
            return None

        hydrated = self._hydrate_albums([album])
        result = hydrated[0] if hydrated else None
        if result:
            logger.info(
                f"[CatalogService] Exit: Returning hydrated album '{result.title}'"
            )
        return result

    def search_publishers(self, query: str) -> List[Publisher]:
        """Search for publishers by name match with resolved hierarchies."""
        logger.info(f"[CatalogService] Entry: search_publishers(query='{query}')")
        pubs = self._pub_repo.search(query)
        result = self._hydrate_publishers(pubs)
        logger.info(f"[CatalogService] Exit: Found {len(result)} publishers.")
        return result

    def get_publisher(self, publisher_id: int) -> Optional[Publisher]:
        """Fetch a single publisher by ID and resolve its full hierarchy."""
        logger.info(f"[CatalogService] Entry: get_publisher(id={publisher_id})")
        publisher = self._pub_repo.get_by_id(publisher_id)
        if not publisher:
            logger.warning(
                f"[CatalogService] Exit: PublisherID {publisher_id} not found."
            )
            return None

        children = self._pub_repo.get_children(publisher_id)
        hydrated_list = self._hydrate_publishers([publisher])
        if not hydrated_list:
            return None

        hydrated = hydrated_list[0]
        result = hydrated.model_copy(update={"sub_publishers": children})
        logger.info(
            f"[CatalogService] Exit: Returning hydrated publisher '{result.name}'"
        )
        return result

    def get_publisher_songs(self, publisher_id: int) -> List[Song]:
        """Fetch the full song repertoire for a given publisher."""
        logger.info(f"[CatalogService] Entry: get_publisher_songs(id={publisher_id})")
        song_ids = self._pub_repo.get_song_ids_by_publisher(publisher_id)
        if not song_ids:
            logger.debug(
                f"[CatalogService] Exit: No repertoire found for ID {publisher_id}"
            )
            return []

        songs = self._song_repo.get_by_ids(song_ids)
        result = self._hydrate_songs(songs)
        logger.info(f"[CatalogService] Exit: Returning {len(result)} songs.")
        return result

    def get_songs_by_identity(self, identity_id: int) -> List[Song]:
        """
        Reverse Credit lookup: Given a seed identity_id, find all related IDs (its aliases + members/groups)
        and return all songs where any of those IDs are credited.
        """
        logger.info(f"[CatalogService] Entry: get_songs_by_identity(id={identity_id})")
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
        logger.info(f"[CatalogService] Exit: Returning {len(result)} songs.")
        return result

    def search_songs(self, query: str) -> List[Song]:
        """
        The Jazler-Debounce Hybrid:
        1. Surface Discovery (Title/Album match).
        2. Deep Resolution (Identity/Group expansion) via Fast Batching (4 Query method).
        """
        logger.info(f"[CatalogService] Entry: search_songs(query='{query}')")

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
        logger.info(f"[CatalogService] Exit: total={len(results)}")
        return results

    def _hydrate_songs(self, songs: List[Song]) -> List[Song]:
        """Centralized batch hydration for songs and their relations."""
        if not songs:
            return []

        song_ids = [s.id for s in songs if s.id is not None]
        logger.debug(f"[CatalogService] Entry: _hydrate_songs(count={len(song_ids)})")

        credits_by_song = self._get_credits_by_song(song_ids)
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

        logger.debug(f"[CatalogService] Exit: hydrated {len(hydrated_songs)} songs.")
        return hydrated_songs

    def _hydrate_identities(self, identities: List[Identity]) -> List[Identity]:
        """Centralized batch hydration for identities and their relations."""
        identities = [i for i in identities if i is not None]
        if not identities:
            return []

        identity_ids = [i.id for i in identities]
        logger.debug(
            f"[CatalogService] Entry: _hydrate_identities(count={len(identity_ids)})"
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
        logger.debug(f"[CatalogService] Exit: hydrated {len(hydrated)} identities.")
        return hydrated

    def _hydrate_publishers(self, pubs: List[Publisher]) -> List[Publisher]:
        """Batch-resolve full parent chains for publishers."""
        if not pubs:
            return []

        # Collect all unique seed publisher IDs
        seed_ids = [p.id for p in pubs if p.id is not None]
        logger.debug(
            f"[CatalogService] Entry: _hydrate_publishers(seed_count={len(seed_ids)})"
        )

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

        logger.debug(f"[CatalogService] Exit: hydrated {len(hydrated)} publishers.")
        return hydrated

    def _hydrate_albums(self, albums: List[Album]) -> List[Album]:
        """Centralized batch hydration for albums and their related songs."""
        if not albums:
            return []

        album_ids = [album.id for album in albums if album.id is not None]
        logger.debug(f"[CatalogService] Entry: _hydrate_albums(count={len(album_ids)})")

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

        logger.debug(f"[CatalogService] Exit: hydrated {len(hydrated)} albums.")
        return hydrated

    def _get_credits_by_song(self, song_ids: List[int]) -> Dict[int, List[SongCredit]]:
        """Fetch and group credits by song ID."""
        logger.debug(
            f"[CatalogService] Entry: _get_credits_by_song(count={len(song_ids)})"
        )
        all_credits = self._credit_repo.get_credits_for_songs(song_ids)
        credits_by_song: Dict[int, List[SongCredit]] = {}
        for credit in all_credits:
            if credit.source_id is not None:
                credits_by_song.setdefault(credit.source_id, []).append(credit)
        logger.debug(
            f"[CatalogService] Exit: Grouped credits for {len(credits_by_song)} songs."
        )
        return credits_by_song

    def _get_publishers_by_song(
        self, song_ids: List[int]
    ) -> Dict[int, List[Publisher]]:
        """Fetch and group master publishers by song ID, then resolve hierarchies."""
        logger.debug(
            f"[CatalogService] Entry: _get_publishers_by_song(count={len(song_ids)})"
        )
        raw_assocs = self._pub_repo.get_publishers_for_songs(song_ids)
        if not raw_assocs:
            logger.debug("[CatalogService] Exit: No publishers found for songs.")
            return {}

        all_found_pubs = [pub for _, pub in raw_assocs]
        hydrated_map: Dict[int, Publisher] = {}
        for p in self._hydrate_publishers(all_found_pubs):
            if p.id is not None:
                hydrated_map[p.id] = p

        pubs_by_song: Dict[int, List[Publisher]] = {}
        for song_id, pub in raw_assocs:
            if song_id is not None:
                if pub.id is not None and pub.id in hydrated_map:
                    pubs_by_song.setdefault(song_id, []).append(hydrated_map[pub.id])
                else:
                    pubs_by_song.setdefault(song_id, []).append(pub)

        logger.debug(
            f"[CatalogService] Exit: Grouped publishers for {len(pubs_by_song)} songs."
        )
        return pubs_by_song

    def _get_tags_by_song(self, song_ids: List[int]) -> Dict[int, List[Tag]]:
        """Fetch and group tags by song ID."""
        logger.debug(
            f"[CatalogService] Entry: _get_tags_by_song(count={len(song_ids)})"
        )
        all_tags = self._tag_repo.get_tags_for_songs(song_ids)
        tags_by_song: Dict[int, List[Tag]] = {}
        for song_id, tag in all_tags:
            if song_id is not None:
                tags_by_song.setdefault(song_id, []).append(tag)
        logger.debug(
            f"[CatalogService] Exit: Grouped tags for {len(tags_by_song)} songs."
        )
        return tags_by_song

    def _get_albums_by_song(self, song_ids: List[int]) -> Dict[int, List[SongAlbum]]:
        """Fetch album associations and hydrate with publishers and credits."""
        logger.debug(
            f"[CatalogService] Entry: _get_albums_by_song(count={len(song_ids)})"
        )
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
            f"[CatalogService] Exit: Hydrated albums for {len(assocs_by_song)} songs."
        )
        return assocs_by_song

    def _get_publishers_by_album(
        self, album_ids: List[int]
    ) -> Dict[int, List[Publisher]]:
        """Batch-fetch and hydrate publishers for albums."""
        logger.debug(
            f"[CatalogService] Entry: _get_publishers_by_album(count={len(album_ids)})"
        )
        if not album_ids:
            return {}

        raw_album_pubs = self._pub_repo.get_publishers_for_albums(album_ids)
        if not raw_album_pubs:
            logger.debug("[CatalogService] Exit: No publishers found for albums.")
            return {}

        all_found_pubs = [pub for _, pub in raw_album_pubs]
        hydrated_map: Dict[int, Publisher] = {}
        for p in self._hydrate_publishers(all_found_pubs):
            if p.id is not None:
                hydrated_map[p.id] = p

        pubs_by_album: Dict[int, List[Publisher]] = {}
        for album_id, pub in raw_album_pubs:
            if album_id is not None:
                if pub.id is not None and pub.id in hydrated_map:
                    pubs_by_album.setdefault(album_id, []).append(hydrated_map[pub.id])
                else:
                    pubs_by_album.setdefault(album_id, []).append(pub)

        logger.debug(
            f"[CatalogService] Exit: Hydrated publishers for {len(pubs_by_album)} albums."
        )
        return pubs_by_album

    def _get_album_credits_by_album(
        self, album_ids: List[int]
    ) -> Dict[int, List[AlbumCredit]]:
        """Batch-fetch album credits grouped by album ID."""
        logger.debug(
            f"[CatalogService] Entry: _get_album_credits_by_album(count={len(album_ids)})"
        )
        if not album_ids:
            return {}

        all_credits = self._album_credit_repo.get_credits_for_albums(album_ids)
        credits_by_album: Dict[int, List[AlbumCredit]] = {}
        for ac in all_credits:
            if ac.album_id is not None:
                credits_by_album.setdefault(ac.album_id, []).append(ac)

        logger.debug(
            f"[CatalogService] Exit: Found credits for {len(credits_by_album)} albums."
        )
        return credits_by_album

    def _get_songs_by_album(self, album_ids: List[int]) -> Dict[int, List[Song]]:
        """Fetch and hydrate songs grouped by album ID."""
        logger.debug(
            f"[CatalogService] Entry: _get_songs_by_album(count={len(album_ids)})"
        )
        if not album_ids:
            return {}

        songs_by_album: Dict[int, List[Song]] = {}
        for album_id in album_ids:
            song_ids = self._album_repo_dir.get_song_ids_by_album(album_id)
            songs = self._song_repo.get_by_ids(song_ids)
            songs_by_album[album_id] = self._hydrate_songs(songs)

        logger.debug(
            f"[CatalogService] Exit: Hydrated songs for {len(songs_by_album)} albums."
        )
        return songs_by_album
