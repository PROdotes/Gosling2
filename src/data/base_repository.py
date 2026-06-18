import sqlite3
import uuid
from contextlib import contextmanager


class BaseRepository:
    """
    The connection owner for all v3core repositories.
    All concrete repositories inherit from this.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _open_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.create_collation(
            "UTF8_NOCASE",
            lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
        )
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """
        Public connection factory for service layer.
        Service layer uses this to create connections for write transactions.
        """
        conn = self._open_connection()

        # Tripwire: any committed NULL batch_id rows mean a write path bypassed
        # write_connection() and called conn.commit() directly. Catches it on
        # the next open so nothing silently escapes the audit log.
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM ChangeLog WHERE batch_id IS NULL"
            ).fetchone()[0]
        except sqlite3.OperationalError:
            count = 0  # ChangeLog table not yet created (pre-migration DB)
        if count > 0:
            raise RuntimeError(
                f"Audit integrity violation: {count} ChangeLog rows committed with "
                f"NULL batch_id. A write path bypassed write_connection(). Fix before continuing."
            )

        return conn

    @contextmanager
    def write_connection(self, label: str):
        """
        Context manager for write transactions. Flushes audit batch and commits
        on success; rolls back on any exception. Use instead of get_connection()
        for all paths that modify the database.
        """
        batch_id = str(uuid.uuid4())
        conn = self.get_connection()
        try:
            yield conn
            conn.execute(
                "UPDATE ChangeLog SET batch_id = ?, batch_label = ? WHERE batch_id IS NULL",
                (batch_id, label),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Internal connection factory for repository read methods."""
        return self._open_connection()
