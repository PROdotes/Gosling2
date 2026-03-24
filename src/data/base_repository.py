import sqlite3


class BaseRepository:
    """
    The connection owner and audit spine for all v3core repositories.
    All concrete repositories inherit from this.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        """
        Public connection factory for service layer.
        Service layer uses this to create connections for write transactions.
        """
        conn = sqlite3.connect(self.db_path)

        # 1. Enable foreign keys so ON DELETE CASCADE fires
        conn.execute("PRAGMA foreign_keys = ON")

        # 2. Ensure the unique index for AudioHash exists to prevent duplicates
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_mediasources_audiohash ON MediaSources(AudioHash)"
        )

        # 3. Register the custom collation from the physical DB
        conn.create_collation(
            "UTF8_NOCASE",
            lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
        )
        return conn

    def _get_connection(self) -> sqlite3.Connection:
        """Internal connection factory for repository read methods."""
        return self.get_connection()
