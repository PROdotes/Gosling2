import sqlite3
from typing import Any, Dict, List, Mapping, Optional
from src.data.base_repository import BaseRepository
from src.models.domain import Identity, ArtistName
from src.services.logger import logger


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

    def get_by_id(self, identity_id: int) -> Optional[Identity]:
        """Fetch a basic Identity record."""
        logger.debug(f"[IdentityRepository] -> get_by_id(id={identity_id})")
        identities = self.get_by_ids([identity_id])
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

    def get_by_ids(self, identity_ids: List[int]) -> List[Identity]:
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
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, identity_ids).fetchall()

        identities = [self._row_to_identity(row) for row in rows]
        logger.debug(f"[IdentityRepository] <- get_by_ids() found {len(identities)}")
        return identities

    def get_all_identities(self) -> List[Identity]:
        """Fetch the directory of all identities."""
        logger.debug("[IdentityRepository] -> get_all_identities()")
        query = f"""
            SELECT {self._IDENTITY_COLUMNS}
            FROM Identities i
            {self._IDENTITY_JOIN}
            WHERE i.IsDeleted = 0
            ORDER BY DisplayName COLLATE NOCASE ASC
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()

        identities = [self._row_to_identity(row) for row in rows]
        logger.debug(
            f"[IdentityRepository] <- get_all_identities() count={len(identities)}"
        )
        return identities

    def search_identities(self, query: str) -> List[Identity]:
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
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, (fmt_q, fmt_q)).fetchall()
            result = [self._row_to_identity(row) for row in rows]
            logger.debug(
                f"[IdentityRepository] <- search_identities(q='{query}') count={len(result)}"
            )
            return result

    def get_group_ids_for_members(self, member_ids: List[int]) -> List[int]:
        """Batch-fetch GroupIdentityIDs for a list of MemberIdentityIDs."""
        logger.debug(
            f"[IdentityRepository] -> get_group_ids_for_members(count={len(member_ids)})"
        )
        if not member_ids:
            return []

        placeholders = ",".join(["?" for _ in member_ids])
        query = f"SELECT DISTINCT GroupIdentityID FROM GroupMemberships WHERE MemberIdentityID IN ({placeholders})"

        with self._get_connection() as conn:
            rows = conn.execute(query, member_ids).fetchall()
            result = [row[0] for row in rows]
            logger.debug(
                f"[IdentityRepository] <- get_group_ids_for_members() count={len(result)}"
            )
            return result

    def get_aliases_batch(self, identity_ids: List[int]) -> Dict[int, List[ArtistName]]:
        """Batch-fetch aliases for a list of identities."""
        logger.debug(
            f"[IdentityRepository] -> get_aliases_batch(count={len(identity_ids)})"
        )
        if not identity_ids:
            return {}

        placeholders = ",".join(["?" for _ in identity_ids])
        query = f"SELECT NameID, DisplayName, IsPrimaryName, OwnerIdentityID FROM ArtistNames WHERE OwnerIdentityID IN ({placeholders})"

        result: Dict[int, List[ArtistName]] = {iid: [] for iid in identity_ids}
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(query, identity_ids):
                alias = ArtistName(
                    id=row["NameID"],
                    display_name=row["DisplayName"],
                    is_primary=bool(row["IsPrimaryName"]),
                )
                result[row["OwnerIdentityID"]].append(alias)

        logger.debug(
            f"[IdentityRepository] <- get_aliases_batch() batched={len(result)} IDs"
        )
        return result

    def get_members_batch(self, identity_ids: List[int]) -> Dict[int, List[Identity]]:
        """Batch-fetch members for a list of group identities."""
        logger.debug(
            f"[IdentityRepository] -> get_members_batch(count={len(identity_ids)})"
        )
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
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(query, identity_ids):
                identity = self._row_to_identity(row)
                result[row["GroupIdentityID"]].append(identity)

        logger.debug(
            f"[IdentityRepository] <- get_members_batch() batched={len(result)} IDs"
        )
        return result

    def get_groups_batch(self, identity_ids: List[int]) -> Dict[int, List[Identity]]:
        """Batch-fetch groups for a list of person identities."""
        logger.debug(
            f"[IdentityRepository] -> get_groups_batch(count={len(identity_ids)})"
        )
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
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(query, identity_ids):
                identity = self._row_to_identity(row)
                result[row["MemberIdentityID"]].append(identity)

        logger.debug(
            f"[IdentityRepository] <- get_groups_batch() batched={len(result)} IDs"
        )
        return result

    def _row_to_identity(self, row: Mapping[str, Any]) -> Identity:
        return Identity(
            id=row["IdentityID"],
            type=row["IdentityType"],
            display_name=row["DisplayName"],
            legal_name=row["LegalName"],
        )
