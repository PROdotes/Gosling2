import sqlite3
from typing import Any, List, Mapping

from src.data.base_repository import BaseRepository
from src.models.domain import AlbumCredit
from src.services.logger import logger


class AlbumCreditRepository(BaseRepository):
    """Bridges Album IDs to their Credits and Human Names."""

    _COLUMNS = "ac.AlbumID, ac.CreditedNameID, ac.RoleID, an.DisplayName, an.IsPrimaryName, an.OwnerIdentityID, r.RoleName"

    def get_credits_for_albums(self, album_ids: List[int]) -> List[AlbumCredit]:
        """Batch-fetches credits for multiple albums in a single query."""
        if not album_ids:
            return []

        logger.debug(
            f"[AlbumCreditRepository] Batch-fetching credits for {len(album_ids)} albums."
        )
        placeholders = ",".join(["?" for _ in album_ids])
        query = f"""
            SELECT {self._COLUMNS}
            FROM AlbumCredits ac
            JOIN ArtistNames an ON ac.CreditedNameID = an.NameID
            JOIN Roles r ON ac.RoleID = r.RoleID
            WHERE ac.AlbumID IN ({placeholders})
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, album_ids).fetchall()

            logger.debug(
                f"[AlbumCreditRepository] Found {len(rows)} raw album credit rows."
            )
            return [self._row_to_album_credit(row) for row in rows]

    def _row_to_album_credit(self, row: Mapping[str, Any]) -> AlbumCredit:
        return AlbumCredit(
            album_id=row["AlbumID"],
            name_id=row["CreditedNameID"],
            identity_id=row["OwnerIdentityID"],
            role_id=row["RoleID"],
            role_name=row["RoleName"],
            display_name=row["DisplayName"],
            is_primary=bool(row["IsPrimaryName"]),
        )
