SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS MediaSources (
    SourceID INTEGER PRIMARY KEY,
    TypeID INTEGER NOT NULL,
    SourcePath TEXT NOT NULL,
    SourceDuration REAL NOT NULL,
    AudioHash TEXT,
    ProcessingStatus INTEGER DEFAULT 0,
    IsActive BOOLEAN DEFAULT 1,
    SourceNotes TEXT,
    MediaName TEXT
);

CREATE TABLE IF NOT EXISTS Songs (
    SourceID INTEGER PRIMARY KEY,
    TempoBPM INTEGER,
    RecordingYear INTEGER,
    ISRC TEXT,
    SongGroups TEXT,
    FOREIGN KEY(SourceID) REFERENCES MediaSources(SourceID)
);

CREATE TABLE IF NOT EXISTS Identities (
    IdentityID INTEGER PRIMARY KEY,
    IdentityType TEXT NOT NULL,
    DisplayName TEXT NOT NULL,
    LegalName TEXT
);

CREATE TABLE IF NOT EXISTS ArtistNames (
    NameID INTEGER PRIMARY KEY,
    OwnerIdentityID INTEGER,
    DisplayName TEXT NOT NULL,
    IsPrimaryName BOOLEAN DEFAULT 0,
    FOREIGN KEY(OwnerIdentityID) REFERENCES Identities(IdentityID)
);

CREATE TABLE IF NOT EXISTS GroupMemberships (
    MembershipID INTEGER PRIMARY KEY,
    GroupIdentityID INTEGER NOT NULL,
    MemberIdentityID INTEGER NOT NULL,
    FOREIGN KEY(GroupIdentityID) REFERENCES Identities(IdentityID),
    FOREIGN KEY(MemberIdentityID) REFERENCES Identities(IdentityID)
);

CREATE TABLE IF NOT EXISTS SongCredits (
    CreditID INTEGER PRIMARY KEY,
    SourceID INTEGER NOT NULL,
    CreditedNameID INTEGER NOT NULL,
    RoleID INTEGER,
    FOREIGN KEY(SourceID) REFERENCES Songs(SourceID),
    FOREIGN KEY(CreditedNameID) REFERENCES ArtistNames(NameID)
);

CREATE TABLE IF NOT EXISTS ChangeLog (
    LogID INTEGER PRIMARY KEY,
    LogTableName TEXT NOT NULL,
    RecordID INTEGER NOT NULL,
    LogFieldName TEXT NOT NULL,
    OldValue TEXT,
    NewValue TEXT,
    BatchID TEXT NOT NULL
);
"""
