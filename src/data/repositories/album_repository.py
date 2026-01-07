from typing import Optional, List, Tuple
import sqlite3
from src.data.database import BaseRepository
from src.data.models.album import Album
from src.data.models.contributor import Contributor
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
        query = "SELECT AlbumID, AlbumTitle, AlbumArtist, AlbumType, ReleaseYear FROM Albums WHERE AlbumID = ?"
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
            SELECT GROUP_CONCAT(c.ContributorName, '|||')
            FROM Contributors c
            JOIN AlbumContributors ac ON c.ContributorID = ac.ContributorID
            WHERE ac.AlbumID = ?
        """
        cursor = conn.execute(query, (album_id,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else None

    def find_by_title(self, title: str) -> Optional[Album]:
        """Retrieve album by exact title match (case-insensitive)."""
        query = "SELECT AlbumID, AlbumTitle, AlbumArtist, AlbumType, ReleaseYear FROM Albums WHERE AlbumTitle = ? COLLATE NOCASE"
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
            "INSERT INTO Albums (AlbumTitle, AlbumArtist, AlbumType, ReleaseYear) VALUES (?, ?, ?, ?)",
            (album.title, album.album_artist, album.album_type, album.release_year)
        )
        return cursor.lastrowid

    def _update_db(self, cursor: sqlite3.Cursor, album: Album, **kwargs) -> None:
        """Execute SQL UPDATE for GenericRepository"""
        cursor.execute(
            "UPDATE Albums SET AlbumTitle = ?, AlbumArtist = ?, AlbumType = ?, ReleaseYear = ? WHERE AlbumID = ?", 
            (album.title, album.album_artist, album.album_type, album.release_year, album.album_id)
        )

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
        cursor.execute("DELETE FROM Albums WHERE AlbumID = ?", (record_id,))

    def find_by_key(
        self, 
        title: str, 
        album_artist: Optional[str] = None, 
        release_year: Optional[int] = None
    ) -> Optional[Album]:
        """
        Find album by unique key (Title, AlbumArtist, ReleaseYear).
        Handles NULL values appropriately for disambiguation.
        """
        # Build query dynamically based on what's provided
        conditions = ["AlbumTitle = ? COLLATE NOCASE"]
        params = [title]
        
        if album_artist:
            conditions.append("AlbumArtist = ? COLLATE NOCASE")
            params.append(album_artist)
        else:
            conditions.append("(AlbumArtist IS NULL OR AlbumArtist = '')")
        
        if release_year:
            conditions.append("ReleaseYear = ?")
            params.append(release_year)
        
        query = f"""
            SELECT AlbumID, AlbumTitle, AlbumArtist, AlbumType, ReleaseYear 
            FROM Albums 
            WHERE {' AND '.join(conditions)}
        """
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            if row:
                return Album.from_row(row)
        return None

    def search(self, query: str, limit: int = 100, empty_only: bool = False) -> List[Album]:
        """Fuzzy search for albums by title or artist, including song counts."""
        # Dynamic HAVING clause
        having_clause = "HAVING SongCount = 0" if empty_only else ""
        
        sql_query = f"""
            SELECT 
                a.AlbumID, a.AlbumTitle, a.AlbumArtist, a.AlbumType, a.ReleaseYear,
                COUNT(sa.SourceID) as SongCount
            FROM Albums a
            LEFT JOIN SongAlbums sa ON a.AlbumID = sa.AlbumID
            WHERE a.AlbumTitle LIKE ? OR a.AlbumArtist LIKE ?
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
                results.append(Album.from_row(row))
        return results



    def create(
        self, 
        title: str, 
        album_artist: Optional[str] = None,
        album_type: str = 'Album', 
        release_year: Optional[int] = None
    ) -> Album:
        """
        Create a new album.
        Uses GenericRepository.insert() for Audit Logging.
        """
        album = Album(
            album_id=None, 
            title=title, 
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
        release_year: Optional[int] = None
    ) -> Tuple[Album, bool]:
        """
        Find an existing album by (Title, AlbumArtist, ReleaseYear) or create a new one.
        This prevents the "Greatest Hits" paradox where different artists' albums merge.
        
        Returns (Album, created).
        """
        existing = self.find_by_key(title, album_artist, release_year)
        if existing:
            return existing, False
        
        return self.create(title, album_artist=album_artist, release_year=release_year), True



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
            SELECT a.AlbumID, a.AlbumTitle, a.AlbumArtist, a.AlbumType, a.ReleaseYear
            FROM Albums a
            JOIN SongAlbums sa ON a.AlbumID = sa.AlbumID
            WHERE sa.SourceID = ?
        """
        albums = []
        with self.get_connection() as conn:
            cursor = conn.execute(query, (source_id,))
            for row in cursor.fetchall():
                albums.append(Album.from_row(row))
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

    def set_primary_album(self, source_id: int, album_id: int) -> None:
        """Promote an album link to be the Primary source."""
        with self.get_connection() as conn:
            # 1. Demote all
            conn.execute("UPDATE SongAlbums SET IsPrimary = 0 WHERE SourceID = ?", (source_id,))
            # 2. Promote specific
            conn.execute("UPDATE SongAlbums SET IsPrimary = 1 WHERE SourceID = ? AND AlbumID = ?", (source_id, album_id))

    def get_item_albums(self, source_id: int) -> List[Album]:
        """Get albums linked to a source item."""
        return self.get_albums_for_song(source_id)

    def assign_album(self, source_id: int, album_title: str, artist: Optional[str] = None, year: Optional[int] = None) -> Album:
        """
        Link a song to an album by title, artist, and year (Find or Create).
        This prevents different artists with the same album title from merging.
        """
        if not album_title or not album_title.strip():
            return None
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Find or Create Album
            album = self.find_by_key(album_title.strip(), artist, year)
            created = False
            if not album:
                cursor.execute(
                    "INSERT INTO Albums (AlbumTitle, AlbumArtist, AlbumType, ReleaseYear) VALUES (?, ?, 'Album', ?)",
                    (album_title.strip(), artist, year)
                )
                new_id = cursor.lastrowid
                album = Album(album_id=new_id, title=album_title.strip(), album_artist=artist, release_year=year, album_type='Album')
                created = True

            # T-91: If newly created, also link the provided artist via M2M
            if created and artist:
                # Handle multiple artists if comma-separated
                artist_names = [a.strip() for a in artist.split(',')]
                for a_name in artist_names:
                    # Resolve artist ID
                    cursor.execute("SELECT ContributorID FROM Contributors WHERE ContributorName = ?", (a_name,))
                    c_row = cursor.fetchone()
                    if not c_row:
                        cursor.execute("INSERT INTO Contributors (ContributorName, SortName, ContributorType) VALUES (?, ?, 'person')", (a_name, a_name))
                        c_id = cursor.lastrowid
                    else:
                        c_id = c_row[0]
                    
                    # Link
                    cursor = cursor.execute(
                        "INSERT OR IGNORE INTO AlbumContributors (AlbumID, ContributorID, RoleID) VALUES (?, ?, (SELECT RoleID FROM Roles WHERE RoleName = 'Performer'))",
                        (album.album_id, c_id)
                    )
                    if cursor.rowcount > 0:
                        from src.core.audit_logger import AuditLogger
                        AuditLogger(conn).log_insert("AlbumContributors", f"{album.album_id}-{c_id}", {"AlbumID": album.album_id, "ContributorID": c_id})

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
    
        return album



    def get_song_count(self, album_id: int) -> int:
        """Get number of songs in an album."""
        query = "SELECT COUNT(*) FROM SongAlbums WHERE AlbumID = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (album_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

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
                INSERT OR IGNORE INTO AlbumContributors (AlbumID, ContributorID, RoleID)
                VALUES (?, ?, ?)
            """, (album_id, contributor_id, role_id))
            
            if cursor.rowcount > 0:
                AuditLogger(conn, batch_id=batch_id).log_insert("AlbumContributors", f"{album_id}-{contributor_id}-{role_id}", {
                    "AlbumID": album_id,
                    "ContributorID": contributor_id,
                    "RoleID": role_id
                })
            return True

    def get_contributors_for_album(self, album_id: int) -> List[Contributor]:
        """Retrieve all contributors linked to an album."""
        from src.data.models.contributor import Contributor
        query = """
            SELECT c.ContributorID, c.ContributorName, c.SortName, c.ContributorType
            FROM Contributors c
            JOIN AlbumContributors ac ON c.ContributorID = ac.ContributorID
            WHERE ac.AlbumID = ?
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, (album_id,))
            return [Contributor.from_row(row) for row in cursor.fetchall()]

    def add_publisher_to_album(self, album_id: int, publisher_name: str, batch_id: Optional[str] = None) -> bool:
        """Link a publisher to an album. (Delegated to PublisherRepository)"""
        if not publisher_name: 
            return False
        from .publisher_repository import PublisherRepository
        with self.get_connection() as conn:
            return PublisherRepository().add_publisher_to_album_by_name(album_id, publisher_name, batch_id=batch_id, conn=conn)

    def get_publishers_for_album(self, album_id: int) -> List[Publisher]:
        """Retrieve all publishers linked to an album. (Delegated to PublisherRepository)"""
        from .publisher_repository import PublisherRepository
        return PublisherRepository().get_publishers_for_album(album_id)

    def get_publisher(self, album_id: int) -> Optional[str]:
        """Get all publisher names for an album (separated by |||). (Delegated to PublisherRepository)"""
        from .publisher_repository import PublisherRepository
        return PublisherRepository().get_joined_names(album_id)

    def remove_contributor_from_album(self, album_id: int, contributor_id: int, batch_id: Optional[str] = None) -> bool:
        """Unlink a contributor from an album."""
        from src.core.audit_logger import AuditLogger
        with self.get_connection() as conn:
            # Snapshot for audit
            query = "SELECT AlbumID, ContributorID, RoleID FROM AlbumContributors WHERE AlbumID = ? AND ContributorID = ?"
            cursor = conn.execute(query, (album_id, contributor_id))
            rows = cursor.fetchall()
            if not rows: return False
            
            auditor = AuditLogger(conn, batch_id=batch_id)
            for row in rows:
                snapshot = {"AlbumID": row[0], "ContributorID": row[1], "RoleID": row[2]}
                auditor.log_delete("AlbumContributors", f"{album_id}-{contributor_id}-{row[2]}", snapshot)
                
            conn.execute("DELETE FROM AlbumContributors WHERE AlbumID = ? AND ContributorID = ?", (album_id, contributor_id))
            return True

    def remove_publisher_from_album(self, album_id: int, publisher_id: int, batch_id: Optional[str] = None) -> bool:
        """Unlink a publisher from an album. (Delegated to PublisherRepository)"""
        from .publisher_repository import PublisherRepository
        with self.get_connection() as conn:
            return PublisherRepository().remove_publisher_from_album(album_id, publisher_id, batch_id=batch_id, conn=conn)

    def set_publisher(self, album_id: int, publisher_name: str, batch_id: Optional[str] = None) -> None:
        """
        LEGACY: Set the primary publisher for an album (Replace existing).
        (Delegated to PublisherRepository)
        """
        from .publisher_repository import PublisherRepository
        with self.get_connection() as conn:
            PublisherRepository().set_primary_publisher(album_id, publisher_name, batch_id=batch_id, conn=conn)

    def sync_publishers(self, album_id: int, publisher_names: List[str], batch_id: Optional[str] = None) -> None:
        """
        Synchronize album publishers to match the provided list exactly.
        (Delegated to PublisherRepository)
        """
        from .publisher_repository import PublisherRepository
        with self.get_connection() as conn:
            PublisherRepository().sync_publishers(album_id, publisher_names, batch_id=batch_id, conn=conn)

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
            cursor = conn.execute("SELECT ContributorID FROM AlbumContributors WHERE AlbumID = ? AND RoleID = ?", (album_id, role_id))
            current_ids = {row[0] for row in cursor.fetchall()}
            
            target_ids = {c.contributor_id for c in contributors if c.contributor_id}
            
            # 3. Remove items not in target
            for c_id in current_ids:
                if c_id not in target_ids:
                    auditor.log_delete("AlbumContributors", f"{album_id}-{c_id}-{role_id}", {"AlbumID": album_id, "ContributorID": c_id, "RoleID": role_id})
                    conn.execute("DELETE FROM AlbumContributors WHERE AlbumID = ? AND ContributorID = ? AND RoleID = ?", (album_id, c_id, role_id))
            
            # 4. Add new items
            for c in contributors:
                if c.contributor_id not in current_ids:
                    cursor = conn.execute(
                        "INSERT OR IGNORE INTO AlbumContributors (AlbumID, ContributorID, RoleID) VALUES (?, ?, ?)",
                        (album_id, c.contributor_id, role_id)
                    )
                    if cursor.rowcount > 0:
                        auditor.log_insert("AlbumContributors", f"{album_id}-{c.contributor_id}-{role_id}", {"AlbumID": album_id, "ContributorID": c.contributor_id, "RoleID": role_id})


