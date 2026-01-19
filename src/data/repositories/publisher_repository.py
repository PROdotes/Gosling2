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

    def get_by_id(self, publisher_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Publisher]:
        """Retrieve publisher by ID."""
        query = "SELECT PublisherID, PublisherName, ParentPublisherID FROM Publishers WHERE PublisherID = ?"
        if conn:
            cursor = conn.execute(query, (publisher_id,))
            row = cursor.fetchone()
            return Publisher.from_row(row) if row else None
            
        with self.get_connection() as conn:
            cursor = conn.execute(query, (publisher_id,))
            row = cursor.fetchone()
            if row:
                return Publisher.from_row(row)
        return None



    def _insert_db(self, cursor: sqlite3.Cursor, publisher: Publisher, **kwargs) -> int:
        """Execute SQL INSERT for GenericRepository"""
        cursor.execute(
            "INSERT INTO Publishers (PublisherName, ParentPublisherID) VALUES (?, ?)",
            (publisher.publisher_name, publisher.parent_publisher_id)
        )
        return cursor.lastrowid

    def _update_db(self, cursor: sqlite3.Cursor, publisher: Publisher, **kwargs) -> None:
        """Execute SQL UPDATE for GenericRepository"""
        cursor.execute(
            "UPDATE Publishers SET PublisherName = ?, ParentPublisherID = ? WHERE PublisherID = ?", 
            (publisher.publisher_name, publisher.parent_publisher_id, publisher.publisher_id)
        )

    def _delete_db(self, cursor: sqlite3.Cursor, record_id: int, **kwargs) -> None:
        """Execute SQL DELETE for GenericRepository"""
        auditor = kwargs.get('auditor')
        # Audit link removals
        if auditor:
            cursor.execute("SELECT AlbumID FROM AlbumPublishers WHERE PublisherID = ?", (record_id,))
            for (a_id,) in cursor.fetchall():
                 auditor.log_delete("AlbumPublishers", f"{a_id}-{record_id}", {"AlbumID": a_id, "PublisherID": record_id})
            
            cursor.execute("SELECT SourceID FROM RecordingPublishers WHERE PublisherID = ?", (record_id,))
            for (s_id,) in cursor.fetchall():
                 auditor.log_delete("RecordingPublishers", f"{s_id}-{record_id}", {"SourceID": s_id, "PublisherID": record_id})

        cursor.execute("DELETE FROM AlbumPublishers WHERE PublisherID = ?", (record_id,))
        cursor.execute("DELETE FROM RecordingPublishers WHERE PublisherID = ?", (record_id,))
        cursor.execute("DELETE FROM Publishers WHERE PublisherID = ?", (record_id,))

    def create(self, name: str, parent_id: Optional[int] = None, conn: Optional[sqlite3.Connection] = None) -> Publisher:
        """
        Create a new publisher.
        Uses GenericRepository.insert() for Audit Logging.
        """
        # T-Fix: Always trim whitespace to prevent duplicates
        pub = Publisher(publisher_id=None, publisher_name=name.strip(), parent_publisher_id=parent_id)
        new_id = self.insert(pub, conn=conn)
        if new_id:
            pub.publisher_id = new_id
            return pub
        raise Exception("Failed to insert publisher")

    def get_or_create(self, name: str, conn: Optional[sqlite3.Connection] = None) -> Tuple[Publisher, bool]:
        """
        Find an existing publisher by name or create a new one.
        Returns (Publisher, created).
        """
        existing = self.find_by_name(name, conn=conn)
        if existing:
            return existing, False
        
        return self.create(name, conn=conn), True

    def find_by_name(self, name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Publisher]:
        """
        Retrieve publisher by name match.
        T-Fix: Use resilient whitespace/case matching as the single source of truth.
        """
        if not name: return None
        
        # Combined Logic: Trim + Unicode NOCASE
        query = "SELECT PublisherID, PublisherName, ParentPublisherID FROM Publishers WHERE trim(PublisherName) = ? COLLATE UTF8_NOCASE"
        
        def _execute(target_conn):
            cursor = target_conn.execute(query, (name.strip(),))
            row = cursor.fetchone()
            if row:
                return Publisher.from_row(row)
            return None

        if conn:
            return _execute(conn)
        with self.get_connection() as main_conn:
            return _execute(main_conn)

    def merge(self, source_id: int, target_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Merge source publisher into target publisher.
        Moves all album and song links, and child publishers to the target.
        """
        from src.core.audit_logger import AuditLogger
        
        def _execute(target_conn):
            auditor = AuditLogger(target_conn)
            
            # 1. Update AlbumPublishers
            # We use INSERT OR IGNORE and then DELETE to handle potential primary key conflicts
            target_conn.execute("""
                INSERT OR IGNORE INTO AlbumPublishers (AlbumID, PublisherID)
                SELECT AlbumID, ? FROM AlbumPublishers WHERE PublisherID = ?
            """, (target_id, source_id))
            target_conn.execute("DELETE FROM AlbumPublishers WHERE PublisherID = ?", (source_id,))
            
            # 2. Update RecordingPublishers
            target_conn.execute("""
                INSERT OR IGNORE INTO RecordingPublishers (SourceID, PublisherID)
                SELECT SourceID, ? FROM RecordingPublishers WHERE PublisherID = ?
            """, (target_id, source_id))
            target_conn.execute("DELETE FROM RecordingPublishers WHERE PublisherID = ?", (source_id,))
            
            # 3. Update Child Publishers
            target_conn.execute("UPDATE Publishers SET ParentPublisherID = ? WHERE ParentPublisherID = ?", (target_id, source_id))
            
            # 4. Delete Source
            target_conn.execute("DELETE FROM Publishers WHERE PublisherID = ?", (source_id,))
            
            return True

        if conn:
            return _execute(conn)
        with self.get_connection() as conn:
            success = _execute(conn)
            if success:
                conn.commit()
            return success

    def add_publisher_to_album(self, album_id: int, publisher_id: int, batch_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> bool:
        """Link a publisher ID to an album."""
        from src.core.audit_logger import AuditLogger
        
        sql = "INSERT OR IGNORE INTO AlbumPublishers (AlbumID, PublisherID) VALUES (?, ?)"
        
        if conn:
            cursor = conn.execute(sql, (album_id, publisher_id))
            if cursor.rowcount > 0:
                AuditLogger(conn, batch_id=batch_id).log_insert("AlbumPublishers", f"{album_id}-{publisher_id}", {
                    "AlbumID": album_id,
                    "PublisherID": publisher_id
                })
            return True

        with self.get_connection() as conn:
            cursor = conn.execute(sql, (album_id, publisher_id))
            if cursor.rowcount > 0:
                AuditLogger(conn, batch_id=batch_id).log_insert("AlbumPublishers", f"{album_id}-{publisher_id}", {
                    "AlbumID": album_id,
                    "PublisherID": publisher_id
                })
            return True

    def add_publisher_to_album_by_name(self, album_id: int, publisher_name: str, batch_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> bool:
        """Link a publisher by name to an album (auto-creates publisher if needed)."""
        if not publisher_name: 
            return False
            
        # 1. Get or create publisher
        publisher, _ = self.get_or_create(publisher_name, conn=conn)
        
        # 2. Link
        return self.add_publisher_to_album(album_id, publisher.publisher_id, batch_id=batch_id, conn=conn)

    def remove_publisher_from_album(self, album_id: int, publisher_id: int, batch_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> bool:
        """Unlink a publisher from an album."""
        from src.core.audit_logger import AuditLogger
        
        def _execute(target_conn):
            # Snapshot for audit
            query = "SELECT AlbumID, PublisherID FROM AlbumPublishers WHERE AlbumID = ? AND PublisherID = ?"
            cursor = target_conn.execute(query, (album_id, publisher_id))
            row = cursor.fetchone()
            if not row: return False
            
            snapshot = {"AlbumID": row[0], "PublisherID": row[1]}
            target_conn.execute("DELETE FROM AlbumPublishers WHERE AlbumID = ? AND PublisherID = ?", (album_id, publisher_id))
            AuditLogger(target_conn, batch_id=batch_id).log_delete("AlbumPublishers", f"{album_id}-{publisher_id}", snapshot)
            return True

        if conn:
            return _execute(conn)
        with self.get_connection() as conn:
            return _execute(conn)

    def add_publisher_to_song(self, song_id: int, publisher_id: int, batch_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> bool:
        """Link a publisher ID to a recording (song)."""
        from src.core.audit_logger import AuditLogger
        
        sql = "INSERT OR IGNORE INTO RecordingPublishers (SourceID, PublisherID) VALUES (?, ?)"
        
        def _execute(target_conn):
            cursor = target_conn.execute(sql, (song_id, publisher_id))
            if cursor.rowcount > 0:
                AuditLogger(target_conn, batch_id=batch_id).log_insert("RecordingPublishers", f"{song_id}-{publisher_id}", {
                    "SourceID": song_id,
                    "PublisherID": publisher_id
                })
            return True

        if conn:
            return _execute(conn)
        with self.get_connection() as conn:
            return _execute(conn)

    def remove_publisher_from_song(self, song_id: int, publisher_id: int, batch_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> bool:
        """Unlink a publisher from a recording (song)."""
        from src.core.audit_logger import AuditLogger
        
        def _execute(target_conn):
            # Snapshot for audit
            query = "SELECT SourceID, PublisherID FROM RecordingPublishers WHERE SourceID = ? AND PublisherID = ?"
            cursor = target_conn.execute(query, (song_id, publisher_id))
            row = cursor.fetchone()
            if not row: return False
            
            snapshot = {"SourceID": row[0], "PublisherID": row[1]}
            target_conn.execute("DELETE FROM RecordingPublishers WHERE SourceID = ? AND PublisherID = ?", (song_id, publisher_id))
            AuditLogger(target_conn, batch_id=batch_id).log_delete("RecordingPublishers", f"{song_id}-{publisher_id}", snapshot)
            return True

        if conn:
            return _execute(conn)
        with self.get_connection() as conn:
            return _execute(conn)

    def get_publishers_for_song(self, song_id: int, conn: Optional[sqlite3.Connection] = None) -> List[Publisher]:
        """Get all publishers associated with a recording (song)."""
        query = """
            SELECT p.PublisherID, p.PublisherName, p.ParentPublisherID
            FROM Publishers p
            JOIN RecordingPublishers rp ON p.PublisherID = rp.PublisherID
            WHERE rp.SourceID = ?
        """
        
        def _execute(target_conn):
            cursor = target_conn.execute(query, (song_id,))
            return [Publisher.from_row(row) for row in cursor.fetchall()]

        if conn:
            return _execute(conn)
        with self.get_connection() as conn:
            return _execute(conn)

    def get_publishers_for_album(self, album_id: int, conn: Optional[sqlite3.Connection] = None) -> List[Publisher]:
        """Get all publishers associated with an album."""
        query = """
            SELECT p.PublisherID, p.PublisherName, p.ParentPublisherID
            FROM Publishers p
            JOIN AlbumPublishers ap ON p.PublisherID = ap.PublisherID
            WHERE ap.AlbumID = ?
        """
        
        def _execute(target_conn):
            cursor = target_conn.execute(query, (album_id,))
            return [Publisher.from_row(row) for row in cursor.fetchall()]

        if conn:
            return _execute(conn)
        with self.get_connection() as conn:
            return _execute(conn)

    def get_joined_names(self, album_id: int, separator: str = "|||", conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
        """Get all publisher names linked to an album, joined by a separator."""
        query = """
            SELECT GROUP_CONCAT(p.PublisherName, ?)
            FROM Publishers p
            JOIN AlbumPublishers ap ON p.PublisherID = ap.PublisherID
            WHERE ap.AlbumID = ?
        """
        if conn:
            row = conn.execute(query, (separator, album_id)).fetchone()
            return row[0] if row else None
            
        with self.get_connection() as conn:
            row = conn.execute(query, (separator, album_id)).fetchone()
            return row[0] if row else None

    def set_primary_publisher(self, album_id: int, publisher_name: str, batch_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> None:
        """
        Set the primary publisher for an album, replacing all existing links.
        """
        from src.core.audit_logger import AuditLogger
        
        def _execute(target_conn):
            auditor = AuditLogger(target_conn, batch_id=batch_id)
            
            # 1. Handle Unsetting
            if not publisher_name or not publisher_name.strip():
                existing = self.get_publishers_for_album(album_id, conn=target_conn)
                for p in existing:
                    auditor.log_delete("AlbumPublishers", f"{album_id}-{p.publisher_id}", {"AlbumID": album_id, "PublisherID": p.publisher_id})
                target_conn.execute("DELETE FROM AlbumPublishers WHERE AlbumID = ?", (album_id,))
                return
             
            pub_name = publisher_name.strip()
            # 2. Get or create target publisher
            publisher, _ = self.get_or_create(pub_name, conn=target_conn)
            pub_id = publisher.publisher_id
            
            # 3. Snapshot for deletions
            existing = self.get_publishers_for_album(album_id, conn=target_conn)
            for p in existing:
                 if p.publisher_id == pub_id: continue 
                 auditor.log_delete("AlbumPublishers", f"{album_id}-{p.publisher_id}", {"AlbumID": album_id, "PublisherID": p.publisher_id})
            
            # 4. Update
            target_conn.execute("DELETE FROM AlbumPublishers WHERE AlbumID = ? AND PublisherID != ?", (album_id, pub_id))
            
            # 5. Link if not present
            cursor = target_conn.execute("SELECT 1 FROM AlbumPublishers WHERE AlbumID = ? AND PublisherID = ?", (album_id, pub_id))
            if not cursor.fetchone():
                target_conn.execute("INSERT INTO AlbumPublishers (AlbumID, PublisherID) VALUES (?, ?)", (album_id, pub_id))
                auditor.log_insert("AlbumPublishers", f"{album_id}-{pub_id}", {"AlbumID": album_id, "PublisherID": pub_id})

        if conn:
            _execute(conn)
        else:
            with self.get_connection() as conn:
                _execute(conn)

    def sync_publishers(self, album_id: int, publisher_names: List[str], batch_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> None:
        """
        Synchronize album publishers to match the provided list exactly.
        """
        from src.core.audit_logger import AuditLogger
        
        def _execute(target_conn):
            auditor = AuditLogger(target_conn, batch_id=batch_id)
            current_pubs = self.get_publishers_for_album(album_id, conn=target_conn)
            current_map = {p.publisher_name.lower(): p.publisher_id for p in current_pubs}
            
            target_names = {name.strip() for name in publisher_names if name and name.strip()}
            target_names_lower = {n.lower() for n in target_names}
            
            # 1. Remove items not in target
            for name_lower, pub_id in current_map.items():
                if name_lower not in target_names_lower:
                    auditor.log_delete("AlbumPublishers", f"{album_id}-{pub_id}", {"AlbumID": album_id, "PublisherID": pub_id})
                    target_conn.execute("DELETE FROM AlbumPublishers WHERE AlbumID = ? AND PublisherID = ?", (album_id, pub_id))
            
            # 2. Add new items
            for name in target_names:
                if name.lower() not in current_map:
                    self.add_publisher_to_album_by_name(album_id, name, batch_id=batch_id, conn=target_conn)

        if conn:
            _execute(conn)
        else:
            with self.get_connection() as conn:
                _execute(conn)

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
