from typing import List, Mapping, Any
from src.models.domain import SongCredit
from src.data.base_repository import BaseRepository
from src.services.logger import logger
import sqlite3


class SongCreditRepository(BaseRepository):
    """Bridges Song IDs to their Credits and Human Names."""

    _COLUMNS = "sc.SourceID, sc.CreditedNameID, sc.RoleID, an.DisplayName, an.IsPrimaryName, an.OwnerIdentityID, r.RoleName"

    def get_credits_for_songs(self, song_ids: List[int]) -> List[SongCredit]:
        """Batch-fetches credits for multiple songs in a single query."""
        if not song_ids:
            return []

        logger.debug(
            f"[SongCreditRepository] Batch-fetching credits for {len(song_ids)} songs."
        )
        placeholders = ",".join(["?" for _ in song_ids])
        query = f"""
            SELECT {self._COLUMNS}
            FROM SongCredits sc
            JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
            JOIN Roles r ON sc.RoleID = r.RoleID
            WHERE sc.SourceID IN ({placeholders})
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, song_ids).fetchall()

            logger.debug(f"[SongCreditRepository] Found {len(rows)} raw credit rows.")
            return [self._row_to_song_credit(row) for row in rows]

    def _row_to_song_credit(self, row: Mapping[str, Any]) -> SongCredit:
        """Maps a physical database row to the strict Pydantic SongCredit model, enforcing RoleID exists."""
        role_id = row["RoleID"]
        if role_id is None:
            msg = (
                f"VIOLATION: Database integrity error. RoleID cannot be NULL "
                f"for CreditedNameID {row['CreditedNameID']} on SourceID {row['SourceID']}"
            )
            logger.error(msg)
            raise ValueError(msg)

        return SongCredit(
            source_id=row["SourceID"],
            name_id=row["CreditedNameID"],
            identity_id=row["OwnerIdentityID"],
            role_id=role_id,
            role_name=row["RoleName"],
            display_name=row["DisplayName"],
            is_primary=bool(row["IsPrimaryName"]),
        )
