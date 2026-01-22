from typing import Optional, List, Tuple
import sqlite3
from src.data.database import BaseRepository
from src.data.models.album import Album
from src.data.models.contributor import Contributor
from src.data.models.publisher import Publisher
from .generic_repository import GenericRepository

class AlbumRepository(GenericRepository[Album]):
    """
    Repository for Album management.
    Inherits GenericRepository for automatic Audit Logging.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path, "Albums", "album_id")

    def get_by_id(self, album_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Album]:
        """Retrieve album by ID."""
        if conn:
            return self._get_by_id_logic(album_id, conn)
        with self.get_connection() as conn:
            return self._get_by_id_logic(album_id, conn)

    def _get_by_id_logic(self, album_id: int, conn: sqlite3.Connection) -> Optional[Album]:
        """Internal logic for retrieving album by ID."""
        query = "SELECT AlbumID, AlbumTitle, AlbumType, ReleaseYear FROM Albums WHERE AlbumID = ?"
        cursor = conn.execute(query, (album_id,))
        row = cursor.fetchone()
        if row:
            album = Album.from_row(row)
            album.album_artist = self._get_joined_album_artist(conn, album_id) or album.album_artist
            return album
        return None

    def _get_joined_album_artist(self, conn: sqlite3.Connection, album_id: int) -> Optional[str]:
        """Get album artists from M2M table (separated by |||)."""
        query = """
            SELECT GROUP_CONCAT(an.DisplayName, '|||')
            FROM ArtistNames an
            JOIN AlbumCredits ac ON an.NameID = ac.CreditedNameID
            WHERE ac.AlbumID = ?
        """
        cursor = conn.execute(query, (album_id,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else None

    def find_by_title(self, title: str) -> Optional[Album]:
        """Retrieve album by exact title match (case-insensitive)."""
        query = "SELECT AlbumID, AlbumTitle, AlbumType, ReleaseYear FROM Albums WHERE AlbumTitle = ? COLLATE UTF8_NOCASE"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (title,))
            row = cursor.fetchone()
            if row:
                album = Album.from_row(row)
                album.album_artist = self._get_joined_album_artist(conn, album.album_id) or album.album_artist
                return album
        return None

    def _insert_db(self, cursor: sqlite3.Cursor, album: Album, **kwargs) -> int:
        """Execute SQL INSERT for GenericRepository"""
        cursor.execute(
            "INSERT INTO Albums (AlbumTitle, AlbumType, ReleaseYear) VALUES (?, ?, ?)",
            (album.title, album.album_type, album.release_year)
        )
        new_id = cursor.lastrowid
        
        # T-91: Automatic M2M linking
        auditor = kwargs.get('auditor')
        self._resolve_and_link_artists(cursor, new_id, album.album_artist, auditor)
        
        return new_id

    def _update_db(self, cursor: sqlite3.Cursor, album: Album, **kwargs) -> None:
        """Execute SQL UPDATE for GenericRepository"""
        cursor.execute(
            "UPDATE Albums SET AlbumTitle = ?, AlbumType = ?, ReleaseYear = ? WHERE AlbumID = ?", 
            (album.title, album.album_type, album.release_year, album.album_id)
        )
        
        # T-91: Re-sync M2M links on update
        auditor = kwargs.get('auditor')
        self._resolve_and_link_artists(cursor, album.album_id, album.album_artist, auditor, sync=True)

    def _resolve_and_link_artists(self, cursor: sqlite3.Cursor, album_id: int, artist_string: Optional[str], auditor=None, sync: bool = False) -> None:
        """
        Helper to resolve a comma-separated artist string into individual artist M2M links.
        If sync=True, clears existing links first (Snapshot strategy).
        """
        if sync:
            # Audit removal of old links if auditor present
            if auditor:
                cursor.execute("SELECT CreditedNameID, RoleID FROM AlbumCredits WHERE AlbumID = ?", (album_id,))
                for c_id, r_id in cursor.fetchall():
                    auditor.log_delete("AlbumCredits", f"{album_id}-{c_id}", {"AlbumID": album_id, "CreditedNameID": c_id, "RoleID": r_id})
            cursor.execute("DELETE FROM AlbumCredits WHERE AlbumID = ?", (album_id,))

        if not artist_string or not artist_string.strip():
            return

        artist_names = [a.strip() for a in artist_string.split(',')]
        for a_name in artist_names:
            if not a_name: continue
            
            # 1. Resolve NameID from ArtistNames
            cursor.execute("SELECT NameID FROM ArtistNames WHERE DisplayName = ? COLLATE UTF8_NOCASE", (a_name,))
            row = cursor.fetchone()
            if row:
                name_id = row[0]
            else:
                # Orphan Create (Implicit Identity Creation?)
                # Actually, standard behavior in assign_album was to just insert into ArtistNames.
                cursor.execute("INSERT INTO ArtistNames (DisplayName, SortName, IsPrimaryName) VALUES (?, ?, 0)", (a_name, a_name))
                name_id = cursor.lastrowid
                if auditor:
                    auditor.log_insert("ArtistNames", name_id, {"DisplayName": a_name, "SortName": a_name, "IsPrimaryName": 0})

            # 2. Link via AlbumCredits
            # Use 'Performer' role (Lookup RoleID)
            cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = 'Performer'")
            r_row = cursor.fetchone()
            role_id = r_row[0] if r_row else 1 # Default fallback if schema missing Roles

            cursor.execute(
                "INSERT OR IGNORE INTO AlbumCredits (AlbumID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
                (album_id, name_id, role_id)
            )
            if cursor.rowcount > 0 and auditor:
                auditor.log_insert("AlbumCredits", f"{album_id}-{name_id}", {"AlbumID": album_id, "CreditedNameID": name_id, "RoleID": role_id})

    def _delete_db(self, cursor: sqlite3.Cursor, record_id: int, **kwargs) -> None:
        """Execute SQL DELETE for GenericRepository"""
        auditor = kwargs.get('auditor')
        # 1. Audit side-effect link removals
        if auditor:
            cursor.execute("SELECT SourceID, TrackNumber, IsPrimary FROM SongAlbums WHERE AlbumID = ?", (record_id,))
            for s_id, t_num, is_p in cursor.fetchall():
                 auditor.log_delete("SongAlbums", f"{s_id}-{record_id}", {"SourceID": s_id, "AlbumID": record_id, "TrackNumber": t_num, "IsPrimary": is_p})
                 
            cursor.execute("SELECT PublisherID FROM AlbumPublishers WHERE AlbumID = ?", (record_id,))
            for (p_id,) in cursor.fetchall():
                 auditor.log_delete("AlbumPublishers", f"{record_id}-{p_id}", {"AlbumID": record_id, "PublisherID": p_id})

        # 2. Cleanup links
        cursor.execute("DELETE FROM SongAlbums WHERE AlbumID = ?", (record_id,))
        cursor.execute("DELETE FROM AlbumPublishers WHERE AlbumID = ?", (record_id,))
        cursor.execute("DELETE FROM AlbumCredits WHERE AlbumID = ?", (record_id,))
        cursor.execute("DELETE FROM Albums WHERE AlbumID = ?", (record_id,))

    def merge(self, source_id: int, target_id: int, conn: Optional[sqlite3.Connection] = None, batch_id: Optional[str] = None) -> bool:
        """
        Merge source album info target album.
        Moves all songs, artists and publishers to the target.
        """
        from src.core.audit_logger import AuditLogger
        
        def _execute(target_conn):
            auditor = AuditLogger(target_conn, batch_id=batch_id)
            
            # 1. Update SongAlbums (Move songs)
            # Use INSERT OR IGNORE and then DELETE to handle potential primary key conflicts
            target_conn.execute("""
                INSERT OR IGNORE INTO SongAlbums (SourceID, AlbumID, TrackNumber, DiscNumber, IsPrimary, TrackPublisherID)
                SELECT SourceID, ?, TrackNumber, DiscNumber, IsPrimary, TrackPublisherID FROM SongAlbums WHERE AlbumID = ?
            """, (target_id, source_id))
            target_conn.execute("DELETE FROM SongAlbums WHERE AlbumID = ?", (source_id,))
            
            # 2. Update AlbumCredits (Artists)
            target_conn.execute("""
                INSERT OR IGNORE INTO AlbumCredits (AlbumID, CreditedNameID, RoleID)
                SELECT ?, CreditedNameID, RoleID FROM AlbumCredits WHERE AlbumID = ?
            """, (target_id, source_id))
            target_conn.execute("DELETE FROM AlbumCredits WHERE AlbumID = ?", (source_id,))
            
            # 3. Update AlbumPublishers
            target_conn.execute("""
                INSERT OR IGNORE INTO AlbumPublishers (AlbumID, PublisherID)
                SELECT ?, PublisherID FROM AlbumPublishers WHERE AlbumID = ?
            """, (target_id, source_id))
            target_conn.execute("DELETE FROM AlbumPublishers WHERE AlbumID = ?", (source_id,))
            
            # 4. Delete Source
            target_conn.execute("DELETE FROM Albums WHERE AlbumID = ?", (source_id,))
            
            return True

        if conn:
            return _execute(conn)
        with self.get_connection() as conn:
            success = _execute(conn)
            if success:
                conn.commit()
            return success

    def find_by_key(
        self, 
        title: str, 
        album_artist: Optional[str] = None, 
        release_year: Optional[int] = None,
        exclude_id: Optional[int] = None
    ) -> Optional[Album]:
        """
        Find album by unique key (Title, AlbumArtist, ReleaseYear).
        Uses M2M AlbumCredits for artist comparison.
        """
        # 1. Find candidates matching Title + Year
        base_query = "SELECT AlbumID FROM Albums WHERE AlbumTitle = ? COLLATE UTF8_NOCASE"
        base_params = [title]
        
        if release_year:
            base_query += " AND ReleaseYear = ?"
            base_params.append(release_year)
        else:
            base_query += " AND ReleaseYear IS NULL"
            
        with self.get_connection() as conn:
            cursor = conn.execute(base_query, base_params)
            candidates = [row[0] for row in cursor.fetchall() if row[0] != exclude_id]
            
            if not candidates:
                return None
                
            # 2. Prepare target artist set
            target_names = set()
            if album_artist and album_artist.strip():
                # Normalize similarly to M2M storage (logic depends on how we want to compare)
                # Here we assume simple case-insensitive set match
                target_names = {a.strip().lower() for a in album_artist.split(',') if a.strip()}
            
            # 3. Check each candidate
            for album_id in candidates:
                cursor.execute("""
                    SELECT lower(AN.DisplayName) 
                    FROM AlbumCredits AC 
                    JOIN ArtistNames AN ON AC.CreditedNameID = AN.NameID 
                    WHERE AC.AlbumID = ?
                """, (album_id,))
                
                linked_names = {row[0] for row in cursor.fetchall()}
                
                if linked_names == target_names:
                    return self.get_by_id(album_id, conn=conn)

        return None

    def search(self, query: str, limit: int = 100, empty_only: bool = False) -> List[Album]:
        """Fuzzy search for albums by title or artist, including song counts."""
        # Dynamic HAVING clause
        having_clause = "HAVING SongCount = 0" if empty_only else ""
        
        # We need to join ArtistNames to search by artist
        sql_query = f"""
            SELECT 
                a.AlbumID, a.AlbumTitle, a.AlbumType, a.ReleaseYear,
                COUNT(DISTINCT sa.SourceID) as SongCount
            FROM Albums a
            LEFT JOIN SongAlbums sa ON a.AlbumID = sa.AlbumID
            LEFT JOIN AlbumCredits ac ON a.AlbumID = ac.AlbumID
            LEFT JOIN ArtistNames an ON ac.CreditedNameID = an.NameID
            WHERE a.AlbumTitle LIKE ? OR an.DisplayName LIKE ?
            GROUP BY a.AlbumID
            {having_clause}
            ORDER BY CASE WHEN a.AlbumTitle LIKE ? THEN 1 ELSE 2 END, a.AlbumTitle
            LIMIT ?
        """
        wildcard = f"%{query}%"
        starts_with = f"{query}%"
        
        results = []
        with self.get_connection() as conn:
            cursor = conn.execute(sql_query, (wildcard, wildcard, starts_with, limit))
            for row in cursor.fetchall():
                # from_row will not have AlbumArtist, but we can hydrate it
                # Optimization: Could GROUP_CONCAT in the search query, but existing pattern parses M2M in from_row?
                # Actually from_row doesn't hydrate. We need to hydrate manually or rely on lazy loading?
                # The existing pattern was:
                # album = Album.from_row(row)
                # But notice search results didn't hydrate artist in the previous code? 
                # Wait, looking at previous code:
                # results.append(Album.from_row(row))
                # It DID NOT call _get_joined_album_artist. So previously it returned whatever was in the TEXT column.
                # Now that column is gone. We SHOULD hydrate it for the UI to show the artist.
                
                album = Album.from_row(row)
                album.album_artist = self._get_joined_album_artist(conn, album.album_id)
                results.append(album)
        return results

    def create(
        self, 
        title: str, 
        album_artist: Optional[str] = None,
        album_type: Optional[str] = None, 
        release_year: Optional[int] = None
    ) -> Album:
        """
        Create a new album.
        Uses GenericRepository.insert() for Audit Logging.
        """
        if album_type is None:
            # Note: The service should ideally provide this from settings. 
            # We keep 'Album' as the absolute hard fallback here for safety.
            album_type = 'Album'

        album = Album(
            album_id=None, 
            title=title, 
            # album_artist IS NONE, intended for M2M linking
            album_artist=album_artist, 
            album_type=album_type, 
            release_year=release_year
        )
        new_id = self.insert(album)
        if new_id:
            album.album_id = new_id
            return album
        raise Exception("Failed to insert album")

    def get_or_create(
        self, 
        title: str,
        album_artist: Optional[str] = None,
        release_year: Optional[int] = None,
        album_type: Optional[str] = None
    ) -> Tuple[Album, bool]:
        """
        Find an existing album by (Title, AlbumArtist, ReleaseYear) or create a new one.
        This prevents the "Greatest Hits" paradox where different artists' albums merge.
        
        Returns (Album, created).
        """
        existing = self.find_by_key(title, album_artist, release_year)
        if existing:
            return existing, False
        
        return self.create(title, album_artist=album_artist, release_year=release_year, album_type=album_type), True



    def add_song_to_album(self, source_id: int, album_id: int, track_number: Optional[int] = None, batch_id: Optional[str] = None) -> None:
        """Link a song to an album. First link is Primary."""
        from src.core.audit_logger import AuditLogger
        with self.get_connection() as conn:
            # 1. Determine if this should be Primary (if no primary exists for this source)
            cursor = conn.execute("SELECT 1 FROM SongAlbums WHERE SourceID = ? AND IsPrimary = 1", (source_id,))
            has_primary = cursor.fetchone() is not None
            is_primary = 0 if has_primary else 1
            
            # 2. Link
            cursor = conn.execute("""
                INSERT OR IGNORE INTO SongAlbums (SourceID, AlbumID, TrackNumber, IsPrimary)
                VALUES (?, ?, ?, ?)
            """, (source_id, album_id, track_number, is_primary))
            
            # 3. Audit
            if cursor.rowcount > 0:
                AuditLogger(conn, batch_id=batch_id).log_insert("SongAlbums", f"{source_id}-{album_id}", {
                    "SourceID": source_id,
                    "AlbumID": album_id,
                    "TrackNumber": track_number,
                    "IsPrimary": is_primary
                })

    def remove_song_from_album(self, source_id: int, album_id: int, batch_id: Optional[str] = None) -> None:
        """Unlink a song from an album."""
        from src.core.audit_logger import AuditLogger
        with self.get_connection() as conn:
            # Snapshot for audit
            cursor = conn.execute("SELECT SourceID, AlbumID, TrackNumber, IsPrimary FROM SongAlbums WHERE SourceID = ? AND AlbumID = ?", (source_id, album_id))
            row = cursor.fetchone()
            if not row: return
            snapshot = {"SourceID": row[0], "AlbumID": row[1], "TrackNumber": row[2], "IsPrimary": row[3]}

            conn.execute("DELETE FROM SongAlbums WHERE SourceID = ? AND AlbumID = ?", (source_id, album_id))
            AuditLogger(conn, batch_id=batch_id).log_delete("SongAlbums", f"{source_id}-{album_id}", snapshot)

    def get_albums_for_song(self, source_id: int) -> List[Album]:
        """Get all albums a song appears on."""
        query = """
            SELECT a.AlbumID, a.AlbumTitle, a.AlbumType, a.ReleaseYear
            FROM Albums a
            JOIN SongAlbums sa ON a.AlbumID = sa.AlbumID
            WHERE sa.SourceID = ?
        """
        albums = []
        with self.get_connection() as conn:
            cursor = conn.execute(query, (source_id,))
            for row in cursor.fetchall():
                album = Album.from_row(row)
                album.album_artist = self._get_joined_album_artist(conn, album.album_id)
                albums.append(album)
        return albums

    def get_songs_in_album(self, album_id: int) -> List[dict]:
        """
        Get lightweight list of songs in an album for preview.
        Returns [{'title': str, 'artist': str}]
        """
        query = """
            SELECT MS.MediaName, 
                   COALESCE(
                       (SELECT Group_Concat(C.ContributorName, '|||') 
                        FROM MediaSourceContributorRoles MSCR 
                        JOIN Contributors C ON MSCR.ContributorID = C.ContributorID
                        JOIN Roles R ON MSCR.RoleID = R.RoleID
                        WHERE MSCR.SourceID = MS.SourceID AND R.RoleName = 'Performer'
                       ), 
                       'Unknown'
                   ) as Artist,
                   SA.IsPrimary,
                   MS.SourceID
            FROM MediaSources MS
            JOIN SongAlbums SA ON MS.SourceID = SA.SourceID
            WHERE SA.AlbumID = ?
            ORDER BY SA.TrackNumber ASC, MS.MediaName ASC
        """
        songs = []
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, (album_id,))
                for row in cursor.fetchall():
                    songs.append({
                        'title': row[0], 
                        'artist': row[1],
                        'is_primary': bool(row[2]),
                        'source_id': row[3]
                    })
        except Exception as e:
            print(f"Error fetching album songs: {e}")
        return songs

    def set_primary_album(self, source_id: int, album_id: int, batch_id: Optional[str] = None) -> None:
        """Promote an album link to be the Primary source."""
        from src.core.audit_logger import AuditLogger
        with self.get_connection() as conn:
            auditor = AuditLogger(conn, batch_id=batch_id)
            cursor = conn.cursor()
            
            # 1. Snapshot current state and demote all
            cursor.execute("SELECT AlbumID, IsPrimary FROM SongAlbums WHERE SourceID = ?", (source_id,))
            for row in cursor.fetchall():
                if row[1] == 1:  # Was primary
                    auditor.log_update("SongAlbums", f"{source_id}-{row[0]}", {"IsPrimary": 1}, {"IsPrimary": 0})
            conn.execute("UPDATE SongAlbums SET IsPrimary = 0 WHERE SourceID = ?", (source_id,))
            
            # 2. Promote specific
            conn.execute("UPDATE SongAlbums SET IsPrimary = 1 WHERE SourceID = ? AND AlbumID = ?", (source_id, album_id))
            auditor.log_update("SongAlbums", f"{source_id}-{album_id}", {"IsPrimary": 0}, {"IsPrimary": 1})

    def get_item_albums(self, source_id: int) -> List[Album]:
        """Get albums linked to a source item."""
        return self.get_albums_for_song(source_id)

    def assign_album(self, source_id: int, album_title: str, artist: Optional[str] = None, year: Optional[int] = None, batch_id: Optional[str] = None, album_type: Optional[str] = None) -> Album:
        """
        Link a song to an album by title, artist, and year (Find or Create).
        This prevents different artists with the same album title from merging.
        """
        if not album_title or not album_title.strip():
            return None
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            from src.core.audit_logger import AuditLogger
            auditor = AuditLogger(conn, batch_id=batch_id)
            
            # Find or Create Album
            album = self.find_by_key(album_title.strip(), artist, year)
            created = False
            if not album:
                if album_type is None:
                    album_type = 'Album'
                    
                cursor.execute(
                    "INSERT INTO Albums (AlbumTitle, AlbumType, ReleaseYear) VALUES (?, ?, ?)",
                    (album_title.strip(), album_type, year)
                )
                new_id = cursor.lastrowid
                album = Album(album_id=new_id, title=album_title.strip(), album_artist=artist, release_year=year, album_type=album_type)
                created = True
                # Audit Album INSERT
                auditor.log_insert("Albums", new_id, {"AlbumTitle": album_title.strip(), "AlbumArtist": artist, "AlbumType": album_type, "ReleaseYear": year})

            # T-91: If newly created, also link the provided artist via M2M
            if created and artist:
                self._resolve_and_link_artists(cursor, album.album_id, artist, auditor)

            # Link song to album
            # Check if link exists
            cursor.execute("SELECT 1 FROM SongAlbums WHERE SourceID = ? AND AlbumID = ?", (source_id, album.album_id))
            if not cursor.fetchone():
                # Check for primary
                cursor.execute("SELECT 1 FROM SongAlbums WHERE SourceID = ? AND IsPrimary = 1", (source_id,))
                is_primary = 0 if cursor.fetchone() else 1
                cursor.execute(
                    "INSERT INTO SongAlbums (SourceID, AlbumID, IsPrimary) VALUES (?, ?, ?)",
                    (source_id, album.album_id, is_primary)
                )
                # Audit SongAlbums INSERT
                auditor.log_insert("SongAlbums", f"{source_id}-{album.album_id}", {"SourceID": source_id, "AlbumID": album.album_id, "IsPrimary": is_primary})
    
        return album



    def get_song_count(self, album_id: int) -> int:
        """Get number of songs in an album."""
        query = "SELECT COUNT(*) FROM SongAlbums WHERE AlbumID = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (album_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

    # ─────────────────────────────────────────────────────────────────
    # T-TOOLS INVENTORY METHODS (Phase 3)
    # ─────────────────────────────────────────────────────────────────

    def get_all_with_usage(self, orphans_only: bool = False) -> List[Tuple[Album, int]]:
        """
        Get all albums with their song count (usage).
        
        Args:
            orphans_only: If True, only return albums with 0 songs.
            
        Returns:
            List of (Album, usage_count) tuples.
        """
        having_clause = "HAVING SongCount = 0" if orphans_only else ""
        
        query = f"""
            SELECT 
                a.AlbumID, a.AlbumTitle, a.AlbumType, a.ReleaseYear,
                COUNT(DISTINCT sa.SourceID) as SongCount
            FROM Albums a
            LEFT JOIN SongAlbums sa ON a.AlbumID = sa.AlbumID
            GROUP BY a.AlbumID
            {having_clause}
            ORDER BY a.AlbumTitle COLLATE NOCASE
        """
        
        results = []
        with self.get_connection() as conn:
            cursor = conn.execute(query)
            for row in cursor.fetchall():
                album = Album.from_row(row)
                album.album_artist = self._get_joined_album_artist(conn, album.album_id)
                usage = row[4] if len(row) > 4 else 0
                results.append((album, usage))
        return results

    def get_orphan_count(self) -> int:
        """Get count of albums with no linked songs."""
        query = """
            SELECT COUNT(*) FROM Albums a
            WHERE NOT EXISTS (
                SELECT 1 FROM SongAlbums sa WHERE sa.AlbumID = a.AlbumID
            )
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query)
            row = cursor.fetchone()
            return row[0] if row else 0

    def delete_all_orphans(self, batch_id: Optional[str] = None) -> int:
        """
        Delete all albums with no linked songs.
        
        Returns:
            Number of albums deleted.
        """
        from src.core.audit_logger import AuditLogger
        
        with self.get_connection() as conn:
            auditor = AuditLogger(conn, batch_id=batch_id)
            
            # 1. Find orphan album IDs
            query = """
                SELECT a.AlbumID, a.AlbumTitle, a.AlbumType, a.ReleaseYear
                FROM Albums a
                WHERE NOT EXISTS (
                    SELECT 1 FROM SongAlbums sa WHERE sa.AlbumID = a.AlbumID
                )
            """
            cursor = conn.execute(query)
            orphans = cursor.fetchall()
            
            if not orphans:
                return 0
            
            deleted_count = 0
            for row in orphans:
                album_id = row[0]
                snapshot = {
                    "AlbumID": row[0],
                    "AlbumTitle": row[1],
                    "AlbumType": row[2],
                    "ReleaseYear": row[3]
                }
                
                # Clean up related M2M links (AlbumCredits, AlbumPublishers)
                conn.execute("DELETE FROM AlbumCredits WHERE AlbumID = ?", (album_id,))
                conn.execute("DELETE FROM AlbumPublishers WHERE AlbumID = ?", (album_id,))
                
                # Delete the album
                conn.execute("DELETE FROM Albums WHERE AlbumID = ?", (album_id,))
                auditor.log_delete("Albums", album_id, snapshot)
                deleted_count += 1
            
            conn.commit()
            return deleted_count

    def add_contributor_to_album(self, album_id: int, contributor_id: int, role_name: str = "Performer", batch_id: Optional[str] = None) -> bool:
        """Link a contributor to an album with a specific role."""
        from src.core.audit_logger import AuditLogger
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT RoleID FROM Roles WHERE RoleName = ?", (role_name,))
            r_row = cursor.fetchone()
            if not r_row: 
                return False
            role_id = r_row[0]

            cursor = conn.execute("""
                INSERT OR IGNORE INTO AlbumCredits (AlbumID, CreditedNameID, RoleID)
                VALUES (?, ?, ?)
            """, (album_id, contributor_id, role_id))
            
            if cursor.rowcount > 0:
                AuditLogger(conn, batch_id=batch_id).log_insert("AlbumCredits", f"{album_id}-{contributor_id}-{role_id}", {
                    "AlbumID": album_id,
                    "CreditedNameID": contributor_id,
                    "RoleID": role_id
                })
            return True

    def get_contributors_for_album(self, album_id: int) -> List[Contributor]:
        """Retrieve all contributors linked to an album."""
        from src.data.models.contributor import Contributor
        query = """
            SELECT an.NameID, an.DisplayName, an.SortName, 'person' -- Simplified type assumption for now, or join Identities
            FROM ArtistNames an
            JOIN AlbumCredits ac ON an.NameID = ac.CreditedNameID
            WHERE ac.AlbumID = ?
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, (album_id,))
            # Note: ArtistNames doesn't have 'type', defaulting to person/unknown. 
            # Ideally we join Identities but ArtistNames can be orphans.
            return [Contributor(contributor_id=row[0], name=row[1], sort_name=row[2], type='person') for row in cursor.fetchall()]

    def add_publisher_to_album(self, album_id: int, publisher_name: str, batch_id: Optional[str] = None) -> bool:
        """Link a publisher to an album. (Delegated to PublisherRepository)"""
        if not publisher_name: 
            return False
        from .publisher_repository import PublisherRepository
        with self.get_connection() as conn:
            return PublisherRepository(self.db_path).add_publisher_to_album_by_name(album_id, publisher_name, batch_id=batch_id, conn=conn)

    def get_publishers_for_album(self, album_id: int) -> List[Publisher]:
        """Retrieve all publishers linked to an album. (Delegated to PublisherRepository)"""
        from .publisher_repository import PublisherRepository
        return PublisherRepository(self.db_path).get_publishers_for_album(album_id)

    def get_publisher(self, album_id: int) -> Optional[str]:
        """Get all publisher names for an album (separated by |||). (Delegated to PublisherRepository)"""
        from .publisher_repository import PublisherRepository
        return PublisherRepository(self.db_path).get_joined_names(album_id)

    def remove_contributor_from_album(self, album_id: int, contributor_id: int, batch_id: Optional[str] = None) -> bool:
        """Unlink a contributor from an album."""
        from src.core.audit_logger import AuditLogger
        with self.get_connection() as conn:
            # Snapshot for audit
            query = "SELECT AlbumID, CreditedNameID, RoleID FROM AlbumCredits WHERE AlbumID = ? AND CreditedNameID = ?"
            cursor = conn.execute(query, (album_id, contributor_id))
            rows = cursor.fetchall()
            if not rows: return False
            
            auditor = AuditLogger(conn, batch_id=batch_id)
            for row in rows:
                snapshot = {"AlbumID": row[0], "CreditedNameID": row[1], "RoleID": row[2]}
                auditor.log_delete("AlbumCredits", f"{album_id}-{contributor_id}-{row[2]}", snapshot)
                
            conn.execute("DELETE FROM AlbumCredits WHERE AlbumID = ? AND CreditedNameID = ?", (album_id, contributor_id))
            return True

    def remove_publisher_from_album(self, album_id: int, publisher_id: int, batch_id: Optional[str] = None) -> bool:
        """Unlink a publisher from an album. (Delegated to PublisherRepository)"""
        from .publisher_repository import PublisherRepository
        with self.get_connection() as conn:
            return PublisherRepository(self.db_path).remove_publisher_from_album(album_id, publisher_id, batch_id=batch_id, conn=conn)

    def set_publisher(self, album_id: int, publisher_name: str, batch_id: Optional[str] = None) -> None:
        """
        LEGACY: Set the primary publisher for an album (Replace existing).
        (Delegated to PublisherRepository)
        """
        from .publisher_repository import PublisherRepository
        with self.get_connection() as conn:
            PublisherRepository(self.db_path).set_primary_publisher(album_id, publisher_name, batch_id=batch_id, conn=conn)

    def sync_publishers(self, album_id: int, publisher_names: List[str], batch_id: Optional[str] = None) -> None:
        """
        Synchronize album publishers to match the provided list exactly.
        (Delegated to PublisherRepository)
        """
        from .publisher_repository import PublisherRepository
        with self.get_connection() as conn:
            PublisherRepository(self.db_path).sync_publishers(album_id, publisher_names, batch_id=batch_id, conn=conn)

    def sync_contributors(self, album_id: int, contributors: List[Contributor], role_name: str = "Performer", batch_id: Optional[str] = None) -> None:
        """
        Synchronize album contributors to match the provided list exactly.
        """
        from src.core.audit_logger import AuditLogger
        
        with self.get_connection() as conn:
            auditor = AuditLogger(conn, batch_id=batch_id)
            
            # 1. Resolve role ID
            cursor = conn.execute("SELECT RoleID FROM Roles WHERE RoleName = ?", (role_name,))
            row = cursor.fetchone()
            if not row:
                conn.execute("INSERT INTO Roles (RoleName) VALUES (?)", (role_name,))
                role_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            else:
                role_id = row[0]

            # 2. Get current links for this role
            cursor = conn.execute("SELECT CreditedNameID FROM AlbumCredits WHERE AlbumID = ? AND RoleID = ?", (album_id, role_id))
            current_ids = {row[0] for row in cursor.fetchall()}
            
            target_ids = {c.contributor_id for c in contributors if c.contributor_id}
            
            # 3. Remove items not in target
            for c_id in current_ids:
                if c_id not in target_ids:
                    auditor.log_delete("AlbumCredits", f"{album_id}-{c_id}-{role_id}", {"AlbumID": album_id, "CreditedNameID": c_id, "RoleID": role_id})
                    conn.execute("DELETE FROM AlbumCredits WHERE AlbumID = ? AND CreditedNameID = ? AND RoleID = ?", (album_id, c_id, role_id))
            
            # 4. Add new items
            for c in contributors:
                if c.contributor_id not in current_ids:
                    cursor = conn.execute(
                        "INSERT OR IGNORE INTO AlbumCredits (AlbumID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
                        (album_id, c.contributor_id, role_id)
                    )
                    if cursor.rowcount > 0:
                        auditor.log_insert("AlbumCredits", f"{album_id}-{c.contributor_id}-{role_id}", {"AlbumID": album_id, "CreditedNameID": c.contributor_id, "RoleID": role_id})


