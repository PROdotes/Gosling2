from typing import Optional, List, Dict
from src.data.song_repository import SongRepository
from src.data.song_credit_repository import SongCreditRepository
from src.data.song_album_repository import SongAlbumRepository
from src.data.publisher_repository import PublisherRepository
from src.data.tag_repository import TagRepository
from src.models.domain import Song, SongAlbum
from src.services.logger import logger


class CatalogService:
    """Entry point for song access. Stateless orchestrator."""

    def __init__(self, db_path: str):
        self._song_repo = SongRepository(db_path)
        self._credit_repo = SongCreditRepository(db_path)
        self._album_repo = SongAlbumRepository(db_path)
        self._pub_repo = PublisherRepository(db_path)
        self._tag_repo = TagRepository(db_path)

    def get_song(self, song_id: int) -> Optional[Song]:
        """Fetch a single song and all its credits by ID."""
        logger.info(f"[CatalogService] Executing get_song(id={song_id})")
        song = self._song_repo.get_by_id(song_id)
        if not song:
            logger.warning(f"[CatalogService] SongID {song_id} not found.")
            return None

        hydrated = self._hydrate_songs([song])
        result = hydrated[0] if hydrated else None
        logger.debug(f"[CatalogService] Returning hydrated song for ID: {song_id}")
        return result

    def search_songs(self, query: str) -> List[Song]:
        """Search for songs by title and hydrate with full metadata."""
        logger.info(f"[CatalogService] Executing search_songs(query='{query}')")
        songs = self._song_repo.get_by_title(query)
        results = self._hydrate_songs(songs)
        logger.info(f"[CatalogService] search_songs found {len(results)} matches.")
        return results

    def _hydrate_songs(self, songs: List[Song]) -> List[Song]:
        """Internal: Centralized batch hydration for all song metadata."""
        if not songs:
            return []

        song_ids = [s.id for s in songs]
        logger.debug(f"[CatalogService] Hydrating {len(song_ids)} songs.")

        credits_by_song = self._get_credits_by_song(song_ids)
        assocs_by_song = self._get_albums_by_song(song_ids)
        pubs_by_song = self._get_publishers_by_song(song_ids)
        tags_by_song = self._get_tags_by_song(song_ids)

        # Model Stitching
        hydrated_songs = []
        for song in songs:
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

        logger.debug(
            f"[CatalogService] Successfully hydrated {len(hydrated_songs)} songs."
        )
        return hydrated_songs

    def _get_credits_by_song(self, song_ids: List[int]) -> Dict[int, List]:
        """Fetch and group credits by song ID."""
        all_credits = self._credit_repo.get_credits_for_songs(song_ids)
        credits_by_song = {}
        for credit in all_credits:
            credits_by_song.setdefault(credit.source_id, []).append(credit)
        return credits_by_song

    def _get_publishers_by_song(self, song_ids: List[int]) -> Dict[int, List]:
        """Fetch and group master publishers by song ID."""
        all_pubs = self._pub_repo.get_publishers_for_songs(song_ids)
        pubs_by_song = {}
        for song_id, pub in all_pubs:
            pubs_by_song.setdefault(song_id, []).append(pub)
        return pubs_by_song

    def _get_tags_by_song(self, song_ids: List[int]) -> Dict[int, List]:
        """Fetch and group tags by song ID."""
        all_tags = self._tag_repo.get_tags_for_songs(song_ids)
        tags_by_song = {}
        for song_id, tag in all_tags:
            tags_by_song.setdefault(song_id, []).append(tag)
        return tags_by_song

    def _get_albums_by_song(self, song_ids: List[int]) -> Dict[int, List[SongAlbum]]:
        """Fetch album associations, resolve publishers, and group by song ID."""
        all_assocs = self._album_repo.get_albums_for_songs(song_ids)

        # Gather album IDs for M2M publisher resolution
        album_ids = list({a.album_id for a in all_assocs})

        # Resolve M2M publishers for albums
        all_album_pubs = self._pub_repo.get_publishers_for_albums(album_ids)
        pubs_by_album = {}
        for album_id, pub in all_album_pubs:
            pubs_by_album.setdefault(album_id, []).append(pub)

        assocs_by_song = {}
        for a in all_assocs:
            # DomainModel is frozen, so set() deduplicates based on contents safely
            resolved_pubs = list(set(pubs_by_album.get(a.album_id, [])))

            # Since 'a' is a frozen DomainModel, we copy it to apply publishers
            hydrated_assoc = a.model_copy(update={"publishers": resolved_pubs})
            assocs_by_song.setdefault(hydrated_assoc.source_id, []).append(
                hydrated_assoc
            )

        return assocs_by_song
