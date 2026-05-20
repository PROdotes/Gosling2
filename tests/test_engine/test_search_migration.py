"""Migration check for the Phase 3.1 _Search shadow columns.

Fresh DBs get the columns from SCHEMA_SQL directly. Legacy DBs that pre-date
this phase get them via _migrate_search_columns. This test simulates the
legacy case by creating tables without the new columns, then asserts the
migration adds them and is a no-op on the second run.
"""
import sqlite3
import pytest

from src.engine_server import _migrate_search_columns, _SEARCH_SHADOW_COLUMNS


LEGACY_SCHEMA = """
CREATE TABLE ArtistNames (
    NameID INTEGER PRIMARY KEY,
    OwnerIdentityID INTEGER,
    DisplayName TEXT NOT NULL,
    IsPrimaryName BOOLEAN DEFAULT 0,
    IsDeleted BOOLEAN DEFAULT 0
);
CREATE TABLE MediaSources (
    SourceID INTEGER PRIMARY KEY,
    TypeID INTEGER NOT NULL,
    MediaName TEXT NOT NULL,
    SourceNotes TEXT,
    SourcePath TEXT UNIQUE,
    SourceDuration REAL,
    AudioHash TEXT UNIQUE,
    IsActive BOOLEAN DEFAULT 0,
    ProcessingStatus INTEGER,
    IsDeleted BOOLEAN DEFAULT 0
);
CREATE TABLE Albums (
    AlbumID INTEGER PRIMARY KEY,
    AlbumTitle TEXT NOT NULL,
    AlbumType TEXT,
    ReleaseYear INTEGER,
    IsDeleted BOOLEAN DEFAULT 0
);
"""


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


@pytest.fixture
def legacy_conn():
    conn = sqlite3.connect(":memory:")
    conn.executescript(LEGACY_SCHEMA)
    conn.commit()
    yield conn
    conn.close()


def test_migration_adds_missing_columns(legacy_conn):
    # Sanity: legacy schema does not have any of the new columns
    for table, col in _SEARCH_SHADOW_COLUMNS:
        assert col not in _column_names(legacy_conn, table)

    _migrate_search_columns(legacy_conn)

    for table, col in _SEARCH_SHADOW_COLUMNS:
        assert col in _column_names(legacy_conn, table), (
            f"Migration failed to add {table}.{col}"
        )


def test_migration_is_idempotent(legacy_conn):
    _migrate_search_columns(legacy_conn)
    # Second call must not raise — sqlite ALTER TABLE on an existing column
    # would error, so this proves the PRAGMA guard works.
    _migrate_search_columns(legacy_conn)
    for table, col in _SEARCH_SHADOW_COLUMNS:
        assert col in _column_names(legacy_conn, table)


def test_migration_preserves_existing_data(legacy_conn):
    legacy_conn.execute(
        "INSERT INTO ArtistNames (NameID, DisplayName) VALUES (1, 'Noëp')"
    )
    legacy_conn.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName) VALUES (1, 1, 'Måneskin Song')"
    )
    legacy_conn.execute(
        "INSERT INTO Albums (AlbumID, AlbumTitle) VALUES (1, 'Straße')"
    )
    legacy_conn.commit()

    _migrate_search_columns(legacy_conn)

    # Row values are intact; new column defaults to NULL (backfill is the
    # responsibility of tools/backfill_search_columns.py).
    name = legacy_conn.execute("SELECT DisplayName, DisplayName_Search FROM ArtistNames WHERE NameID = 1").fetchone()
    assert name == ("Noëp", None)
    media = legacy_conn.execute("SELECT MediaName, MediaName_Search FROM MediaSources WHERE SourceID = 1").fetchone()
    assert media == ("Måneskin Song", None)
    album = legacy_conn.execute("SELECT AlbumTitle, AlbumTitle_Search FROM Albums WHERE AlbumID = 1").fetchone()
    assert album == ("Straße", None)
