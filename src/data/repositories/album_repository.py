from typing import Optional, List, Tuple
from src.data.database import BaseRepository
from src.data.models.album import Album

class AlbumRepository(BaseRepository):
    """Repository for Album management."""

    def get_by_id(self, album_id: int) -> Optional[Album]:
        """Retrieve album by ID."""
        query = "SELECT AlbumID, Title, AlbumArtist, AlbumType, ReleaseYear FROM Albums WHERE AlbumID = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (album_id,))
            row = cursor.fetchone()
            if row:
                return Album.from_row(row)
        return None

    def find_by_title(self, title: str) -> Optional[Album]:
        """Retrieve album by exact title match (case-insensitive)."""
        query = "SELECT AlbumID, Title, AlbumArtist, AlbumType, ReleaseYear FROM Albums WHERE Title = ? COLLATE NOCASE"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (title,))
            row = cursor.fetchone()
            if row:
                return Album.from_row(row)
        return None

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
        conditions = ["Title = ? COLLATE NOCASE"]
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
            SELECT AlbumID, Title, AlbumArtist, AlbumType, ReleaseYear 
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
                a.AlbumID, a.Title, a.AlbumArtist, a.AlbumType, a.ReleaseYear,
                COUNT(sa.SourceID) as SongCount
            FROM Albums a
            LEFT JOIN SongAlbums sa ON a.AlbumID = sa.AlbumID
            WHERE a.Title LIKE ? OR a.AlbumArtist LIKE ?
            GROUP BY a.AlbumID
            {having_clause}
            ORDER BY CASE WHEN a.Title LIKE ? THEN 1 ELSE 2 END, a.Title
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

    def set_publisher(self, album_id: int, publisher_name: str) -> None:
        """
        Link an album to a publisher (creating publisher if needed).
        Note: Currently assumes 1 publisher per album (clears previous).
        """
        if not publisher_name:
            return

        with self.get_connection() as conn:
            # 1. Get/Create Publisher ID
            cur = conn.execute("SELECT PublisherID FROM Publishers WHERE PublisherName = ?", (publisher_name,))
            row = cur.fetchone()
            if row:
                pub_id = row[0]
            else:
                cur = conn.execute("INSERT INTO Publishers (PublisherName) VALUES (?)", (publisher_name,))
                pub_id = cur.lastrowid
            
            # 2. Clear existing (M2M table but treated as 1-to-Maybe for now)
            conn.execute("DELETE FROM AlbumPublishers WHERE AlbumID = ?", (album_id,))
            
            # 3. Link
            conn.execute("INSERT INTO AlbumPublishers (AlbumID, PublisherID) VALUES (?, ?)", (album_id, pub_id))

    def create(
        self, 
        title: str, 
        album_artist: Optional[str] = None,
        album_type: str = 'Album', 
        release_year: Optional[int] = None
    ) -> Album:
        """Create a new album."""
        query = """
            INSERT INTO Albums (Title, AlbumArtist, AlbumType, ReleaseYear)
            VALUES (?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, (title, album_artist, album_type, release_year))
            album_id = cursor.lastrowid
            
        return Album(
            album_id=album_id, 
            title=title, 
            album_artist=album_artist,
            album_type=album_type, 
            release_year=release_year
        )

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

    def update(self, album: Album) -> bool:
        """Update an existing album's metadata (Title, AlbumArtist, Type, Year)."""
        if album.album_id is None:
            return False
        query = """
            UPDATE Albums
            SET Title = ?, AlbumArtist = ?, AlbumType = ?, ReleaseYear = ?
            WHERE AlbumID = ?
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, (
                    album.title, 
                    album.album_artist,
                    album.album_type, 
                    album.release_year, 
                    album.album_id
                ))
                return cursor.rowcount > 0
        except Exception as e:
            try:
                from src.core import logger
                logger.error(f"Error updating album: {e}")
            except ImportError:
                print(f"Error updating album (Logger unavailable): {e}")
            return False

    def add_song_to_album(self, source_id: int, album_id: int, track_number: Optional[int] = None) -> None:
        """Link a song to an album."""
        query = """
            INSERT OR IGNORE INTO SongAlbums (SourceID, AlbumID, TrackNumber)
            VALUES (?, ?, ?)
        """
        with self.get_connection() as conn:
            conn.execute(query, (source_id, album_id, track_number))

    def remove_song_from_album(self, source_id: int, album_id: int) -> None:
        """Unlink a song from an album."""
        query = "DELETE FROM SongAlbums WHERE SourceID = ? AND AlbumID = ?"
        with self.get_connection() as conn:
            conn.execute(query, (source_id, album_id))

    def get_albums_for_song(self, source_id: int) -> List[Album]:
        """Get all albums a song appears on."""
        query = """
            SELECT a.AlbumID, a.Title, a.AlbumArtist, a.AlbumType, a.ReleaseYear
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
            SELECT MS.Name, 
                   COALESCE(
                       (SELECT Group_Concat(C.ContributorName, ', ') 
                        FROM MediaSourceContributorRoles MSCR 
                        JOIN Contributors C ON MSCR.ContributorID = C.ContributorID
                        JOIN Roles R ON MSCR.RoleID = R.RoleID
                        WHERE MSCR.SourceID = MS.SourceID AND R.RoleName = 'Performer'
                       ), 
                       'Unknown'
                   ) as Artist
            FROM MediaSources MS
            JOIN SongAlbums SA ON MS.SourceID = SA.SourceID
            WHERE SA.AlbumID = ?
            ORDER BY SA.TrackNumber ASC, MS.Name ASC
        """
        songs = []
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, (album_id,))
                for row in cursor.fetchall():
                    songs.append({'title': row[0], 'artist': row[1]})
        except Exception as e:
            print(f"Error fetching album songs: {e}")
        return songs

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

    def delete_album(self, album_id: int) -> bool:
        """Delete an album by ID. Explicitly clears links to prevent orphaned data."""
        try:
            with self.get_connection() as conn:
                # 1. Clear links manually (in case cascade isn't configured in older DBs)
                conn.execute("DELETE FROM SongAlbums WHERE AlbumID = ?", (album_id,))
                # 2. Delete the album record
                cursor = conn.execute("DELETE FROM Albums WHERE AlbumID = ?", (album_id,))
                return cursor.rowcount > 0
        except Exception as e:
            from src.core import logger
            logger.error(f"Error deleting album {album_id}: {e}")
            return False

    def get_song_count(self, album_id: int) -> int:
        """Get number of songs in an album."""
        query = "SELECT COUNT(*) FROM SongAlbums WHERE AlbumID = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (album_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_publisher(self, album_id: int) -> Optional[str]:
        """Get the primary publisher name for an album."""
        query = """
            SELECT p.PublisherName 
            FROM Publishers p
            JOIN AlbumPublishers ap ON p.PublisherID = ap.PublisherID
            WHERE ap.AlbumID = ?
            LIMIT 1
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


