"""Contributor Repository for database operations"""
from typing import List, Tuple, Optional
from src.data.database import BaseRepository
from ..models.contributor import Contributor


class ContributorRepository(BaseRepository):
    """Repository for Contributor data access"""

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
                cursor.execute("SELECT ContributorID FROM Contributors WHERE ContributorName = ? COLLATE NOCASE", (name,))
                row = cursor.fetchone()
                if row:
                    return self.get_by_id(row[0], conn=conn)
                
                # try alias match (case-insensitive)
                cursor.execute("SELECT ContributorID FROM ContributorAliases WHERE AliasName = ? COLLATE NOCASE", (name,))
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

    def get_by_role(self, role_name: str) -> List[Tuple[int, str]]:
        """Get all contributors for a specific role"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT DISTINCT C.ContributorID, C.ContributorName
                    FROM Contributors C
                    JOIN MediaSourceContributorRoles MSCR ON C.ContributorID = MSCR.ContributorID
                    JOIN Roles R ON MSCR.RoleID = R.RoleID
                    WHERE R.RoleName = ?
                    ORDER BY C.SortName ASC
                """
                cursor.execute(query, (role_name,))
                return cursor.fetchall()
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching contributors: {e}")
            return []

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

    def create(self, name: str, type: str = 'person', sort_name: str = None, conn=None) -> Contributor:
        """Create new contributor. Auto-generates sort_name if not provided. (Connection Aware)"""
        if not sort_name:
            sort_name = self._generate_sort_name(name)
        
        if conn:
            return self._create_logic(name, type, sort_name, conn)

        try:
            with self.get_connection() as conn:
                return self._create_logic(name, type, sort_name, conn)
        except Exception as e:
            from src.core import logger
            logger.error(f"Error creating contributor: {e}")
            raise

    def _create_logic(self, name: str, type: str, sort_name: str, conn) -> Contributor:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Contributors (ContributorName, SortName, ContributorType) VALUES (?, ?, ?)",
            (name, sort_name, type)
        )
        new_id = cursor.lastrowid
        return Contributor(contributor_id=new_id, name=name, sort_name=sort_name, type=type)

    def update(self, contributor: Contributor) -> bool:
        """Update name, sort_name, type. (Automatically severs invalid membership links on type change)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get existing type to check for change
                cursor.execute("SELECT ContributorType FROM Contributors WHERE ContributorID = ?", (contributor.contributor_id,))
                row = cursor.fetchone()
                old_type = row[0] if row else None
                
                # 1. Update Core Identity
                cursor.execute(
                    "UPDATE Contributors SET ContributorName = ?, SortName = ?, ContributorType = ? WHERE ContributorID = ?",
                    (contributor.name, contributor.sort_name, contributor.type, contributor.contributor_id)
                )
                success = cursor.rowcount > 0
                
                # 2. Cleanup relationships if type changed
                if old_type and old_type != contributor.type:
                    if contributor.type == "person":
                        # Was a Group, now a Person: Can't have members anymore.
                        cursor.execute("DELETE FROM GroupMembers WHERE GroupID = ?", (contributor.contributor_id,))
                    else:
                        # Was a Person, now a Group: Can't belong to other groups anymore.
                        cursor.execute("DELETE FROM GroupMembers WHERE MemberID = ?", (contributor.contributor_id,))
                
                return success
        except Exception as e:
            from src.core import logger
            logger.error(f"Error updating contributor: {e}")
            return False

    def delete(self, contributor_id: int) -> bool:
        """Delete contributor and cascade to aliases, memberships, roles."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Contributors WHERE ContributorID = ?", (contributor_id,))
                return cursor.rowcount > 0
        except Exception as e:
            from src.core import logger
            logger.error(f"Error deleting contributor: {e}")
            return False

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
                # For safety, we process in chunks or use a temp table, but for now assuming < 500 active artists in filter.
                # If list is huge, we might just query ALL contributors/types and map in memory.
                
                cursor.execute("SELECT ContributorName, ContributorType FROM Contributors")
                rows = cursor.fetchall()
                # Build map (Memory intensive if 100k artists? No, string keys are fine for < 10k)
                
                # Case insensitive lookup map
                name_map = {r[0].lower(): r[1] for r in rows}
                
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

    def get_or_create(self, name: str, type: str = 'person', conn=None) -> Tuple[Contributor, bool]:
        """
        Get existing or create new. 
        Returns (contributor, was_created). (Connection Aware)
        """
        if conn:
            return self._get_or_create_logic(name, type, conn)

        try:
            with self.get_connection() as conn:
                return self._get_or_create_logic(name, type, conn)
        except Exception as e:
            from src.core import logger
            logger.error(f"Error in get_or_create: {e}")
            # Fallback to creating a disconnected object if everything fails? 
            # Better to let it bubble or return a dummy.
            raise

    def _get_or_create_logic(self, name: str, type: str, conn) -> Tuple[Contributor, bool]:
        cursor = conn.cursor()
        # 1. Check direct name match
        cursor.execute("SELECT ContributorID FROM Contributors WHERE ContributorName = ?", (name,))
        row = cursor.fetchone()
        if row:
            return self.get_by_id(row[0], conn=conn), False
        
        # 2. Check alias match
        cursor.execute("SELECT ContributorID FROM ContributorAliases WHERE AliasName = ?", (name,))
        row = cursor.fetchone()
        if row:
            return self.get_by_id(row[0], conn=conn), False
        
        # 3. Create if not found
        return self.create(name, type, conn=conn), True

    def validate_identity(self, name: str, exclude_id: int = None) -> Tuple[Optional[int], str]:
        """
        Check if name exists as Primary or Alias. 
        Returns (conflict_id_or_none, message).
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check Name Conflict
                query = "SELECT ContributorID, ContributorName FROM Contributors WHERE ContributorName = ?"
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
                    WHERE CA.AliasName = ?
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

    def merge(self, source_id: int, target_id: int) -> bool:
        """
        Consolidate source identity into target.
        Transfers all songs, aliases, and relationships.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Get Source Primary Name
                cursor.execute("SELECT ContributorName FROM Contributors WHERE ContributorID = ?", (source_id,))
                s_name = cursor.fetchone()[0]
                
                # 2. Source Name becomes an alias for target
                cursor.execute("INSERT OR IGNORE INTO ContributorAliases (ContributorID, AliasName) VALUES (?, ?)", (target_id, s_name))
                
                # Retrieve the AliasID for this name (newly created or existing) to preserve credit
                cursor.execute("SELECT AliasID FROM ContributorAliases WHERE ContributorID = ? AND AliasName = ?", (target_id, s_name))
                row = cursor.fetchone()
                source_name_alias_id = row[0] if row else None
                
                # 3. Transfer existing Aliases
                cursor.execute("UPDATE OR IGNORE ContributorAliases SET ContributorID = ? WHERE ContributorID = ?", (target_id, source_id))
                
                # 4. Transfer Song Roles (MediaSourceContributorRoles)
                # Deduplicate before updating to avoid primary key violations
                cursor.execute("""
                    DELETE FROM MediaSourceContributorRoles 
                    WHERE ContributorID = ? AND (SourceID, RoleID) IN (
                        SELECT SourceID, RoleID FROM MediaSourceContributorRoles WHERE ContributorID = ?
                    )
                """, (source_id, target_id))
                
                # Update links: Point to TargetID, and record the Source Name as the Credited Alias (if none was set)
                # This ensures that songs previously credited to "Pink" (Primary) are now credited to "P!nk" (Master) as "Pink" (Alias)
                if source_name_alias_id:
                     cursor.execute("""
                        UPDATE MediaSourceContributorRoles 
                        SET ContributorID = ?, 
                            CreditedAliasID = COALESCE(CreditedAliasID, ?)
                        WHERE ContributorID = ?
                     """, (target_id, source_name_alias_id, source_id))
                else:
                     cursor.execute("UPDATE MediaSourceContributorRoles SET ContributorID = ? WHERE ContributorID = ?", (target_id, source_id))
                
                # 5. Transfer Group Memberships
                # Cleanup duplicates where source and target were already in the same relationship
                cursor.execute("""
                    DELETE FROM GroupMembers 
                    WHERE MemberID = ? AND GroupID IN (
                        SELECT GroupID FROM GroupMembers WHERE MemberID = ?
                    )
                """, (source_id, target_id))
                cursor.execute("UPDATE GroupMembers SET MemberID = ? WHERE MemberID = ?", (target_id, source_id))
                
                cursor.execute("""
                    DELETE FROM GroupMembers 
                    WHERE GroupID = ? AND MemberID IN (
                        SELECT MemberID FROM GroupMembers WHERE GroupID = ?
                    )
                """, (source_id, target_id))
                cursor.execute("UPDATE GroupMembers SET GroupID = ? WHERE GroupID = ?", (target_id, source_id))
                
                # SAFETY: Remove any resulting self-references (e.g. if A was member of B, now B is member of B)
                # This handles circular merges (Parent A merging into Child B)
                cursor.execute("DELETE FROM GroupMembers WHERE GroupID = MemberID")
                
                # 6. Delete Source
                cursor.execute("DELETE FROM Contributors WHERE ContributorID = ?", (source_id,))
                
                return True
        except Exception as e:
            from src.core import logger
            logger.error(f"CRITICAL: Failed to merge artist identities {source_id} -> {target_id}: {e}")
            return False

    def get_member_count(self, contributor_id: int) -> int:
        """Return count of associated group memberships (as Group or as Member)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT (SELECT COUNT(*) FROM GroupMembers WHERE GroupID = ?) +
                           (SELECT COUNT(*) FROM GroupMembers WHERE MemberID = ?)
                """, (contributor_id, contributor_id))
                return cursor.fetchone()[0]
        except Exception as e:
            return 0

    def get_members(self, group_id: int) -> List[Contributor]:
        """Get all members of a Group."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT C.ContributorID, C.ContributorName, C.SortName, C.ContributorType
                    FROM Contributors C
                    JOIN GroupMembers GM ON C.ContributorID = GM.MemberID
                    WHERE GM.GroupID = ?
                    ORDER BY C.SortName ASC
                """, (group_id,))
                return [Contributor(contributor_id=r[0], name=r[1], sort_name=r[2], type=r[3]) for r in cursor.fetchall()]
        except Exception as e:
            return []

    def get_groups(self, person_id: int) -> List[Contributor]:
        """Get all Groups a Person belongs to."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT C.ContributorID, C.ContributorName, C.SortName, C.ContributorType
                    FROM Contributors C
                    JOIN GroupMembers GM ON C.ContributorID = GM.GroupID
                    WHERE GM.MemberID = ?
                    ORDER BY C.SortName ASC
                """, (person_id,))
                return [Contributor(contributor_id=r[0], name=r[1], sort_name=r[2], type=r[3]) for r in cursor.fetchall()]
        except Exception as e:
            return []

    def add_member(self, group_id: int, person_id: int) -> bool:
        """Add a member to a group."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO GroupMembers (GroupID, MemberID) VALUES (?, ?)", (group_id, person_id))
                return cursor.rowcount > 0
        except Exception as e:
            return False

    def remove_member(self, group_id: int, person_id: int) -> bool:
        """Remove a member from a group."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM GroupMembers WHERE GroupID = ? AND MemberID = ?", (group_id, person_id))
                return cursor.rowcount > 0
        except Exception as e:
            return False

    def get_aliases(self, contributor_id: int) -> List[Tuple[int, str]]:
        """Get all aliases for a contributor (ID and Name)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT AliasID, AliasName FROM ContributorAliases WHERE ContributorID = ?", (contributor_id,))
                return cursor.fetchall()
        except Exception as e:
            return []

    def add_alias(self, contributor_id: int, alias_name: str) -> int:
        """Add an alias."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO ContributorAliases (ContributorID, AliasName) VALUES (?, ?)", (contributor_id, alias_name))
                return cursor.lastrowid
        except Exception as e:
            return -1

    def update_alias(self, alias_id: int, new_name: str) -> bool:
        """Rename an alias."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE ContributorAliases SET AliasName = ? WHERE AliasID = ?", (new_name, alias_id))
                return cursor.rowcount > 0
        except Exception as e:
            return False

    def promote_alias(self, contributor_id: int, alias_id: int) -> bool:
        """
        Swap the current primary name with an alias.
        The current primary name becomes a new alias.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Get current primary name
                cursor.execute("SELECT ContributorName FROM Contributors WHERE ContributorID = ?", (contributor_id,))
                old_primary = cursor.fetchone()[0]
                
                # 2. Get the target alias name
                cursor.execute("SELECT AliasName FROM ContributorAliases WHERE AliasID = ?", (alias_id,))
                new_primary = cursor.fetchone()[0]
                
                # 3. Swap in Contributors table
                cursor.execute("UPDATE Contributors SET ContributorName = ? WHERE ContributorID = ?", (new_primary, contributor_id))
                
                # 4. Update the alias record to hold the old primary name
                cursor.execute("UPDATE ContributorAliases SET AliasName = ? WHERE AliasID = ?", (old_primary, alias_id))
                
                # 5. STABLE SWAP of Credits
                # Songs that pointed to Primary (NULL) should now point to Alias (Old Primary Name).
                # Songs that pointed to Alias should now point to Primary (New Primary Name).
                cursor.execute("""
                    UPDATE MediaSourceContributorRoles
                    SET CreditedAliasID = CASE
                        WHEN CreditedAliasID IS NULL THEN ?
                        WHEN CreditedAliasID = ? THEN NULL
                    END
                    WHERE ContributorID = ? 
                      AND (CreditedAliasID IS NULL OR CreditedAliasID = ?)
                """, (alias_id, alias_id, contributor_id, alias_id))
                
                return True
        except Exception as e:
            from src.core import logger
            logger.error(f"Error promoting alias {alias_id}: {e}")
            return False

    def delete_alias(self, alias_id: int) -> bool:
        """Delete an alias. Nullifies any specific credit references first."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 1. Nullify usage in credits (Reverts display to Primary Name)
                cursor.execute("UPDATE MediaSourceContributorRoles SET CreditedAliasID = NULL WHERE CreditedAliasID = ?", (alias_id,))
                # 2. Delete
                cursor.execute("DELETE FROM ContributorAliases WHERE AliasID = ?", (alias_id,))
                return cursor.rowcount > 0
        except Exception as e:
            return False

    def _generate_sort_name(self, name: str) -> str:
        """Generate sort-friendly name (e.g., 'The Beatles' -> 'Beatles, The')."""
        for article in ['The ', 'A ', 'An ']:
            if name.startswith(article):
                return f"{name[len(article):]}, {article.strip()}"
        return name

    def resolve_identity_graph(self, search_term: str) -> List[str]:
        """
        Resolve a search term to a complete list of related artist identities.
         Strategy:
         1. Find ContributorIDs matching name (Direct) or Alias (via ContributorAliases).
         2. Expand to find Groups these contributors belong to (if Person).
         3. Collect ALL display names and aliases for the resolved set of IDs.
        """
        identities = set()
        term = search_term.strip()
        if not term: return []

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Find Seed IDs
                cursor.execute("""
                    SELECT C.ContributorID, C.ContributorType 
                    FROM Contributors C
                    WHERE C.ContributorName = ? 
                    UNION
                    SELECT CA.ContributorID, C.ContributorType
                    FROM ContributorAliases CA
                    JOIN Contributors C ON CA.ContributorID = C.ContributorID
                    WHERE CA.AliasName = ?
                """, (term, term))
                
                seeds = cursor.fetchall()
                final_ids = set()
                
                for seed_id, seed_type in seeds:
                    final_ids.add(seed_id)
                    
                    if seed_type == 'person': 
                        cursor.execute("SELECT GroupID FROM GroupMembers WHERE MemberID = ?", (seed_id,))
                        for g in cursor.fetchall():
                            final_ids.add(g[0])
                            
                if not final_ids: return [term]

                # 3. Collect ALL Names
                placeholders = ','.join('?' for _ in final_ids)
                params = list(final_ids)
                
                cursor.execute(f"SELECT ContributorName FROM Contributors WHERE ContributorID IN ({placeholders})", params)
                for row in cursor.fetchall(): identities.add(row[0])
                    
                cursor.execute(f"SELECT AliasName FROM ContributorAliases WHERE ContributorID IN ({placeholders})", params)
                for row in cursor.fetchall(): identities.add(row[0])

        except Exception as e:
            from src.core import logger
            logger.error(f"Error resolving identity graph: {e}")
            return [term]

        return list(identities)
