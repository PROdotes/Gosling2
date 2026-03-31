import sqlite3
from typing import Any, List, Mapping, Optional

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
            WHERE ac.AlbumID IN ({placeholders}) AND an.IsDeleted = 0
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

    def add_credit(
        self,
        album_id: int,
        display_name: str,
        role_name: str,
        conn: sqlite3.Connection,
        identity_id: Optional[int] = None,
    ) -> int:
        """
        Add a credit to an album. Get-or-creates ArtistName and Role. Does NOT commit.
        Returns the name_id of the credited artist.
        """
        logger.debug(
            f"[AlbumCreditRepository] -> add_credit(album_id={album_id}, name='{display_name}', role='{role_name}', identity_id={identity_id})"
        )
        from src.data.song_credit_repository import SongCreditRepository

        credit_repo = SongCreditRepository(self.db_path)
        cursor = conn.cursor()
        role_id = credit_repo.get_or_create_role(role_name, cursor)
        name_id = credit_repo.get_or_create_credit_name(display_name, cursor, identity_id)
        cursor.execute(
            "INSERT OR IGNORE INTO AlbumCredits (AlbumID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
            (album_id, name_id, role_id),
        )
        logger.debug(
            f"[AlbumCreditRepository] <- add_credit() done name_id={name_id} role_id={role_id}"
        )
        return name_id

    def remove_credit(
        self, album_id: int, name_id: int, conn: sqlite3.Connection
    ) -> None:
        """
        Remove a credit from an album. Deletes link only. Does NOT commit.
        """
        logger.debug(
            f"[AlbumCreditRepository] -> remove_credit(album_id={album_id}, name_id={name_id})"
        )
        conn.cursor().execute(
            "DELETE FROM AlbumCredits WHERE AlbumID = ? AND CreditedNameID = ?",
            (album_id, name_id),
        )
        logger.debug("[AlbumCreditRepository] <- remove_credit() done")
