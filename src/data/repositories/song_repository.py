"""Song Repository for database operations"""
import os
from typing import List, Optional, Tuple, Union, Any
import sqlite3
from src.data.database import BaseRepository
from ..models.song import Song
from ...core import yellberus, logger
from .generic_repository import GenericRepository
from .album_repository import AlbumRepository
from ..models.contributor import Contributor


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
        from ...business.services.song_sync_service import SongSyncService
        self.sync_service = SongSyncService()
        
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
            INSERT INTO MediaSources (TypeID, MediaName, SourcePath, IsActive, SourceDuration, SourceNotes, AudioHash) 
            VALUES (1, ?, ?, ?, ?, ?, ?)
            """,
            (file_title, file_path, 1 if song.is_active else 0, song.duration, song.notes, song.audio_hash)
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
        album_type = kwargs.get('album_type')
        self.sync_service.sync_all(song, cursor, auditor=auditor, album_type=album_type)
        
        return source_id

    def insert(self, entity_or_path: Union[Song, str], **kwargs) -> Optional[int]:
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
            return super().insert(song, **kwargs)
        else:
            return super().insert(entity_or_path, **kwargs)

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
            cursor.execute("SELECT CreditedNameID, RoleID FROM SongCredits WHERE SourceID = ?", (record_id,))
            for n_id, r_id in cursor.fetchall():
                 auditor.log_delete("SongCredits", f"{record_id}-{n_id}-{r_id}", {
                     "SourceID": record_id, "CreditedNameID": n_id, "RoleID": r_id
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

    def get_by_id(self, source_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Song]:
        """Fetch a single song by ID. Wrapper for get_songs_by_ids."""
        songs = self.get_songs_by_ids([source_id], conn=conn)
        return songs[0] if songs else None

    def _update_db(self, cursor: sqlite3.Cursor, song: Song, **kwargs) -> None:
        """Execute SQL UPDATE for GenericRepository"""
        auditor = kwargs.get('auditor')

        # 1. Update MediaSources
        normalized_path = os.path.normcase(os.path.abspath(song.source))
        cursor.execute("""
            UPDATE MediaSources
            SET MediaName = ?, SourcePath = ?, SourceDuration = ?, SourceNotes = ?, IsActive = ?, 
                AudioHash = COALESCE(?, AudioHash)
            WHERE SourceID = ?
        """, (song.name, normalized_path, song.duration, song.notes, 1 if song.is_active else 0, song.audio_hash, song.source_id))

        # 2. Update Songs
        groups_str = ", ".join(song.groups) if song.groups else None
        cursor.execute("""
            UPDATE Songs
            SET TempoBPM = ?, RecordingYear = ?, ISRC = ?, SongGroups = ?
            WHERE SourceID = ?
        """, (song.bpm, song.recording_year, song.isrc, groups_str, song.source_id))

        # Delegated Sync Logic (Moved to SongSyncService to reduce file size)
        album_type = kwargs.get('album_type')
        self.sync_service.sync_all(song, cursor, auditor=auditor, album_type=album_type)

    def update_status(self, file_id: int, is_done: bool, batch_id: Optional[str] = None) -> bool:
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
                    cursor = cursor.execute("INSERT OR IGNORE INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)", (file_id, tag_id))
                    if cursor.rowcount > 0:
                        from src.core.audit_logger import AuditLogger
                        AuditLogger(conn, batch_id=batch_id).log_insert("MediaSourceTags", f"{file_id}-{tag_id}", {"SourceID": file_id, "TagID": tag_id})
                else:
                    # Remove 'Unprocessed' status tag
                    # First get the tag ID for auditing
                    cursor.execute("SELECT TagID FROM Tags WHERE TagCategory = 'Status' AND TagName = 'Unprocessed'")
                    tag_row = cursor.fetchone()
                    if tag_row:
                        tag_id = tag_row[0]
                        # Check if link exists before deleting
                        cursor.execute("SELECT 1 FROM MediaSourceTags WHERE SourceID = ? AND TagID = ?", (file_id, tag_id))
                        if cursor.fetchone():
                            cursor.execute("DELETE FROM MediaSourceTags WHERE SourceID = ? AND TagID = ?", (file_id, tag_id))
                            from src.core.audit_logger import AuditLogger
                            AuditLogger(conn, batch_id=batch_id).log_delete("MediaSourceTags", f"{file_id}-{tag_id}", {"SourceID": file_id, "TagID": tag_id})

                # 2. Sync LEGACY (Skip - DB cleanup in progress)
                # (The column likely still exists but we don't write to it)
                return True
        except Exception as e:
            logger.error(f"Error updating song status: {e}")
            return False

    # Sync methods removed (Moved to SongSyncService)

    def get_by_performer(self, performer_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific performer"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = f"""
                    {yellberus.QUERY_SELECT}
                    {yellberus.QUERY_FROM}
                    WHERE MS.SourceID IN (
                        SELECT SC.SourceID 
                        FROM SongCredits SC
                        JOIN ArtistNames AN ON SC.CreditedNameID = AN.NameID
                        JOIN Roles R ON SC.RoleID = R.RoleID
                        WHERE AN.DisplayName = ? AND R.RoleName = 'Performer'
                    ) AND MS.IsActive = 1
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
                query = f"""
                    {yellberus.QUERY_SELECT}
                    {yellberus.QUERY_FROM}
                    WHERE MS.SourceID IN (
                        SELECT SC.SourceID 
                        FROM SongCredits SC
                        JOIN ArtistNames AN ON SC.CreditedNameID = AN.NameID
                        JOIN Roles R ON SC.RoleID = R.RoleID
                        WHERE AN.DisplayName = ? AND R.RoleName = 'Composer'
                    ) AND MS.IsActive = 1
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
                    WHERE (
                        S.SongGroups IN ({placeholders}) 
                        OR MS.SourceID IN (
                            SELECT SC.SourceID 
                            FROM SongCredits SC
                            JOIN ArtistNames AN ON SC.CreditedNameID = AN.NameID
                            JOIN Roles R ON SC.RoleID = R.RoleID
                            WHERE AN.DisplayName IN ({placeholders}) AND R.RoleName = 'Performer'
                        )
                    ) AND MS.IsActive = 1
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

    def get_by_path(self, path: str) -> Optional[Song]:
        """Get full song object by path (Legacy wrapper)"""
        songs = self.get_songs_by_paths([path])
        return songs[0] if songs else None

    def get_songs_by_ids(self, source_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[Song]:
        """Bulk fetch songs by their SourceID (High Performance)"""
        if not source_ids:
            return []
            
        if conn:
            return self._get_songs_by_ids_logic(source_ids, conn)
        try:
            with self.get_connection() as conn:
                return self._get_songs_by_ids_logic(source_ids, conn)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error bulk fetching songs: {e}")
            return []

    def _get_songs_by_ids_logic(self, source_ids: List[int], conn: sqlite3.Connection) -> List[Song]:
        """Internal logic for bulk fetching songs by their SourceID."""
        cursor = conn.cursor()
        
        # 1. Fetch main song data using efficient IN clause
        placeholders = ",".join(["?"] * len(source_ids))
        query = f"""
            SELECT 
                MS.SourceID, MS.SourcePath, MS.MediaName, MS.SourceDuration, 
                S.TempoBPM, S.RecordingYear, S.ISRC, S.SongGroups,
                MS.SourceNotes, MS.IsActive, MS.AudioHash,
                (
                    SELECT GROUP_CONCAT(A.AlbumTitle, '|||')
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
                        SELECT GROUP_CONCAT(P.PublisherName, '|||')
                        FROM RecordingPublishers RP
                        JOIN Publishers P ON RP.PublisherID = P.PublisherID
                        WHERE RP.SourceID = MS.SourceID
                    ),
                    (
                        SELECT P.PublisherName 
                        FROM SongAlbums SA 
                        JOIN Publishers P ON SA.TrackPublisherID = P.PublisherID 
                        WHERE SA.SourceID = MS.SourceID AND SA.IsPrimary = 1
                    )
                ) as PublisherName,

                (
                    SELECT GROUP_CONCAT(AN.DisplayName, '|||')
                    FROM Albums A 
                    JOIN SongAlbums SA ON A.AlbumID = SA.AlbumID 
                    JOIN AlbumCredits AC ON A.AlbumID = AC.AlbumID
                    JOIN ArtistNames AN ON AC.CreditedNameID = AN.NameID
                    WHERE SA.SourceID = MS.SourceID AND SA.IsPrimary = 1
                ) as AlbumArtist,
                (
                    SELECT GROUP_CONCAT(TG.TagCategory || ':' || TG.TagName, '|||')
                    FROM MediaSourceTags MST
                    JOIN Tags TG ON MST.TagID = TG.TagID
                    WHERE MST.SourceID = MS.SourceID
                ) as AllTags,
                COALESCE(
                    (
                        SELECT GROUP_CONCAT(RP.PublisherID, '|||')
                        FROM RecordingPublishers RP
                        WHERE RP.SourceID = MS.SourceID
                    ),
                    (
                        SELECT TrackPublisherID 
                        FROM SongAlbums SA 
                        WHERE SA.SourceID = MS.SourceID AND SA.IsPrimary = 1
                    )
                ) as PublisherID
            FROM MediaSources MS
            JOIN Songs S ON MS.SourceID = S.SourceID
            WHERE MS.SourceID IN ({placeholders})
        """
        cursor.execute(query, source_ids)
        rows = cursor.fetchall()
        songs_map = {}
        for row in rows:
            try:
                (source_id, path, name, duration, bpm, recording_year, isrc, groups_str, 
                 notes, is_active_int, audio_hash, album_title, album_id, publisher_name, 
                 album_artist, all_tags_str, publisher_id) = row

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
                    audio_hash=audio_hash,
                    is_active=bool(is_active_int),
                    album=[a.strip() for a in album_title.split('|||')] if album_title else [],
                    album_id=album_id,
                    album_artist=album_artist,
                    publisher=[p.strip() for p in publisher_name.split('|||')] if publisher_name else [],
                    publisher_id=[int(p) for p in str(publisher_id).split('|||') if p] if publisher_id else [],
                    groups=groups,
                    tags=tags
                )
                songs_map[source_id] = song
            except Exception:
                import traceback
                traceback.print_exc()

        # 2. Fetch all roles for all songs in one go (with Credit Preservation)
        query_roles = f"""
            SELECT sc.SourceID, r.RoleName, an.DisplayName
            FROM SongCredits sc
            JOIN Roles r ON sc.RoleID = r.RoleID
            JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
            WHERE sc.SourceID IN ({placeholders})
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

    def get_contributors_for_song(self, song_id: int, role_name: Optional[str] = None) -> List[Contributor]:
        """Fetch all performers/composers linked to a song as formal objects."""
        from ..models.contributor import Contributor
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT DISTINCT c.ContributorID, c.ContributorName, c.SortName, c.ContributorType
                    FROM Contributors c
                    JOIN MediaSourceContributorRoles mscr ON c.ContributorID = mscr.ContributorID
                    JOIN Roles r ON mscr.RoleID = r.RoleID
                    WHERE mscr.SourceID = ?
                """
                params = [song_id]
                if role_name:
                    query += " AND r.RoleName = ?"
                    params.append(role_name)
                    
                cursor.execute(query, params)
                # Use from_row which handles either tuple or dict-like Row
                return [Contributor.from_row(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching song contributors: {e}")
            return []

    def get_publishers_for_song(self, song_id: int) -> List[Any]:
        """Fetch all publishers linked to a song (via tracks or albums)."""
        from ..models.publisher import Publisher
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Direct recording publishers
                cursor.execute("""
                    SELECT P.PublisherID, P.PublisherName, P.ParentPublisherID
                    FROM RecordingPublishers RP
                    JOIN Publishers P ON RP.PublisherID = P.PublisherID
                    WHERE RP.SourceID = ?
                """, (song_id,))
                results = [Publisher.from_row(r) for r in cursor.fetchall()]
                
                if results: return results # Track level wins
                
                # 2. Album level publishers (if primary)
                cursor.execute("""
                    SELECT P.PublisherID, P.PublisherName, P.ParentPublisherID
                    FROM SongAlbums SA 
                    JOIN AlbumPublishers AP ON SA.AlbumID = AP.AlbumID
                    JOIN Publishers P ON AP.PublisherID = P.PublisherID
                    WHERE SA.SourceID = ? AND SA.IsPrimary = 1
                """, (song_id,))
                return [Publisher.from_row(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching song publishers: {e}")
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

    def get_virtual_member_count(self, zip_path: str) -> int:
        """Count how many library items belong to this ZIP container."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Ensure we match the pipe separator
                # DB stores normalized paths (lowercase on Windows)
                normalized_zip = os.path.normcase(os.path.abspath(zip_path))
                pattern = f"{normalized_zip}|%"
                cursor.execute("SELECT COUNT(*) FROM MediaSources WHERE SourcePath LIKE ?", (pattern,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error counting virtual members: {e}")
            return 0

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
        elif field_name in ("performers", "unified_artist"):
            query = """
                SELECT DISTINCT AN.DisplayName 
                FROM SongCredits SC
                JOIN ArtistNames AN ON SC.CreditedNameID = AN.NameID
                JOIN Roles R ON SC.RoleID = R.RoleID
                WHERE R.RoleName = 'Performer'
            """
        elif field_name == "composers":
            query = """
                SELECT DISTINCT AN.DisplayName 
                FROM SongCredits SC
                JOIN ArtistNames AN ON SC.CreditedNameID = AN.NameID
                JOIN Roles R ON SC.RoleID = R.RoleID
                WHERE R.RoleName = 'Composer'
            """
        elif field_name == "publisher":
            query = "SELECT DISTINCT PublisherName FROM Publishers"
        elif field_name == "album":
            query = "SELECT DISTINCT AlbumTitle FROM Albums"
        elif field_name == "album_artist":
            query = """
                SELECT DISTINCT AN.DisplayName
                FROM AlbumCredits AC
                JOIN ArtistNames AN ON AC.CreditedNameID = AN.NameID
            """
        
        # 2. Tag Mapping Path
        if not query:
            field_def = yellberus.get_field(field_name)
            if field_def and field_def.tag_category:
                query = f"SELECT DISTINCT TagName FROM Tags WHERE TagCategory = '{field_def.tag_category}'"

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
            
