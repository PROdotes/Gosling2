"""Contributor Repository for database operations"""
from typing import List, Tuple
from .base_repository import BaseRepository
from ..models.contributor import Contributor


class ContributorRepository(BaseRepository):
    """Repository for Contributor data access"""

    def get_by_role(self, role_name: str) -> List[Tuple[int, str]]:
        """Get all contributors for a specific role"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT DISTINCT C.ContributorID, C.Name
                    FROM Contributors C
                    JOIN MediaSourceContributorRoles MSCR ON C.ContributorID = MSCR.ContributorID
                    JOIN Roles R ON MSCR.RoleID = R.RoleID
                    WHERE R.Name = ?
                    ORDER BY C.SortName ASC
                """
                cursor.execute(query, (role_name,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching contributors: {e}")
            return []

