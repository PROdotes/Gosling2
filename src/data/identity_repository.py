import sqlite3
from typing import Any, Callable, Dict, List, Mapping, Optional, TypeVar
from src.data.base_repository import BaseRepository
from src.models.domain import Identity, ArtistName
from src.services.logger import logger

T = TypeVar("T")


class IdentityRepository(BaseRepository):
    """
    Pure data fetcher for Artist Identities and their related data.
    No hydration logic - that belongs in the service layer.
    """

    _IDENTITY_COLUMNS = """
        i.IdentityID, i.IdentityType, i.LegalName, 
        COALESCE(an.DisplayName, i.LegalName, 'Unknown Artist #' || i.IdentityID) AS DisplayName
    """
    _IDENTITY_JOIN = "LEFT JOIN ArtistNames an ON i.IdentityID = an.OwnerIdentityID AND an.IsPrimaryName = 1 AND an.IsDeleted = 0"

    def get_by_id(
        self, identity_id: int, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[Identity]:
        """Fetch a basic Identity record."""
        logger.debug(f"[IdentityRepository] -> get_by_id(id={identity_id})")
        identities = self.get_by_ids([identity_id], conn=conn)
        if not identities:
            logger.debug(
                f"[IdentityRepository] <- get_by_id(id={identity_id}) NOT_FOUND"
            )
            return None

        identity = identities[0]
        logger.debug(
            f"[IdentityRepository] <- get_by_id(id={identity_id}) '{identity.display_name}'"
        )
        return identity

    def get_by_ids(
        self, identity_ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> List[Identity]:
        """Batch-fetch multiple identities by ID."""
        if not identity_ids:
            return []

        logger.debug(f"[IdentityRepository] -> get_by_ids(count={len(identity_ids)})")
        placeholders = ",".join(["?" for _ in identity_ids])
        query = f"""
            SELECT {self._IDENTITY_COLUMNS}
            FROM Identities i
            {self._IDENTITY_JOIN}
            WHERE i.IdentityID IN ({placeholders}) AND i.IsDeleted = 0
        """

        if conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, identity_ids).fetchall()
            return [self._row_to_identity(row) for row in rows]

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            rows = new_conn.execute(query, identity_ids).fetchall()
            identities = [self._row_to_identity(row) for row in rows]
            logger.debug(
                f"[IdentityRepository] <- get_by_ids() found {len(identities)}"
            )
            return identities

    def get_all_identities(
        self, conn: Optional[sqlite3.Connection] = None
    ) -> List[Identity]:
        """Fetch the directory of all identities."""
        logger.debug("[IdentityRepository] -> get_all_identities()")
        query = f"""
            SELECT {self._IDENTITY_COLUMNS}
            FROM Identities i
            {self._IDENTITY_JOIN}
            WHERE i.IsDeleted = 0
            ORDER BY DisplayName COLLATE NOCASE ASC
        """

        if conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
            return [self._row_to_identity(row) for row in rows]

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            rows = new_conn.execute(query).fetchall()
            identities = [self._row_to_identity(row) for row in rows]
            logger.debug(
                f"[IdentityRepository] <- get_all_identities() count={len(identities)}"
            )
            return identities

    def search_identities(
        self, query: str, conn: Optional[sqlite3.Connection] = None
    ) -> List[Identity]:
        """Find identities whose DisplayName, LegalName, or Alias match the query."""
        logger.debug(f"[IdentityRepository] -> search_identities(q='{query}')")
        fmt_q = f"%{query}%"

        # Search against all aliases, but return identities with their primary DisplayName
        query_sql = f"""
            SELECT DISTINCT {self._IDENTITY_COLUMNS}
            FROM Identities i
            {self._IDENTITY_JOIN}
            WHERE i.IsDeleted = 0 AND (i.IdentityID IN (
                SELECT OwnerIdentityID FROM ArtistNames 
                WHERE DisplayName LIKE ? AND IsDeleted = 0
            ) OR i.LegalName LIKE ?)
            ORDER BY DisplayName ASC
        """

        if conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, (fmt_q, fmt_q)).fetchall()
            return [self._row_to_identity(row) for row in rows]

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            rows = new_conn.execute(query_sql, (fmt_q, fmt_q)).fetchall()
            result = [self._row_to_identity(row) for row in rows]
            logger.debug(
                f"[IdentityRepository] <- search_identities(q='{query}') count={len(result)}"
            )
            return result

    def get_group_ids_for_members(
        self, member_ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> List[int]:
        """Batch-fetch GroupIdentityIDs for a list of MemberIdentityIDs."""
        logger.debug(
            f"[IdentityRepository] -> get_group_ids_for_members(count={len(member_ids)})"
        )
        if not member_ids:
            return []

        placeholders = ",".join(["?" for _ in member_ids])
        query = f"SELECT DISTINCT GroupIdentityID FROM GroupMemberships WHERE MemberIdentityID IN ({placeholders})"

        if conn:
            rows = conn.execute(query, member_ids).fetchall()
            return [row[0] for row in rows]

        with self._get_connection() as new_conn:
            rows = new_conn.execute(query, member_ids).fetchall()
            result = [row[0] for row in rows]
            logger.debug(
                f"[IdentityRepository] <- get_group_ids_for_members() count={len(result)}"
            )
            return result

    def _run_batch_query(
        self,
        query: str,
        ids: List[int],
        result: Dict[int, List[T]],
        row_mapper: Callable[[sqlite3.Row], None],
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[int, List[T]]:
        """Execute a batch query and map rows into result using row_mapper."""
        if conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(query, ids):
                row_mapper(row)
            return result
        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            for row in new_conn.execute(query, ids):
                row_mapper(row)
            return result

    def get_aliases_batch(
        self,
        identity_ids: List[int],
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[int, List[ArtistName]]:
        """Batch-fetch aliases for a list of identities."""
        logger.debug(f"[IdentityRepository] -> get_aliases_batch(count={len(identity_ids)})")
        if not identity_ids:
            return {}
        placeholders = ",".join(["?" for _ in identity_ids])
        query = f"SELECT NameID, DisplayName, IsPrimaryName, OwnerIdentityID FROM ArtistNames WHERE OwnerIdentityID IN ({placeholders}) AND IsDeleted = 0"
        result: Dict[int, List[ArtistName]] = {iid: [] for iid in identity_ids}
        return self._run_batch_query(query, identity_ids, result, lambda row: result[row["OwnerIdentityID"]].append(
            ArtistName(id=row["NameID"], display_name=row["DisplayName"], is_primary=bool(row["IsPrimaryName"]))
        ), conn)

    def get_members_batch(
        self,
        identity_ids: List[int],
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[int, List[Identity]]:
        """Batch-fetch members for a list of group identities."""
        logger.debug(f"[IdentityRepository] -> get_members_batch(count={len(identity_ids)})")
        if not identity_ids:
            return {}
        placeholders = ",".join(["?" for _ in identity_ids])
        query = f"""
            SELECT gm.GroupIdentityID, i.IdentityID, i.IdentityType, i.LegalName,
                   COALESCE(an.DisplayName, i.LegalName, 'Unknown Artist #' || i.IdentityID) AS DisplayName
            FROM GroupMemberships gm
            JOIN Identities i ON gm.MemberIdentityID = i.IdentityID
            LEFT JOIN ArtistNames an ON i.IdentityID = an.OwnerIdentityID AND an.IsPrimaryName = 1 AND an.IsDeleted = 0
            WHERE gm.GroupIdentityID IN ({placeholders}) AND i.IsDeleted = 0
        """
        result: Dict[int, List[Identity]] = {iid: [] for iid in identity_ids}
        return self._run_batch_query(query, identity_ids, result, lambda row: result[row["GroupIdentityID"]].append(
            self._row_to_identity(row)
        ), conn)

    def get_groups_batch(
        self,
        identity_ids: List[int],
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[int, List[Identity]]:
        """Batch-fetch groups for a list of person identities."""
        logger.debug(f"[IdentityRepository] -> get_groups_batch(count={len(identity_ids)})")
        if not identity_ids:
            return {}
        placeholders = ",".join(["?" for _ in identity_ids])
        query = f"""
            SELECT gm.MemberIdentityID, i.IdentityID, i.IdentityType, i.LegalName,
                   COALESCE(an.DisplayName, i.LegalName, 'Unknown Artist #' || i.IdentityID) AS DisplayName
            FROM GroupMemberships gm
            JOIN Identities i ON gm.GroupIdentityID = i.IdentityID
            LEFT JOIN ArtistNames an ON i.IdentityID = an.OwnerIdentityID AND an.IsPrimaryName = 1 AND an.IsDeleted = 0
            WHERE gm.MemberIdentityID IN ({placeholders}) AND i.IsDeleted = 0
        """
        result: Dict[int, List[Identity]] = {iid: [] for iid in identity_ids}
        return self._run_batch_query(query, identity_ids, result, lambda row: result[row["MemberIdentityID"]].append(
            self._row_to_identity(row)
        ), conn)

    def add_alias(
        self,
        identity_id: int,
        display_name: str,
        cursor: sqlite3.Cursor,
        name_id: Optional[int] = None,
    ) -> int:
        """Link a name to an identity. ID-First: If name_id is provided, prioritize it."""
        logger.debug(
            f"[IdentityRepository] -> add_alias(id={identity_id}, name='{display_name}', name_id={name_id})"
        )
        display_name = display_name.strip()

        # 1. Collision Check (Truth-First)
        # If name_id is null, the name MUST be truly new OR already belong to this identity.
        if not name_id:
            collision = cursor.execute(
                "SELECT NameID, OwnerIdentityID FROM ArtistNames WHERE DisplayName = ? COLLATE UTF8_NOCASE",
                (display_name,),
            ).fetchone()

            if collision:
                if collision[1] == identity_id:
                    # Scenario A: Already belongs to this identity (Idempotent)
                    # Reactivate if it was soft-deleted
                    cursor.execute(
                        "UPDATE ArtistNames SET IsDeleted = 0 WHERE NameID = ?",
                        (collision[0],),
                    )
                    return collision[0]
                else:
                    # Theft/Ambiguity: Blocked
                    logger.error(
                        f"[IdentityRepository] Blocked: '{display_name}' already exists for identity {collision[1]}. Mandatory ID required for re-linking."
                    )
                    raise ValueError(
                        f"Identity collision: '{display_name}' already exists in the database belonging to another identity. You must provide a specific NameID/IdentityID to re-parent this name."
                    )

        # 2. Lookup the record to move/idempotence check
        found_row = None
        if name_id:
            # 2.1 Try NameID (Direct match from search results or specific alias)
            found_row = cursor.execute(
                "SELECT NameID, OwnerIdentityID, IsPrimaryName FROM ArtistNames WHERE NameID = ?",
                (name_id,),
            ).fetchone()

            # 2.2 Fallback: Try IdentityID (Search Picker returns Identity IDs)
            if not found_row:
                found_row = cursor.execute(
                    "SELECT NameID, OwnerIdentityID, IsPrimaryName FROM ArtistNames WHERE OwnerIdentityID = ? AND IsPrimaryName = 1",
                    (name_id,),
                ).fetchone()

        if found_row:
            found_name_id, current_owner, is_primary = (
                found_row[0],
                found_row[1],
                bool(found_row[2]),
            )

            # Scenario A: Already belongs to this identity
            if current_owner == identity_id:
                # Reactivate if it was soft-deleted
                cursor.execute(
                    "UPDATE ArtistNames SET IsDeleted = 0 WHERE NameID = ?",
                    (found_name_id,),
                )
                return found_name_id

            # Scenario B: Move a non-primary alias (Safe)
            if not is_primary:
                cursor.execute(
                    "UPDATE ArtistNames SET OwnerIdentityID = ?, IsDeleted = 0 WHERE NameID = ?",
                    (identity_id, found_name_id),
                )
                logger.info(
                    f"[IdentityRepository] Re-parented alias '{display_name}' (ID={found_name_id}) from {current_owner} to {identity_id}"
                )
                return found_name_id

            # Scenario C: Re-parenting a PRIMARY name (Hierarchy check)
            if self._is_parent_identity(current_owner, cursor):
                logger.error(
                    f"[IdentityRepository] Collision: '{display_name}' is primary for {current_owner} which already has other aliases."
                )
                raise ValueError(
                    f"Cannot orphan a parent identity: '{display_name}' is the primary name for identity {current_owner} which already has other aliases linked to it."
                )

            # Scenario D: Re-parenting primary name of a "Dead" identity (Safe Merge)
            cursor.execute(
                "UPDATE ArtistNames SET OwnerIdentityID = ?, IsPrimaryName = 0, IsDeleted = 0 WHERE NameID = ?",
                (identity_id, found_name_id),
            )
            # Mark old identity as deleted
            cursor.execute(
                "UPDATE Identities SET IsDeleted = 1 WHERE IdentityID = ?",
                (current_owner,),
            )
            logger.info(
                f"[IdentityRepository] Merged identity {current_owner} into {identity_id} by re-parenting primary name '{display_name}'"
            )
            return found_name_id

        # 2. Truly new name (or name_id was provided but not found, which shouldn't happen)
        cursor.execute(
            "INSERT INTO ArtistNames (OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (?, ?, 0)",
            (identity_id, display_name),
        )
        return cursor.lastrowid

    def _is_parent_identity(self, identity_id: int, cursor: sqlite3.Cursor) -> bool:
        """Return True if this identity has multiple aliases (is a parent of a tree)."""
        # A solo identity is safe to merge. A parent with multiple aliases is not.
        row = cursor.execute(
            "SELECT COUNT(*) FROM ArtistNames WHERE OwnerIdentityID = ? AND IsDeleted = 0",
            (identity_id,),
        ).fetchone()
        count = row[0] if row else 0
        return count > 1

    def delete_alias(self, name_id: int, cursor: sqlite3.Cursor) -> None:
        """Remove an alias link. Guard: primary names cannot be deleted."""
        logger.debug(f"[IdentityRepository] -> delete_alias(name_id={name_id})")
        # 1. Primary check
        row = cursor.execute(
            "SELECT IsPrimaryName FROM ArtistNames WHERE NameID = ?", (name_id,)
        ).fetchone()
        if not row:
            return
        if row[0]:
            raise ValueError("Cannot delete the primary name of an identity")

        cursor.execute(
            "UPDATE ArtistNames SET IsDeleted = 1 WHERE NameID = ?", (name_id,)
        )

    def update_legal_name(
        self, identity_id: int, legal_name: Optional[str], conn: sqlite3.Connection
    ) -> None:
        """Update the LegalName field on an Identity. Pass None to clear it."""
        logger.debug(
            f"[IdentityRepository] -> update_legal_name(id={identity_id}, name={legal_name!r})"
        )
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT IdentityID FROM Identities WHERE IdentityID = ? AND IsDeleted = 0",
            (identity_id,),
        ).fetchone()
        if not row:
            raise LookupError(f"Identity ID {identity_id} not found")
        cursor.execute(
            "UPDATE Identities SET LegalName = ? WHERE IdentityID = ?",
            (legal_name, identity_id),
        )

    def find_identity_by_name(
        self, name: str, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[int]:
        """Return the IdentityID for an exact (case-insensitive) ArtistName match, or None."""
        logger.debug(f"[IdentityRepository] -> find_identity_by_name(name='{name}')")
        query = "SELECT OwnerIdentityID FROM ArtistNames WHERE DisplayName = ? COLLATE UTF8_NOCASE AND IsDeleted = 0"

        if conn:
            row = conn.execute(query, (name,)).fetchone()
            if row:
                return row[0]
            return None

        with self._get_connection() as new_conn:
            row = new_conn.execute(query, (name,)).fetchone()
            if row:
                logger.debug(
                    f"[IdentityRepository] <- find_identity_by_name() found ID={row[0]}"
                )
                return row[0]
            logger.debug("[IdentityRepository] <- find_identity_by_name() NOT_FOUND")
            return None

    def _row_to_identity(self, row: Mapping[str, Any]) -> Identity:
        return Identity(
            id=row["IdentityID"],
            type=row["IdentityType"],
            display_name=row["DisplayName"],
            legal_name=row["LegalName"],
        )
