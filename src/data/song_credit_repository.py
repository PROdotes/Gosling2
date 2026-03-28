from typing import List, Mapping, Any
from src.models.domain import SongCredit
from src.data.base_repository import BaseRepository
from src.services.logger import logger
import sqlite3


class SongCreditRepository(BaseRepository):
    """Bridges Song IDs to their Credits and Human Names."""

    _COLUMNS = "sc.CreditID, sc.SourceID, sc.CreditedNameID, sc.RoleID, an.DisplayName, an.IsPrimaryName, an.OwnerIdentityID, r.RoleName"

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
            WHERE sc.SourceID IN ({placeholders}) AND an.IsDeleted = 0
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
            role_id = self.get_or_create_role(credit.role_name, cursor)
            name_id = self.get_or_create_credit_name(credit.display_name, cursor)
            cursor.execute(
                "INSERT OR IGNORE INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
                (source_id, name_id, role_id),
            )

        logger.info(
            f"[SongCreditRepository] <- insert_credits(source_id={source_id}) wrote {len(credits)} credits"
        )

    def get_or_create_role(self, role_name: str, cursor) -> int:
        """Get-or-create a Role by name. Returns role_id."""
        row = cursor.execute(
            "SELECT RoleID FROM Roles WHERE RoleName = ?", (role_name,)
        ).fetchone()
        if row:
            return row[0]
        cursor.execute("INSERT INTO Roles (RoleName) VALUES (?)", (role_name,))
        return cursor.lastrowid

    def get_or_create_credit_name(self, display_name: str, cursor) -> int:
        """
        Get-or-create an ArtistName by display name. Returns name_id.
        Reactivates soft-deleted records. Creates linked Identity if needed.
        """
        row = cursor.execute(
            "SELECT NameID, IsDeleted, OwnerIdentityID FROM ArtistNames WHERE DisplayName = ? COLLATE UTF8_NOCASE",
            (display_name,),
        ).fetchone()

        if row:
            name_id = row[0]
            if row[1]:  # IsDeleted — wake it up
                cursor.execute(
                    "UPDATE ArtistNames SET IsDeleted = 0 WHERE NameID = ?", (name_id,)
                )
                cursor.execute(
                    "UPDATE Identities SET IsDeleted = 0 WHERE IdentityID = ? AND IsDeleted = 1",
                    (row[2],),
                )
            return name_id

        # No ArtistName found — check if an Identity with this LegalName exists
        identity_row = cursor.execute(
            "SELECT IdentityID, IsDeleted FROM Identities WHERE LegalName = ?",
            (display_name,),
        ).fetchone()
        if identity_row:
            owner_identity_id = identity_row[0]
            if identity_row[1]:
                cursor.execute(
                    "UPDATE Identities SET IsDeleted = 0 WHERE IdentityID = ?",
                    (owner_identity_id,),
                )
        else:
            cursor.execute(
                "INSERT INTO Identities (IdentityType, LegalName) VALUES ('person', ?)",
                (display_name,),
            )
            owner_identity_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO ArtistNames (OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (?, ?, 1)",
            (owner_identity_id, display_name),
        )
        return cursor.lastrowid

    def add_credit(
        self,
        source_id: int,
        display_name: str,
        role_name: str,
        conn: sqlite3.Connection,
    ) -> SongCredit:
        """
        Add a single artist credit to a song. Get-or-creates ArtistName and Role.
        Returns the new SongCredit. Does NOT commit.
        """
        logger.debug(
            f"[SongCreditRepository] -> add_credit(source_id={source_id}, name='{display_name}', role='{role_name}')"
        )
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        role_id = self.get_or_create_role(role_name, cursor)
        name_id = self.get_or_create_credit_name(display_name, cursor)
        cursor.execute(
            "INSERT OR IGNORE INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
            (source_id, name_id, role_id),
        )
        row = cursor.execute(
            f"SELECT {self._COLUMNS} FROM SongCredits sc JOIN ArtistNames an ON sc.CreditedNameID = an.NameID JOIN Roles r ON sc.RoleID = r.RoleID WHERE sc.SourceID = ? AND sc.CreditedNameID = ? AND sc.RoleID = ?",
            (source_id, name_id, role_id),
        ).fetchone()
        logger.debug(
            f"[SongCreditRepository] <- add_credit() done name_id={name_id} role_id={role_id}"
        )
        return self._row_to_song_credit(row)

    def remove_credit(self, credit_id: int, conn: sqlite3.Connection) -> None:
        """
        Remove a single SongCredits link by its CreditID. Keeps ArtistName record.
        Does NOT commit.
        """
        logger.debug(f"[SongCreditRepository] -> remove_credit(credit_id={credit_id})")
        conn.cursor().execute(
            "DELETE FROM SongCredits WHERE CreditID = ?", (credit_id,)
        )
        logger.debug(
            f"[SongCreditRepository] <- remove_credit(credit_id={credit_id}) done"
        )

    def update_credit_name(
        self, name_id: int, new_name: str, conn: sqlite3.Connection
    ) -> None:
        """
        Update an ArtistName's DisplayName globally. Affects all songs linked to this name.
        Does NOT commit.
        """
        logger.debug(
            f"[SongCreditRepository] -> update_credit_name(name_id={name_id}, new_name='{new_name}')"
        )
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE ArtistNames SET DisplayName = ? WHERE NameID = ?",
            (new_name, name_id),
        )
        if cursor.rowcount == 0:
            logger.warning(
                f"[SongCreditRepository] update_credit_name(id={name_id}) NOT_FOUND"
            )
            raise LookupError(f"ArtistName {name_id} not found")
        logger.debug("[SongCreditRepository] <- update_credit_name() done")

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
            credit_id=row["CreditID"],
            source_id=row["SourceID"],
            name_id=row["CreditedNameID"],
            identity_id=row["OwnerIdentityID"],
            role_id=role_id,
            role_name=row["RoleName"],
            display_name=row["DisplayName"],
            is_primary=bool(row["IsPrimaryName"]),
        )
