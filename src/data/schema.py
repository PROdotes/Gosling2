import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS Types (
    TypeID INTEGER PRIMARY KEY,
    TypeName TEXT NOT NULL,
    UNIQUE(TypeName COLLATE UTF8_NOCASE)
);

CREATE TABLE IF NOT EXISTS MediaSources (
    SourceID INTEGER PRIMARY KEY,
    TypeID INTEGER NOT NULL,
    MediaName TEXT NOT NULL,
    MediaName_Search TEXT,
    SourceNotes TEXT,
    SourcePath TEXT UNIQUE,
    SourceDuration REAL,
    AudioHash TEXT UNIQUE,
    IsActive BOOLEAN DEFAULT 0,
    ProcessingStatus INTEGER,  -- NULL = Pending/Unseen by engine
    IsDeleted BOOLEAN DEFAULT 0,
    FOREIGN KEY (TypeID) REFERENCES Types(TypeID)
);

CREATE TABLE IF NOT EXISTS Songs (
    SourceID INTEGER PRIMARY KEY,
    TempoBPM INTEGER,
    RecordingYear INTEGER,
    ISRC TEXT,
    SongGroups TEXT,
    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Identities (
    IdentityID INTEGER PRIMARY KEY,
    IdentityType TEXT NOT NULL,
    LegalName TEXT,
    IsDeleted BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ArtistNames (
    NameID INTEGER PRIMARY KEY,
    OwnerIdentityID INTEGER,
    DisplayName TEXT NOT NULL,
    DisplayName_Search TEXT,
    IsPrimaryName BOOLEAN DEFAULT 0,
    IsDeleted BOOLEAN DEFAULT 0,
    FOREIGN KEY (OwnerIdentityID) REFERENCES Identities(IdentityID),
    UNIQUE(DisplayName COLLATE UTF8_NOCASE)
);

CREATE TABLE IF NOT EXISTS GroupMemberships (
    MembershipID INTEGER PRIMARY KEY,
    GroupIdentityID INTEGER NOT NULL,
    MemberIdentityID INTEGER NOT NULL,
    FOREIGN KEY (GroupIdentityID) REFERENCES Identities(IdentityID),
    FOREIGN KEY (MemberIdentityID) REFERENCES Identities(IdentityID)
);

CREATE TABLE IF NOT EXISTS Roles (
    RoleID INTEGER PRIMARY KEY,
    RoleName TEXT NOT NULL,
    UNIQUE(RoleName COLLATE UTF8_NOCASE)
);

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
);

CREATE TABLE IF NOT EXISTS Albums (
    AlbumID INTEGER PRIMARY KEY,
    AlbumTitle TEXT NOT NULL,
    AlbumTitle_Search TEXT,
    AlbumType TEXT,
    ReleaseYear INTEGER,
    IsDeleted BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS SongAlbums (
    SourceID INTEGER NOT NULL,
    AlbumID INTEGER NOT NULL,
    TrackNumber INTEGER,
    DiscNumber INTEGER DEFAULT 1,
    IsPrimary BOOLEAN DEFAULT 1,
    PRIMARY KEY (SourceID, AlbumID),
    FOREIGN KEY (SourceID) REFERENCES Songs(SourceID) ON DELETE CASCADE,
    FOREIGN KEY (AlbumID) REFERENCES Albums(AlbumID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Publishers (
    PublisherID INTEGER PRIMARY KEY,
    PublisherName TEXT NOT NULL,
    ParentPublisherID INTEGER,
    IsDeleted BOOLEAN DEFAULT 0,
    FOREIGN KEY (ParentPublisherID) REFERENCES Publishers(PublisherID),
    UNIQUE(PublisherName COLLATE UTF8_NOCASE)
);

CREATE TABLE IF NOT EXISTS AlbumPublishers (
    AlbumID INTEGER NOT NULL,
    PublisherID INTEGER NOT NULL,
    PRIMARY KEY (AlbumID, PublisherID),
    FOREIGN KEY (AlbumID) REFERENCES Albums(AlbumID) ON DELETE CASCADE,
    FOREIGN KEY (PublisherID) REFERENCES Publishers(PublisherID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS RecordingPublishers (
    SourceID INTEGER NOT NULL,
    PublisherID INTEGER NOT NULL,
    PRIMARY KEY (SourceID, PublisherID),
    FOREIGN KEY (SourceID) REFERENCES Songs(SourceID) ON DELETE CASCADE,
    FOREIGN KEY (PublisherID) REFERENCES Publishers(PublisherID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS AlbumCredits (
    CreditID INTEGER PRIMARY KEY,
    AlbumID INTEGER NOT NULL,
    CreditedNameID INTEGER NOT NULL,
    RoleID INTEGER NOT NULL,
    FOREIGN KEY (AlbumID) REFERENCES Albums(AlbumID) ON DELETE CASCADE,
    FOREIGN KEY (CreditedNameID) REFERENCES ArtistNames(NameID),
    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID),
    UNIQUE(AlbumID, CreditedNameID, RoleID)
);

CREATE TABLE IF NOT EXISTS Tags (
    TagID INTEGER PRIMARY KEY,
    TagName TEXT NOT NULL,
    TagCategory TEXT,
    IsDeleted BOOLEAN DEFAULT 0,
    UNIQUE(TagName COLLATE UTF8_NOCASE, TagCategory COLLATE UTF8_NOCASE)
);

CREATE TABLE IF NOT EXISTS MediaSourceTags (
    SourceID INTEGER NOT NULL,
    TagID INTEGER NOT NULL,
    IsPrimary BOOLEAN DEFAULT 0,
    PRIMARY KEY (SourceID, TagID),
    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE,
    FOREIGN KEY (TagID) REFERENCES Tags(TagID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS StagingOrigins (
    SourceID INTEGER PRIMARY KEY,
    OriginPath TEXT NOT NULL,
    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ChangeLog (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id    TEXT,
    batch_label TEXT,
    changed_at  TEXT NOT NULL DEFAULT (datetime('now')),
    table_name  TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    field_name  TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT
);
"""

# Tables excluded from audit triggers. Everything else is audited.
EXCLUDED_FROM_AUDIT = {"ChangeLog", "StagingOrigins"}


def build_trigger_sql(conn: sqlite3.Connection) -> str:
    """Generate CREATE TRIGGER IF NOT EXISTS SQL for every non-excluded table,
    derived live from PRAGMA table_info so triggers always match the real schema."""
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        if row[0] not in EXCLUDED_FROM_AUDIT
    ]

    parts = []
    for table in tables:
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        if not cols:
            continue

        ins = "\n    ".join(
            f"INSERT INTO ChangeLog (table_name, entity_id, field_name, old_value, new_value) "
            f"VALUES ('{table}', NEW.rowid, '{c}', NULL, NULLIF(CAST(NEW.{c} AS TEXT), ''));"
            for c in cols
        )
        upd = "\n    ".join(
            f"INSERT INTO ChangeLog (table_name, entity_id, field_name, old_value, new_value) "
            f"SELECT '{table}', NEW.rowid, '{c}', "
            f"NULLIF(CAST(OLD.{c} AS TEXT), ''), NULLIF(CAST(NEW.{c} AS TEXT), '') "
            f"WHERE OLD.{c} IS NOT NEW.{c};"
            for c in cols
        )
        dlt = "\n    ".join(
            f"INSERT INTO ChangeLog (table_name, entity_id, field_name, old_value, new_value) "
            f"VALUES ('{table}', OLD.rowid, '{c}', NULLIF(CAST(OLD.{c} AS TEXT), ''), NULL);"
            for c in cols
        )
        parts += [
            f"CREATE TRIGGER IF NOT EXISTS trg_{table}_INSERT\n"
            f"AFTER INSERT ON {table} FOR EACH ROW\nBEGIN\n    {ins}\nEND",
            f"CREATE TRIGGER IF NOT EXISTS trg_{table}_UPDATE\n"
            f"AFTER UPDATE ON {table} FOR EACH ROW\nBEGIN\n    {upd}\nEND",
            f"CREATE TRIGGER IF NOT EXISTS trg_{table}_DELETE\n"
            f"AFTER DELETE ON {table} FOR EACH ROW\nBEGIN\n    {dlt}\nEND",
        ]

    return ";\n\n".join(parts) + ";"
