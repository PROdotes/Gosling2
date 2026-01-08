from typing import Optional, List, Tuple, Any
import sqlite3
from src.data.database import BaseRepository
from src.data.models.tag import Tag
from .generic_repository import GenericRepository

class TagRepository(GenericRepository[Tag]):
    """
    Repository for Tag (Genre/Category) management.
    Inherits GenericRepository for automatic Audit Logging.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path, "Tags", "tag_id")

    def get_by_id(self, tag_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Tag]:
        """Retrieve tag by ID."""
        query = "SELECT TagID, TagName, TagCategory FROM Tags WHERE TagID = ?"
        if conn:
            cursor = conn.execute(query, (tag_id,))
            row = cursor.fetchone()
            return Tag.from_row(row) if row else None

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

    def _insert_db(self, cursor: sqlite3.Cursor, tag: Tag, **kwargs) -> int:
        """Execute SQL INSERT for GenericRepository"""
        cursor.execute("INSERT INTO Tags (TagName, TagCategory) VALUES (?, ?)", (tag.tag_name, tag.category))
        return cursor.lastrowid

    def _update_db(self, cursor: sqlite3.Cursor, tag: Tag, **kwargs) -> None:
        """Execute SQL UPDATE for GenericRepository"""
        cursor.execute("UPDATE Tags SET TagName = ?, TagCategory = ? WHERE TagID = ?", 
                      (tag.tag_name, tag.category, tag.tag_id))

    def _delete_db(self, cursor: sqlite3.Cursor, record_id: int, **kwargs) -> None:
        """Execute SQL DELETE for GenericRepository"""
        auditor = kwargs.get('auditor')
        # Cleanup links first (Manual Cascade, Audited)
        if auditor:
            cursor.execute("SELECT SourceID FROM MediaSourceTags WHERE TagID = ?", (record_id,))
            for (s_id,) in cursor.fetchall():
                 auditor.log_delete("MediaSourceTags", f"{s_id}-{record_id}", {"SourceID": s_id, "TagID": record_id})

        cursor.execute("DELETE FROM MediaSourceTags WHERE TagID = ?", (record_id,))
        cursor.execute("DELETE FROM Tags WHERE TagID = ?", (record_id,))

    def create(self, name: str, category: Optional[str] = None) -> Tag:
        """
        Create a new tag with automatic sentence casing.
        Uses GenericRepository.insert() for Audit Logging.
        """
        # T-83: Auto-format to Sentence Case (e.g., "pop" -> "Pop")
        formatted_name = name.strip()
        if formatted_name:
            formatted_name = formatted_name[0].upper() + formatted_name[1:]
        
        tag = Tag(tag_id=None, tag_name=formatted_name, category=category)
        new_id = self.insert(tag)
        
        if new_id:
            tag.tag_id = new_id
            return tag
        else:
            raise Exception("Failed to insert tag")

    def get_or_create(self, name: str, category: Optional[str] = None) -> Tuple[Tag, bool]:
        """
        Find existing tag or create new one.
        Returns (Tag, created).
        """
        existing = self.find_by_name(name, category)
        if existing:
            return existing, False
        
        return self.create(name, category), True

    def add_tag_to_source(self, source_id: int, tag_id: Any, category: Optional[str] = None, batch_id: Optional[str] = None) -> bool:
        """
        Link a tag to a source item (song).
        Returns True on success.
        """
        if isinstance(tag_id, str):
            tag_obj, _ = self.get_or_create(tag_id, category)
            tag_id = tag_obj.tag_id

        from src.core.audit_logger import AuditLogger
        with self.get_connection() as conn:
            # Check if link already exists
            cur = conn.execute("SELECT 1 FROM MediaSourceTags WHERE SourceID = ? AND TagID = ?", (source_id, tag_id))
            if cur.fetchone(): return True

            conn.execute("INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)", (source_id, tag_id))
            AuditLogger(conn, batch_id=batch_id).log_insert("MediaSourceTags", f"{source_id}-{tag_id}", {
                "SourceID": source_id,
                "TagID": tag_id
            })
        return True

    def remove_tag_from_source(self, source_id: int, tag_id: int, batch_id: Optional[str] = None) -> bool:
        """Unlink a tag from a source item. Returns True on success."""
        from src.core.audit_logger import AuditLogger
        with self.get_connection() as conn:
            # Snapshot for audit
            cur = conn.execute("SELECT SourceID, TagID FROM MediaSourceTags WHERE SourceID = ? AND TagID = ?", (source_id, tag_id))
            row = cur.fetchone()
            if not row: return True
            snapshot = {"SourceID": row[0], "TagID": row[1]}

            conn.execute("DELETE FROM MediaSourceTags WHERE SourceID = ? AND TagID = ?", (source_id, tag_id))
            AuditLogger(conn, batch_id=batch_id).log_delete("MediaSourceTags", f"{source_id}-{tag_id}", snapshot)
        return True
            
    def remove_all_tags_from_source(self, source_id: int, category: Optional[str] = None, batch_id: Optional[str] = None) -> None:
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
            
        from src.core.audit_logger import AuditLogger
        with self.get_connection() as conn:
            auditor = AuditLogger(conn, batch_id=batch_id)
            # Find all tags being removed for auditing
            if category:
                cursor = conn.execute("SELECT SourceID, T.TagID FROM MediaSourceTags MT JOIN Tags T ON MT.TagID = T.TagID WHERE SourceID = ? AND TagCategory = ?", (source_id, category))
            else:
                cursor = conn.execute("SELECT SourceID, TagID FROM MediaSourceTags WHERE SourceID = ?", (source_id,))
            
            for row in cursor.fetchall():
                 auditor.log_delete("MediaSourceTags", f"{row[0]}-{row[1]}", {"SourceID": row[0], "TagID": row[1]})

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

    def get_all_tags(self) -> List[Tag]:
        """Retrieve all tags from the database."""
        query = "SELECT TagID, TagName, TagCategory FROM Tags ORDER BY TagName"
        tags = []
        with self.get_connection() as conn:
            cursor = conn.execute(query)
            for row in cursor.fetchall():
                tags.append(Tag.from_row(row))
        return tags

    def search(self, query: str) -> List[Tag]:
        """Search for tags by name (case-insensitive partial match)."""
        sql = "SELECT TagID, TagName, TagCategory FROM Tags WHERE TagName LIKE ? ORDER BY TagName"
        q = f"%{query}%"
        tags = []
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(sql, (q,))
                for row in cursor.fetchall():
                    tags.append(Tag.from_row(row))
        except Exception as e:
            from src.core import logger
            logger.error(f"Error searching tags: {e}")
        return tags

    def get_distinct_categories(self) -> List[str]:
        """Get all distinct tag categories that exist in the database."""
        query = "SELECT DISTINCT TagCategory FROM Tags WHERE TagCategory IS NOT NULL ORDER BY TagCategory"
        categories = []
        with self.get_connection() as conn:
            cursor = conn.execute(query)
            for row in cursor.fetchall():
                if row[0]:  # Skip NULL
                    categories.append(row[0])
        return categories

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

    def merge_tags(self, source_id: int, target_id: int, batch_id: Optional[str] = None) -> bool:
        """
        Merge source_id into target_id.
        1. Reassign all MediaSourceTags
        2. Delete source_id (Audited Manually)
        """
        try:
            from src.core.audit_logger import AuditLogger
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Snapshot for Audit (Deleted Tag)
                old_tag = self.get_by_id(source_id)
                old_snapshot = old_tag.to_dict() if old_tag else {}

                # Auditor for Batching
                auditor = AuditLogger(conn, batch_id=batch_id)

                # 1. Audit Migration: Find all links that will move
                cursor.execute("SELECT SourceID, TagID FROM MediaSourceTags WHERE TagID = ?", (source_id,))
                for s_id, t_id in cursor.fetchall():
                     # If target already exists, this is a delete
                     cursor.execute("SELECT 1 FROM MediaSourceTags WHERE SourceID = ? AND TagID = ?", (s_id, target_id))
                     if cursor.fetchone():
                          auditor.log_delete("MediaSourceTags", f"{s_id}-{source_id}", {"SourceID": s_id, "TagID": source_id})
                     else:
                          auditor.log_update("MediaSourceTags", f"{s_id}-{source_id}", {"TagID": source_id}, {"TagID": target_id})

                # Move tags (Deduplicate)
                cursor.execute("INSERT OR IGNORE INTO MediaSourceTags (SourceID, TagID) SELECT SourceID, ? FROM MediaSourceTags WHERE TagID = ?", (target_id, source_id))
                cursor.execute("DELETE FROM MediaSourceTags WHERE TagID = ?", (source_id,))
                
                # 3. Delete tag
                cursor.execute("DELETE FROM Tags WHERE TagID = ?", (source_id,))
                
                # 4. Log Audit
                auditor.log_delete("Tags", source_id, old_snapshot)
                
                auditor.log_action("MERGE_TAGS", "Tags", target_id, {"absorbed_id": source_id})
                
            return True
        except Exception as e:
            from src.core import logger
            logger.error(f"Merge error: {e}")
            return False

    def count_sources_for_tag(self, tag_id: int) -> int:
        """Count how many songs use this tag."""
        query = "SELECT COUNT(*) FROM MediaSourceTags WHERE TagID = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (tag_id,))
            result = cursor.fetchone()
            return result[0] if result else 0

    def get_active_tags(self) -> dict:
        """
        Get all tags that are currently linked to at least one active source.
        Returns: {Category: [TagName, ...]}
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT t.TagCategory, t.TagName
                    FROM Tags t
                    JOIN MediaSourceTags mst ON t.TagID = mst.TagID
                    JOIN MediaSources ms ON mst.SourceID = ms.SourceID
                    WHERE ms.IsActive = 1 AND t.TagCategory IS NOT NULL
                    ORDER BY t.TagCategory, t.TagName
                """)
                categories = {}
                for row in cursor.fetchall():
                    cat = row[0] or "Other"
                    tag_name = row[1]
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(tag_name)
                return categories
        except Exception as e:
            from src.core import logger
            logger.error(f"Error fetching active tags: {e}")
            return {}
