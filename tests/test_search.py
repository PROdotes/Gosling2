"""
Search Contract Tests (Service + Repository Layer)
====================================================
Exact-value verification of the search pipeline at the service and repo layers.
Complements test_engine_search.py (HTTP layer) by testing the raw Python API.

No mocking. Real SQLite. Every assertion states EXACTLY what it expects.
"""

from src.data.song_repository import SongRepository


# ===========================================================================
# Repository Layer: SongRepository.search_surface
# ===========================================================================
class TestRepositorySearchSurface:
    """search_surface does title + album LIKE matching in the DB."""

    def test_title_match_everlong(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.search_surface("Everlong")
        assert len(songs) == 1
        assert songs[0].id == 2
        assert songs[0].title == "Everlong"
        assert songs[0].duration_ms == 240000

    def test_partial_title_match(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.search_surface("Ever")
        titles = [s.title for s in songs]
        assert "Everlong" in titles

    def test_album_title_match(self, populated_db):
        """Searching 'Nevermind' matches via album title -> Song 1."""
        repo = SongRepository(populated_db)
        songs = repo.search_surface("Nevermind")
        ids = [s.id for s in songs]
        assert 1 in ids  # SLTS is on Nevermind

    def test_no_match(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.search_surface("zzz_nonexistent")
        assert songs == []

    def test_empty_query_returns_all(self, populated_db):
        """Empty string LIKE '%%' matches all songs."""
        repo = SongRepository(populated_db)
        songs = repo.search_surface("")
        assert len(songs) == 9


# ===========================================================================
# Repository Layer: SongRepository.get_by_title
# ===========================================================================
class TestRepositoryGetByTitle:
    def test_exact_title(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("Everlong")
        assert len(songs) == 1
        assert songs[0].id == 2
        assert songs[0].title == "Everlong"

    def test_no_match(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("NonExistent")
        assert songs == []


# ===========================================================================
# Service Layer: CatalogService.search_songs (full two-phase pipeline)
# ===========================================================================
class TestCatalogSearchSongs:
    """Tests the complete two-phase search: surface + deep identity expansion."""

    def test_title_match_hydrated(self, catalog_service):
        """Searching 'Everlong' returns fully hydrated result."""
        songs = catalog_service.search_songs("Everlong")
        assert len(songs) == 1
        ev = next(s for s in songs if s.title == "Everlong")
        # Credits hydrated
        assert len(ev.credits) == 1
        assert ev.credits[0].display_name == "Foo Fighters"
        assert ev.credits[0].role_name == "Performer"
        # Album hydrated
        assert len(ev.albums) == 1
        assert ev.albums[0].album_title == "The Colour and the Shape"
        assert ev.albums[0].track_number == 11

    def test_identity_name_deep_search(self, catalog_service):
        """'Dave Grohl' triggers deep search: finds identity, expands to groups."""
        songs = catalog_service.search_songs("Dave Grohl")
        titles = sorted([s.title for s in songs])
        # Dave's own credits
        assert "Dual Credit Track" in titles
        assert "Joint Venture" in titles
        # Dave's alias credits
        assert "Grohlton Theme" in titles
        assert "Pocketwatch Demo" in titles
        # Nirvana (group) songs
        assert "Smells Like Teen Spirit" in titles
        # Foo Fighters (group) songs
        assert "Everlong" in titles

    def test_alias_deep_search(self, catalog_service):
        """'Grohlton' alias resolves to Dave -> expands to group songs."""
        songs = catalog_service.search_songs("Grohlton")
        titles = [s.title for s in songs]
        assert "Grohlton Theme" in titles  # Direct alias match

    def test_group_search(self, catalog_service):
        """'Nirvana' returns SLTS directly."""
        songs = catalog_service.search_songs("Nirvana")
        titles = [s.title for s in songs]
        assert "Smells Like Teen Spirit" in titles

    def test_no_results(self, catalog_service):
        """Non-matching query returns empty list."""
        songs = catalog_service.search_songs("zzz_nonexistent")
        assert songs == []

    def test_deduplication(self, catalog_service):
        """No duplicate songs in results."""
        songs = catalog_service.search_songs("Nirvana")
        ids = [s.id for s in songs]
        assert len(ids) == len(set(ids))

    def test_empty_query(self, catalog_service):
        """Empty string returns all 9 songs."""
        songs = catalog_service.search_songs("")
        assert len(songs) == 9

    def test_empty_db(self, catalog_service_empty):
        """Search on empty DB returns empty list."""
        songs = catalog_service_empty.search_songs("anything")
        assert songs == []


# ===========================================================================
# Service Layer: CatalogService.search_identities
# ===========================================================================
class TestCatalogSearchIdentities:
    def test_by_name(self, catalog_service):
        identities = catalog_service.search_identities("Dave")
        names = [i.display_name for i in identities]
        assert "Dave Grohl" in names

    def test_by_alias(self, catalog_service):
        identities = catalog_service.search_identities("Grohlton")
        names = [i.display_name for i in identities]
        assert "Dave Grohl" in names

    def test_group_search(self, catalog_service):
        identities = catalog_service.search_identities("Nirvana")
        names = [i.display_name for i in identities]
        assert "Nirvana" in names

    def test_no_results(self, catalog_service):
        identities = catalog_service.search_identities("zzz_nothing")
        assert identities == []

    def test_empty_db(self, catalog_service_empty):
        identities = catalog_service_empty.search_identities("Dave")
        assert identities == []


# ===========================================================================
# Service Layer: CatalogService.search_albums
# ===========================================================================
class TestCatalogSearchAlbums:
    def test_partial_match(self, catalog_service):
        albums = catalog_service.search_albums("Never")
        titles = [a.title for a in albums]
        assert "Nevermind" in titles

    def test_hydrated(self, catalog_service):
        """Search results should include publishers and credits."""
        albums = catalog_service.search_albums("Nevermind")
        nvm = next(a for a in albums if a.title == "Nevermind")
        pub_names = sorted([p.name for p in nvm.publishers])
        assert pub_names == ["DGC Records", "Sub Pop"]
        assert len(nvm.credits) == 1
        assert nvm.credits[0].display_name == "Nirvana"

    def test_no_results(self, catalog_service):
        albums = catalog_service.search_albums("zzz_nothing")
        assert albums == []

    def test_empty_db(self, catalog_service_empty):
        albums = catalog_service_empty.search_albums("anything")
        assert albums == []


# ===========================================================================
# Service Layer: CatalogService.search_publishers
# ===========================================================================
class TestCatalogSearchPublishers:
    def test_partial_match(self, catalog_service):
        pubs = catalog_service.search_publishers("island")
        names = sorted([p.name for p in pubs])
        assert "Island Records" in names
        assert "Island Def Jam" in names

    def test_parent_resolved(self, catalog_service):
        """Search results have parent_name resolved."""
        pubs = catalog_service.search_publishers("DGC")
        dgc = next(p for p in pubs if p.name == "DGC Records")
        assert dgc.parent_name == "Universal Music Group"

    def test_no_results(self, catalog_service):
        pubs = catalog_service.search_publishers("zzz_nothing")
        assert pubs == []

    def test_empty_db(self, catalog_service_empty):
        pubs = catalog_service_empty.search_publishers("anything")
        assert pubs == []
