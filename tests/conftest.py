"""
Gosling2 Test Fixtures
======================
Three database fixtures for contract testing against real SQLite:

    empty_db      - Schema only. For negative/empty tests.
    populated_db  - Rich "Dave Grohl" scenario with known exact values.
    edge_case_db  - Orphans, nulls, unicode, boundary values.

Every fixture returns a file path to a hermetic SQLite DB.
No mocking. No env leaking. Every test states what it expects EXACTLY.
"""

import sys
import shutil
from pathlib import Path

# Ensure project root is in path for tests
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import sqlite3  # noqa: E402
import pytest  # noqa: E402
from src.data.schema import SCHEMA_SQL  # noqa: E402
from src.services.catalog_service import CatalogService  # noqa: E402
from src.services.audit_service import AuditService  # noqa: E402
from src.engine import config  # noqa: E402


@pytest.fixture(autouse=True)
def disable_side_effects(monkeypatch):
    """Disable destructive side-effects during general test runs."""
    monkeypatch.setattr(config, "AUTO_MOVE_ON_APPROVE", False)
    monkeypatch.setattr(config, "AUTO_SAVE_ID3", False)


@pytest.fixture(scope="session", autouse=True)
def hermetic_logging(tmp_path_factory):
    """
    Ensure tests do not pollute the production log file or console.
    Redirects all logs to a temporary file in the pytest session directory.
    """
    from src.services.logger import logger

    # Create a session-specific log file
    test_log_dir = tmp_path_factory.mktemp("logs")
    test_log_file = test_log_dir / "test_gosling.log"

    # Backup original settings
    orig_file = logger.log_file
    orig_console = logger.console_enabled

    # Apply hermetic settings
    logger.log_file = str(test_log_file)
    logger.console_enabled = False

    yield

    # Restore
    logger.log_file = orig_file
    logger.console_enabled = orig_console



# ---------------------------------------------------------------------------
# Helper: Create a hermetic DB with schema + custom collation
# ---------------------------------------------------------------------------
def _create_db(tmp_path, name="test.db"):
    db_file = tmp_path / name
    conn = sqlite3.connect(db_file)
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    return str(db_file)


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    return conn


# ---------------------------------------------------------------------------
# Session-level master databases (Created once, reused for speed)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def _master_empty_db(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("master")
    return _create_db(tmp_path, "master_empty.db")


@pytest.fixture(scope="session")
def _master_populated_db(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("master")
    path = _create_db(tmp_path, "master_populated.db")
    _populate_db_data(path)
    return path


@pytest.fixture(scope="session")
def _master_edge_case_db(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("master")
    path = _create_db(tmp_path, "master_edge.db")
    _populate_edge_case_data(path)
    return path


# ---------------------------------------------------------------------------
# FIXTURE: empty_db
# ---------------------------------------------------------------------------
@pytest.fixture
def empty_db(tmp_path, _master_empty_db):
    """Heremetic copy of the empty schema."""
    dest = tmp_path / "empty.db"
    shutil.copy(_master_empty_db, dest)
    return str(dest)


# ---------------------------------------------------------------------------
# FIXTURE: mock_db_path (alias)
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_db_path(empty_db):
    return empty_db


# ---------------------------------------------------------------------------
# FIXTURE: populated_db
# ---------------------------------------------------------------------------
# Data map (EXACT values - tests MUST reference these):
#
# IDENTITIES:
#   ID=1: person "Dave Grohl" (aliases: Grohlton NameID=11, Late! NameID=12, Ines Prajo NameID=33)
#   ID=2: group  "Nirvana"    (members: Dave)
#   ID=3: group  "Foo Fighters" (members: Dave, Taylor)
#   ID=4: person "Taylor Hawkins"
#
# SONGS (SourceID -> MediaName -> SourceDuration(sec) -> duration_ms):
#   1: "Smells Like Teen Spirit"  200s -> 200000ms  credited: Nirvana(NameID=20)       Album: Nevermind(100) Track 1
#   2: "Everlong"                 240s -> 240000ms  credited: Foo Fighters(NameID=30)   Album: TCATS(200) Track 11
#   3: "Range Rover Bitch"        180s -> 180000ms  credited: Taylor Hawkins(NameID=40) No album
#   4: "Grohlton Theme"           120s -> 120000ms  credited: Grohlton(NameID=11)       No album
#   5: "Pocketwatch Demo"         180s -> 180000ms  credited: Late!(NameID=12)          No album
#   6: "Dual Credit Track"        300s -> 300000ms  credited: Dave Grohl(NameID=10) Performer + Taylor(NameID=40) Composer
#   7: "Hollow Song"              10s  -> 10000ms   ZERO credits                        No album
#   8: "Joint Venture"            180s -> 180000ms  credited: Dave Grohl(NameID=10) Performer + Taylor(NameID=40) Performer
#   9: "Priority Test"            100s -> 100000ms  ZERO credits                        No album
#
# ALBUMS:
#   100: "Nevermind"                1991  Publishers: DGC Records(10), Sub Pop(5)   Credit: Nirvana(NameID=20) Performer
#   200: "The Colour and the Shape" 1997  Publishers: Roswell Records(4)           Credit: Foo Fighters(NameID=30) Performer
#
# PUBLISHERS:
#   1:  "Universal Music Group"  parent=NULL
#   2:  "Island Records"         parent=1
#   3:  "Island Def Jam"         parent=2
#   4:  "Roswell Records"        parent=NULL
#   5:  "Sub Pop"                parent=NULL
#   10: "DGC Records"            parent=1
#
# TAGS on songs:
#   Song 1: Grunge(1/Genre), Energetic(2/Mood), English(5/Jezik)
#   Song 2: 90s(3/Era), Rock(7/Genre)
#   Song 4: Electronic(4/Style)
#   Song 9: Grunge(1/Genre, NOT primary), Alt Rock(6/Genre, IS primary)
#
# RECORDING PUBLISHERS:
#   Song 1 -> DGC Records(10)
#
# AUDIT DATA:
#   ActionLog: ActionID=1, RENAME on ArtistNames ID=33, "User updated artist name"
#   ChangeLog: LogID=1, ArtistNames record 33, DisplayName: "PinkPantheress" -> "Ines Prajo"
#   DeletedRecords: DeleteID=1, Songs record 99, snapshot='{"Title": "Deleted Song", "Type": "Song"}'
#
# ROLES:
#   1: Performer, 2: Composer, 3: Lyricist, 4: Producer
#
# ---------------------------------------------------------------------------
# FIXTURE: populated_db
# ---------------------------------------------------------------------------
@pytest.fixture
def populated_db(tmp_path, _master_populated_db):
    """Heremetic copy of the populated 'Dave Grohl' DB."""
    dest = tmp_path / "populated.db"
    shutil.copy(_master_populated_db, dest)
    return str(dest)


def _populate_db_data(db_path):
    """Internal helper to fill the master DB."""
    conn = _connect(db_path)
    cursor = conn.cursor()

    # --- Types ---
    cursor.execute("INSERT INTO Types (TypeID, TypeName) VALUES (1, 'Song')")

    # --- Roles ---
    cursor.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (1, 'Performer')")
    cursor.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (2, 'Composer')")
    cursor.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (3, 'Lyricist')")
    cursor.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (4, 'Producer')")

    conn.commit()

    # --- Identities ---
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType, LegalName) VALUES (1, 'person', 'David Eric Grohl')"
    )  # Dave Grohl
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType) VALUES (2, 'group')"
    )  # Nirvana
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType) VALUES (3, 'group')"
    )  # Foo Fighters
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType) VALUES (4, 'person')"
    )  # Taylor Hawkins

    # --- Group Memberships ---
    cursor.execute(
        "INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (2, 1)"
    )  # Dave in Nirvana
    cursor.execute(
        "INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (3, 1)"
    )  # Dave in Foo Fighters
    cursor.execute(
        "INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (3, 4)"
    )  # Taylor in Foo Fighters

    # --- Artist Names (aliases) ---
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
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (30, 3, 'Foo Fighters', 1)"
    )
    # Taylor
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (40, 4, 'Taylor Hawkins', 1)"
    )
    # Audit alias (Dave's extra alias for rename test)
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (33, 1, 'Ines Prajo', 0)"
    )

    # --- Publishers ---
    cursor.execute(
        "INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (1, 'Universal Music Group', NULL)"
    )
    cursor.execute(
        "INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (2, 'Island Records', 1)"
    )
    cursor.execute(
        "INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (3, 'Island Def Jam', 2)"
    )
    cursor.execute(
        "INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (4, 'Roswell Records', NULL)"
    )
    cursor.execute(
        "INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (5, 'Sub Pop', NULL)"
    )
    cursor.execute(
        "INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (10, 'DGC Records', 1)"
    )

    # sid, tid, name, path, dur, active, ahash, status, recording_year, bpm, isrc
    songs = [
        (
            1,
            1,
            "Smells Like Teen Spirit",
            "/path/1",
            200,
            1,
            "hash_1",
            0,
            1991,
            None,
            None,
        ),
        (2, 1, "Everlong", "/path/2", 240, 1, None, 0, 1997, None, None),
        (3, 1, "Range Rover Bitch", "/path/3", 180, 1, None, 0, 2016, None, None),
        (4, 1, "Grohlton Theme", "/path/4", 120, 1, None, 0, None, None, None),
        (5, 1, "Pocketwatch Demo", "/path/5", 180, 1, None, 0, 1992, None, None),
        (6, 1, "Dual Credit Track", "/path/6", 300, 1, None, 0, None, None, None),
        (7, 1, "Hollow Song", "/path/7", 10, 1, None, 1, None, 128, "ISRC123"),
        (8, 1, "Joint Venture", "/path/8", 180, 1, None, 0, None, None, None),
        (9, 1, "Priority Test", "/path/9", 100, 1, None, 1, None, None, None),
    ]
    for sid, tid, name, path, dur, active, ahash, status, ryear, bpm, isrc in songs:
        cursor.execute(
            "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive, AudioHash, ProcessingStatus) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, tid, name, path, dur, active, ahash, status),
        )
        cursor.execute(
            "INSERT INTO Songs (SourceID, RecordingYear, TempoBPM, ISRC) VALUES (?, ?, ?, ?)",
            (sid, ryear, bpm, isrc),
        )

    # --- Song Credits ---
    credits = [
        (1, 20, 1),  # SLTS -> Nirvana, Performer
        (2, 30, 1),  # Everlong -> Foo Fighters, Performer
        (3, 40, 1),  # Range Rover Bitch -> Taylor Hawkins, Performer
        (4, 11, 1),  # Grohlton Theme -> Grohlton (alias), Performer
        (5, 12, 1),  # Pocketwatch Demo -> Late! (alias), Performer
        (6, 10, 1),  # Dual Credit Track -> Dave Grohl, Performer
        (6, 40, 2),  # Dual Credit Track -> Taylor Hawkins, Composer
        (8, 10, 1),  # Joint Venture -> Dave Grohl, Performer
        (8, 40, 1),  # Joint Venture -> Taylor Hawkins, Performer
    ]
    for source_id, name_id, role_id in credits:
        cursor.execute(
            "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
            (source_id, name_id, role_id),
        )

    # --- Albums ---
    cursor.execute(
        "INSERT INTO Albums (AlbumID, AlbumTitle, ReleaseYear) VALUES (100, 'Nevermind', 1991)"
    )
    cursor.execute(
        "INSERT INTO Albums (AlbumID, AlbumTitle, ReleaseYear) VALUES (200, 'The Colour and the Shape', 1997)"
    )

    # --- Song-Album links ---
    cursor.execute(
        "INSERT INTO SongAlbums (SourceID, AlbumID, TrackNumber, IsPrimary) VALUES (1, 100, 1, 1)"
    )
    cursor.execute(
        "INSERT INTO SongAlbums (SourceID, AlbumID, TrackNumber, IsPrimary) VALUES (2, 200, 11, 1)"
    )

    # --- Album Publishers ---
    cursor.execute(
        "INSERT INTO AlbumPublishers (AlbumID, PublisherID) VALUES (100, 10)"
    )  # Nevermind -> DGC Records
    cursor.execute(
        "INSERT INTO AlbumPublishers (AlbumID, PublisherID) VALUES (100, 5)"
    )  # Nevermind -> Sub Pop
    cursor.execute(
        "INSERT INTO AlbumPublishers (AlbumID, PublisherID) VALUES (200, 4)"
    )  # TCATS -> Roswell Records

    # --- Album Credits ---
    cursor.execute(
        "INSERT INTO AlbumCredits (AlbumID, CreditedNameID, RoleID) VALUES (100, 20, 1)"
    )  # Nirvana Performer on Nevermind
    cursor.execute(
        "INSERT INTO AlbumCredits (AlbumID, CreditedNameID, RoleID) VALUES (200, 30, 1)"
    )  # Foo Fighters Performer on TCATS

    # --- Recording Publishers ---
    cursor.execute(
        "INSERT INTO RecordingPublishers (SourceID, PublisherID) VALUES (1, 10)"
    )  # SLTS -> DGC Records

    # --- Tags ---
    tags = [
        (1, "Grunge", "Genre"),
        (2, "Energetic", "Mood"),
        (3, "90s", "Era"),
        (4, "Electronic", "Style"),
        (5, "English", "Jezik"),
        (6, "Alt Rock", "Genre"),
        (7, "Rock", "Genre"),
    ]
    for tag_id, name, category in tags:
        cursor.execute(
            "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (?, ?, ?)",
            (tag_id, name, category),
        )

    # --- Media Source Tags ---
    song_tags = [
        (1, 1, 1),  # SLTS -> Grunge (primary Genre — only/first genre)
        (1, 2, 0),  # SLTS -> Energetic
        (1, 5, 0),  # SLTS -> English
        (2, 3, 0),  # Everlong -> 90s
        (2, 7, 1),  # Everlong -> Rock (primary)
        (4, 4, 0),  # Grohlton Theme -> Electronic
        (9, 1, 0),  # Priority Test -> Grunge (NOT primary)
        (9, 6, 1),  # Priority Test -> Alt Rock (IS primary)
    ]
    for source_id, tag_id, is_primary in song_tags:
        cursor.execute(
            "INSERT INTO MediaSourceTags (SourceID, TagID, IsPrimary) VALUES (?, ?, ?)",
            (source_id, tag_id, is_primary),
        )

    # --- Audit Data ---
    cursor.execute(
        "INSERT INTO ActionLog (ActionID, ActionLogType, TargetTable, ActionTargetID, ActionDetails) "
        "VALUES (1, 'RENAME', 'ArtistNames', 33, 'User updated artist name')"
    )
    cursor.execute(
        "INSERT INTO ChangeLog (LogID, LogTableName, RecordID, LogFieldName, OldValue, NewValue) "
        "VALUES (1, 'ArtistNames', 33, 'DisplayName', 'PinkPantheress', 'Ines Prajo')"
    )

    # --- Deleted Records ---
    cursor.execute(
        "INSERT INTO DeletedRecords (DeleteID, DeletedFromTable, RecordID, FullSnapshot) "
        """VALUES (1, 'Songs', 99, '{"Title": "Deleted Song", "Type": "Song"}')"""
    )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# FIXTURE: edge_case_db
# ---------------------------------------------------------------------------
@pytest.fixture
def edge_case_db(tmp_path, _master_edge_case_db):
    """Heremetic copy of the edge case DB."""
    dest = tmp_path / "edge_case.db"
    shutil.copy(_master_edge_case_db, dest)
    return str(dest)


def _populate_edge_case_data(db_path):
    """Internal helper to fill the master edge case DB."""
    conn = _connect(db_path)
    cursor = conn.cursor()

    # Types
    cursor.execute("INSERT INTO Types (TypeID, TypeName) VALUES (1, 'Song')")

    # Roles
    cursor.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (1, 'Performer')")

    # --- Identities ---
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType) VALUES (100, 'person')"
    )  # No name at all
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType, LegalName) VALUES (101, 'person', 'John Legal')"
    )  # LegalName only
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType) VALUES (102, 'group')"
    )  # Circular A
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType) VALUES (103, 'group')"
    )  # Circular B
    cursor.execute(
        "INSERT INTO Identities (IdentityID, IdentityType) VALUES (104, 'person')"
    )  # Unicode

    # Artist Names
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (200, 102, 'Circular Group A', 1)"
    )
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (201, 103, 'Circular Group B', 1)"
    )
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (202, 104, 'Bjork', 1)"
    )

    # Circular memberships
    cursor.execute(
        "INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (102, 103)"
    )
    cursor.execute(
        "INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID) VALUES (103, 102)"
    )

    # --- Publishers ---
    cursor.execute(
        "INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (100, 'Orphan Publisher', 999)"
    )

    # --- Songs ---
    edge_songs = [
        (100, 1, "Orphaned Song", "/edge/1", 180, 1, 1),
        (101, 1, " ", "/edge/2", 60, 1, 1),
        (102, 1, "A", "/edge/3", 30, 1, 1),
        (103, 1, "\u65e5\u672c\u8a9e\u30bd\u30f3\u30b0", "/edge/4", 200, 1, 1),
        (104, 1, "Zero Duration", "/edge/5", 0, 1, 1),
        (105, 1, "No Identity Name Song", "/edge/6", 120, 1, 1),
    ]
    for sid, tid, name, path, dur, active, status in edge_songs:
        cursor.execute(
            "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive, ProcessingStatus) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sid, tid, name, path, dur, active, status),
        )
        cursor.execute("INSERT INTO Songs (SourceID) VALUES (?)", (sid,))

    # Credit pointing to identity 100 (no ArtistName record for this identity)
    # We create a standalone ArtistName for the credit but identity 100 has no primary name
    cursor.execute(
        "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (300, 100, 'Ghost Artist', 0)"
    )
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (105, 300, 1)"
    )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# SERVICE FIXTURES (use monkeypatch for DB_PATH isolation)
# ---------------------------------------------------------------------------
@pytest.fixture
def catalog_service(populated_db):
    """CatalogService wired to the populated test DB."""
    return CatalogService(populated_db)


@pytest.fixture
def catalog_service_empty(empty_db):
    """CatalogService wired to an empty test DB."""
    return CatalogService(empty_db)


@pytest.fixture
def audit_service(populated_db):
    """AuditService wired to the populated test DB."""
    return AuditService(populated_db)


@pytest.fixture
def audit_service_empty(empty_db):
    """AuditService wired to an empty test DB."""
    return AuditService(empty_db)


@pytest.fixture
def test_audio_file():
    """Path to a real audio file for integration tests."""
    return str(Path(__file__).parent / "fixtures" / "silence.mp3")


@pytest.fixture(autouse=True)
def cleanup_staging_dir(tmp_path, monkeypatch):
    """
    Redirects STAGING_DIR to a per-test tmp directory so tests never
    touch the real staging folder on disk.
    """
    test_staging = tmp_path / "staging"
    test_staging.mkdir(parents=True, exist_ok=True)

    import src.engine.config as config_mod
    import src.engine.routers.ingest as ingest_mod
    import src.services.catalog_service as catalog_service_mod

    monkeypatch.setattr(config_mod, "STAGING_DIR", test_staging)
    monkeypatch.setattr(ingest_mod, "STAGING_DIR", test_staging)
    monkeypatch.setattr(catalog_service_mod, "STAGING_DIR", test_staging)

    yield
