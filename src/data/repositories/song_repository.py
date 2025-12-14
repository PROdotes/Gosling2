"""Song Repository for database operations"""
import os
from typing import List, Optional, Tuple
from .base_repository import BaseRepository
from ..models.song import Song


class SongRepository(BaseRepository):
    """Repository for Song data access"""

    def insert(self, file_path: str) -> Optional[int]:
        """Insert a new file record"""
        # Normalize path to ensure uniqueness across case/separator differences
        file_path = os.path.normcase(os.path.abspath(file_path))
        file_title = os.path.basename(file_path)
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO Files (Path, Title) VALUES (?, ?)",
                    (file_path, file_title)
                )
                if cursor.rowcount > 0:
                    return cursor.lastrowid
                return None
        except Exception as e:
            print(f"Error inserting file: {e}")
            return None

    def get_all(self) -> Tuple[List[str], List[Tuple]]:
        """Get all songs from the library"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT F.FileID,
                           GROUP_CONCAT(CASE WHEN R.Name = 'Performer' THEN C.Name END, ', ') AS Performers,
                           F.Title AS Title,
                           F.Duration AS Duration,
                           F.Path AS Path,
                           GROUP_CONCAT(CASE WHEN R.Name = 'Composer' THEN C.Name END, ', ') AS Composers,
                           F.TempoBPM AS BPM
                    FROM Files F
                    LEFT JOIN FileContributorRoles FCR ON F.FileID = FCR.FileID
                    LEFT JOIN Contributors C ON FCR.ContributorID = C.ContributorID
                    LEFT JOIN Roles R ON FCR.RoleID = R.RoleID
                    GROUP BY F.FileID, F.Path, F.Title, F.Duration, F.TempoBPM
                    ORDER BY F.FileID DESC
                """
                cursor.execute(query)
                headers = [description[0] for description in cursor.description]
                data = cursor.fetchall()
                return headers, data
        except Exception as e:
            print(f"Error fetching library data: {e}")
            return [], []

    def delete(self, file_id: int) -> bool:
        """Delete a song by its ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Files WHERE FileID = ?", (file_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    def update(self, song: Song) -> bool:
        """Update song metadata"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Update basic file info
                cursor.execute("""
                    UPDATE Files
                    SET Title = ?, Duration = ?, TempoBPM = ?
                    WHERE FileID = ?
                """, (song.title, song.duration, song.bpm, song.file_id))

                # Clear existing contributor roles
                cursor.execute(
                    "DELETE FROM FileContributorRoles WHERE FileID = ?",
                    (song.file_id,)
                )

                # Sync contributor roles
                self._sync_contributor_roles(song, conn)

                return True
        except Exception as e:
            print(f"Error updating song: {e}")
            return False

    def _sync_contributor_roles(self, song: Song, conn) -> None:
        """Sync contributors and their roles"""
        cursor = conn.cursor()
        role_map = {
            'performers': 'Performer',
            'composers': 'Composer',
            'lyricists': 'Lyricist',
            'producers': 'Producer'
        }

        for attr, role_name in role_map.items():
            contributors = getattr(song, attr, [])
            if not contributors:
                continue

            # Get RoleID
            cursor.execute("SELECT RoleID FROM Roles WHERE Name = ?", (role_name,))
            role_row = cursor.fetchone()
            if not role_row:
                continue
            role_id = role_row[0]

            # Process each contributor
            for contributor_name in contributors:
                if not contributor_name.strip():
                    continue

                # Insert or get contributor
                cursor.execute(
                    "INSERT OR IGNORE INTO Contributors (Name, SortName) VALUES (?, ?)",
                    (contributor_name, contributor_name)
                )
                cursor.execute(
                    "SELECT ContributorID FROM Contributors WHERE Name = ?",
                    (contributor_name,)
                )
                contributor_row = cursor.fetchone()
                if not contributor_row:
                    continue
                contributor_id = contributor_row[0]

                # Link file, contributor, and role
                cursor.execute("""
                    INSERT OR IGNORE INTO FileContributorRoles (FileID, ContributorID, RoleID)
                    VALUES (?, ?, ?)
                """, (song.file_id, contributor_id, role_id))

    def get_by_performer(self, performer_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific performer"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT F.FileID,
                           GROUP_CONCAT(CASE WHEN R.Name = 'Performer' THEN C.Name END, ', ') AS Performers,
                           F.Title AS Title,
                           F.Duration AS Duration,
                           F.Path AS Path,
                           GROUP_CONCAT(CASE WHEN R.Name = 'Composer' THEN C.Name END, ', ') AS Composers,
                           F.TempoBPM AS BPM
                    FROM Files F
                    LEFT JOIN FileContributorRoles FCR ON F.FileID = FCR.FileID
                    LEFT JOIN Contributors C ON FCR.ContributorID = C.ContributorID
                    LEFT JOIN Roles R ON FCR.RoleID = R.RoleID
                    WHERE C.Name = ? AND R.Name = 'Performer'
                    GROUP BY F.FileID, F.Path, F.Title, F.Duration, F.TempoBPM
                    ORDER BY F.FileID DESC
                """
                cursor.execute(query, (performer_name,))
                headers = [description[0] for description in cursor.description]
                data = cursor.fetchall()
                return headers, data
        except Exception as e:
            print(f"Error fetching songs by performer: {e}")
            return [], []

    def get_by_composer(self, composer_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific composer"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT F.FileID,
                           GROUP_CONCAT(CASE WHEN R.Name = 'Performer' THEN C.Name END, ', ') AS Performers,
                           F.Title AS Title,
                           F.Duration AS Duration,
                           F.Path AS Path,
                           GROUP_CONCAT(CASE WHEN R.Name = 'Composer' THEN C.Name END, ', ') AS Composers,
                           F.TempoBPM AS BPM
                    FROM Files F
                    LEFT JOIN FileContributorRoles FCR ON F.FileID = FCR.FileID
                    LEFT JOIN Contributors C ON FCR.ContributorID = C.ContributorID
                    LEFT JOIN Roles R ON FCR.RoleID = R.RoleID
                    WHERE C.Name = ? AND R.Name = 'Composer'
                    GROUP BY F.FileID, F.Path, F.Title, F.Duration, F.TempoBPM
                    ORDER BY F.FileID DESC
                """
                cursor.execute(query, (composer_name,))
                headers = [description[0] for description in cursor.description]
                data = cursor.fetchall()
                return headers, data
        except Exception as e:
            print(f"Error fetching songs by composer: {e}")
            return [], []

    def get_by_path(self, path: str) -> Optional[Song]:
        """Get full song object by path"""
        try:
            # Normalize path for lookup
            norm_path = os.path.normcase(os.path.abspath(path))
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Fetch basic info
                cursor.execute("""
                    SELECT FileID, Title, Duration, TempoBPM
                    FROM Files
                    WHERE Path = ?
                """, (norm_path,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                file_id, title, duration, bpm = row
                
                # Fetch contributors
                song = Song(
                    file_id=file_id,
                    path=path,
                    title=title,
                    duration=duration,
                    bpm=bpm
                )
                song.path = norm_path
                
                # Fetch roles
                cursor.execute("""
                    SELECT R.Name, C.Name
                    FROM FileContributorRoles FCR
                    JOIN Roles R ON FCR.RoleID = R.RoleID
                    JOIN Contributors C ON FCR.ContributorID = C.ContributorID
                    WHERE FCR.FileID = ?
                """, (file_id,))
                
                for role_name, contributor_name in cursor.fetchall():
                    if role_name == 'Performer':
                        song.performers.append(contributor_name)
                    elif role_name == 'Composer':
                        song.composers.append(contributor_name)
                    elif role_name == 'Lyricist':
                        song.lyricists.append(contributor_name)
                    elif role_name == 'Producer':
                        song.producers.append(contributor_name)
                
                return song
        except Exception as e:
            print(f"Error getting song by path: {e}")
            return None
