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
