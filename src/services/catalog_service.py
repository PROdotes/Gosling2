from typing import Optional
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
        logger.debug(f"[CatalogService] Executing get_song for ID: {song_id}")
        song = self._song_repo.get_by_id(song_id)
        if not song:
            logger.debug(f"[CatalogService] SongID: {song_id} not found in database.")
            return None

        credits = self._credit_repo.get_credits_for_song(song_id)

        # Pydantic requires copying or using model_copy if model is frozen,
        # but since 'credits' is empty by default and extra is forbid,
        # we can use model_copy(update={"credits": credits})
        logger.debug(
            f"[CatalogService] Successfully hydrated SongID: {song_id} with {len(credits)} credits."
        )
        return song.model_copy(update={"credits": credits})
