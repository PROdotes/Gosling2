"""
Publisher Service

Handles business logic for Publisher management.
"""
from typing import List, Optional, Tuple
from ...data.models.publisher import Publisher
from ...data.repositories.publisher_repository import PublisherRepository

class PublisherService:
    """Service for managing publishers and their hierarchical relationships."""
    
    def __init__(self, publisher_repository: Optional[PublisherRepository] = None):
        self._repo = publisher_repository or PublisherRepository()

    def search(self, query: str = "") -> List[Publisher]:
        """Search for publishers by name or part of name."""
        return self._repo.search(query)

    def get_all(self) -> List[Publisher]:
        """Alias for search("") to support universal picker."""
        return self.search("")

    def get_by_id(self, publisher_id: int) -> Optional[Publisher]:
        """Fetch a specific publisher by its ID."""
        return self._repo.get_by_id(publisher_id)

    def get_for_song(self, song_id: int) -> List[Publisher]:
        """Fetch all publishers associated with a recording (song)."""
        return self._repo.get_publishers_for_song(song_id)

    def find_by_name(self, name: str) -> Optional[Publisher]:
        """Fetch a specific publisher by its exact name."""
        return self._repo.find_by_name(name)
    
    def get_by_name(self, name: str) -> Optional[Publisher]:
        """Alias for find_by_name to support EntityPickerDialog."""
        return self.find_by_name(name)

    def get_or_create(self, name: str, _type: str = None) -> Tuple[Publisher, bool]:
        """Find an existing publisher or create a new one."""
        return self._repo.get_or_create(name)

    def update(self, publisher: Publisher) -> bool:
        """
        Smart Update: Updates name/parent, or merges if the new name already exists.
        """
        if not publisher.publisher_id:
            return False
            
        current = self.get_by_id(publisher.publisher_id)
        if not current: 
            return False
            
        new_name = publisher.publisher_name.strip()
        
        # 1. Handle Name Change & Possible Merge
        # Check if ANOTHER publisher already has this name (case-insensitive)
        with self._repo.get_connection() as conn:
            query = "SELECT PublisherID FROM Publishers WHERE trim(PublisherName) = ? COLLATE UTF8_NOCASE AND PublisherID != ?"
            cursor = conn.execute(query, (new_name, publisher.publisher_id))
            collision = cursor.fetchone()
            
        if collision:
            # COLLISION: Merge our current record INTO the existing one
            return self.merge(source_id=publisher.publisher_id, target_id=collision[0])

        # 2. Safety Check: Prevent circular parent-child relationships
        if publisher.parent_publisher_id:
            if self.would_create_cycle(publisher.publisher_id, publisher.parent_publisher_id):
                return False
                
        return self._repo.update(publisher)

    def merge(self, source_id: int, target_id: int) -> bool:
        """Merge two publishers into one."""
        return self._repo.merge(source_id, target_id)

    def delete(self, publisher_id: int) -> bool:
        """Delete a publisher record."""
        return self._repo.delete(publisher_id)

    def add_publisher_to_song(self, song_id: int, publisher_id: int, batch_id: Optional[str] = None) -> bool:
        """Link a publisher to a recording (song)."""
        return self._repo.add_publisher_to_song(song_id, publisher_id, batch_id=batch_id)

    def remove_publisher_from_song(self, song_id: int, publisher_id: int, batch_id: Optional[str] = None) -> bool:
        """Unlink a publisher from a recording (song)."""
        return self._repo.remove_publisher_from_song(song_id, publisher_id, batch_id=batch_id)

    def get_usage_stats(self, publisher_id: int) -> dict:
        """Retrieve usage statistics (referenced albums, dependencies) for safety checks."""
        return {
            'album_count': self._repo.get_album_count(publisher_id),
            'child_count': self._repo.get_child_count(publisher_id)
        }

    def would_create_cycle(self, child_id: int, proposed_parent_id: Optional[int]) -> bool:
        """
        Detect if setting proposed_parent_id as the parent of child_id would create a circular loop.
        """
        if not proposed_parent_id:
            return False
            
        if proposed_parent_id == child_id:
            return True # Can't be your own parent
            
        # Walk up the chain from the proposed parent to see if we ever hit the child
        visited = {child_id}
        current_id = proposed_parent_id
        
        while current_id:
            if current_id in visited:
                return True
            visited.add(current_id)
            
            p = self._repo.get_by_id(current_id)
            if not p:
                break
            current_id = p.parent_publisher_id
            
        return False
    def get_with_descendants(self, publisher_id: int) -> List[Publisher]:
        """Fetch a publisher and all its recursive descendants."""
        return self._repo.get_with_descendants(publisher_id)

    # --- Inventory Management (T-Tools) ---

    def get_all_with_usage(self, orphans_only: bool = False) -> List[Tuple[Publisher, int]]:
        """
        Get all publishers with their usage counts.

        Args:
            orphans_only: If True, only return publishers with 0 usage.

        Returns:
            List of (Publisher, usage_count) tuples.
        """
        return self._repo.get_all_with_usage(orphans_only=orphans_only)

    def get_orphan_count(self) -> int:
        """Count publishers with zero usage."""
        return self._repo.get_orphan_count()

    def delete_all_orphans(self, batch_id: Optional[str] = None) -> int:
        """Delete all publishers with zero usage. Returns count deleted."""
        return self._repo.delete_all_orphans(batch_id=batch_id)

    def get_usage_count(self, publisher_id: int) -> int:
        """Get total usage count (albums + songs) for a publisher."""
        return self._repo.get_usage_count(publisher_id)
