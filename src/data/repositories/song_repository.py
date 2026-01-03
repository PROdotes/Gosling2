"""Song Repository for database operations"""
import os
from typing import List, Optional, Tuple
from src.data.database import BaseRepository
from ..models.song import Song
from ...core import yellberus, logger
from .album_repository import AlbumRepository


class SongRepository(BaseRepository):
    """Repository for Song data access"""

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path)
        self.album_repository = AlbumRepository(db_path)
        from .contributor_repository import ContributorRepository
        self.contributor_repository = ContributorRepository(db_path)
        # Check for orphan columns in DB (runtime yell)
        try:
            with self.get_connection() as conn:
                yellberus.check_db_integrity(conn.cursor())
        except Exception as e:
            # Don't crash startup on integrity check error
            logger.error(f"Non-fatal integrity check error: {e}")

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
                    INSERT INTO MediaSources (TypeID, MediaName, SourcePath, IsActive) 
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
            logger.error(f"Error inserting song: {e}")
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
            logger.error(f"Error fetching library data: {e}")
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
            logger.error(f"Error deleting song: {e}")
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
                    SET MediaName = ?, SourcePath = ?, SourceDuration = ?, SourceNotes = ?, IsActive = ?, AudioHash = ?
                    WHERE SourceID = ?
                """, (song.name, normalized_path, song.duration, song.notes, 1 if song.is_active else 0, song.audio_hash, song.source_id))

                # 2. Update Songs (Extended info)
                # Note: Groups is TIT1 (Content Group Description)
                cursor.execute("""
                    UPDATE Songs
                    SET TempoBPM = ?, RecordingYear = ?, ISRC = ?, SongGroups = ?
                    WHERE SourceID = ?
                """, (song.bpm, song.recording_year, song.isrc, 
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

                # 7. Sync Tags (Genre & Mood)
                if song.genre is not None:
                     self._sync_tags(song, conn, 'genre', 'Genre')
                if song.mood is not None:
                     self._sync_tags(song, conn, 'mood', 'Mood')

                # Status is now managed by TagRepository directly, not here.

                return True
        except Exception as e:
            logger.error(f"Error updating song: {e}")
            return False

    def update_status(self, file_id: int, is_done: bool) -> bool:
        """Update the status of a song (Tag-Driven, Flag-Synced)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Sync Tag (The New Truth)
                if not is_done:
                    # Add 'Unprocessed' status tag
                    cursor.execute("SELECT TagID FROM Tags WHERE TagCategory = 'Status' AND TagName = 'Unprocessed'")
                    row = cursor.fetchone()
                    if not row:
                        cursor.execute("INSERT INTO Tags (TagCategory, TagName) VALUES ('Status', 'Unprocessed')")
                        tag_id = cursor.lastrowid
                    else:
                        tag_id = row[0]
                    cursor.execute("INSERT OR IGNORE INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)", (file_id, tag_id))
                else:
                    # Remove 'Unprocessed' status tag
                    cursor.execute("""
                        DELETE FROM MediaSourceTags 
                        WHERE SourceID = ? AND TagID IN (
                            SELECT TagID FROM Tags WHERE TagCategory = 'Status' AND TagName = 'Unprocessed'
                        )
                    """, (file_id,))

                # 2. Sync LEGACY (Skip - DB cleanup in progress)
                # (The column likely still exists but we don't write to it)
                return True
        except Exception as e:
            logger.error(f"Error updating song status: {e}")
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

                # T-70: Use ContributorRepository for identity-aware syncing
                artist, created = self.contributor_repository.get_or_create(contributor_name, conn=conn)
                contributor_id = artist.contributor_id
                
                # Check if the name we used ("Pink") is actually the matched alias (or if we can find it)
                credited_alias_id = None
                if artist.matched_alias and artist.matched_alias.lower() == contributor_name.lower():
                     # If the repository search/lookup already told us this is an alias match
                     # Wait, get_or_create doesn't return matched_alias in the object usually?
                     # We need to look it up to be sure.
                     pass
                else:
                     # Check if 'contributor_name' is an alias for this artist
                     # (Don't do this if name matches primary name)
                     if contributor_name.lower() != artist.name.lower():
                         cursor.execute("SELECT AliasID FROM ContributorAliases WHERE ContributorID = ? AND AliasName = ?", (contributor_id, contributor_name))
                         alias_row = cursor.fetchone()
                         if alias_row:
                             credited_alias_id = alias_row[0]

                # Link source, contributor, and role (with Credit Preservation)
                cursor.execute("""
                    INSERT OR IGNORE INTO MediaSourceContributorRoles (SourceID, ContributorID, RoleID, CreditedAliasID)
                    VALUES (?, ?, ?, ?)
                """, (song.source_id, contributor_id, role_id, credited_alias_id))

    def _sync_album(self, song: Song, conn) -> None:
        """
        Sync album relationship (Find or Create with Artist Disambiguation).
        Non-Destructive Update: Existing links are kept; new target becomes Primary.
        """
        cursor = conn.cursor()
        
        # Normalize Album Title (Handle List from UI)
        effective_title = None
        if isinstance(song.album, list):
            effective_title = str(song.album[0]).strip() if song.album else None
        elif song.album:
             effective_title = str(song.album).strip()

        # Determine the Target Album ID
        target_album_id = None
        
        # 1. Use Precise ID if trustworthy (and no text override)
        # CRITICAL: If song.album is provided, it might mean the user edited the text!
        use_precise_id = False
        if getattr(song, 'album_id', None) is not None:
             if not effective_title:
                 use_precise_id = True
             else:
                 # Check if name matches existing ID to see if it's stale
                 cursor.execute("SELECT AlbumTitle FROM Albums WHERE AlbumID = ?", (song.album_id,))
                 id_row = cursor.fetchone()
                 
                 if id_row and id_row[0].lower() == effective_title.lower():
                     use_precise_id = True

        if use_precise_id:
             target_album_id = song.album_id

        elif effective_title:
            # 2. Get/Create Album using (Title, AlbumArtist, Year) for disambiguation
            album_title = effective_title
            album_artist = getattr(song, 'album_artist', None)
            if album_artist:
                album_artist = album_artist.strip() or None
            release_year = getattr(song, 'recording_year', None)
            
            # Build query dynamically based on what's provided
            conditions = ["AlbumTitle = ? COLLATE NOCASE"]
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
                target_album_id = row[0]
            else:
                # Create new album
                cursor.execute(
                    "INSERT INTO Albums (AlbumTitle, AlbumArtist, AlbumType, ReleaseYear) VALUES (?, ?, 'Album', ?)", 
                    (album_title, album_artist, release_year)
                )
                target_album_id = cursor.lastrowid

        # 3. Apply Link logic (Primary Switch)
        if target_album_id:
            # Check if link exists
            cursor.execute("SELECT IsPrimary FROM SongAlbums WHERE SourceID = ? AND AlbumID = ?", (song.source_id, target_album_id))
            link_row = cursor.fetchone()
            
            if link_row:
                # Link exists. Is it already primary?
                if not link_row[0]:
                    # Demote others
                    cursor.execute("UPDATE SongAlbums SET IsPrimary = 0 WHERE SourceID = ?", (song.source_id,))
                    # Promote this one
                    cursor.execute("UPDATE SongAlbums SET IsPrimary = 1 WHERE SourceID = ? AND AlbumID = ?", (song.source_id, target_album_id))
            else:
                # New Link
                # Demote others
                cursor.execute("UPDATE SongAlbums SET IsPrimary = 0 WHERE SourceID = ?", (song.source_id,))
                # Insert as Primary
                cursor.execute("INSERT INTO SongAlbums (SourceID, AlbumID, IsPrimary) VALUES (?, ?, 1)", (song.source_id, target_album_id))
        
        # Note: If no target_album derived (user cleared album), we do ??
        # In a non-destructive world, maybe we just don't add a new primary?
        # Or do we clear the Primary flag from existing?
        # Legacy behavior was "Unlink". 
        # If song.album is explicitly empty string, maybe we should unlink primary?
        if effective_title is not None and not effective_title.strip() and not use_precise_id:
             # User cleared the field. Unset Primary on everything?
             # Or leave it? "Clear Album" usually means "Remove from Album".
             # Let's unlink the current Primary.
             cursor.execute("DELETE FROM SongAlbums WHERE SourceID = ? AND IsPrimary = 1", (song.source_id,))


    def _sync_publisher(self, song: Song, conn) -> None:
        """
        Sync publisher relationship (Find or Create).
        Policy: Side Panel edits are "Track Overrides" (Level 1).
        Schema Constraint: Level 1 (TrackPublisherID) is 1:1. Level 3 (RecordingPublishers) is M:M.
        Strategy:
        1. Write ALL publishers to RecordingPublishers (Level 3) for archival.
        2. Write PRIMARY publisher to TrackPublisherID (Level 1) to force override of Album Label.
        3. If "Single Paradox" (No Album), create/link Album and set AlbumPublishers (Level 2).
        """
        cursor = conn.cursor()

        # 1. Parse Publishers
        if isinstance(song.publisher, list):
            publisher_names = [str(p).strip() for p in song.publisher if p]
        else:
            raw_val = song.publisher or ""
            publisher_names = [p.strip() for p in raw_val.split(',') if p.strip()]

        # Resolve Publisher IDs
        publisher_ids = []
        for pub_name in publisher_names:
            cursor.execute("SELECT PublisherID FROM Publishers WHERE PublisherName = ?", (pub_name,))
            row = cursor.fetchone()
            if row:
                pid = row[0]
            else:
                cursor.execute("INSERT INTO Publishers (PublisherName) VALUES (?)", (pub_name,))
                pid = cursor.lastrowid
            publisher_ids.append(pid)

        # 2. Update RecordingPublishers (Level 3 - M:M Archival)
        cursor.execute("DELETE FROM RecordingPublishers WHERE SourceID = ?", (song.source_id,))
        for pid in publisher_ids:
            cursor.execute("INSERT OR IGNORE INTO RecordingPublishers (SourceID, PublisherID) VALUES (?, ?)", (song.source_id, pid))

        # 3. Handle Album Links & Overrides
        cursor.execute("SELECT AlbumID, IsPrimary FROM SongAlbums WHERE SourceID = ?", (song.source_id,))
        rows = cursor.fetchall()
        
        album_ids = [r[0] for r in rows]
        
        if not album_ids:
            # --- SINGLE PARADOX (DEPRECATED) ---
            # We used to auto-create "Single" albums here to house the publisher.
            # But now we support RecordingPublishers (Level 3) which links to SourceID directly.
            # So we don't need to force an album.
            # If the user cleared the album, let it be cleared.
            pass
        else:
            # --- TRACK OVERRIDE ---

            # --- TRACK OVERRIDE ---
            # Song is on an Album. We DO NOT touch AlbumPublishers (Level 2).
            # We set Level 1 (TrackPublisherID) to override Level 2 for this song only.
            # Limitation: TrackPublisherID is single-value. usage of [0].
            primary_pid = publisher_ids[0] if publisher_ids else None
            
            # Update all links for this song (or just Primary? Let's do all to be safe overrides)
            cursor.execute("UPDATE SongAlbums SET TrackPublisherID = ? WHERE SourceID = ?", (primary_pid, song.source_id))

    def _sync_tags(self, song: Song, conn, field_name: str, category: str) -> None:
        """Dynamic Tag Sync (Generic for Genre, Mood, etc.)"""
        cursor = conn.cursor()
        val = getattr(song, field_name)
        if val is None: return

        # 1. Clear existing links for this category
        cursor.execute("""
            DELETE FROM MediaSourceTags 
            WHERE SourceID = ? 
            AND TagID IN (SELECT TagID FROM Tags WHERE TagCategory = ?)
        """, (song.source_id, category))
        
        # 2. Add new links
        tags = []
        if isinstance(val, list):
            tags = val
        elif isinstance(val, str):
            tags = [t.strip() for t in val.split(',') if t.strip()]
            
        for tag_name in tags:
            # Find or create tag
            cursor.execute("SELECT TagID FROM Tags WHERE TagCategory = ? AND TagName = ?", (category, tag_name))
            row = cursor.fetchone()
            if row:
                tag_id = row[0]
            else:
                cursor.execute("INSERT INTO Tags (TagCategory, TagName) VALUES (?, ?)", (category, tag_name))
                tag_id = cursor.lastrowid
            
            cursor.execute("INSERT OR IGNORE INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)", (song.source_id, tag_id))

    # _sync_status_tag removed: Status is now managed by TagRepository.is_unprocessed/set_unprocessed

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
            logger.error(f"Error fetching songs by performer: {e}")
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
            logger.error(f"Error fetching songs by composer: {e}")
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
                    WHERE (S.SongGroups IN ({placeholders}) OR (C.ContributorName IN ({placeholders}) AND R.RoleName = 'Performer')) 
                      AND MS.IsActive = 1
                    {yellberus.QUERY_GROUP_BY}
                    ORDER BY MS.SourceID DESC
                """
                cursor.execute(query, params)
                headers = [description[0] for description in cursor.description]
                data = cursor.fetchall()
                return headers, data
        except Exception as e:
            logger.error(f"Error fetching songs by unified artists: {e}")
            return [], []

    def get_by_id(self, source_id: int) -> Optional[Song]:
        """Get full song object by ID (Legacy wrapper)"""
        songs = self.get_songs_by_ids([source_id])
        return songs[0] if songs else None

    def get_by_path(self, path: str) -> Optional[Song]:
        """Get full song object by path (Legacy wrapper)"""
        songs = self.get_songs_by_paths([path])
        return songs[0] if songs else None

    def get_songs_by_ids(self, source_ids: List[int]) -> List[Song]:
        """Bulk fetch songs by their SourceID (High Performance)"""
        if not source_ids:
            return []
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Fetch main song data using efficient IN clause
                placeholders = ",".join(["?"] * len(source_ids))
                query = f"""
                    SELECT 
                        MS.SourceID, MS.SourcePath, MS.MediaName, MS.SourceDuration, 
                        S.TempoBPM, S.RecordingYear, S.ISRC, S.SongGroups,
                        MS.SourceNotes, MS.IsActive,
                        (
                            SELECT GROUP_CONCAT(A.AlbumTitle)
                            FROM Albums A 
                            JOIN SongAlbums SA ON A.AlbumID = SA.AlbumID 
                            WHERE SA.SourceID = MS.SourceID
                            ORDER BY SA.IsPrimary DESC
                        ) as AlbumTitle,
                        (
                            SELECT A.AlbumID FROM Albums A 
                            JOIN SongAlbums SA ON A.AlbumID = SA.AlbumID 
                            WHERE SA.SourceID = MS.SourceID AND SA.IsPrimary = 1
                            LIMIT 1
                        ) as AlbumID,
                        COALESCE(
                            (
                                SELECT P.PublisherName 
                                FROM SongAlbums SA 
                                JOIN Publishers P ON SA.TrackPublisherID = P.PublisherID 
                                WHERE SA.SourceID = MS.SourceID AND SA.IsPrimary = 1
                            ),
                            (
                                SELECT GROUP_CONCAT(P.PublisherName, ', ')
                                FROM SongAlbums SA 
                                JOIN AlbumPublishers AP ON SA.AlbumID = AP.AlbumID
                                JOIN Publishers P ON AP.PublisherID = P.PublisherID
                                WHERE SA.SourceID = MS.SourceID AND SA.IsPrimary = 1
                            ),
                            (
                                SELECT GROUP_CONCAT(P.PublisherName, ', ')
                                FROM RecordingPublishers RP
                                JOIN Publishers P ON RP.PublisherID = P.PublisherID
                                WHERE RP.SourceID = MS.SourceID
                            )
                        ) as PublisherName,
                        (
                            SELECT GROUP_CONCAT(TG.TagName, ', ')
                            FROM MediaSourceTags MST
                            JOIN Tags TG ON MST.TagID = TG.TagID
                            WHERE MST.SourceID = MS.SourceID AND TG.TagCategory = 'Genre'
                        ) as Genre,
                        (
                            SELECT GROUP_CONCAT(TG.TagName, ', ')
                            FROM MediaSourceTags MST
                            JOIN Tags TG ON MST.TagID = TG.TagID
                            WHERE MST.SourceID = MS.SourceID AND TG.TagCategory = 'Mood'
                        ) as Mood,
                        (
                            SELECT A.AlbumArtist FROM Albums A 
                            JOIN SongAlbums SA ON A.AlbumID = SA.AlbumID 
                            WHERE SA.SourceID = MS.SourceID AND SA.IsPrimary = 1
                            LIMIT 1
                        ) as AlbumArtist,
                        (
                            SELECT GROUP_CONCAT(TG.TagCategory || ':' || TG.TagName, '|||')
                            FROM MediaSourceTags MST
                            JOIN Tags TG ON MST.TagID = TG.TagID
                            WHERE MST.SourceID = MS.SourceID
                        ) as AllTags
                    FROM MediaSources MS
                    JOIN Songs S ON MS.SourceID = S.SourceID
                    WHERE MS.SourceID IN ({placeholders})
                """
                cursor.execute(query, source_ids)
                
                songs_map = {}
                for row in cursor.fetchall():
                    (source_id, path, name, duration, bpm, recording_year, isrc, groups_str, 
                     notes, is_active_int, album_title, album_id, publisher_name, genre_str, 
                     mood_str, album_artist, all_tags_str) = row
                    
                    groups = [g.strip() for g in groups_str.split(',')] if groups_str else []
                    tags = [t.strip() for t in all_tags_str.split('|||')] if all_tags_str else []
                    
                    song = Song(
                        source_id=source_id,
                        source=path,
                        name=name,
                        duration=duration,
                        bpm=bpm,
                        recording_year=recording_year,
                        isrc=isrc,
                        notes=notes,
                        is_active=bool(is_active_int),
                        album=album_title,
                        album_id=album_id,
                        album_artist=album_artist,
                        publisher=[p.strip() for p in publisher_name.split(',')] if publisher_name else [],
                        genre=genre_str,
                        mood=mood_str,
                        groups=groups,
                        tags=tags
                    )
                    songs_map[source_id] = song

                # 2. Fetch all roles for all songs in one go (with Credit Preservation)
                query_roles = f"""
                    SELECT MSCR.SourceID, R.RoleName, COALESCE(CA.AliasName, C.ContributorName)
                    FROM MediaSourceContributorRoles MSCR
                    JOIN Roles R ON MSCR.RoleID = R.RoleID
                    JOIN Contributors C ON MSCR.ContributorID = C.ContributorID
                    LEFT JOIN ContributorAliases CA ON MSCR.CreditedAliasID = CA.AliasID
                    WHERE MSCR.SourceID IN ({placeholders})
                """
                cursor.execute(query_roles, source_ids)
                
                for source_id, role_name, contributor_name in cursor.fetchall():
                    if source_id in songs_map:
                        song = songs_map[source_id]
                        if role_name == 'Performer':
                            song.performers.append(contributor_name)
                        elif role_name == 'Composer':
                            song.composers.append(contributor_name)
                        elif role_name == 'Lyricist':
                            song.lyricists.append(contributor_name)
                        elif role_name == 'Producer':
                            song.producers.append(contributor_name)

                # 3. Fetch all releases (Multi-Album Hydration)
                query_releases = f"""
                    SELECT SA.SourceID, A.AlbumID, A.AlbumTitle, A.ReleaseYear, SA.TrackNumber, SA.IsPrimary
                    FROM SongAlbums SA
                    JOIN Albums A ON SA.AlbumID = A.AlbumID
                    WHERE SA.SourceID IN ({placeholders})
                    ORDER BY SA.IsPrimary DESC, A.ReleaseYear DESC
                """
                cursor.execute(query_releases, source_ids)
                
                for r_src_id, r_alb_id, r_title, r_year, r_track, r_primary in cursor.fetchall():
                    if r_src_id in songs_map:
                         songs_map[r_src_id].releases.append({
                             'album_id': r_alb_id,
                             'title': r_title,
                             'year': r_year,
                             'track_number': r_track,
                             'is_primary': bool(r_primary)
                         })

                # Maintain original order of requested IDs
                return [songs_map[sid] for sid in source_ids if sid in songs_map]
                
        except Exception as e:
            logger.error(f"Error bulk fetching songs: {e}")
            return []

    def get_songs_by_paths(self, paths: List[str]) -> List[Song]:
        """Bulk fetch songs by their absolute paths"""
        if not paths:
            return []
            
        # Optimization: Skip os.path.abspath for network performance. 
        # Paths are already stored absolute/normalized in DB.
        norm_paths = [os.path.normcase(p) for p in paths]
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                placeholders = ",".join(["?"] * len(norm_paths))
                cursor.execute(f"SELECT SourceID FROM MediaSources WHERE SourcePath IN ({placeholders})", norm_paths)
                ids = [row[0] for row in cursor.fetchall()]
                
            return self.get_songs_by_ids(ids)
        except Exception as e:
            logger.error(f"Error resolving paths for bulk fetch: {e}")
            return []

    def get_all_years(self) -> List[int]:
        """Get list of distinct recording years"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT RecordingYear FROM Songs WHERE RecordingYear IS NOT NULL ORDER BY RecordingYear DESC")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all years: {e}")
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
            logger.error(f"Error fetching songs by year: {e}")
            return [], []

    def get_by_status(self, is_done: bool) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by their Done status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = f"""
                    {yellberus.QUERY_SELECT}
                    {yellberus.QUERY_FROM}
                    WHERE S.SongIsDone = ? AND MS.IsActive = 1
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
            logger.error(f"Error fetching songs by status: {e}")
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
            logger.error(f"Error getting song by ISRC: {e}")
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
            logger.error(f"Error getting song by audio hash: {e}")
            return None
            