"""
Phase 3.1 Unit C.2 — read-path normalization tests.

Inserts rows with diacritics and shadow columns populated, then asserts that
queries containing diacritics (or their ASCII equivalents) reach those rows
through the service layer.
"""

import sqlite3

import pytest

from src.services.catalog_service import CatalogService


def _make_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    return conn


@pytest.fixture
def service(populated_db):
    return CatalogService(populated_db)


@pytest.fixture
def conn(populated_db):
    c = _make_conn(populated_db)
    yield c
    c.close()


@pytest.fixture
def seeded_diacritics(conn):
    """Add diacritic-named rows to the populated DB with shadow columns set."""
    cur = conn.cursor()
    # New identity with diacritic primary name ("Noëp")
    cur.execute("INSERT INTO Identities (IdentityType) VALUES ('person')")
    noep_identity = cur.lastrowid
    cur.execute(
        "INSERT INTO ArtistNames (OwnerIdentityID, DisplayName, DisplayName_Search, IsPrimaryName) "
        "VALUES (?, 'Noëp', 'noep', 1)",
        (noep_identity,),
    )
    # New album with diacritic title ("Straße")
    cur.execute(
        "INSERT INTO Albums (AlbumTitle, AlbumTitle_Search, ReleaseYear) VALUES (?, ?, ?)",
        ("Straße", "strasse", 2020),
    )
    strasse_album = cur.lastrowid
    # Plain ASCII twin for "Strasse"
    cur.execute(
        "INSERT INTO Albums (AlbumTitle, AlbumTitle_Search, ReleaseYear) VALUES (?, ?, ?)",
        ("Strasse", "strasse", 2021),
    )
    # New song with diacritic media name + link to the Straße album
    cur.execute(
        "INSERT INTO MediaSources (TypeID, MediaName, MediaName_Search, SourcePath, SourceDuration, IsActive, ProcessingStatus) "
        "VALUES (1, ?, ?, ?, 180, 1, 0)",
        ("Šima, unučad i praunučad", "sima, unucad i praunucad", "/path/diacritic"),
    )
    sima_song = cur.lastrowid
    cur.execute(
        "INSERT INTO Songs (SourceID, RecordingYear) VALUES (?, 2024)",
        (sima_song,),
    )
    conn.commit()
    return {
        "noep_identity": noep_identity,
        "strasse_album": strasse_album,
        "sima_song": sima_song,
    }


class TestIdentitySearchNormalization:
    def test_diacritic_query_matches_diacritic_row(self, service, seeded_diacritics):
        rows = service.search_identities_slim("Noëp")
        ids = {r["IdentityID"] for r in rows}
        assert seeded_diacritics["noep_identity"] in ids

    def test_ascii_query_matches_diacritic_row(self, service, seeded_diacritics):
        rows = service.search_identities_slim("noep")
        ids = {r["IdentityID"] for r in rows}
        assert seeded_diacritics["noep_identity"] in ids

    def test_ascii_only_query_still_works(self, service):
        # Existing fixture: Dave Grohl. Shadow is NULL on populated_db (no backfill in test),
        # so this verifies the LegalName / ASCII raw fallback is unaffected — actually, the
        # LIKE now targets DisplayName_Search which is NULL on the fixture identities. So
        # this query relies on the OR i.LegalName LIKE ? branch (Dave has LegalName 'David Eric Grohl').
        rows = service.search_identities_slim("David")
        names = {r["DisplayName"] for r in rows}
        assert "Dave Grohl" in names


class TestAlbumSearchNormalization:
    def test_diacritic_query_matches_both(self, service, seeded_diacritics):
        # query "straße" normalizes to "strasse", which matches both rows.
        rows = service.search_albums_slim("straße")
        titles = {r["AlbumTitle"] for r in rows}
        assert "Straße" in titles
        assert "Strasse" in titles

    def test_ascii_query_matches_both(self, service, seeded_diacritics):
        rows = service.search_albums_slim("strasse")
        titles = {r["AlbumTitle"] for r in rows}
        assert "Straße" in titles
        assert "Strasse" in titles


class TestSongSearchNormalization:
    def test_diacritic_media_name_matches(self, service, seeded_diacritics):
        rows = service.search_songs_slim("Šima")
        ids = {r["SourceID"] for r in rows}
        assert seeded_diacritics["sima_song"] in ids

    def test_ascii_media_name_matches_diacritic(self, service, seeded_diacritics):
        rows = service.search_songs_slim("sima")
        ids = {r["SourceID"] for r in rows}
        assert seeded_diacritics["sima_song"] in ids
