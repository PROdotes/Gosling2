"""Song Repository for database operations"""
import os
from typing import List, Optional, Tuple
from .base_repository import BaseRepository
from ..models.song import Song
from ...core import yellberus


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
                
                # 1. Insert into MediaSources
                cursor.execute(
                    """
                    INSERT INTO MediaSources (TypeID, Name, Source, IsActive) 
                    VALUES (1, ?, ?, 1)
                    """,
                    (file_title, file_path)
                )
                source_id = cursor.lastrowid
                
                # 2. Insert into Songs
                cursor.execute(
                    "INSERT INTO Songs (SourceID) VALUES (?)",
                    (source_id,)
                )
                
                return source_id
        except Exception as e:
            print(f"Error inserting song: {e}")
            return None

    def get_all(self) -> Tuple[List[str], List[Tuple]]:
        """Get all songs from the library"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Use Yellberus definitions
                query = f"{yellberus.BASE_QUERY} ORDER BY MS.SourceID DESC"
                
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
                # Deleting from MediaSources cascades to Songs and Roles
                cursor.execute("DELETE FROM MediaSources WHERE SourceID = ?", (file_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting song: {e}")
            return False

    def update(self, song: Song) -> bool:
        """Update song metadata"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Update MediaSources (Base info)
                cursor.execute("""
                    UPDATE MediaSources
                    SET Name = ?, Duration = ?
                    WHERE SourceID = ?
                """, (song.name, song.duration, song.source_id))

                # 2. Update Songs (Extended info)
                # Note: Created helper query to ensure record exists if it was manually messed with
                cursor.execute("""
                    UPDATE Songs
                    SET TempoBPM = ?, RecordingYear = ?, ISRC = ?, IsDone = ?
                    WHERE SourceID = ?
                """, (song.bpm, song.recording_year, song.isrc, 1 if song.is_done else 0, song.source_id))

                # 3. Clear existing contributor roles
                cursor.execute(
                    "DELETE FROM MediaSourceContributorRoles WHERE SourceID = ?",
                    (song.source_id,)
                )

                # 4. Sync new contributor roles
                self._sync_contributor_roles(song, conn)

                return True
        except Exception as e:
            print(f"Error updating song: {e}")
            return False

    def update_status(self, file_id: int, is_done: bool) -> bool:
        """Update just the IsDone status of a song"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE Songs SET IsDone = ? WHERE SourceID = ?",
                    (1 if is_done else 0, file_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating song status: {e}")
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

                # Link source, contributor, and role
                cursor.execute("""
                    INSERT OR IGNORE INTO MediaSourceContributorRoles (SourceID, ContributorID, RoleID)
                    VALUES (?, ?, ?)
                """, (song.source_id, contributor_id, role_id))

    def get_by_performer(self, performer_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific performer"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Filter by Contributor Name where Role is Performer
                query = f"""
                    {yellberus.QUERY_SELECT}
                    {yellberus.QUERY_FROM}
                    WHERE C.Name = ? AND R.Name = 'Performer' AND MS.IsActive = 1
                    {yellberus.QUERY_GROUP_BY}
                    ORDER BY MS.SourceID DESC
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
                # Filter by Contributor Name where Role is Composer
                query = f"""
                    {yellberus.QUERY_SELECT}
                    {yellberus.QUERY_FROM}
                    WHERE C.Name = ? AND R.Name = 'Composer' AND MS.IsActive = 1
                    {yellberus.QUERY_GROUP_BY}
                    ORDER BY MS.SourceID DESC
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
                
                # Fetch basic info from JOIN
                cursor.execute("""
                    SELECT MS.SourceID, MS.Name, MS.Duration, S.TempoBPM, S.RecordingYear, S.ISRC, S.IsDone
                    FROM MediaSources MS
                    JOIN Songs S ON MS.SourceID = S.SourceID
                    WHERE MS.Source = ?
                """, (norm_path,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                source_id, name, duration, bpm, recording_year, isrc, is_done_int = row
                
                # Fetch contributors
                song = Song(
                    source_id=source_id,
                    source=norm_path,
                    name=name,
                    duration=duration,
                    bpm=bpm,
                    recording_year=recording_year,
                    isrc=isrc,
                    is_done=bool(is_done_int)
                )
                
                # Fetch roles
                cursor.execute("""
                    SELECT R.Name, C.Name
                    FROM MediaSourceContributorRoles MSCR
                    JOIN Roles R ON MSCR.RoleID = R.RoleID
                    JOIN Contributors C ON MSCR.ContributorID = C.ContributorID
                    WHERE MSCR.SourceID = ?
                """, (source_id,))
                
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

    def get_all_years(self) -> List[int]:
        """Get list of distinct recording years"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT RecordingYear FROM Songs WHERE RecordingYear IS NOT NULL ORDER BY RecordingYear DESC")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting all years: {e}")
            return []

    def get_by_year(self, year: int) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific recording year"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = f"""
                    {yellberus.QUERY_SELECT}
                    {yellberus.QUERY_FROM}
                    WHERE S.RecordingYear = ? AND MS.IsActive = 1
                    {yellberus.QUERY_GROUP_BY}
                    ORDER BY MS.SourceID DESC
                """
                cursor.execute(query, (year,))
                headers = [description[0] for description in cursor.description]
                data = cursor.fetchall()
                return headers, data
        except Exception as e:
            print(f"Error fetching songs by year: {e}")
            return [], []

    def get_by_status(self, is_done: bool) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by their Done status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = f"""
                    {yellberus.QUERY_SELECT}
                    {yellberus.QUERY_FROM}
                    WHERE S.IsDone = ? AND MS.IsActive = 1
                    {yellberus.QUERY_GROUP_BY}
                    ORDER BY MS.SourceID DESC
                """
                # Convert bool to int (0/1) for SQLite
                status_val = 1 if is_done else 0
                cursor.execute(query, (status_val,))
                headers = [description[0] for description in cursor.description]
                data = cursor.fetchall()
                return headers, data
        except Exception as e:
            print(f"Error fetching songs by status: {e}")
            return [], []
