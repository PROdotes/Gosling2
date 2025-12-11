"""Base Repository with database operations"""
import sqlite3
from typing import Optional
from contextlib import contextmanager
from ..database_config import DatabaseConfig


class BaseRepository:
    """Base repository with database connection management"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DatabaseConfig.get_database_path()
        self._ensure_schema()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        """Create database schema if it doesn't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create Files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Files (
                    FileID INTEGER PRIMARY KEY,
                    Path TEXT NOT NULL UNIQUE,
                    Title TEXT NOT NULL,
                    Duration REAL,
                    TempoBPM INTEGER
                )
            """)

            # Create Contributors table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Contributors (
                    ContributorID INTEGER PRIMARY KEY,
                    Name TEXT NOT NULL UNIQUE,
                    SortName TEXT
                )
            """)

            # Create Roles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Roles (
                    RoleID INTEGER PRIMARY KEY,
                    Name TEXT NOT NULL UNIQUE
                )
            """)

            # Insert default roles
            default_roles = ["Performer", "Composer", "Lyricist", "Producer"]
            cursor.executemany(
                "INSERT OR IGNORE INTO Roles (Name) VALUES (?)",
                [(r,) for r in default_roles]
            )

            # Create FileContributorRoles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS FileContributorRoles (
                    FileID INTEGER NOT NULL,
                    ContributorID INTEGER NOT NULL,
                    RoleID INTEGER NOT NULL,
                    PRIMARY KEY (FileID, ContributorID, RoleID),
                    FOREIGN KEY (FileID) REFERENCES Files(FileID) ON DELETE CASCADE,
                    FOREIGN KEY (ContributorID) REFERENCES Contributors(ContributorID) ON DELETE CASCADE,
                    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID)
                )
            """)

            # Create GroupMembers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS GroupMembers (
                    GroupID INTEGER NOT NULL,
                    MemberID INTEGER NOT NULL,
                    PRIMARY KEY (GroupID, MemberID),
                    FOREIGN KEY (GroupID) REFERENCES Contributors(ContributorID),
                    FOREIGN KEY (MemberID) REFERENCES Contributors(ContributorID)
                )
            """)

