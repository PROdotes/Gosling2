import sys
from pathlib import Path

# Ensure project root is in path for tests
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import sqlite3  # noqa: E402
import pytest  # noqa: E402
from src.data.schema import SCHEMA_SQL  # noqa: E402
from src.services.catalog_service import CatalogService  # noqa: E402


@pytest.fixture
def mock_db_path(tmp_path):
    """
    Creates a hermetic, in-memory SQLite database initialized with the v3core schema.
    This ensures tests are always running against the current schema.
    """
    db_file = tmp_path / "test_v3core_hermetic.db"
    conn = sqlite3.connect(db_file)
    # Register the custom collation from the physical DB
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    return str(db_file)


@pytest.fixture
def catalog_service(mock_db_path):
    """Fixture to provide a clean CatalogService for every test."""
    return CatalogService(mock_db_path)


@pytest.fixture
def populated_db(mock_db_path):
    """
    A 'Dave Grohl' scenario pre-populated into the hermetic test DB.
    Use this for logic/paradigm tests.
    """
    conn = sqlite3.connect(mock_db_path)
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    cursor = conn.cursor()

    # 0. Types
    cursor.execute("INSERT INTO Types (TypeID, TypeName) VALUES (1, 'Song')")

    # 1. Identities
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType, DisplayName) VALUES (1, 'person', 'Dave Grohl')"
    )
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType, DisplayName) VALUES (2, 'group', 'Nirvana')"
    )
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType, DisplayName) VALUES (3, 'group', 'Foo Fighters')"
    )
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType, DisplayName) VALUES (4, 'person', 'Taylor Hawkins')"
    )

    # 2. Memberships
    cursor.execute(
        "INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (2, 1)"
    )  # Dave in Nirvana
    cursor.execute(
        "INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (3, 1)"
    )  # Dave in Foo Fighters
    cursor.execute(
        "INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (3, 4)"
    )  # Taylor in Foo Fighters

    # 3. Aliases
    # Dave's Primary + Aliases
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (10, 1, 'Dave Grohl', 1)"
    )
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (11, 1, 'Grohlton', 0)"
    )
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (12, 1, 'Late!', 0)"
    )

    # Groups
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (20, 2, 'Nirvana', 1)"
    )
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) "
        "VALUES (30, 3, 'Foo Fighters', 1)"
    )

    # Taylor's Primary
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (40, 4, 'Taylor Hawkins', 1)"
    )

    # 4. Media & Songs
    # Nirvana Track
    cursor.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (1, 1, 'Smells Like Teen Spirit', '/path/1', 200, 1)"
    )
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (1)")
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (1, 20, 1)"
    )

    # Foo Fighters Track
    cursor.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (2, 1, 'Everlong', '/path/2', 240, 1)"
    )
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (2)")
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (2, 30, 1)"
    )

    # Taylor Hawkins Solo Track
    cursor.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (3, 1, 'Range Rover Bitch', '/path/3', 180, 1)"
    )
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (3)")
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (3, 40, 1)"
    )

    # Dave Grohl Alias Track #1 (Grohlton)
    cursor.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (4, 1, 'Grohlton Theme', '/path/4', 120, 1)"
    )
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (4)")
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (4, 11, 1)"
    )

    # Dave Grohl Alias Track #2 (Late!)
    cursor.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (5, 1, 'Pocketwatch Demo', '/path/5', 180, 1)"
    )
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (5)")
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (5, 12, 1)"
    )

    # Song with MULTIPLE credits
    cursor.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (6, 1, 'Dual Credit Track', '/path/6', 300, 1)"
    )
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (6)")
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (6, 10, 1)"
    )
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (6, 40, 2)"
    )

    # Song with ZERO credits
    cursor.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) "
        "VALUES (7, 1, 'Hollow Song', '/path/7', 10, 1)"
    )
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (7)")

    # Song with MULTIPLE PERFORMERS (Joint Venture)
    cursor.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (8, 1, 'Joint Venture', '/path/8', 180, 1)"
    )
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (8)")
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (8, 10, 1)"
    )  # Dave
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (8, 40, 1)"
    )  # Taylor

    # 6. Albums & Roles & Publishers
    cursor.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (1, 'Performer')")
    cursor.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (2, 'Composer')")
    cursor.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (3, 'Lyricist')")
    cursor.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (4, 'Producer')")

    # Publishers
    cursor.execute(
        "INSERT INTO Publishers (PublisherID, PublisherName) VALUES (1, 'DGC Records')"
    )
    cursor.execute(
        "INSERT INTO Publishers (PublisherID, PublisherName) VALUES (2, 'Roswell Records')"
    )
    cursor.execute(
        "INSERT INTO Publishers (PublisherID, PublisherName) VALUES (3, 'Sub Pop')"
    )

    # Album Data
    cursor.execute(
        "INSERT INTO Albums (AlbumID, AlbumTitle, ReleaseYear) VALUES (100, 'Nevermind', 1991)"
    )
    cursor.execute(
        "INSERT INTO SongAlbums (SourceID, AlbumID, TrackNumber, IsPrimary, TrackPublisherID) VALUES (1, 100, 1, 1, 1)"
    )
    cursor.execute("INSERT INTO AlbumPublishers (AlbumID, PublisherID) VALUES (100, 1)")
    cursor.execute("INSERT INTO AlbumPublishers (AlbumID, PublisherID) VALUES (100, 3)")

    cursor.execute(
        "INSERT INTO Albums (AlbumID, AlbumTitle, ReleaseYear) VALUES (200, 'The Colour and the Shape', 1997)"
    )
    cursor.execute(
        "INSERT INTO SongAlbums (SourceID, AlbumID, TrackNumber, IsPrimary, TrackPublisherID) VALUES (2, 200, 11, 1, 2)"
    )
    cursor.execute("INSERT INTO AlbumPublishers (AlbumID, PublisherID) VALUES (200, 2)")

    # Recording Publisher
    cursor.execute(
        "INSERT INTO RecordingPublishers (SourceID, PublisherID) VALUES (1, 1)"
    )

    # 8. Tags
    cursor.execute(
        "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (1, 'Grunge', 'Genre')"
    )
    cursor.execute(
        "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (2, 'Energetic', 'Mood')"
    )
    cursor.execute(
        "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (3, '90s', 'Era')"
    )
    cursor.execute(
        "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (4, 'Electronic', 'Style')"
    )
    cursor.execute(
        "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (5, 'English', 'Jezik')"
    )

    cursor.execute("INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (1, 1)")
    cursor.execute("INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (1, 2)")
    cursor.execute("INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (1, 5)")
    cursor.execute("INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (2, 3)")
    cursor.execute("INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (4, 4)")

    conn.commit()
    conn.close()
    return mock_db_path
