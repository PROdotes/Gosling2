"""Base Repository with database operations"""
import sqlite3
from typing import Optional
from contextlib import contextmanager
from .database_config import DatabaseConfig


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

            # 1. Types (Lookup)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Types (
                    TypeID INTEGER PRIMARY KEY,
                    TypeName TEXT NOT NULL UNIQUE
                )
            """)
            
            # Insert default types
            default_types = ["Song", "Jingle", "Commercial", "VoiceTrack", "Recording", "Stream"]
            cursor.executemany(
                "INSERT OR IGNORE INTO Types (TypeName) VALUES (?)",
                [(t,) for t in default_types]
            )

            # 2. MediaSources (Base Table)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS MediaSources (
                    SourceID INTEGER PRIMARY KEY,
                    TypeID INTEGER NOT NULL,
                    Name TEXT NOT NULL,
                    Notes TEXT,
                    Source TEXT NOT NULL UNIQUE,
                    Duration REAL,
                    IsActive BOOLEAN DEFAULT 1,
                    FOREIGN KEY (TypeID) REFERENCES Types(TypeID)
                )
            """)

            # 3. Songs (Extension Table)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Songs (
                    SourceID INTEGER PRIMARY KEY,
                    TempoBPM INTEGER,
                    RecordingYear INTEGER,
                    ISRC TEXT,
                    Groups TEXT,
                    IsDone BOOLEAN DEFAULT 0,
                    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE
                )
            """)

            # 4. Contributors
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Contributors (
                    ContributorID INTEGER PRIMARY KEY,
                    ContributorName TEXT NOT NULL UNIQUE,
                    SortName TEXT,
                    Type TEXT CHECK(Type IN ('person', 'group'))
                )
            """)

            # 5. Roles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Roles (
                    RoleID INTEGER PRIMARY KEY,
                    RoleName TEXT NOT NULL UNIQUE
                )
            """)

            # Insert default roles
            default_roles = ["Performer", "Composer", "Lyricist", "Producer"]
            cursor.executemany(
                "INSERT OR IGNORE INTO Roles (RoleName) VALUES (?)",
                [(r,) for r in default_roles]
            )

            # 6. MediaSourceContributorRoles (Junction)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS MediaSourceContributorRoles (
                    SourceID INTEGER NOT NULL,
                    ContributorID INTEGER NOT NULL,
                    RoleID INTEGER NOT NULL,
                    PRIMARY KEY (SourceID, ContributorID, RoleID),
                    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE,
                    FOREIGN KEY (ContributorID) REFERENCES Contributors(ContributorID) ON DELETE CASCADE,
                    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID)
                )
            """)

            # 7. GroupMembers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS GroupMembers (
                    GroupID INTEGER NOT NULL,
                    MemberID INTEGER NOT NULL,
                    PRIMARY KEY (GroupID, MemberID),
                    FOREIGN KEY (GroupID) REFERENCES Contributors(ContributorID),
                    FOREIGN KEY (MemberID) REFERENCES Contributors(ContributorID)
                )
            """)

            # 8. ContributorAliases
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ContributorAliases (
                    AliasID INTEGER PRIMARY KEY,
                    ContributorID INTEGER NOT NULL,
                    AliasName TEXT NOT NULL,
                    FOREIGN KEY (ContributorID) REFERENCES Contributors(ContributorID) ON DELETE CASCADE
                )
            """)

            # 23. Albums
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Albums (
                    AlbumID INTEGER PRIMARY KEY,
                    Title TEXT NOT NULL,
                    AlbumType TEXT,
                    ReleaseYear INTEGER
                )
            """)

            # 24. SongAlbums (Junction)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SongAlbums (
                    SourceID INTEGER NOT NULL,
                    AlbumID INTEGER NOT NULL,
                    TrackNumber INTEGER,
                    PRIMARY KEY (SourceID, AlbumID),
                    FOREIGN KEY (SourceID) REFERENCES Songs(SourceID) ON DELETE CASCADE,
                    FOREIGN KEY (AlbumID) REFERENCES Albums(AlbumID) ON DELETE CASCADE
                )
            """)

            # 22. Publishers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Publishers (
                    PublisherID INTEGER PRIMARY KEY,
                    PublisherName TEXT NOT NULL UNIQUE,
                    ParentPublisherID INTEGER,
                    FOREIGN KEY (ParentPublisherID) REFERENCES Publishers(PublisherID)
                )
            """)

            # 25. AlbumPublishers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS AlbumPublishers (
                    AlbumID INTEGER NOT NULL,
                    PublisherID INTEGER NOT NULL,
                    PRIMARY KEY (AlbumID, PublisherID),
                    FOREIGN KEY (AlbumID) REFERENCES Albums(AlbumID) ON DELETE CASCADE,
                    FOREIGN KEY (PublisherID) REFERENCES Publishers(PublisherID) ON DELETE CASCADE
                )
            """)

            # 9. Tags
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Tags (
                    TagID INTEGER PRIMARY KEY,
                    TagName TEXT NOT NULL,
                    Category TEXT,
                    UNIQUE(TagName, Category)
                )
            """)

            # 10. MediaSourceTags
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS MediaSourceTags (
                    SourceID INTEGER NOT NULL,
                    TagID INTEGER NOT NULL,
                    PRIMARY KEY (SourceID, TagID),
                    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE,
                    FOREIGN KEY (TagID) REFERENCES Tags(TagID) ON DELETE CASCADE
                )
            """)





