"""Song Repository for database operations"""
import os
from typing import List, Optional, Tuple
from src.data.database import BaseRepository
from ..models.song import Song
from ...core import yellberus
from .album_repository import AlbumRepository


class SongRepository(BaseRepository):
    """Repository for Song data access"""

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path)
        self.album_repository = AlbumRepository(db_path)
        # Check for orphan columns in DB (runtime yell)
        try:
            with self.get_connection() as conn:
                yellberus.check_db_integrity(conn.cursor())
        except Exception as e:
            # Don't crash startup on integrity check error
            print(f"Non-fatal integrity check error: {e}")

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

                # 1. Update MediaSources (Base info) including Path (Source)
                # Note: Normalize path before saving
                normalized_path = os.path.normcase(os.path.abspath(song.path))
                cursor.execute("""
                    UPDATE MediaSources
                    SET Name = ?, Source = ?, Duration = ?, Notes = ?, IsActive = ?, AudioHash = ?
                    WHERE SourceID = ?
                """, (song.name, normalized_path, song.duration, song.notes, 1 if song.is_active else 0, song.audio_hash, song.source_id))

                # 2. Update Songs (Extended info)
                # Note: Groups is TIT1 (Content Group Description)
                cursor.execute("""
                    UPDATE Songs
                    SET TempoBPM = ?, RecordingYear = ?, ISRC = ?, IsDone = ?, Groups = ?
                    WHERE SourceID = ?
                """, (song.bpm, song.recording_year, song.isrc, 1 if song.is_done else 0, 
                      ", ".join(song.groups) if song.groups else None, song.source_id))

                # 3. Clear existing contributor roles
                cursor.execute(
                    "DELETE FROM MediaSourceContributorRoles WHERE SourceID = ?",
                    (song.source_id,)
                )

                # 4. Sync new contributor roles
                self._sync_contributor_roles(song, conn)

                # 5. Sync Album
                if song.album is not None:
                     self._sync_album(song, conn)

                # 6. Sync Publisher
                if song.publisher is not None:
                     self._sync_publisher(song, conn)

                # 7. Sync Genre (Tags)
                if song.genre is not None:
                     self._sync_genre(song, conn)

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
            cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = ?", (role_name,))
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
                    "INSERT OR IGNORE INTO Contributors (ContributorName, SortName) VALUES (?, ?)",
                    (contributor_name, contributor_name)
                )
                cursor.execute(
                    "SELECT ContributorID FROM Contributors WHERE ContributorName = ?",
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

    def _sync_album(self, song: Song, conn) -> None:
        """Sync album relationship (Find or Create with Artist Disambiguation) - Replacement Logic"""
        cursor = conn.cursor()
        
        # 1. Clear existing links (Fixes the "Append" bug)
        cursor.execute("DELETE FROM SongAlbums WHERE SourceID = ?", (song.source_id,))

        if not song.album or not song.album.strip():
            return

        # 2. Get/Create Album using (Title, AlbumArtist, Year) for disambiguation
        # This prevents the "Greatest Hits Paradox" where Queen and ABBA albums merge.
        
        album_title = song.album.strip()
        album_artist = getattr(song, 'album_artist', None)
        if album_artist:
            album_artist = album_artist.strip() or None
        release_year = getattr(song, 'recording_year', None)
        
        # Build query dynamically based on what's provided
        conditions = ["Title = ? COLLATE NOCASE"]
        params = [album_title]
        
        if album_artist:
            conditions.append("AlbumArtist = ? COLLATE NOCASE")
            params.append(album_artist)
        else:
            conditions.append("(AlbumArtist IS NULL OR AlbumArtist = '')")
        
        if release_year:
            conditions.append("ReleaseYear = ?")
            params.append(release_year)
        
        query = f"SELECT AlbumID FROM Albums WHERE {' AND '.join(conditions)}"
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        if row:
            album_id = row[0]
        else:
            # Create new album with all disambiguation fields
            cursor.execute(
                "INSERT INTO Albums (Title, AlbumArtist, AlbumType, ReleaseYear) VALUES (?, ?, 'Album', ?)", 
                (album_title, album_artist, release_year)
            )
            album_id = cursor.lastrowid
            
        # Link: Since we cleared above, this is the only link.
        cursor.execute("INSERT OR IGNORE INTO SongAlbums (SourceID, AlbumID) VALUES (?, ?)", (song.source_id, album_id))

    def _sync_publisher(self, song: Song, conn) -> None:
        """Sync publisher relationship (Find or Create) - Replacement Logic"""
        # Unlike previous additive logic, we now CLEAR existing publishers for the album
        # and replace them with the new set. This matches user expectation of "Editing".

        cursor = conn.cursor()

        # 1. Identify Target Albums
        # Logic: Publisher links to ALBUM, not Song.
        cursor.execute("SELECT AlbumID FROM SongAlbums WHERE SourceID = ?", (song.source_id,))
        rows = cursor.fetchall()
        album_ids = [r[0] for r in rows]

        if not album_ids:
            # If TPUB present but no Album, create 'Single' album?
            # Or simplified: if no album, we can't link publisher in this schema.
            # But earlier _sync_album should have ensured an album exists if song.album is set.
            # If song.album was None, we might legally skip publisher linking or create a dummy album.
            # Consistent with previous logic: try to create one if publisher exists.
            if song.publisher and song.publisher.strip():
                 single_title = song.name or "Unknown Single"
                 # Check/Create generic album
                 cursor.execute("SELECT AlbumID FROM Albums WHERE Title = ?", (single_title,))
                 alb_row = cursor.fetchone()
                 if alb_row:
                     album_id = alb_row[0]
                 else:
                     cursor.execute("INSERT INTO Albums (Title, AlbumType) VALUES (?, 'Single')", (single_title,))
                     album_id = cursor.lastrowid
                 
                 # Link Song -> Album
                 cursor.execute("INSERT INTO SongAlbums (SourceID, AlbumID) VALUES (?, ?)", (song.source_id, album_id))
                 album_ids = [album_id]
            else:
                return

        # 2. Parse Publishers (Comma separated)
        # If song.publisher is None/Empty, we treated it as "Clear Publishers"
        raw_val = song.publisher or ""
        publisher_names = [p.strip() for p in raw_val.split(',') if p.strip()]

        # 3. Clear Existing Links for these Albums
        # This fixes the "Append" bug.
        placeholders = ",".join(["?"] * len(album_ids))
        cursor.execute(f"DELETE FROM AlbumPublishers WHERE AlbumID IN ({placeholders})", album_ids)

        # 4. Insert New Links
        for pub_name in publisher_names:
            # Find or Create Publisher
            cursor.execute("SELECT PublisherID FROM Publishers WHERE PublisherName = ?", (pub_name,))
            row = cursor.fetchone()
            
            if row:
                publisher_id = row[0]
            else:
                cursor.execute("INSERT INTO Publishers (PublisherName) VALUES (?)", (pub_name,))
                publisher_id = cursor.lastrowid

            # Link to all albums involved (usually just one)
            for alb_id in album_ids:
                cursor.execute("""
                    INSERT OR IGNORE INTO AlbumPublishers (AlbumID, PublisherID)
                    VALUES (?, ?)
                """, (alb_id, publisher_id))

    def _sync_genre(self, song: Song, conn) -> None:
        """Sync genre (Tag) relationship"""
        # Strategy: Valid genre string = Replacement.
        if song.genre is None: 
            return

        cursor = conn.cursor()
        
        # 1. Clear existing GENRE tags for this song (Replacement logic)
        cursor.execute("""
            DELETE FROM MediaSourceTags 
            WHERE SourceID = ? 
            AND TagID IN (SELECT TagID FROM Tags WHERE Category = 'Genre')
        """, (song.source_id,))
        
        # If empty string, we're done (cleared).
        if not song.genre.strip():
            return
            
        # 2. Parse Genres (Comma-separated support)
        genres = [g.strip() for g in song.genre.split(',') if g.strip()]
        
        for g_name in genres:
            # 3. Find or Create Tag (Category='Genre')
            # Fix case sensitivity: COLLATE NOCASE must apply to TagName comparison
            cursor.execute("SELECT TagID FROM Tags WHERE TagName = ? COLLATE NOCASE AND Category='Genre'", (g_name,))
            row = cursor.fetchone()
            
            if row:
                tag_id = row[0]
            else:
                cursor.execute("INSERT INTO Tags (TagName, Category) VALUES (?, 'Genre')", (g_name,))
                tag_id = cursor.lastrowid
            
            # 4. Link
            cursor.execute("INSERT OR IGNORE INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)", (song.source_id, tag_id))

    def get_by_performer(self, performer_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific performer"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Filter by Contributor Name where Role is Performer
                query = f"""
                    {yellberus.QUERY_SELECT}
                    {yellberus.QUERY_FROM}
                    WHERE C.ContributorName = ? AND R.RoleName = 'Performer' AND MS.IsActive = 1
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
                    WHERE C.ContributorName = ? AND R.RoleName = 'Composer' AND MS.IsActive = 1
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

    def get_by_unified_artist(self, artist_name: str) -> Tuple[List[str], List[Tuple]]:
        """Legacy wrapper - resolves to get_by_unified_artists with single name"""
        return self.get_by_unified_artists([artist_name])

    def get_by_unified_artists(self, names: List[str]) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a list of related artists (T-17: Identity Graph)"""
        if not names:
            return [], []
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Create dynamic placeholders for IN clause
                placeholders = ",".join(["?"] * len(names))
                # We need to provide names twice: once for Groups, once for Performers
                params = names + names
                
                query = f"""
                    {yellberus.QUERY_SELECT}
                    {yellberus.QUERY_FROM}
                    WHERE (S.Groups IN ({placeholders}) OR (C.ContributorName IN ({placeholders}) AND R.RoleName = 'Performer')) 
                      AND MS.IsActive = 1
                    {yellberus.QUERY_GROUP_BY}
                    ORDER BY MS.SourceID DESC
                """
                cursor.execute(query, params)
                headers = [description[0] for description in cursor.description]
                data = cursor.fetchall()
                return headers, data
        except Exception as e:
            print(f"Error fetching songs by unified artists: {e}")
            return [], []

    def get_by_id(self, source_id: int) -> Optional[Song]:
        """Get full song object by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                

                # Fetch basic info from JOIN
                cursor.execute("""
                    SELECT
                        MS.SourceID, MS.Name, MS.Source, MS.Duration,
                        S.TempoBPM, S.RecordingYear, S.ISRC, S.IsDone, S.Groups,
                        MS.Notes, MS.IsActive,
                        (
                            SELECT Title FROM Albums A
                            JOIN SongAlbums SA ON A.AlbumID = SA.AlbumID
                            WHERE SA.SourceID = MS.SourceID
                        ) as AlbumTitle,
                        (
                            SELECT GROUP_CONCAT(P.PublisherName, ', ')
                            FROM SongAlbums SA
                            JOIN AlbumPublishers AP ON SA.AlbumID = AP.AlbumID
                            JOIN Publishers P ON AP.PublisherID = P.PublisherID
                            WHERE SA.SourceID = MS.SourceID
                        ) as PublisherName,
                        (
                            SELECT GROUP_CONCAT(TG.TagName, ', ')
                            FROM MediaSourceTags MST
                            JOIN Tags TG ON MST.TagID = TG.TagID
                            WHERE MST.SourceID = MS.SourceID AND TG.Category = 'Genre'
                        ) as Genre
                    FROM MediaSources MS
                    JOIN Songs S ON MS.SourceID = S.SourceID
                    WHERE MS.SourceID = ?
                """, (source_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                source_id, name, path, duration, bpm, recording_year, isrc, is_done_int, groups_str, notes, is_active_int, album_title, publisher_name, genre_str = row

                groups = [g.strip() for g in groups_str.split(',')] if groups_str else []

                # Fetch contributors
                song = Song(
                    source_id=source_id,
                    source=path,
                    name=name,
                    duration=duration,
                    bpm=bpm,
                    recording_year=recording_year,
                    isrc=isrc,
                    is_done=bool(is_done_int),
                    notes=notes,
                    is_active=bool(is_active_int),
                    album=album_title, # AlbumTitle
                    publisher=publisher_name, # PublisherName
                    genre=genre_str, # Genre
                    groups=groups
                )
                cursor.execute("""
                    SELECT R.RoleName, C.ContributorName
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
            print(f"Error getting song by id: {e}")
            return None

    def get_by_path(self, path: str) -> Optional[Song]:
        """Get full song object by path"""
        try:
            # Normalize path for lookup
            norm_path = os.path.normcase(os.path.abspath(path))
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Fetch basic info from JOIN
                cursor.execute("""
                    SELECT 
                        MS.SourceID, MS.Name, MS.Duration, 
                        S.TempoBPM, S.RecordingYear, S.ISRC, S.IsDone, S.Groups,
                        MS.Notes, MS.IsActive,
                        (
                            SELECT Title FROM Albums A 
                            JOIN SongAlbums SA ON A.AlbumID = SA.AlbumID 
                            WHERE SA.SourceID = MS.SourceID
                        ) as AlbumTitle,
                        (
                            SELECT GROUP_CONCAT(P.PublisherName, ', ')
                            FROM SongAlbums SA 
                            JOIN AlbumPublishers AP ON SA.AlbumID = AP.AlbumID
                            JOIN Publishers P ON AP.PublisherID = P.PublisherID
                            WHERE SA.SourceID = MS.SourceID
                        ) as PublisherName,
                        (
                            SELECT GROUP_CONCAT(TG.TagName, ', ')
                            FROM MediaSourceTags MST
                            JOIN Tags TG ON MST.TagID = TG.TagID
                            WHERE MST.SourceID = MS.SourceID AND TG.Category = 'Genre'
                        ) as Genre
                    FROM MediaSources MS
                    JOIN Songs S ON MS.SourceID = S.SourceID
                    WHERE MS.Source = ?
                """, (norm_path,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                source_id, name, duration, bpm, recording_year, isrc, is_done_int, groups_str, notes, is_active_int, album_title, publisher_name, genre_str = row
                
                groups = [g.strip() for g in groups_str.split(',')] if groups_str else []

                # Fetch contributors
                song = Song(
                    source_id=source_id,
                    source=norm_path,
                    name=name,
                    duration=duration,
                    bpm=bpm,
                    recording_year=recording_year,
                    isrc=isrc,
                    is_done=bool(is_done_int),
                    notes=notes,
                    is_active=bool(is_active_int),
                    album=album_title, # AlbumTitle
                    publisher=publisher_name, # PublisherName
                    genre=genre_str, # Genre
                    groups=groups
                )
                
                # Fetch roles
                cursor.execute("""
                    SELECT R.RoleName, C.ContributorName
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

    # get_all_groups removed (Legacy zombie logic)

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

    def get_by_isrc(self, isrc: str) -> Optional[Song]:
        """Get song by ISRC code (for duplicate detection)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT SourceID FROM Songs WHERE ISRC = ?",
                    (isrc,)
                )
                row = cursor.fetchone()
                if row:
                    return self.get_by_id(row[0])
                return None
        except Exception as e:
            print(f"Error getting song by ISRC: {e}")
            return None
    
    def get_by_audio_hash(self, audio_hash: str) -> Optional[Song]:
        """Get song by audio hash (for duplicate detection)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT SourceID FROM MediaSources WHERE AudioHash = ?",
                    (audio_hash,)
                )
                row = cursor.fetchone()
                if row:
                    return self.get_by_id(row[0])
                return None
        except Exception as e:
            print(f"Error getting song by audio hash: {e}")
            return None
            