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
        """Context manager for database connections. Enables WAL mode for concurrent performance."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL") # Enable write-ahead logging
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
                    MediaName TEXT NOT NULL,
                    SourceNotes TEXT,
                    SourcePath TEXT NOT NULL UNIQUE,
                    SourceDuration REAL,
                    AudioHash TEXT,
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
                    SongGroups TEXT,
                    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE
                )
            """)

            # 4. Contributors
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Contributors (
                    ContributorID INTEGER PRIMARY KEY,
                    ContributorName TEXT NOT NULL UNIQUE,
                    SortName TEXT,
                    ContributorType TEXT CHECK(ContributorType IN ('person', 'group'))
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
                    CreditedAliasID INTEGER,
                    PRIMARY KEY (SourceID, ContributorID, RoleID),
                    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE,
                    FOREIGN KEY (ContributorID) REFERENCES Contributors(ContributorID) ON DELETE CASCADE,
                    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID),
                    FOREIGN KEY (CreditedAliasID) REFERENCES ContributorAliases(AliasID) ON DELETE SET NULL
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
                    AlbumTitle TEXT NOT NULL,
                    AlbumArtist TEXT,
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
                    DiscNumber INTEGER DEFAULT 1,
                    IsPrimary BOOLEAN DEFAULT 1,
                    TrackPublisherID INTEGER,
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

            # 26. RecordingPublishers (Master Owners)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS RecordingPublishers (
                    SourceID INTEGER NOT NULL,
                    PublisherID INTEGER NOT NULL,
                    PRIMARY KEY (SourceID, PublisherID),
                    FOREIGN KEY (SourceID) REFERENCES Songs(SourceID) ON DELETE CASCADE,
                    FOREIGN KEY (PublisherID) REFERENCES Publishers(PublisherID) ON DELETE CASCADE
                )
            """)

            # 9. Tags
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Tags (
                    TagID INTEGER PRIMARY KEY,
                    TagName TEXT NOT NULL,
                    TagCategory TEXT,
                    UNIQUE(TagName, TagCategory)
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


            # Schema Migrations (Add columns that might not exist in older databases)
            # Add AudioHash column to MediaSources if it doesn't exist
            cursor.execute("PRAGMA table_info(MediaSources)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'AudioHash' not in columns:
                cursor.execute("ALTER TABLE MediaSources ADD COLUMN AudioHash TEXT")

            # SongAlbums Migrations (DiscNumber, IsPrimary, TrackPublisherID)
            cursor.execute("PRAGMA table_info(SongAlbums)")
            sa_cols = [row[1] for row in cursor.fetchall()]
            if 'DiscNumber' not in sa_cols:
                cursor.execute("ALTER TABLE SongAlbums ADD COLUMN DiscNumber INTEGER DEFAULT 1")
            if 'IsPrimary' not in sa_cols:
                # If we are adding IsPrimary, existing links should be Primary? 
                # Yes, until we have logic to say otherwise.
                cursor.execute("ALTER TABLE SongAlbums ADD COLUMN IsPrimary BOOLEAN DEFAULT 1")
            if 'TrackPublisherID' not in sa_cols:
                cursor.execute("ALTER TABLE SongAlbums ADD COLUMN TrackPublisherID INTEGER")

            # MediaSourceContributorRoles Migrations (CreditedAliasID)
            cursor.execute("PRAGMA table_info(MediaSourceContributorRoles)")
            mscr_cols = [row[1] for row in cursor.fetchall()]
            if 'CreditedAliasID' not in mscr_cols:
                cursor.execute("ALTER TABLE MediaSourceContributorRoles ADD COLUMN CreditedAliasID INTEGER REFERENCES ContributorAliases(AliasID) ON DELETE SET NULL")
            
            # Create indexes for duplicate detection and performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mediasources_audiohash ON MediaSources(AudioHash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_isrc ON Songs(ISRC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_year ON Songs(RecordingYear)")
            
            # Reverse lookup indexes for junction tables
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_songalbums_albumid ON SongAlbums(AlbumID)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mscr_contributorid ON MediaSourceContributorRoles(ContributorID)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mscr_roleid ON MediaSourceContributorRoles(RoleID)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_category ON Tags(TagCategory)")




