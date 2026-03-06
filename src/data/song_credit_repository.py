import sqlite3
from typing import List
from src.models.domain import SongCredit
from src.data.base_repository import BaseRepository
from src.services.logger import logger


class SongCreditRepository(BaseRepository):
    """Bridges Song IDs to their Credits and Human Names."""

    def get_credits_for_song(self, song_id: int) -> List[SongCredit]:
        """Fetches all credits for a song, joining on ArtistNames for the text name."""
        logger.debug(f"[SongCreditRepository] Fetching credits for SongID: {song_id}")
        query = """
            SELECT 
                sc.SourceID, 
                sc.CreditedNameID, 
                sc.RoleID, 
                an.DisplayName
            FROM SongCredits sc
            JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
            WHERE sc.SourceID = ?
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, (song_id,)).fetchall()

            logger.debug(
                f"[SongCreditRepository] Found {len(rows)} credits for SongID: {song_id}"
            )
            return [self._row_to_song_credit(row) for row in rows]

    def _row_to_song_credit(self, row: sqlite3.Row) -> SongCredit:
        """Maps a physical database row to the strict Pydantic SongCredit model, enforcing RoleID exists."""
        role_id = row["RoleID"]
        if role_id is None:
            msg = f"VIOLATION: Database integrity error. RoleID cannot be NULL for CreditedNameID {row['CreditedNameID']} on SourceID {row['SourceID']}"
            logger.error(msg)
            raise ValueError(msg)

        return SongCredit(
            source_id=row["SourceID"],
            name_id=row["CreditedNameID"],
            role_id=role_id,
            display_name=row["DisplayName"],
        )
