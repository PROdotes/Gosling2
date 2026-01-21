"""
Album Service

Handles business logic for Album management.
"""
from typing import List, Optional, Tuple
from ...data.models.album import Album
from ...data.models.publisher import Publisher
from ...data.repositories.album_repository import AlbumRepository

class AlbumService:
    """Service for managing albums and their associated metadata."""
    
    def __init__(self, album_repository: Optional[AlbumRepository] = None):
        self._repo = album_repository or AlbumRepository()

    def search(self, query: str = "", limit: int = 100) -> List[dict]:
        """Fuzzy search for albums with song counts."""
        return self._repo.search(query, limit)

    def get_by_id(self, album_id: int) -> Optional[Album]:
        """Fetch a specific album by its ID."""
        return self._repo.get_by_id(album_id)

    def create(self, title: str, artist: Optional[str] = None, year: Optional[int] = None, album_type: Optional[str] = None) -> Album:
        """Create a new album record."""
        return self._repo.create(title, album_artist=artist, release_year=year, album_type=album_type)

    def get_or_create(self, title: str, artist: Optional[str] = None, year: Optional[int] = None, album_type: Optional[str] = None) -> Tuple[Album, bool]:
        """Find an existing album or create a new one."""
        return self._repo.get_or_create(title, album_artist=artist, release_year=year, album_type=album_type)

    def update(self, album: Album) -> bool:
        """
        Smart Update: Updates title/year, or merges if the new key already exists.
        """
        if not album.album_id:
            return False
            
        current = self.get_by_id(album.album_id)
        if not current:
            return False
            
        # 1. Check for collision
        # Note: comparison uses key (Title, Artist, Year)
        existing = self._repo.find_by_key(album.title, album.album_artist, album.release_year, exclude_id=album.album_id)
        if existing:
            # COLLISION: Merge our current record INTO the existing one
            return self.merge(source_id=album.album_id, target_id=existing.album_id)
                
        return self._repo.update(album)

    def merge(self, source_id: int, target_id: int) -> bool:
        """Merge two albums into one."""
        return self._repo.merge(source_id, target_id)

    def delete(self, album_id: int) -> bool:
        """Delete an album record."""
        return self._repo.delete(album_id)

    def assign_to_song(self, source_id: int, album_title: str, artist: Optional[str] = None, year: Optional[int] = None, album_type: Optional[str] = None) -> Album:
        """Link a song to an album by title, artist, and year."""
        return self._repo.assign_album(source_id, album_title, artist, year, album_type=album_type)

    def get_publisher_name(self, album_id: int) -> Optional[str]:
        """Get the publisher name(s) associated with an album."""
        return self._repo.get_publisher(album_id)

    def set_publisher(self, album_id: int, publisher_name: str) -> None:
        """Set or update the publisher for an album."""
        self._repo.set_publisher(album_id, publisher_name)

    def get_songs_in_album(self, album_id: int) -> List[dict]:
        """Retrieve a list of songs contained in an album."""
        return self._repo.get_songs_in_album(album_id)

    def get_publisher(self, album_id: int) -> Optional[str]:
        """Alias for get_publisher_name."""
        return self._repo.get_publisher(album_id)

    def remove_song_from_album(self, source_id: int, album_id: int) -> bool:
        """Unlink a song from an album."""
        return self._repo.remove_song_from_album(source_id, album_id)

    def get_publishers_for_album(self, album_id: int) -> List[Publisher]:
        """Fetch all publishers associated with an album."""
        return self._repo.get_publishers_for_album(album_id)

    def link_song_to_album(self, source_id: int, album_id: int, is_primary: int = 0) -> bool:
        """Link a song to an album."""
        # Fix: Method name in repo is 'add_song_to_album'
        self._repo.add_song_to_album(source_id, album_id)
        if is_primary:
             self._repo.set_primary_album(source_id, album_id)
        return True

    def get_albums_for_song(self, song_id: int) -> List[Album]:
        """Get all albums linked to a song."""
        return self._repo.get_albums_for_song(song_id)

    def set_primary_album(self, source_id: int, album_id: int) -> bool:
        """Set the primary album for a song."""
        return self._repo.set_primary_album(source_id, album_id)

    # ─────────────────────────────────────────────────────────────────
    # T-TOOLS INVENTORY METHODS (Phase 3)
    # ─────────────────────────────────────────────────────────────────

    def get_all_with_usage(self, orphans_only: bool = False) -> List[Tuple["Album", int]]:
        """
        Get all albums with their song count (usage).
        
        Args:
            orphans_only: If True, only return albums with 0 songs.
            
        Returns:
            List of (Album, usage_count) tuples.
        """
        return self._repo.get_all_with_usage(orphans_only=orphans_only)

    def get_orphan_count(self) -> int:
        """Get count of albums with no linked songs."""
        return self._repo.get_orphan_count()

    def delete_all_orphans(self, batch_id: Optional[str] = None) -> int:
        """
        Delete all albums with no linked songs.
        
        Returns:
            Number of albums deleted.
        """
        return self._repo.delete_all_orphans(batch_id=batch_id)

