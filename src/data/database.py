"""Base Repository with database operations"""
import sqlite3
from typing import Optional, Any
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
        
        # T-Fix: Add Unicode-aware search/collation (SQLite's NOCASE and LOWER are ASCII-only)
        # 1. Function for use in queries like py_lower(Name)
        conn.create_function("py_lower", 1, lambda x: x.lower() if x is not None else None)
        
        # 2. Collation for use in Table Definitions (COLLATE UTF8_NOCASE)
        def unicode_compare(s1, s2):
            l1, l2 = s1.lower(), s2.lower()
            if l1 < l2: return -1
            if l1 > l2: return 1
            return 0
        conn.create_collation("UTF8_NOCASE", unicode_compare)
        
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def log_action(self, action_type: str, target_table: str = None, target_id: int = None, details: Any = None, batch_id: str = None) -> None:
        """Log a high-level systemic or user action."""
        from src.core.audit_logger import AuditLogger
        with self.get_connection() as conn:
            AuditLogger(conn, batch_id=batch_id).log_action(action_type, target_table, target_id, details)

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
                    ProcessingStatus INTEGER DEFAULT 1,
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

            # 4. Identities (The Real Person/Group)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Identities (
                    IdentityID INTEGER PRIMARY KEY,
                    IdentityType TEXT CHECK(IdentityType IN ('person', 'group', 'placeholder')) NOT NULL,
                    LegalName TEXT,
                    DateOfBirth DATE,
                    DateOfDeath DATE,
                    Nationality TEXT,
                    FormationDate DATE,
                    DisbandDate DATE,
                    Biography TEXT,
                    Notes TEXT
                )
            """)

            # 5. ArtistNames (Names Owned by Identities)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ArtistNames (
                    NameID INTEGER PRIMARY KEY,
                    OwnerIdentityID INTEGER,
                    DisplayName TEXT NOT NULL,
                    SortName TEXT,
                    IsPrimaryName BOOLEAN DEFAULT 0,
                    DisambiguationNote TEXT,
                    FOREIGN KEY (OwnerIdentityID) REFERENCES Identities(IdentityID) ON DELETE SET NULL,
                    UNIQUE(DisplayName COLLATE UTF8_NOCASE)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_artistnames_owner ON ArtistNames(OwnerIdentityID)")
            # Upgrade existing index to UNIQUE and Unicode-aware
            cursor.execute("DROP INDEX IF EXISTS idx_artistnames_display")
            cursor.execute("DROP INDEX IF EXISTS idx_artistnames_display_unique")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_artistnames_display_v2 ON ArtistNames(DisplayName COLLATE UTF8_NOCASE)")

            # 6. GroupMemberships (Links persons to groups)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS GroupMemberships (
                    MembershipID INTEGER PRIMARY KEY,
                    GroupIdentityID INTEGER NOT NULL,
                    MemberIdentityID INTEGER NOT NULL,
                    CreditedAsNameID INTEGER,
                    JoinDate DATE,
                    LeaveDate DATE,
                    FOREIGN KEY (GroupIdentityID) REFERENCES Identities(IdentityID) ON DELETE CASCADE,
                    FOREIGN KEY (MemberIdentityID) REFERENCES Identities(IdentityID) ON DELETE CASCADE,
                    FOREIGN KEY (CreditedAsNameID) REFERENCES ArtistNames(NameID) ON DELETE SET NULL,
                    UNIQUE(GroupIdentityID, MemberIdentityID)
                )
            """)

            # 7. SongCredits (Immutable credits on songs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SongCredits (
                    CreditID INTEGER PRIMARY KEY,
                    SourceID INTEGER NOT NULL,
                    CreditedNameID INTEGER NOT NULL,
                    RoleID INTEGER NOT NULL,
                    CreditPosition INTEGER DEFAULT 0,
                    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE,
                    FOREIGN KEY (CreditedNameID) REFERENCES ArtistNames(NameID),
                    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID),
                    UNIQUE(SourceID, CreditedNameID, RoleID)
                )
            """)

            # 8. AlbumCredits (Immutable credits on albums)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS AlbumCredits (
                    CreditID INTEGER PRIMARY KEY,
                    AlbumID INTEGER NOT NULL,
                    CreditedNameID INTEGER NOT NULL,
                    RoleID INTEGER NOT NULL,
                    FOREIGN KEY (AlbumID) REFERENCES Albums(AlbumID) ON DELETE CASCADE,
                    FOREIGN KEY (CreditedNameID) REFERENCES ArtistNames(NameID),
                    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID),
                    UNIQUE(AlbumID, CreditedNameID, RoleID)
                )
            """)

            # Insert default identities
            cursor.execute("INSERT OR IGNORE INTO Identities (IdentityID, IdentityType, LegalName) VALUES (0, 'placeholder', 'Unknown Artist')")
            cursor.execute("INSERT OR IGNORE INTO Identities (IdentityID, IdentityType, LegalName) VALUES (-1, 'placeholder', 'Various Artists')")
            cursor.execute("INSERT OR IGNORE INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (0, 0, 'Unknown Artist', 1)")
            cursor.execute("INSERT OR IGNORE INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (-1, -1, 'Various Artists', 1)")

            # 4. Contributors (LEGACY)
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
                    MemberAliasID INTEGER,
                    PRIMARY KEY (GroupID, MemberID),
                    FOREIGN KEY (GroupID) REFERENCES Contributors(ContributorID),
                    FOREIGN KEY (MemberID) REFERENCES Contributors(ContributorID),
                    FOREIGN KEY (MemberAliasID) REFERENCES ContributorAliases(AliasID) ON DELETE SET NULL
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
                    AlbumType TEXT,
                    ReleaseYear INTEGER
                )
            """)
            # T-Fix: Add unique constraint to Albums (Title + Year)
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_albums_title_year_v2 ON Albums(AlbumTitle COLLATE UTF8_NOCASE, ReleaseYear)")

            # 31. AlbumContributors (Junction)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS AlbumContributors (
                    AlbumID INTEGER NOT NULL,
                    ContributorID INTEGER NOT NULL,
                    RoleID INTEGER NOT NULL,
                    PRIMARY KEY (AlbumID, ContributorID, RoleID),
                    FOREIGN KEY (AlbumID) REFERENCES Albums(AlbumID) ON DELETE CASCADE,
                    FOREIGN KEY (ContributorID) REFERENCES Contributors(ContributorID) ON DELETE CASCADE,
                    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID)
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
                    PublisherName TEXT NOT NULL,
                    ParentPublisherID INTEGER,
                    FOREIGN KEY (ParentPublisherID) REFERENCES Publishers(PublisherID),
                    UNIQUE(PublisherName COLLATE UTF8_NOCASE)
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
                    UNIQUE(TagName COLLATE UTF8_NOCASE, TagCategory COLLATE UTF8_NOCASE)
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

            # 17. ChangeLog (Audit)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ChangeLog (
                    LogID INTEGER PRIMARY KEY AUTOINCREMENT,
                    LogTableName TEXT NOT NULL,
                    RecordID INTEGER NOT NULL,
                    LogFieldName TEXT NOT NULL,
                    OldValue TEXT,
                    NewValue TEXT,
                    LogTimestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    BatchID TEXT
                )
            """)

            # 18. DeletedRecords (Audit)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS DeletedRecords (
                    DeleteID INTEGER PRIMARY KEY AUTOINCREMENT,
                    DeletedFromTable TEXT NOT NULL,
                    RecordID INTEGER NOT NULL,
                    FullSnapshot TEXT NOT NULL,
                    DeletedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                    RestoredAt DATETIME,
                    BatchID TEXT
                )
            """)

            # 20. ActionLog (Audit)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ActionLog (
                    ActionID INTEGER PRIMARY KEY AUTOINCREMENT,
                    ActionLogType TEXT NOT NULL,
                    TargetTable TEXT,
                    ActionTargetID INTEGER,
                    ActionDetails TEXT,
                    ActionTimestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UserID TEXT,
                    BatchID TEXT
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
            
            # GroupMembers Migrations (MemberAliasID)
            cursor.execute("PRAGMA table_info(GroupMembers)")
            gm_cols = [row[1] for row in cursor.fetchall()]
            if 'MemberAliasID' not in gm_cols:
                cursor.execute("ALTER TABLE GroupMembers ADD COLUMN MemberAliasID INTEGER REFERENCES ContributorAliases(AliasID) ON DELETE SET NULL")

            # Create indexes for duplicate detection and performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mediasources_audiohash ON MediaSources(AudioHash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_isrc ON Songs(ISRC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_songs_year ON Songs(RecordingYear)")
            
            # Reverse lookup indexes for junction tables
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_songalbums_albumid ON SongAlbums(AlbumID)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mscr_contributorid ON MediaSourceContributorRoles(ContributorID)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mscr_roleid ON MediaSourceContributorRoles(RoleID)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_albumcontributor_albumid ON AlbumContributors(AlbumID)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_category ON Tags(TagCategory)")

            # ProcessingStatus Migration (Workflow Redesign)
            cursor.execute("PRAGMA table_info(MediaSources)")
            ms_cols_v2 = [row[1] for row in cursor.fetchall()]
            if 'ProcessingStatus' not in ms_cols_v2:
                # 1. Add Column (Default 1 = Done)
                cursor.execute("ALTER TABLE MediaSources ADD COLUMN ProcessingStatus INTEGER DEFAULT 1")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mediasources_status ON MediaSources(ProcessingStatus)")
                
                # 2. Migrate Data: Find 'Unprocessed' tags and set Status=0
                cursor.execute("""
                    UPDATE MediaSources 
                    SET ProcessingStatus = 0 
                    WHERE SourceID IN (
                        SELECT MST.SourceID 
                        FROM MediaSourceTags MST
                        JOIN Tags T ON MST.TagID = T.TagID
                        WHERE T.TagCategory = 'Status' AND T.TagName = 'Unprocessed'
                    )
                """)
                
                # 3. Cleanup: Remove the specific 'Unprocessed' tag links
                # (We do this safely by subquery in case IDs shift)
                cursor.execute("""
                    DELETE FROM MediaSourceTags 
                    WHERE TagID IN (SELECT TagID FROM Tags WHERE TagCategory = 'Status' AND TagName = 'Unprocessed')
                """)
                
                # 4. Remove the Tag Definition
                cursor.execute("DELETE FROM Tags WHERE TagCategory = 'Status' AND TagName = 'Unprocessed'")




