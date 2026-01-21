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

    def search(self, query: str) -> List[Any]:
        """Search for tags."""
        return self._repo.search(query)

    def get_all(self) -> List[Any]:
        """Alias for get_all_tags to support universal picker."""
        return self.get_all_tags()

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
        """
        Global rename of a tag across all songs.
        If the new name exists in the same category, merges the tags.
        """
        tag = self._repo.find_by_name(old_name, category)
        if not tag: return False
        
        # T-83: Auto-format to Sentence Case
        new_name = new_name.strip()
        if new_name:
            new_name = new_name[0].upper() + new_name[1:]
            
        existing = self._repo.find_by_name(new_name, category, exclude_id=tag.tag_id)
        if existing:
            return self._repo.merge_tags(tag.tag_id, existing.tag_id)
            
        tag.tag_name = new_name
        return self._repo.update(tag)


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

    # --- Inventory Management (T-Tools) ---

    def get_all_with_usage(self, category: Optional[str] = None, orphans_only: bool = False) -> List[Tuple[Any, int]]:
        """
        Get all tags with their usage counts.

        Args:
            category: Filter by category. None = all.
            orphans_only: Only return tags with 0 usage.

        Returns:
            List of (Tag, usage_count) tuples.
        """
        return self._repo.get_all_with_usage(category=category, orphans_only=orphans_only)

    def get_orphan_count(self, category: Optional[str] = None) -> int:
        """Count tags with zero usage."""
        return self._repo.get_orphan_count(category=category)

    def delete_all_orphans(self, category: Optional[str] = None) -> int:
        """Delete all tags with zero usage. Returns count deleted."""
        return self._repo.delete_all_orphans(category=category)

    def delete_tag(self, tag_id: int) -> bool:
        """Delete a tag by ID (will also unlink from all songs)."""
        return self._repo.delete(tag_id)

