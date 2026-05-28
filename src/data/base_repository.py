import sqlite3


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

        # Audit integrity tripwire: detect any write path that committed without
        # calling flush_batch. NULL rows here mean triggers fired but batch_id was
        # never filled in — points directly at a missing flush_batch call.
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM ChangeLog WHERE batch_id IS NULL"
            ).fetchone()[0]
        except sqlite3.OperationalError:
            count = 0  # ChangeLog table not yet created (pre-migration DB)
        if count > 0:
            raise RuntimeError(
                f"Audit integrity violation: {count} ChangeLog rows committed with "
                f"NULL batch_id. A write path is missing flush_batch(). Fix before continuing."
            )

        return conn

    def _get_connection(self) -> sqlite3.Connection:
        """Internal connection factory for repository read methods."""
        return self._open_connection()
