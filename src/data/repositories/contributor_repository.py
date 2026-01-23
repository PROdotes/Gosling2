from typing import List, Tuple, Optional, Any, Union
import sqlite3
from src.data.database import BaseRepository
from ..models.contributor import Contributor
from ..models.contributor_alias import ContributorAlias
from .generic_repository import GenericRepository

class ContributorRepository(GenericRepository[Contributor]):
    """
    Repository for Contributor data access.
    Inherits GenericRepository for automatic Audit Logging.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path, "Contributors", "contributor_id")

    def get_by_id(self, contributor_id: int, conn=None) -> Optional[Contributor]:
        """Fetch single contributor by ID. (Connection Aware)"""
        if conn:
            return self._get_by_id_logic(contributor_id, conn)
        
        try:
            with self.get_connection() as conn:
                return self._get_by_id_logic(contributor_id, conn)
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching contributor by id: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[Contributor]:
        """Fetch single contributor by primary name or alias. (Case-insensitive exact match)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Try primary name match (case-insensitive)
                cursor.execute("SELECT ContributorID FROM Contributors WHERE ContributorName = ? COLLATE UTF8_NOCASE", (name,))
                row = cursor.fetchone()
                if row:
                    return self.get_by_id(row[0], conn=conn)
                
                # try alias match (case-insensitive)
                cursor.execute("SELECT ContributorID FROM ContributorAliases WHERE AliasName = ? COLLATE UTF8_NOCASE", (name,))
                row = cursor.fetchone()
                if row:
                    return self.get_by_id(row[0], conn=conn)
                
                return None
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching contributor by name: {e}")
            return None

    def _get_by_id_logic(self, contributor_id: int, conn) -> Optional[Contributor]:
        cursor = conn.cursor()
        cursor.execute("SELECT ContributorID, ContributorName, SortName, ContributorType FROM Contributors WHERE ContributorID = ?", (contributor_id,))
        row = cursor.fetchone()
        if row:
            return Contributor(
                contributor_id=row[0],
                name=row[1],
                sort_name=row[2],
                type=row[3]
            )
        return None

    def get_by_role(self, role_name: str) -> List[Contributor]:
        """Fetch all contributors who have a specific role assigned at least once"""
        from ..models.contributor import Contributor
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT c.ContributorID, c.ContributorName, c.SortName, c.ContributorType
                    FROM Contributors c
                    JOIN MediaSourceContributorRoles mscr ON c.ContributorID = mscr.ContributorID
                    JOIN Roles r ON mscr.RoleID = r.RoleID
                    WHERE r.RoleName = ?
                    ORDER BY c.SortName ASC
                """, (role_name,))

                return [Contributor(contributor_id=r[0], name=r[1], sort_name=r[2], type=r[3]) for r in cursor.fetchall()]
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching contributors by role: {e}")
            return []

    def get_usage_count(self, contributor_id: int) -> int:
        """Return the number of songs this contributor is linked to."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM MediaSourceContributorRoles WHERE ContributorID = ?", (contributor_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            from src.core import logger
            logger.error(f"Error getting usage count for {contributor_id}: {e}")
            return 0

    def get_all_with_usage(self, type_filter: Optional[str] = None, orphans_only: bool = False) -> List[Tuple[Contributor, int]]:
        """
        Get all contributors with their usage counts in a single query.

        Args:
            type_filter: Filter by type ('person', 'group'). None = all.
            orphans_only: If True, only return contributors with 0 usage.

        Returns:
            List of (Contributor, usage_count) tuples, sorted by name.
        """
        query = """
            SELECT c.ContributorID, c.ContributorName, c.SortName, c.ContributorType,
                   COUNT(DISTINCT mscr.SourceID) as usage_count
            FROM Contributors c
            LEFT JOIN MediaSourceContributorRoles mscr ON c.ContributorID = mscr.ContributorID
        """
        params = []

        if type_filter:
            query += " WHERE c.ContributorType = ? COLLATE NOCASE"
            params.append(type_filter)

        query += " GROUP BY c.ContributorID, c.ContributorName, c.SortName, c.ContributorType"

        if orphans_only:
            query += " HAVING usage_count = 0"

        query += " ORDER BY c.SortName COLLATE NOCASE"

        results = []
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, tuple(params))
                for row in cursor.fetchall():
                    contrib = Contributor(
                        contributor_id=row[0],
                        name=row[1],
                        sort_name=row[2],
                        type=row[3]
                    )
                    usage = row[4]
                    results.append((contrib, usage))
        except Exception as e:
            from src.core import logger
            logger.error(f"Error in get_all_with_usage: {e}")
        return results

    def get_orphan_count(self, type_filter: Optional[str] = None) -> int:
        """Count contributors with zero usage (orphans)."""
        query = """
            SELECT COUNT(*) FROM (
                SELECT c.ContributorID
                FROM Contributors c
                LEFT JOIN MediaSourceContributorRoles mscr ON c.ContributorID = mscr.ContributorID
        """
        params = []

        if type_filter:
            query += " WHERE c.ContributorType = ? COLLATE NOCASE"
            params.append(type_filter)

        query += " GROUP BY c.ContributorID HAVING COUNT(DISTINCT mscr.SourceID) = 0)"

        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, tuple(params))
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            from src.core import logger
            logger.error(f"Error in get_orphan_count: {e}")
            return 0

    def delete_all_orphans(self, type_filter: Optional[str] = None, batch_id: Optional[str] = None) -> int:
        """
        Delete all contributors with zero usage.

        Args:
            type_filter: Only delete orphans of this type. None = all.
            batch_id: Audit batch ID.

        Returns:
            Number of contributors deleted.
        """
        from src.core.audit_logger import AuditLogger

        # First get the orphans
        orphans = self.get_all_with_usage(type_filter=type_filter, orphans_only=True)

        if not orphans:
            return 0

        deleted = 0
        try:
            with self.get_connection() as conn:
                auditor = AuditLogger(conn, batch_id=batch_id)
                cursor = conn.cursor()

                for contrib, _ in orphans:
                    # Log deletion
                    auditor.log_delete("Contributors", contrib.contributor_id, contrib.to_dict())
                    # Delete aliases first
                    cursor.execute("DELETE FROM ContributorAliases WHERE ContributorID = ?", (contrib.contributor_id,))
                    # Delete contributor
                    cursor.execute("DELETE FROM Contributors WHERE ContributorID = ?", (contrib.contributor_id,))
                    deleted += 1
        except Exception as e:
            from src.core import logger
            logger.error(f"Error in delete_all_orphans: {e}")

        return deleted

    def swap_song_contributor(self, song_id: int, old_id: int, new_id: int, batch_id: Optional[str] = None) -> bool:
        """Replace one contributor link with another for a single song. (Deduplication aware)"""
        try:
            from src.core.audit_logger import AuditLogger
            with self.get_connection() as conn:
                cursor = conn.cursor()
                auditor = AuditLogger(conn, batch_id=batch_id)
                
                # 1. Fetch current roles for old_id to audit
                cursor.execute("SELECT RoleID, CreditedAliasID FROM MediaSourceContributorRoles WHERE SourceID = ? AND ContributorID = ?", (song_id, old_id))
                old_links = cursor.fetchall()

                # 2. Deduplicate: Find roles that BOTH already have for this song
                # If both have the same role, we must delete the OLD one to avoiding breaking the PK (Source, Contributor, Role)
                cursor.execute("""
                    DELETE FROM MediaSourceContributorRoles 
                    WHERE SourceID = ? AND ContributorID = ? AND RoleID IN (
                        SELECT RoleID FROM MediaSourceContributorRoles WHERE SourceID = ? AND ContributorID = ?
                    )
                """, (song_id, old_id, song_id, new_id))
                
                # 3. Update remaining roles from OLD to NEW
                cursor.execute("""
                    UPDATE MediaSourceContributorRoles 
                    SET ContributorID = ?, CreditedAliasID = NULL
                    WHERE SourceID = ? AND ContributorID = ?
                """, (new_id, song_id, old_id))

                # 4. Audit
                for r_id, a_id in old_links:
                    auditor.log_update("MediaSourceContributorRoles", f"{song_id}-{old_id}-{r_id}", 
                        {"ContributorID": old_id}, {"ContributorID": new_id})

                return True 
        except Exception as e:
            from src.core import logger
            logger.error(f"Error swapping contributor {old_id} -> {new_id} on song {song_id}: {e}")
            return False



    def get_all_aliases(self) -> List[str]:
        """Get all alias names"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT AliasName FROM ContributorAliases ORDER BY AliasName ASC")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching aliases: {e}")
            return []

    def get_all_names(self) -> List[str]:
        """Fetch all unique contributor primary names (Ordered by SortName)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT ContributorName FROM Contributors ORDER BY SortName")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching contributor names: {e}")
            return []

    def _insert_db(self, cursor: sqlite3.Cursor, contributor: Contributor, **kwargs) -> int:
        """Execute SQL INSERT for GenericRepository"""
        cursor.execute(
            "INSERT INTO Contributors (ContributorName, SortName, ContributorType) VALUES (?, ?, ?)",
            (contributor.name, contributor.sort_name, contributor.type)
        )
        return cursor.lastrowid

    def _update_db(self, cursor: sqlite3.Cursor, contributor: Contributor, **kwargs) -> None:
        """Execute SQL UPDATE for GenericRepository.
        Note: Type change membership cleanup is handled by ContributorService.update()
        which uses IdentityRepository methods with the new GroupMemberships table.
        """
        cursor.execute(
            "UPDATE Contributors SET ContributorName = ?, SortName = ?, ContributorType = ? WHERE ContributorID = ?",
            (contributor.name, contributor.sort_name, contributor.type, contributor.contributor_id)
        )

    def _delete_db(self, cursor: sqlite3.Cursor, record_id: int, **kwargs) -> None:
        """Execute SQL DELETE for GenericRepository"""
        cursor.execute("DELETE FROM Contributors WHERE ContributorID = ?", (record_id,))

    def create(self, name: str, type: str = 'person', sort_name: str = None, conn=None, batch_id: Optional[str] = None) -> Contributor:
        """Create new contributor. Auto-generates sort_name if not provided. (Connection Aware)"""
        if not sort_name:
            sort_name = self._generate_sort_name(name)
        
        # Helper: Construct Object
        c = Contributor(None, name, sort_name, type)

        if conn:
            # Connection Passed: Manual Audit to preserve transaction context
            cursor = conn.cursor()
            new_id = self._insert_db(cursor, c)
            c.contributor_id = new_id
            
            from src.core.audit_logger import AuditLogger
            try:
                AuditLogger(conn, batch_id=batch_id).log_insert("Contributors", new_id, c.to_dict())
            except Exception:
                pass # Don't fail create if audit fails in legacy path? 
            return c

        else:
            # No Connection: Use GenericRepository.insert (Auto Transaction + Audit)
            new_id = self.insert(c, batch_id=batch_id)
            if new_id:
                c.contributor_id = new_id
                return c
            else:
                 raise Exception("Failed to insert contributor")





    def search(self, query: str) -> List[Contributor]:
        """Search by name or alias (case-insensitive, partial match)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Unified search across name and aliases
                q = f"%{query}%"
                cursor.execute("""
                    SELECT 
                        C.ContributorID, 
                        C.ContributorName, 
                        C.SortName, 
                        C.ContributorType,
                        CASE 
                            WHEN C.ContributorName LIKE ? THEN NULL
                            ELSE (SELECT AliasName FROM ContributorAliases 
                                  WHERE ContributorID = C.ContributorID AND AliasName LIKE ? 
                                  ORDER BY CASE WHEN AliasName = ? THEN 0 ELSE 1 END, AliasName ASC 
                                  LIMIT 1)
                        END as MatchedAlias
                    FROM Contributors C
                    LEFT JOIN ContributorAliases CA ON C.ContributorID = CA.ContributorID
                    WHERE C.ContributorName LIKE ? OR CA.AliasName LIKE ?
                    GROUP BY C.ContributorID
                    ORDER BY 
                        CASE WHEN C.ContributorName LIKE ? THEN 0 ELSE 1 END, -- Exact/Partial Name Match
                        CASE WHEN CA.AliasName LIKE ? THEN 0 ELSE 1 END,      -- Alias Match
                        C.SortName ASC
                """, (q, q, query, q, q, q, q))
                return [Contributor(contributor_id=r[0], name=r[1], sort_name=r[2], type=r[3], matched_alias=r[4]) for r in cursor.fetchall()]
        except Exception as e:
            from src.core import logger
            logger.error(f"Error searching contributors: {e}")
            return []

    def get_all(self) -> List[Contributor]:
        """Fetch all contributors."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ContributorID, ContributorName, SortName, ContributorType FROM Contributors ORDER BY SortName ASC")
                return [Contributor(contributor_id=r[0], name=r[1], sort_name=r[2], type=r[3]) for r in cursor.fetchall()]
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching all contributors: {e}")
            return []

    def get_all_by_type(self, type_name: str) -> List[Contributor]:
        """Fetch all contributors of a specific type (supports 'person', 'group', 'alias')."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                type_lower = type_name.lower()
                
                if type_lower == "alias":
                    cursor.execute("""
                        SELECT 
                            C.ContributorID, 
                            CA.AliasName as Name, 
                            C.ContributorType
                        FROM ContributorAliases CA 
                        JOIN Contributors C ON CA.ContributorID = C.ContributorID
                        ORDER BY Name ASC
                    """)
                    return [Contributor(contributor_id=r[0], name=r[1], type=r[2], matched_alias=r[1]) for r in cursor.fetchall()]
                
                cursor.execute("""
                    SELECT ContributorID, ContributorName, SortName, ContributorType 
                    FROM Contributors 
                    WHERE ContributorType = ? COLLATE UTF8_NOCASE 
                    ORDER BY SortName ASC
                """, (type_lower,))
                return [Contributor(contributor_id=r[0], name=r[1], sort_name=r[2], type=r[3]) for r in cursor.fetchall()]
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching contributors by type: {e}")
            return []

    def search_identities(self, query: str) -> List[Tuple[int, str, str, str]]:
        """
        Search for ANY matching name (Primary or Alias) and return flat results.
        Returns list of (ContributorID, DisplayName, Type, MatchSource)
        MatchSource is 'Primary' or 'Alias'.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                q = f"%{query}%" if query else "%"
                
                # We want a UNION of Primary matches and Alias matches
                # If query is empty (%), it returns EVERYTHING.
                cursor.execute("""
                    SELECT 
                        ContributorID, 
                        ContributorName as Name, 
                        ContributorType, 
                        'Primary' as MatchSource
                    FROM Contributors 
                    WHERE ContributorName LIKE ?
                    
                    UNION
                    
                    SELECT 
                        C.ContributorID, 
                        CA.AliasName as Name, 
                        C.ContributorType, 
                        'Alias' as MatchSource
                    FROM ContributorAliases CA 
                    JOIN Contributors C ON CA.ContributorID = C.ContributorID
                    WHERE CA.AliasName LIKE ?
                    
                    ORDER BY Name ASC
                """, (q, q))
                
                return cursor.fetchall()
        except Exception as e:
            from src.core import logger
            logger.error(f"Error searching identities: {e}")
            return []

    def get_types_for_names(self, names: List[str]) -> dict:
        """
        Get type ('person' or 'group') for a list of names.
        Returns: {name: type}
        """
        if not names: return {}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Batch query? SQLite limit is 999 vars. 
                cursor.execute("""
                    SELECT an.DisplayName, i.IdentityType, an.IsPrimaryName 
                    FROM ArtistNames an
                    LEFT JOIN Identities i ON an.OwnerIdentityID = i.IdentityID
                """)
                rows = cursor.fetchall()
                
                # Case insensitive lookup map
                name_map = {}
                for r in rows:
                    name = r[0].lower()
                    id_type = r[1]
                    is_primary = r[2]
                    
                    if not is_primary:
                        # Explicitly mark as alias so FilterWidget can bin it correctly
                        name_map[name] = 'alias'
                    else:
                        name_map[name] = id_type or 'person'
                
                result = {}
                for n in names:
                    t = name_map.get(n.lower())
                    if t:
                        result[n] = t
                return result
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching contributor types: {e}")
            return {}

    def get_or_create(self, name: str, type: str = 'person', conn=None, batch_id: Optional[str] = None) -> Tuple[Contributor, bool]:
        """
        Get existing or create new. 
        Returns (contributor, was_created). (Connection Aware)
        """
        if conn:
            return self._get_or_create_logic(name, type, conn, batch_id=batch_id)

        try:
            with self.get_connection() as conn:
                return self._get_or_create_logic(name, type, conn, batch_id=batch_id)
        except Exception as e:
            from src.core import logger
            logger.error(f"Error in get_or_create: {e}")
            # Fallback to creating a disconnected object if everything fails? 
            # Better to let it bubble or return a dummy.
            raise

    def _get_or_create_logic(self, name: str, type: str, conn, batch_id: Optional[str] = None) -> Tuple[Contributor, bool]:
        cursor = conn.cursor()
        # 1. Check direct name match (NOCASE)
        cursor.execute("SELECT ContributorID FROM Contributors WHERE ContributorName = ? COLLATE UTF8_NOCASE", (name,))
        row = cursor.fetchone()
        if row:
            return self.get_by_id(row[0], conn=conn), False
        
        # 2. Check alias match (NOCASE)
        cursor.execute("SELECT ContributorID FROM ContributorAliases WHERE AliasName = ? COLLATE UTF8_NOCASE", (name,))
        row = cursor.fetchone()
        if row:
            return self.get_by_id(row[0], conn=conn), False
        
        # 3. Create if not found
        return self.create(name, type, conn=conn, batch_id=batch_id), True

    def validate_identity(self, name: str, exclude_id: int = None) -> Tuple[Optional[int], str]:
        """
        Check if name exists as Primary or Alias. 
        Returns (conflict_id_or_none, message).
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check Name Conflict
                query = "SELECT ContributorID, ContributorName FROM Contributors WHERE ContributorName = ? COLLATE UTF8_NOCASE"
                params = [name]
                if exclude_id:
                    query += " AND ContributorID != ?"
                    params.append(exclude_id)
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                if row:
                    return row[0], f"Name '{name}' already exists as a primary artist (ID: {row[0]})."
                
                # Check Alias Conflict
                query = """
                    SELECT C.ContributorID, C.ContributorName 
                    FROM ContributorAliases CA
                    JOIN Contributors C ON CA.ContributorID = C.ContributorID
                    WHERE CA.AliasName = ? COLLATE UTF8_NOCASE
                """
                params = [name]
                if exclude_id:
                    query += " AND C.ContributorID != ?"
                    params.append(exclude_id)
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                if row:
                    return row[0], f"Name '{name}' exists as an alias for artist '{row[1]}' (ID: {row[0]})."
                
                return None, ""
        except Exception as e:
            return None, str(e)

    # Complex identity methods removed (Moved to IdentityService)











    def get_aliases(self, contributor_id: int) -> List[ContributorAlias]:
        """Get all aliases for a contributor (ID and Name)."""
        from ..models.contributor_alias import ContributorAlias
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT AliasID, ContributorID, AliasName FROM ContributorAliases WHERE ContributorID = ?", (contributor_id,))
                return [ContributorAlias(alias_id=r[0], contributor_id=r[1], alias_name=r[2]) for r in cursor.fetchall()]
        except Exception as e:
            return []

    def add_alias(self, contributor_id: int, alias_name: str, batch_id: Optional[str] = None) -> int:
        """Add an alias."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO ContributorAliases (ContributorID, AliasName) VALUES (?, ?)", (contributor_id, alias_name))
                new_id = cursor.lastrowid
                
                # Audit Aliases
                from src.core.audit_logger import AuditLogger
                AuditLogger(conn, batch_id=batch_id).log_insert("ContributorAliases", new_id, {
                    "ContributorID": contributor_id,
                    "AliasName": alias_name
                })
                
                return new_id
        except Exception as e:
            return -1

    def update_alias(self, alias_id: int, new_name: str, batch_id: Optional[str] = None) -> bool:
        """Rename an alias."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Get old name for audit
                cursor.execute("SELECT ContributorID, AliasName FROM ContributorAliases WHERE AliasID = ?", (alias_id,))
                row = cursor.fetchone()
                if not row: return False
                old_cid, old_name = row

                cursor.execute("UPDATE ContributorAliases SET AliasName = ? WHERE AliasID = ?", (new_name, alias_id))
                
                if cursor.rowcount > 0:
                    from src.core.audit_logger import AuditLogger
                    AuditLogger(conn, batch_id=batch_id).log_update("ContributorAliases", alias_id, 
                        {"AliasName": old_name}, {"AliasName": new_name}
                    )
                return cursor.rowcount > 0
        except Exception as e:
            return False




    def delete_alias(self, alias_id: int, batch_id: Optional[str] = None) -> bool:
        """Delete an alias. Nullifies any specific credit references first."""
        try:
            from src.core.audit_logger import AuditLogger
            with self.get_connection() as conn:
                cursor = conn.cursor()
                auditor = AuditLogger(conn, batch_id=batch_id)
                # Snapshot
                cursor.execute("SELECT ContributorID, AliasName FROM ContributorAliases WHERE AliasID = ?", (alias_id,))
                row = cursor.fetchone()
                if not row: return False
                snapshot = {"ContributorID": row[0], "AliasName": row[1]}

                # Audit Credit Nullification
                cursor.execute("SELECT SourceID, RoleID FROM MediaSourceContributorRoles WHERE CreditedAliasID = ?", (alias_id,))
                affected = cursor.fetchall()
                for s_id, r_id in affected:
                    auditor.log_update("MediaSourceContributorRoles", f"{s_id}-{row[0]}-{r_id}", 
                        {"CreditedAliasID": alias_id}, {"CreditedAliasID": None}
                    )

                cursor.execute("UPDATE MediaSourceContributorRoles SET CreditedAliasID = NULL WHERE CreditedAliasID = ?", (alias_id,))
                cursor.execute("DELETE FROM ContributorAliases WHERE AliasID = ?", (alias_id,))
                
                auditor.log_delete("ContributorAliases", alias_id, snapshot)
                return True
        except Exception as e:
            return False

    def _generate_sort_name(self, name: str) -> str:
        """Generate sort-friendly name (e.g., 'The Beatles' -> 'Beatles, The')."""
        for article in ['The ', 'A ', 'An ']:
            if name.startswith(article):
                return f"{name[len(article):]}, {article.strip()}"
        return name


    def add_song_role(self, source_id: int, contributor_id: int, role_name: str, batch_id: Optional[str] = None) -> bool:
        """Instant Link: Link a contributor to a song with a specific role."""
        try:
            from src.core.audit_logger import AuditLogger
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Resolve RoleID
                # Map plural field names to singular roles if needed
                role_map = {
                    'performers': 'Performer',
                    'composers': 'Composer',
                    'lyricists': 'Lyricist',
                    'producers': 'Producer'
                }
                mapped_role = role_map.get(role_name.lower(), role_name)
                
                cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = ?", (mapped_role,))
                role_row = cursor.fetchone()
                if not role_row: return False
                role_id = role_row[0]

                # 2. Link
                cursor.execute("""
                    INSERT OR IGNORE INTO MediaSourceContributorRoles (SourceID, ContributorID, RoleID)
                    VALUES (?, ?, ?)
                """, (source_id, contributor_id, role_id))
                
                if cursor.rowcount > 0:
                    AuditLogger(conn, batch_id=batch_id).log_insert("MediaSourceContributorRoles", f"{source_id}-{contributor_id}-{role_id}", {
                        "SourceID": source_id,
                        "ContributorID": contributor_id,
                        "RoleID": role_id
                    })
                return True
        except Exception as e:
            from src.core import logger
            logger.error(f"Error adding song role: {e}")
            return False

    def remove_song_role(self, source_id: int, contributor_id: int, role_name: str, batch_id: Optional[str] = None) -> bool:
        """Instant Unlink: Remove a contributor role from a song."""
        try:
            from src.core.audit_logger import AuditLogger
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Resolve RoleID
                role_map = {
                    'performers': 'Performer',
                    'composers': 'Composer',
                    'lyricists': 'Lyricist',
                    'producers': 'Producer'
                }
                mapped_role = role_map.get(role_name.lower(), role_name)
                
                cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = ?", (mapped_role,))
                role_row = cursor.fetchone()
                if not role_row: return False
                role_id = role_row[0]

                # 2. Snapshot for Audit
                cursor.execute("""
                    SELECT SourceID, ContributorID, RoleID, CreditedAliasID 
                    FROM MediaSourceContributorRoles 
                    WHERE SourceID = ? AND ContributorID = ? AND RoleID = ?
                """, (source_id, contributor_id, role_id))
                row = cursor.fetchone()
                if not row: return False # Idempotent success
                snapshot = {"SourceID": row[0], "ContributorID": row[1], "RoleID": row[2], "CreditedAliasID": row[3]}

                # 3. Delete
                cursor.execute("""
                    DELETE FROM MediaSourceContributorRoles 
                    WHERE SourceID = ? AND ContributorID = ? AND RoleID = ?
                """, (source_id, contributor_id, role_id))
                
                if cursor.rowcount > 0:
                    AuditLogger(conn, batch_id=batch_id).log_delete("MediaSourceContributorRoles", f"{source_id}-{contributor_id}-{role_id}", snapshot)
                return True
        except Exception as e:
            from src.core import logger
            logger.error(f"Error removing song role: {e}")
            return False
