from typing import Optional, List, Tuple
from src.data.database import BaseRepository
from src.data.models.album import Album

class AlbumRepository(BaseRepository):
    """Repository for Album management."""

    def get_by_id(self, album_id: int) -> Optional[Album]:
        """Retrieve album by ID."""
        query = "SELECT AlbumID, Title, AlbumType, ReleaseYear FROM Albums WHERE AlbumID = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (album_id,))
            row = cursor.fetchone()
            if row:
                return Album.from_row(row)
        return None

    def find_by_title(self, title: str) -> Optional[Album]:
        """Retrieve album by exact title match (case-insensitive usually depends on DB collation)."""
        query = "SELECT AlbumID, Title, AlbumType, ReleaseYear FROM Albums WHERE Title = ? COLLATE NOCASE"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (title,))
            row = cursor.fetchone()
            if row:
                return Album.from_row(row)
        return None

    def create(self, title: str, album_type: str = 'Album', release_year: Optional[int] = None) -> Album:
        """Create a new album."""
        query = """
            INSERT INTO Albums (Title, AlbumType, ReleaseYear)
            VALUES (?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, (title, album_type, release_year))
            album_id = cursor.lastrowid
            
        return Album(album_id=album_id, title=title, album_type=album_type, release_year=release_year)

    def get_or_create(self, title: str) -> Tuple[Album, bool]:
        """
        Find an existing album by title or create a new one.
        Returns (Album, created).
        """
        existing = self.find_by_title(title)
        if existing:
            return existing, False
        
        return self.create(title), True

    def update(self, album: Album) -> bool:
        """Update an existing album's metadata (Title, Type, Year)."""
        if album.album_id is None:
            return False
        query = """
            UPDATE Albums
            SET Title = ?, AlbumType = ?, ReleaseYear = ?
            WHERE AlbumID = ?
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, (album.title, album.album_type, album.release_year, album.album_id))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating album: {e}")
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
            SELECT a.AlbumID, a.Title, a.AlbumType, a.ReleaseYear
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
