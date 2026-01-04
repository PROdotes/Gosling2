"""
Song Service

Handles business logic for Songs.
"""
from typing import List, Optional, Tuple, Any
from ...data.models.song import Song
from ...data.repositories.song_repository import SongRepository

class SongService:
    """Service for managing song records and their associations."""
    
    def __init__(self, song_repository: Optional[SongRepository] = None):
        self._repo = song_repository or SongRepository()

    def get_by_id(self, song_id: int) -> Optional[Song]:
        """Fetch a song by its DB ID."""
        return self._repo.get_by_id(song_id)

    def get_by_path(self, path: str) -> Optional[Song]:
        """Fetch a song by its file path."""
        return self._repo.get_by_path(path)

    def search(self, query: str) -> Tuple[List[str], List[Tuple]]:
        """Generic library search."""
        return self._repo.search(query)

    def get_all(self) -> Tuple[List[str], List[Tuple]]:
        """Fetch all songs in the library."""
        return self._repo.get_all()

    def update(self, song: Song) -> bool:
        """Update song metadata."""
        return self._repo.update(song)

    def delete(self, song_id: int) -> bool:
        """Delete a song record."""
        return self._repo.delete(song_id)

    def update_status(self, song_id: int, is_done: bool) -> bool:
        """Update the 'Done' status of a song."""
        return self._repo.update_status(song_id, is_done)

    def get_songs_by_ids(self, song_ids: List[int]) -> List[Song]:
        """Bulk fetch songs."""
        return self._repo.get_songs_by_ids(song_ids)

    def get_distinct_values(self, field_name: str) -> List[Any]:
        """Get unique values for filtering (Years, Genres, etc)."""
        return self._repo.get_distinct_values(field_name)

    def log_action(self, action_type: str, target_table: str = None, target_id: int = None, details: Any = None) -> None:
        """Log a high-level action via the repository."""
        self._repo.log_action(action_type, target_table, target_id, details)
