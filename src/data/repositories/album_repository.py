from typing import Optional, List, Tuple
import sqlite3
from src.data.database import BaseRepository
from src.data.models.album import Album
from .generic_repository import GenericRepository

class AlbumRepository(GenericRepository[Album]):
    """
    Repository for Album management.
    Inherits GenericRepository for automatic Audit Logging.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path, "Albums", "album_id")

    def get_by_id(self, album_id: int) -> Optional[Album]:
        """Retrieve album by ID."""
        query = "SELECT AlbumID, AlbumTitle, AlbumArtist, AlbumType, ReleaseYear FROM Albums WHERE AlbumID = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (album_id,))
            row = cursor.fetchone()
            if row:
                return Album.from_row(row)
        return None

    def find_by_title(self, title: str) -> Optional[Album]:
        """Retrieve album by exact title match (case-insensitive)."""
        query = "SELECT AlbumID, AlbumTitle, AlbumArtist, AlbumType, ReleaseYear FROM Albums WHERE AlbumTitle = ? COLLATE NOCASE"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (title,))
            row = cursor.fetchone()
            if row:
                return Album.from_row(row)
        return None

    def _insert_db(self, cursor: sqlite3.Cursor, album: Album) -> int:
        """Execute SQL INSERT for GenericRepository"""
        cursor.execute(
            "INSERT INTO Albums (AlbumTitle, AlbumArtist, AlbumType, ReleaseYear) VALUES (?, ?, ?, ?)",
            (album.title, album.album_artist, album.album_type, album.release_year)
        )
        return cursor.lastrowid

    def _update_db(self, cursor: sqlite3.Cursor, album: Album) -> None:
        """Execute SQL UPDATE for GenericRepository"""
        cursor.execute(
            "UPDATE Albums SET AlbumTitle = ?, AlbumArtist = ?, AlbumType = ?, ReleaseYear = ? WHERE AlbumID = ?", 
            (album.title, album.album_artist, album.album_type, album.release_year, album.album_id)
        )

    def _delete_db(self, cursor: sqlite3.Cursor, record_id: int) -> None:
        """Execute SQL DELETE for GenericRepository"""
        # Cleanup links first
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



    def add_song_to_album(self, source_id: int, album_id: int, track_number: Optional[int] = None) -> None:
        """Link a song to an album. First link is Primary."""
        with self.get_connection() as conn:
            # Check if any primary link exists
            cur = conn.execute("SELECT 1 FROM SongAlbums WHERE SourceID = ? AND IsPrimary = 1", (source_id,))
            has_primary = cur.fetchone() is not None
            
            is_primary = 0 if has_primary else 1
            
            query = """
                INSERT OR IGNORE INTO SongAlbums (SourceID, AlbumID, TrackNumber, IsPrimary)
                VALUES (?, ?, ?, ?)
            """
            conn.execute(query, (source_id, album_id, track_number, is_primary))

    def remove_song_from_album(self, source_id: int, album_id: int) -> None:
        """Unlink a song from an album."""
        query = "DELETE FROM SongAlbums WHERE SourceID = ? AND AlbumID = ?"
        with self.get_connection() as conn:
            conn.execute(query, (source_id, album_id))

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
                       (SELECT Group_Concat(C.ContributorName, ', ') 
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
        
        album, created = self.get_or_create(
            title=album_title.strip(),
            album_artist=artist,
            release_year=year
        )
    
        # Link song to album
        self.add_song_to_album(source_id, album.album_id)
    
        return album



    def get_song_count(self, album_id: int) -> int:
        """Get number of songs in an album."""
        query = "SELECT COUNT(*) FROM SongAlbums WHERE AlbumID = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (album_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_publisher(self, album_id: int) -> Optional[str]:
        """Get all publisher names for an album (comma-separated)."""
        query = """
            SELECT GROUP_CONCAT(p.PublisherName, ', ')
            FROM Publishers p
            JOIN AlbumPublishers ap ON p.PublisherID = ap.PublisherID
            WHERE ap.AlbumID = ?
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, (album_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_publisher(self, album_id: int, publisher_name: str) -> None:
        """Set the publisher for an album (Replace existing)."""
        if not publisher_name or not publisher_name.strip():
             # Handle Unsetting
             with self.get_connection() as conn:
                 conn.execute("DELETE FROM AlbumPublishers WHERE AlbumID = ?", (album_id,))
             return
             
        pub_name = publisher_name.strip()
        with self.get_connection() as conn:
            # Ensure Publisher exists
            conn.execute("INSERT OR IGNORE INTO Publishers (PublisherName) VALUES (?)", (pub_name,))
            # Get ID
            cursor = conn.execute("SELECT PublisherID FROM Publishers WHERE PublisherName = ?", (pub_name,))
            pub_row = cursor.fetchone()
            if not pub_row: return
            pub_id = pub_row[0]
            
            # Link to Album (Replace old)
            conn.execute("DELETE FROM AlbumPublishers WHERE AlbumID = ?", (album_id,))
            conn.execute("INSERT INTO AlbumPublishers (AlbumID, PublisherID) VALUES (?, ?)", (album_id, pub_id))


