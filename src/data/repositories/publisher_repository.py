from typing import Optional, List, Tuple
from src.data.database import BaseRepository
from src.data.models.publisher import Publisher

class PublisherRepository(BaseRepository):
    """Repository for Publisher management."""

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

    def create(self, name: str, parent_id: Optional[int] = None) -> Publisher:
        """Create a new publisher."""
        query = """
            INSERT INTO Publishers (PublisherName, ParentPublisherID)
            VALUES (?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, (name, parent_id))
            publisher_id = cursor.lastrowid
            
        return Publisher(publisher_id=publisher_id, publisher_name=name, parent_publisher_id=parent_id)

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

    def update(self, publisher: Publisher) -> bool:
        """Update an existing publisher."""
        query = """
            UPDATE Publishers
            SET PublisherName = ?, ParentPublisherID = ?
            WHERE PublisherID = ?
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, (
                publisher.publisher_name,
                publisher.parent_publisher_id,
                publisher.publisher_id
            ))
            return cursor.rowcount > 0

    def delete(self, publisher_id: int) -> bool:
        """Delete a publisher from the database."""
        with self.get_connection() as conn:
            # Also clean up links
            conn.execute("DELETE FROM AlbumPublishers WHERE PublisherID = ?", (publisher_id,))
            cursor = conn.execute("DELETE FROM Publishers WHERE PublisherID = ?", (publisher_id,))
            return cursor.rowcount > 0

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
