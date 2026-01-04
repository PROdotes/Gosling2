from typing import Optional, List, Tuple
import sqlite3
from src.data.database import BaseRepository
from src.data.models.publisher import Publisher
from .generic_repository import GenericRepository

class PublisherRepository(GenericRepository[Publisher]):
    """
    Repository for Publisher management.
    Inherits GenericRepository for automatic Audit Logging.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path, "Publishers", "publisher_id")

    def get_by_id(self, publisher_id: int) -> Optional[Publisher]:
        """Retrieve publisher by ID."""
        query = "SELECT PublisherID, PublisherName, ParentPublisherID FROM Publishers WHERE PublisherID = ?"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (publisher_id,))
            row = cursor.fetchone()
            if row:
                return Publisher.from_row(row)
        return None

    def find_by_name(self, name: str) -> Optional[Publisher]:
        """Retrieve publisher by exact name match."""
        query = "SELECT PublisherID, PublisherName, ParentPublisherID FROM Publishers WHERE PublisherName = ? COLLATE NOCASE"
        with self.get_connection() as conn:
            cursor = conn.execute(query, (name,))
            row = cursor.fetchone()
            if row:
                return Publisher.from_row(row)
        return None

    def _insert_db(self, cursor: sqlite3.Cursor, publisher: Publisher) -> int:
        """Execute SQL INSERT for GenericRepository"""
        cursor.execute(
            "INSERT INTO Publishers (PublisherName, ParentPublisherID) VALUES (?, ?)",
            (publisher.publisher_name, publisher.parent_publisher_id)
        )
        return cursor.lastrowid

    def _update_db(self, cursor: sqlite3.Cursor, publisher: Publisher) -> None:
        """Execute SQL UPDATE for GenericRepository"""
        cursor.execute(
            "UPDATE Publishers SET PublisherName = ?, ParentPublisherID = ? WHERE PublisherID = ?", 
            (publisher.publisher_name, publisher.parent_publisher_id, publisher.publisher_id)
        )

    def _delete_db(self, cursor: sqlite3.Cursor, record_id: int) -> None:
        """Execute SQL DELETE for GenericRepository"""
        cursor.execute("DELETE FROM AlbumPublishers WHERE PublisherID = ?", (record_id,))
        cursor.execute("DELETE FROM Publishers WHERE PublisherID = ?", (record_id,))

    def create(self, name: str, parent_id: Optional[int] = None) -> Publisher:
        """
        Create a new publisher.
        Uses GenericRepository.insert() for Audit Logging.
        """
        pub = Publisher(publisher_id=None, publisher_name=name, parent_publisher_id=parent_id)
        new_id = self.insert(pub)
        if new_id:
            pub.publisher_id = new_id
            return pub
        raise Exception("Failed to insert publisher")

    def get_or_create(self, name: str) -> Tuple[Publisher, bool]:
        """
        Find an existing publisher by name or create a new one.
        Returns (Publisher, created).
        """
        existing = self.find_by_name(name)
        if existing:
            return existing, False
        
        return self.create(name), True

    def add_publisher_to_album(self, album_id: int, publisher_id: int) -> None:
        """Link a publisher to an album."""
        query = """
            INSERT OR IGNORE INTO AlbumPublishers (AlbumID, PublisherID)
            VALUES (?, ?)
        """
        with self.get_connection() as conn:
            conn.execute(query, (album_id, publisher_id))

    def remove_publisher_from_album(self, album_id: int, publisher_id: int) -> None:
        """Unlink a publisher from an album."""
        query = "DELETE FROM AlbumPublishers WHERE AlbumID = ? AND PublisherID = ?"
        with self.get_connection() as conn:
            conn.execute(query, (album_id, publisher_id))

    def get_publishers_for_album(self, album_id: int) -> List[Publisher]:
        """Get all publishers associated with an album."""
        query = """
            SELECT p.PublisherID, p.PublisherName, p.ParentPublisherID
            FROM Publishers p
            JOIN AlbumPublishers ap ON p.PublisherID = ap.PublisherID
            WHERE ap.AlbumID = ?
        """
        publishers = []
        with self.get_connection() as conn:
            cursor = conn.execute(query, (album_id,))
            for row in cursor.fetchall():
                publishers.append(Publisher.from_row(row))
        return publishers

    def search(self, query: str = "") -> List[Publisher]:
        """Search for publishers by name."""
        sql = "SELECT PublisherID, PublisherName, ParentPublisherID FROM Publishers"
        params = []
        if query:
            sql += " WHERE PublisherName LIKE ?"
            params.append(f"%{query}%")
        
        sql += " ORDER BY PublisherName ASC"
        
        publishers = []
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            for row in cursor.fetchall():
                publishers.append(Publisher.from_row(row))
        return publishers





    def get_with_descendants(self, publisher_id: int) -> List[Publisher]:
        """
        Get a publisher and all its descendants (children, grandchildren, etc.).
        Uses recursive CTE for hierarchical queries.
        Useful for filtering: "Show all songs from EMI and its sub-labels".
        """
        query = """
            WITH RECURSIVE descendants AS (
                -- Base: the starting publisher
                SELECT PublisherID, PublisherName, ParentPublisherID
                FROM Publishers
                WHERE PublisherID = ?
                
                UNION ALL
                
                -- Recursive: children of current set
                SELECT p.PublisherID, p.PublisherName, p.ParentPublisherID
                FROM Publishers p
                INNER JOIN descendants d ON p.ParentPublisherID = d.PublisherID
            )
            SELECT PublisherID, PublisherName, ParentPublisherID FROM descendants
        """
        publishers = []
        with self.get_connection() as conn:
            cursor = conn.execute(query, (publisher_id,))
            for row in cursor.fetchall():
                publishers.append(Publisher.from_row(row))
        return publishers

    def get_album_count(self, publisher_id: int) -> int:
        """Count how many albums use this publisher."""
        query = "SELECT COUNT(*) FROM AlbumPublishers WHERE PublisherID = ?"
        with self.get_connection() as conn:
            return conn.execute(query, (publisher_id,)).fetchone()[0]

    def get_child_count(self, publisher_id: int) -> int:
        """Count direct subsidiaries."""
        query = "SELECT COUNT(*) FROM Publishers WHERE ParentPublisherID = ?"
        with self.get_connection() as conn:
            return conn.execute(query, (publisher_id,)).fetchone()[0]
