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
    cursor = conn.cursor()

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

    # Taylor Hawkins Solo Track (Co-worker's work: Dave should NOT get this)
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

    # 5. Edge Cases
    # Song with MULTIPLE credits (Multiple performers/composers)
    cursor.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (6, 1, 'Dual Credit Track', '/path/6', 300, 1)"
    )
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (6)")
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (6, 10, 1)"
    )  # Dave Grohl
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (6, 40, 2)"
    )  # Taylor Hawkins (Composer)

    # Song with ZERO credits
    cursor.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) "
        "VALUES (7, 1, 'Hollow Song', '/path/7', 10, 1)"
    )
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (7)")

    conn.commit()
    conn.close()
    return mock_db_path
