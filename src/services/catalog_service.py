from typing import Optional, List
from src.data.song_repository import SongRepository
from src.data.song_credit_repository import SongCreditRepository
from src.models.domain import Song
from src.services.logger import logger


class CatalogService:
    """Entry point for song access. Stateless orchestrator."""

    def __init__(self, db_path: str):
        self._song_repo = SongRepository(db_path)
        self._credit_repo = SongCreditRepository(db_path)

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
        """Internal: Centralized batch hydration for song credits."""
        if not songs:
            return []

        song_ids = [s.id for s in songs]
        logger.debug(f"[CatalogService] Hydrating {len(song_ids)} songs.")

        # 1. Fetch flat list of credits from DB
        all_credits = self._credit_repo.get_credits_for_songs(song_ids)

        # 2. Orchestrate (Group) them locally for O(1) attribute access
        credits_by_song = {}
        for credit in all_credits:
            credits_by_song.setdefault(credit.source_id, []).append(credit)

        # 3. Stitch them back to the Songs
        hydrated_songs = []
        for song in songs:
            credits = credits_by_song.get(song.id, [])
            hydrated_songs.append(song.model_copy(update={"credits": credits}))

        logger.debug(
            f"[CatalogService] Successfully hydrated {len(hydrated_songs)} songs."
        )
        return hydrated_songs
