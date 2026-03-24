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

    def insert_credits(
        self, source_id: int, credits: List[SongCredit], conn: sqlite3.Connection
    ) -> None:
        """Get-or-create Roles + ArtistNames rows, then insert SongCredits links."""
        logger.debug(
            f"[SongCreditRepository] -> insert_credits(source_id={source_id}, count={len(credits)})"
        )
        if not credits:
            logger.debug("[SongCreditRepository] <- insert_credits() empty list, no-op")
            return

        cursor = conn.cursor()
        for credit in credits:
            # Get-or-create Role
            row = cursor.execute(
                "SELECT RoleID FROM Roles WHERE RoleName = ?",
                (credit.role_name,),
            ).fetchone()

            if row:
                role_id = row[0]
            else:
                cursor.execute(
                    "INSERT INTO Roles (RoleName) VALUES (?)",
                    (credit.role_name,),
                )
                role_id = cursor.lastrowid

            # Get-or-create ArtistName (match on DisplayName; new names get NULL identity)
            # TODO: Validate NULL OwnerIdentityID pattern against work DB (~500 entries)
            row = cursor.execute(
                "SELECT NameID FROM ArtistNames WHERE DisplayName = ?",
                (credit.display_name,),
            ).fetchone()

            if row:
                name_id = row[0]
            else:
                cursor.execute(
                    "INSERT INTO ArtistNames (OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (NULL, ?, 0)",
                    (credit.display_name,),
                )
                name_id = cursor.lastrowid

            # Insert SongCredits link (OR IGNORE for idempotency on UNIQUE constraint)
            cursor.execute(
                "INSERT OR IGNORE INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
                (source_id, name_id, role_id),
            )

        logger.info(
            f"[SongCreditRepository] <- insert_credits(source_id={source_id}) wrote {len(credits)} credits"
        )

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
