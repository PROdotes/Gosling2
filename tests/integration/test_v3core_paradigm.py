"""
Paradigm tests for v3core Identity Resolution.
Uses a controlled, in-memory test database to verify complex identity graph expansion.
"""
import sqlite3
import pytest
from src.v3core.services.identity_service import IdentityService

@pytest.fixture
def mock_db_path(tmp_path):
    db_file = tmp_path / "test_v3core.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create schema (subset needed for tests)
    cursor.executescript("""
        CREATE TABLE MediaSources (
            SourceID INTEGER PRIMARY KEY,
            TypeID INTEGER,
            MediaName TEXT,
            SourcePath TEXT,
            SourceDuration REAL,
            AudioHash TEXT,
            IsActive BOOLEAN,
            ProcessingStatus INTEGER,
            SourceNotes TEXT
        );
        CREATE TABLE Songs (
            SourceID INTEGER PRIMARY KEY,
            TempoBPM INTEGER,
            RecordingYear INTEGER,
            ISRC TEXT,
            SongGroups TEXT
        );
        CREATE TABLE Identities (
            IdentityID INTEGER PRIMARY KEY,
            IdentityType TEXT,
            DisplayName TEXT,
            LegalName TEXT
        );
        CREATE TABLE ArtistNames (
            NameID INTEGER PRIMARY KEY,
            OwnerIdentityID INTEGER,
            DisplayName TEXT,
            IsPrimaryName BOOLEAN
        );
        CREATE TABLE GroupMemberships (
            MembershipID INTEGER PRIMARY KEY,
            GroupIdentityID INTEGER,
            MemberIdentityID INTEGER
        );
        CREATE TABLE SongCredits (
            CreditID INTEGER PRIMARY KEY,
            SourceID INTEGER,
            CreditedNameID INTEGER,
            RoleID INTEGER
        );
        CREATE TABLE ChangeLog (
            LogID INTEGER PRIMARY KEY,
            LogTableName TEXT,
            RecordID INTEGER,
            LogFieldName TEXT,
            OldValue TEXT,
            NewValue TEXT,
            BatchID TEXT
        );
    """)

    # --- THE "GROHL" SCENARIO ---
    # 1. Identities
    cursor.execute("INSERT INTO Identities (IdentityID, IdentityType, DisplayName) VALUES (1, 'person', 'Dave Grohl')")
    cursor.execute("INSERT INTO Identities (IdentityID, IdentityType, DisplayName) VALUES (2, 'group', 'Nirvana')")
    cursor.execute("INSERT INTO Identities (IdentityID, IdentityType, DisplayName) VALUES (3, 'group', 'Foo Fighters')")

    # 2. Memberships (Dave is in Nirvana and Foo Fighters)
    cursor.execute("INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (2, 1)")
    cursor.execute("INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (3, 1)")

    # 3. Aliases
    cursor.execute("INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (10, 1, 'Dave Grohl', 1)")
    cursor.execute("INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (20, 2, 'Nirvana', 1)")
    cursor.execute("INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (30, 3, 'Foo Fighters', 1)")

    # 4. Media & Songs
    # Song 1: Nirvana Track
    cursor.execute("INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (1, 1, 'Smells Like Teen Spirit', '/path/1', 200, 1)")
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (1)")
    cursor.execute("INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (1, 20, 1)")

    # Song 2: Foo Fighters Track
    cursor.execute("INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (2, 1, 'Everlong', '/path/2', 240, 1)")
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (2)")
    cursor.execute("INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (2, 30, 1)")

    # Song 3: Solo Dave Track
    cursor.execute("INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (3, 1, 'Play', '/path/3', 1380, 1)")
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (3)")
    cursor.execute("INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (3, 10, 1)")

    conn.commit()
    conn.close()
    return str(db_file)

def test_grohlton_expansion(mock_db_path):
    """Verify that Dave Grohl ID returns songs from Nirvana, Foo Fighters, and Solo."""
    service = IdentityService(mock_db_path)
    
    # Identify ID 1 is Dave Grohl
    songs = service.get_songs_for_identity(1)
    
    titles = {s.title for s in songs}
    assert "Smells Like Teen Spirit" in titles
    assert "Everlong" in titles
    assert "Play" in titles
    assert len(songs) == 3

def test_group_to_member_expansion(mock_db_path):
    """Verify that Nirvana (Group) returns songs from its members (Dave)."""
    service = IdentityService(mock_db_path)
    
    # Identity ID 2 is Nirvana
    songs = service.get_songs_for_identity(2)
    
    titles = {s.title for s in songs}
    assert "Smells Like Teen Spirit" in titles
    # Dave Grohl's solo work should be included because he is a member of Nirvana
    assert "Play" in titles
    # Foo Fighters should also be included because Dave links Nirvana to Foo Fighters
    assert "Everlong" in titles
