"""Contributor Repository for database operations"""
from typing import List, Tuple
from src.data.database import BaseRepository
from ..models.contributor import Contributor


class ContributorRepository(BaseRepository):
    """Repository for Contributor data access"""

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

    def resolve_identity_graph(self, search_term: str) -> List[str]:
        """
        Resolve a search term to a complete list of related artist identities.
        Strategy:
        1. Find ContributorIDs matching name (Direct) or Alias (via ContributorAliases).
        2. Expand to find Groups these contributors belong to (if Person).
        3. Collect ALL display names and aliases for the resolved set of IDs.
        """
        identities = set()
        
        # Normalize term for broader matching logic (e.g. case insensitive)
        term = search_term.strip()
        if not term:
            return []

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Find Seed IDs (Direct Match or Alias Match)
                cursor.execute("""
                    SELECT C.ContributorID, C.Type 
                    FROM Contributors C
                    WHERE C.ContributorName = ? 
                    UNION
                    SELECT CA.ContributorID, C.Type
                    FROM ContributorAliases CA
                    JOIN Contributors C ON CA.ContributorID = C.ContributorID
                    WHERE CA.AliasName = ?
                """, (term, term))
                
                seeds = cursor.fetchall()
                final_ids = set()
                pending_ids = set()
                
                for seed_id, seed_type in seeds:
                    final_ids.add(seed_id)
                    
                    # 2. Expand: ONLY Person -> Group
                    # We strictly avoid Group -> Member to prevent pulling in unrelated bands via shared members.
                    
                    # Resolve type if unknown (from Alias match)
                    if seed_type == 'unknown' or seed_type is None:
                        cursor.execute("SELECT Type FROM Contributors WHERE ContributorID = ?", (seed_id,))
                        row = cursor.fetchone()
                        if row: 
                            seed_type = row[0]
                    
                    # If it's a person, find their groups
                    if seed_type == 'person': 
                        cursor.execute("SELECT GroupID FROM GroupMembers WHERE MemberID = ?", (seed_id,))
                        groups = cursor.fetchall()
                        for g in groups:
                            final_ids.add(g[0])
                            
                if not final_ids:
                    return [term]

                # 3. Collect ALL Names for these IDs
                placeholders = ','.join('?' for _ in final_ids)
                params = list(final_ids)
                
                # Get Main Names
                cursor.execute(f"SELECT ContributorName FROM Contributors WHERE ContributorID IN ({placeholders})", params)
                for row in cursor.fetchall():
                    identities.add(row[0])
                    
                # Get Aliases (if table exists - we know it does now)
                cursor.execute(f"SELECT AliasName FROM ContributorAliases WHERE ContributorID IN ({placeholders})", params)
                for row in cursor.fetchall():
                    identities.add(row[0])

        except Exception as e:
            from src.core import logger
            logger.error(f"Error resolving identity graph: {e}")
            return [term] # Fallback

        return list(identities)

