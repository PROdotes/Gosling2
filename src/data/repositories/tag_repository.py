from typing import Optional, List, Tuple, Any
from src.data.database import BaseRepository
from src.data.models.tag import Tag

class TagRepository(BaseRepository):
    """Repository for Tag (Genre/Category) management."""

    def get_by_id(self, tag_id: int) -> Optional[Tag]:
        """Retrieve tag by ID."""
        query = "SELECT TagID, TagName, TagCategory FROM Tags WHERE TagID = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (tag_id,))
            row = cursor.fetchone()
            if row:
                return Tag.from_row(row)
        return None

    def find_by_name(self, name: str, category: Optional[str] = None) -> Optional[Tag]:
        """
        Retrieve tag by exact name and category.
        If category is None, it matches where Category IS NULL.
        """
        if category:
            query = "SELECT TagID, TagName, TagCategory FROM Tags WHERE TagName = ? COLLATE NOCASE AND TagCategory = ?"
            params = (name, category)
        else:
            query = "SELECT TagID, TagName, TagCategory FROM Tags WHERE TagName = ? COLLATE NOCASE AND TagCategory IS NULL"
            params = (name,)
            
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            if row:
                return Tag.from_row(row)
        return None

    def update(self, tag: Tag) -> bool:
        """Update an existing tag."""
        query = "UPDATE Tags SET TagName = ?, TagCategory = ? WHERE TagID = ?"
        with self.get_connection() as conn:
            conn.execute(query, (tag.tag_name, tag.category, tag.tag_id))
        return True

    def create(self, name: str, category: Optional[str] = None) -> Tag:
        """Create a new tag with automatic sentence casing."""
        # T-83: Auto-format to Sentence Case (e.g., "pop" -> "Pop")
        formatted_name = name.strip()
        if formatted_name:
            formatted_name = formatted_name[0].upper() + formatted_name[1:]
        
        query = "INSERT INTO Tags (TagName, TagCategory) VALUES (?, ?)"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (formatted_name, category))
            tag_id = cursor.lastrowid
            
        return Tag(tag_id=tag_id, tag_name=formatted_name, category=category)

    def get_or_create(self, name: str, category: Optional[str] = None) -> Tuple[Tag, bool]:
        """
        Find existing tag or create new one.
        Returns (Tag, created).
        """
        existing = self.find_by_name(name, category)
        if existing:
            return existing, False
        
        return self.create(name, category), True

    def add_tag_to_source(self, source_id: int, tag_id: Any, category: Optional[str] = None) -> None:
        """
        Link a tag to a source item (song).
        If tag_id is a string, it's treated as a TagName and will be resolved/created
        within the optional category.
        """
        if isinstance(tag_id, str):
            tag_obj, _ = self.get_or_create(tag_id, category)
            tag_id = tag_obj.tag_id

        query = "INSERT OR IGNORE INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)"
        with self.get_connection() as conn:
            conn.execute(query, (source_id, tag_id))

    def remove_tag_from_source(self, source_id: int, tag_id: int) -> None:
        """Unlink a tag from a source item."""
        query = "DELETE FROM MediaSourceTags WHERE SourceID = ? AND TagID = ?"
        with self.get_connection() as conn:
            conn.execute(query, (source_id, tag_id))
            
    def remove_all_tags_from_source(self, source_id: int, category: Optional[str] = None) -> None:
        """
        Unlink all tags from a source.
        Optionally filter by category (e.g., clear only Genres).
        """
        if category:
            query = """
                DELETE FROM MediaSourceTags 
                WHERE SourceID = ? 
                AND TagID IN (SELECT TagID FROM Tags WHERE TagCategory = ?)
            """
            params = (source_id, category)
        else:
            query = "DELETE FROM MediaSourceTags WHERE SourceID = ?"
            params = (source_id,)
            
        with self.get_connection() as conn:
            conn.execute(query, params)

    def get_tags_for_source(self, source_id: int, category: Optional[str] = None) -> List[Tag]:
        """Get all tags associated with a source item."""
        if category:
            query = """
                SELECT t.TagID, t.TagName, t.TagCategory
                FROM Tags t
                JOIN MediaSourceTags mst ON t.TagID = mst.TagID
                WHERE mst.SourceID = ? AND t.TagCategory = ?
            """
            params = (source_id, category)
        else:
            query = """
                SELECT t.TagID, t.TagName, t.TagCategory
                FROM Tags t
                JOIN MediaSourceTags mst ON t.TagID = mst.TagID
                WHERE mst.SourceID = ?
            """
            params = (source_id,)
            
        tags = []
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            for row in cursor.fetchall():
                tags.append(Tag.from_row(row))
        return tags
    
    def get_all_by_category(self, category: str) -> List[Tag]:
        """Get all distinct tags of a certain category."""
        query = "SELECT TagID, TagName, TagCategory FROM Tags WHERE TagCategory = ? ORDER BY TagName"
        tags = []
        with self.get_connection() as conn:
            cursor = conn.execute(query, (category,))
            for row in cursor.fetchall():
                tags.append(Tag.from_row(row))
        return tags

    def is_unprocessed(self, source_id: int) -> bool:
        """
        Check if a source has the 'Status:Unprocessed' tag.
        This is THE source of truth for workflow status.
        Returns True if unprocessed, False if ready/done.
        """
        query = """
            SELECT 1 FROM MediaSourceTags mst
            JOIN Tags t ON mst.TagID = t.TagID
            WHERE mst.SourceID = ? AND t.TagCategory = 'Status' AND t.TagName = 'Unprocessed'
            LIMIT 1
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, (source_id,))
            return cursor.fetchone() is not None

    def set_unprocessed(self, source_id: int, unprocessed: bool) -> None:
        """
        Set the unprocessed state for a source.
        unprocessed=True → adds the tag
        unprocessed=False → removes the tag (permission granted)
        """
        if unprocessed:
            self.add_tag_to_source(source_id, "Unprocessed", category="Status")
        else:
            # Find and remove the tag
            tag = self.find_by_name("Unprocessed", "Status")
            if tag:
                self.remove_tag_from_source(source_id, tag.tag_id)
