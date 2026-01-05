"""
Tag Service

Handles business logic for Genres and Custom Tags.
"""
from typing import List, Optional, Tuple, Dict, Any
from ...data.repositories.tag_repository import TagRepository

class TagService:
    """Service for managing tags and category hierarchies."""
    
    def __init__(self, tag_repository: Optional[TagRepository] = None):
        self._repo = tag_repository or TagRepository()


    def get_distinct_categories(self) -> List[str]:
        """Fetch all used categories."""
        return self._repo.get_distinct_categories()

    def get_all_tags(self) -> List[Any]:
        """Get all tags."""
        return self._repo.get_all_tags()

    def get_all_by_category(self, category: str) -> List[Any]:
        """Get all tags in a specific category."""
        return self._repo.get_all_by_category(category)

    def get_tags_for_song(self, song_id: int) -> List[Any]:
        """Get all tags linked to a song."""
        return self._repo.get_tags_for_source(song_id)

    def set_tags(self, song_id: int, tags: List[str], category: str) -> bool:
        """Update tags for a song by category (Replaces existing)."""
        try:
            self._repo.remove_all_tags_from_source(song_id, category)
            for t_name in tags:
                self._repo.add_tag_to_source(song_id, t_name, category)
            return True
        except Exception:
            return False
        
    def rename_tag(self, old_name: str, new_name: str, category: str) -> bool:
        """Global rename of a tag across all songs."""
        tag = self._repo.find_by_name(old_name, category)
        if not tag: return False
        
        tag.tag_name = new_name
        return self._repo.update(tag)

    def is_unprocessed(self, song_id: int) -> bool:
        """Check if a song has the 'Status:Unprocessed' tag."""
        return self._repo.is_unprocessed(song_id)

    def set_unprocessed(self, song_id: int, unprocessed: bool) -> bool:
        """Set the 'Status:Unprocessed' state for a song."""
        return self._repo.set_unprocessed(song_id, unprocessed)

    def get_or_create(self, name: str, category: Optional[str] = None) -> Tuple[Any, bool]:
        """Find or create a tag."""
        return self._repo.get_or_create(name, category)

    def get_by_id(self, tag_id: int) -> Optional[Any]:
        """Fetch a tag by ID."""
        return self._repo.get_by_id(tag_id)

    def find_by_name(self, name: str, category: Optional[str] = None) -> Optional[Any]:
        """Find a tag by name."""
        return self._repo.find_by_name(name, category)

    def count_sources_for_tag(self, tag_id: int) -> int:
        """Count songs using this tag."""
        return self._repo.count_sources_for_tag(tag_id)

    def add_tag_to_source(self, source_id: int, tag_id: Any, category: Optional[str] = None) -> bool:
        """Link tag to song."""
        return self._repo.add_tag_to_source(source_id, tag_id, category)

    def remove_tag_from_source(self, source_id: int, tag_id: int) -> bool:
        """Unlink tag from song."""
        return self._repo.remove_tag_from_source(source_id, tag_id)

    def remove_all_tags_from_source(self, source_id: int, category: Optional[str] = None) -> bool:
        """Clear tags for a song."""
        return self._repo.remove_all_tags_from_source(source_id, category)

    def merge_tags(self, source_id: int, target_id: int) -> bool:
        """Merge two tags."""
        return self._repo.merge_tags(source_id, target_id)

    def update(self, tag: Any) -> bool:
        """Update tag metadata."""
        return self._repo.update(tag)

    def get_tags_for_source(self, source_id: int, category: Optional[str] = None) -> List[Any]:
        """Get tags for a song."""
        return self._repo.get_tags_for_source(source_id, category)

    def get_active_tags(self) -> Dict[str, List[str]]:
        """Get all currently used tags grouped by category."""
        return self._repo.get_active_tags()

