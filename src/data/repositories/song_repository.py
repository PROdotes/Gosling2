"""Song Repository for database operations"""
import os
from typing import List, Optional, Tuple, Union
import sqlite3
from src.data.database import BaseRepository
from ..models.song import Song
from ...core import yellberus, logger
from .generic_repository import GenericRepository
from .album_repository import AlbumRepository


class SongRepository(GenericRepository[Song]):
    """
    Repository for Song management.
    Inherits GenericRepository for automatic Audit Logging.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path, "Songs", "source_id")
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

    def _insert_db(self, cursor: sqlite3.Cursor, song: Song, **kwargs) -> int:
        """Execute SQL INSERT for GenericRepository"""
        auditor = kwargs.get('auditor')
        # Normalize path
        file_path = os.path.normcase(os.path.abspath(song.source))
        file_title = song.name or os.path.basename(file_path)

        # 1. Insert into MediaSources
        cursor.execute(
            """
            INSERT INTO MediaSources (TypeID, MediaName, SourcePath, IsActive) 
            VALUES (1, ?, ?, ?)
            """,
            (file_title, file_path, 1 if song.is_active else 0)
        )
        source_id = cursor.lastrowid
        
        # 2. Insert into Songs
        groups_str = ", ".join(song.groups) if song.groups else None
        cursor.execute(
            "INSERT INTO Songs (SourceID, TempoBPM, RecordingYear, ISRC, SongGroups) VALUES (?, ?, ?, ?, ?)",
            (source_id, song.bpm, song.recording_year, song.isrc, groups_str)
        )
        
        # 3. Handle Relationships (if provided)
        # Temporarily set ID on object so helpers can use it
        song.source_id = source_id 
        if song.album: self._sync_album(song, cursor, auditor=auditor)
        if song.publisher: self._sync_publisher(song, cursor, auditor=auditor)
        self._sync_contributor_roles(song, cursor, auditor=auditor)
        
        return source_id

    def insert(self, entity_or_path: Union[Song, str]) -> Optional[int]:
        """
        Overridden insert to support legacy path-string argument.
        Delegates to GenericRepository.insert(Song).
        """
        if isinstance(entity_or_path, str):
            # Legacy: Create Stub Song
            path = entity_or_path
            # We create a stub song. Helpers won't run because fields are None/Empty.
            song = Song(
                source_id=0, # Placeholder
                source=path,
                name=os.path.basename(path),
                is_active=True
            )
            return super().insert(song)
        else:
            return super().insert(entity_or_path)

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

    def _delete_db(self, cursor: sqlite3.Cursor, record_id: int, **kwargs) -> None:
        """Execute SQL DELETE for GenericRepository"""
        auditor = kwargs.get('auditor')
        # Audit cascaded deletes for junctions
        if auditor:
            cursor.execute("SELECT ContributorID, RoleID, CreditedAliasID FROM MediaSourceContributorRoles WHERE SourceID = ?", (record_id,))
            for c_id, r_id, a_id in cursor.fetchall():
                 auditor.log_delete("MediaSourceContributorRoles", f"{record_id}-{c_id}-{r_id}", {
                     "SourceID": record_id, "ContributorID": c_id, "RoleID": r_id, "CreditedAliasID": a_id
                 })
            
            cursor.execute("SELECT AlbumID, TrackNumber, IsPrimary FROM SongAlbums WHERE SourceID = ?", (record_id,))
            for a_id, t_num, isp in cursor.fetchall():
                 auditor.log_delete("SongAlbums", f"{record_id}-{a_id}", {
                     "SourceID": record_id, "AlbumID": a_id, "TrackNumber": t_num, "IsPrimary": isp
                 })

            cursor.execute("SELECT PublisherID FROM RecordingPublishers WHERE SourceID = ?", (record_id,))
            for p_id in cursor.fetchall():
                 auditor.log_delete("RecordingPublishers", f"{record_id}-{p_id[0]}", {
                     "SourceID": record_id, "PublisherID": p_id[0]
                 })

        cursor.execute("DELETE FROM MediaSources WHERE SourceID = ?", (record_id,))

    def get_by_id(self, source_id: int) -> Optional[Song]:
        """Fetch a single song by ID. Wrapper for get_songs_by_ids."""
        songs = self.get_songs_by_ids([source_id])
        return songs[0] if songs else None

    def _update_db(self, cursor: sqlite3.Cursor, song: Song, **kwargs) -> None:
        """Execute SQL UPDATE for GenericRepository"""
        auditor = kwargs.get('auditor')

        # 1. Update MediaSources
        normalized_path = os.path.normcase(os.path.abspath(song.source))
        cursor.execute("""
            UPDATE MediaSources
            SET MediaName = ?, SourcePath = ?, SourceDuration = ?, SourceNotes = ?, IsActive = ?, AudioHash = ?
            WHERE SourceID = ?
        """, (song.name, normalized_path, song.duration, song.notes, 1 if song.is_active else 0, song.audio_hash, song.source_id))

        # 2. Update Songs
        groups_str = ", ".join(song.groups) if song.groups else None
        cursor.execute("""
            UPDATE Songs
            SET TempoBPM = ?, RecordingYear = ?, ISRC = ?, SongGroups = ?
            WHERE SourceID = ?
        """, (song.bpm, song.recording_year, song.isrc, groups_str, song.source_id))

        # 3. Cleanup handled by Sync methods now (Diff-based)
        # (Blocks 3 and 4 merged logically into smart syncs)
        
        # 4. Sync contributor roles (Handle Inserts and Deletes internally)
        self._sync_contributor_roles(song, cursor, auditor=auditor)

        # 5. Sync Album
        if song.album is not None:
             self._sync_album(song, cursor, auditor=auditor)

        # 6. Sync Publisher
        if song.publisher is not None:
             self._sync_publisher(song, cursor, auditor=auditor)

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

    def _sync_contributor_roles(self, song: Song, cursor, auditor=None) -> None:
        """Sync contributors by calculating diff between DB and Object model."""
        conn = cursor.connection
        
        # 1. Calculate Desired State
        role_map = {
            'performers': 'Performer',
            'composers': 'Composer',
            'lyricists': 'Lyricist',
            'producers': 'Producer'
        }
        
        desired_links = set() # Set of (ContributorID, RoleID, CreditedAliasID)
        
        for attr, role_name in role_map.items():
            contributors = getattr(song, attr, [])
            if not contributors: continue

             # Get RoleID
            cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = ?", (role_name,))
            role_row = cursor.fetchone()
            if not role_row: continue
            role_id = role_row[0]

            for contributor_name in contributors:
                if not contributor_name.strip(): continue

                # Resolve Identity
                artist, _ = self.contributor_repository.get_or_create(contributor_name, conn=conn)
                contributor_id = artist.contributor_id
                
                # Resolve Alias
                credited_alias_id = None
                if artist.matched_alias and artist.matched_alias.lower() == contributor_name.lower():
                     pass # (Logic TBD if we stash matched_alias in object)
                else:
                     if contributor_name.lower() != artist.name.lower():
                         cursor.execute("SELECT AliasID FROM ContributorAliases WHERE ContributorID = ? AND AliasName = ? COLLATE NOCASE", (contributor_id, contributor_name))
                         arow = cursor.fetchone()
                         if arow: credited_alias_id = arow[0]
                
                desired_links.add((contributor_id, role_id, credited_alias_id))

        # 2. Get Current State
        cursor.execute("SELECT ContributorID, RoleID, CreditedAliasID FROM MediaSourceContributorRoles WHERE SourceID = ?", (song.source_id,))
        current_links_raw = cursor.fetchall()
        # Convert tuple to (c_id, r_id, a_id) - handle NULL alias
        current_links = set()
        for c, r, a in current_links_raw:
            current_links.add((c, r, a))
            
        # 3. Calculate Diff
        to_add = desired_links - current_links
        to_remove = current_links - desired_links
        
        # 4. Execute Changes
        # DELETE
        for c_id, r_id, a_id in to_remove:
            cursor.execute(
                "DELETE FROM MediaSourceContributorRoles WHERE SourceID = ? AND ContributorID = ? AND RoleID = ?",
                (song.source_id, c_id, r_id)
            )
            if auditor:
                auditor.log_delete("MediaSourceContributorRoles", f"{song.source_id}-{c_id}-{r_id}", {
                    "SourceID": song.source_id,
                    "ContributorID": c_id,
                    "RoleID": r_id,
                    "CreditedAliasID": a_id
                })
                
        # INSERT
        for c_id, r_id, a_id in to_add:
            cursor.execute(
                "INSERT INTO MediaSourceContributorRoles (SourceID, ContributorID, RoleID, CreditedAliasID) VALUES (?, ?, ?, ?)",
                (song.source_id, c_id, r_id, a_id)
            )
            if auditor:
                auditor.log_insert("MediaSourceContributorRoles", f"{song.source_id}-{c_id}-{r_id}", {
                    "SourceID": song.source_id,
                    "ContributorID": c_id,
                    "RoleID": r_id,
                    "CreditedAliasID": a_id
                })

    def _sync_album(self, song: Song, cursor, auditor=None) -> None:
        """
        Sync album relationship (Find or Create with Artist Disambiguation).
        Diff-Based Update: Preserves TrackNumbers and prevents unnecessary deletions.
        """
        # 0. Normalize Inputs -> Determine Target IDs
        effective_title = None
        all_titles = []
        if isinstance(song.album, list):
            all_titles = [str(t).strip() for t in song.album if t]
            effective_title = all_titles[0] if all_titles else ""
        elif song.album:
             t = str(song.album).strip()
             if t:
                 all_titles = [t]
                 effective_title = t

        target_ids = []
        
        # A. Attempt Precise ID Match
        use_precise_id = False
        if getattr(song, 'album_id', None) is not None:
             if not effective_title:
                 use_precise_id = True
             else:
                 check_id = song.album_id
                 if isinstance(check_id, list): check_id = check_id[0] if check_id else None
                 cursor.execute("SELECT AlbumTitle FROM Albums WHERE AlbumID = ?", (check_id,))
                 id_row = cursor.fetchone()
                 if id_row and id_row[0].lower() == effective_title.lower():
                     use_precise_id = True

        if use_precise_id:
             ids = song.album_id
             if isinstance(ids, list): target_ids = ids
             elif ids: target_ids = [ids]
             
        elif all_titles:
            # B. Get/Create by Name
            album_artist = getattr(song, 'album_artist', None)
            if album_artist: album_artist = album_artist.strip() or None
            release_year = getattr(song, 'recording_year', None)
            
            for album_title in all_titles:
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
                
                cursor.execute(f"SELECT AlbumID FROM Albums WHERE {' AND '.join(conditions)}", params)
                row = cursor.fetchone()
                if row:
                    target_ids.append(row[0])
                else:
                    cursor.execute("INSERT INTO Albums (AlbumTitle, AlbumArtist, AlbumType, ReleaseYear) VALUES (?, ?, 'Album', ?)", (album_title, album_artist, release_year))
                    target_ids.append(cursor.lastrowid)

        # Handle 'Clear Album' scenario (Explicit empty string)
        if effective_title is not None and not effective_title.strip() and not use_precise_id:
            target_ids = [] 
            
        # 1. Get Current State: {AlbumID: {'IsPrimary': bool, 'TrackNumber': int}}
        cursor.execute("SELECT AlbumID, TrackNumber, IsPrimary FROM SongAlbums WHERE SourceID = ?", (song.source_id,))
        current_map = {}
        for a_id, t_num, is_p in cursor.fetchall():
            current_map[a_id] = {'IsPrimary': is_p, 'TrackNumber': t_num}
            
        # 2. Build Desired State: {AlbumID: IsPrimary} (List order determines primary)
        desired_map = {}
        for idx, a_id in enumerate(target_ids):
            desired_map[a_id] = (1 if idx == 0 else 0)
            
        # 3. Calculate Diffs
        current_ids = set(current_map.keys())
        desired_ids = set(desired_map.keys())
        
        to_delete = current_ids - desired_ids
        to_add = desired_ids - current_ids
        to_check = current_ids.intersection(desired_ids)
        
        # 4. Execute Changes
        # DELETE
        for a_id in to_delete:
            snap = current_map[a_id]
            cursor.execute("DELETE FROM SongAlbums WHERE SourceID = ? AND AlbumID = ?", (song.source_id, a_id))
            if auditor:
                auditor.log_delete("SongAlbums", f"{song.source_id}-{a_id}", {
                     "SourceID": song.source_id, "AlbumID": a_id, "TrackNumber": snap['TrackNumber'], "IsPrimary": snap['IsPrimary']
                })

        # INSERT
        for a_id in to_add:
            is_p = desired_map[a_id]
            cursor.execute("INSERT INTO SongAlbums (SourceID, AlbumID, IsPrimary) VALUES (?, ?, ?)", (song.source_id, a_id, is_p))
            if auditor:
                auditor.log_insert("SongAlbums", f"{song.source_id}-{a_id}", {
                    "SourceID": song.source_id, "AlbumID": a_id, "IsPrimary": is_p
                })
                
        # UPDATE (Only if IsPrimary Changed)
        for a_id in to_check:
            cur_p = current_map[a_id]['IsPrimary']
            new_p = desired_map[a_id]
            if cur_p != new_p:
                cursor.execute("UPDATE SongAlbums SET IsPrimary = ? WHERE SourceID = ? AND AlbumID = ?", (new_p, song.source_id, a_id))
                if auditor:
                    auditor.log_update("SongAlbums", f"{song.source_id}-{a_id}", {"IsPrimary": cur_p}, {"IsPrimary": new_p})


    def _sync_publisher(self, song: Song, cursor, auditor=None) -> None:
        """
        Sync publisher relationship (RecordingPublishers - M:M).
        Diff-Based Update: Only adds/removes links that changed.
        """
        # 1. Parse Publishers
        if isinstance(song.publisher, list):
            publisher_names = [str(p).strip() for p in song.publisher if p]
        else:
            raw_val = song.publisher or ""
            publisher_names = [p.strip() for p in raw_val.split(',') if p.strip()]

        # Resolve Publisher IDs
        desired_ids = set()
        publisher_ids = [] # Ordered list for Primary Override logic
        
        for pub_name in publisher_names:
            cursor.execute("SELECT PublisherID FROM Publishers WHERE PublisherName = ?", (pub_name,))
            row = cursor.fetchone()
            if row:
                pid = row[0]
            else:
                # Insert missing publisher
                cursor.execute("INSERT INTO Publishers (PublisherName) VALUES (?)", (pub_name,))
                pid = cursor.lastrowid
            
            desired_ids.add(pid)
            publisher_ids.append(pid) # Keep order

        # 2. Get Current IDs
        cursor.execute("SELECT PublisherID FROM RecordingPublishers WHERE SourceID = ?", (song.source_id,))
        # Fetchall returns list of tuples [(1,), (2,)]
        current_ids = set(r[0] for r in cursor.fetchall())
        
        # 3. Calculate Diff
        to_add = desired_ids - current_ids
        to_remove = current_ids - desired_ids
        
        # 4. Execute Changes
        # DELETE
        for pid in to_remove:
            cursor.execute("DELETE FROM RecordingPublishers WHERE SourceID = ? AND PublisherID = ?", (song.source_id, pid))
            if auditor:
                auditor.log_delete("RecordingPublishers", f"{song.source_id}-{pid}", {
                     "SourceID": song.source_id, "PublisherID": pid
                })
                
        # INSERT
        for pid in to_add:
            cursor.execute("INSERT INTO RecordingPublishers (SourceID, PublisherID) VALUES (?, ?)", (song.source_id, pid))
            if auditor:
                auditor.log_insert("RecordingPublishers", f"{song.source_id}-{pid}", {
                    "SourceID": song.source_id, "PublisherID": pid
                })

        # 5. Handle Album Links & Overrides (TrackPublisherID)
        # Note: This logic seems to depend on Album links being established.
        # It updates existing SongAlbums rows.
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
            if auditor:
                # TrackPublisherID is technically a field in SongAlbums, so this is log_update
                cursor.execute("SELECT AlbumID, TrackPublisherID FROM SongAlbums WHERE SourceID = ?", (song.source_id,))
                for a_id, old_tp_id in cursor.fetchall():
                     if old_tp_id != primary_pid:
                         auditor.log_update("SongAlbums", f"{song.source_id}-{a_id}", {"TrackPublisherID": old_tp_id}, {"TrackPublisherID": primary_pid})

            cursor.execute("UPDATE SongAlbums SET TrackPublisherID = ? WHERE SourceID = ?", (primary_pid, song.source_id))

    # _sync_tags removed (Legacy)

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
                    
                    # Migration: Fold Legacy Genre/Mood into Tags
                    if genre_str:
                        # Split by comma if multiple legacy genres
                        for g in genre_str.split(','):
                             g_clean = g.strip()
                             if g_clean: tags.append(f"Genre:{g_clean}")
                    if mood_str:
                        for m in mood_str.split(','):
                             m_clean = m.strip()
                             if m_clean: tags.append(f"Mood:{m_clean}")
                    
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
                        # genre/mood arguments removed
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
                final_list = []
                for sid in source_ids:
                    if sid in songs_map:
                        song = songs_map[sid]
                        # T-Fix: Re-hydrate album/album_id from structured releases to prevent
                        # "GROUP_CONCAT" merging (e.g. "Album A, Album B" becoming one title).
                        if song.releases:
                            # Releases are already sorted by IsPrimary DESC
                            titles = [r['title'] for r in song.releases]
                            ids = [r['album_id'] for r in song.releases]
                            
                            if len(titles) > 1:
                                song.album = titles
                                song.album_id = ids
                            elif titles:
                                song.album = titles[0]
                                song.album_id = ids[0]
                        
                        final_list.append(song)
                
                return final_list
                
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
                    WHERE MS.IsActive = 1
                    {yellberus.QUERY_GROUP_BY}
                    HAVING is_done = ?
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

    def get_distinct_values(self, field_name: str) -> List[Any]:
        """
        Get distinct values for a field to populate filters.
        Logic moved from LibraryService to centralize SQL access.
        """
        from src.core import yellberus
        
        # 1. OPTIMIZED PATH: Direct queries for common fields
        query = None
        if field_name == "recording_year":
             return self.get_all_years()
        elif field_name == "performers":
            query = """
                SELECT DISTINCT C.ContributorName 
                FROM Contributors C
                JOIN MediaSourceContributorRoles MSCR ON C.ContributorID = MSCR.ContributorID
                JOIN Roles R ON MSCR.RoleID = R.RoleID
                WHERE R.RoleName = 'Performer'
            """
        elif field_name == "composers":
            query = """
                SELECT DISTINCT C.ContributorName 
                FROM Contributors C
                JOIN MediaSourceContributorRoles MSCR ON C.ContributorID = MSCR.ContributorID
                JOIN Roles R ON MSCR.RoleID = R.RoleID
                WHERE R.RoleName = 'Composer'
            """
        elif field_name == "publisher":
            query = "SELECT DISTINCT PublisherName FROM Publishers"
        elif field_name == "genre":
            query = "SELECT DISTINCT TagName FROM Tags WHERE TagCategory = 'Genre'"
        elif field_name == "mood":
            query = "SELECT DISTINCT TagName FROM Tags WHERE TagCategory = 'Mood'"
        elif field_name == "album":
            query = "SELECT DISTINCT AlbumTitle FROM Albums"
        elif field_name == "album_artist":
            query = "SELECT DISTINCT AlbumArtist FROM Albums WHERE AlbumArtist IS NOT NULL"

        if query:
            with self.get_connection() as conn:
                cursor = conn.execute(query)
                results = [row[0] for row in cursor.fetchall() if row[0]]
                return sorted(results, key=lambda x: str(x).lower() if isinstance(x, str) else x)

        # 2. FALLBACK PATH for generic fields
        field_def = yellberus.get_field(field_name)
        if not field_def:
            return []
            
        expr = field_def.query_expression or field_def.db_column
        if " AS " in expr.upper():
            expr = expr.split(" AS ")[0].strip()
            
        query = f"SELECT DISTINCT {expr} {yellberus.QUERY_FROM} {yellberus.QUERY_BASE_WHERE}"
        
        with self.get_connection() as conn:
            cursor = conn.execute(query)
            results = set()
            for row in cursor.fetchall():
                val = row[0]
                if val:
                    if isinstance(val, str) and ',' in val:
                        for item in val.split(','):
                            item = item.strip()
                            if item: results.add(item)
                    else:
                        results.add(val)
            return sorted(list(results), key=lambda x: str(x).lower() if isinstance(x, str) else x)
            