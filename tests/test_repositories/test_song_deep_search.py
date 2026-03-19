import pytest
from src.services.catalog_service import CatalogService


@pytest.fixture
def service(populated_db):
    return CatalogService(populated_db)


def test_search_title(service):
    # Match by title
    results = service.search_songs("Spirit")
    assert len(results) == 1
    assert results[0].title == "Smells Like Teen Spirit"


def test_search_album(service):
    # Match by album 'Nevermind' (Song 1)
    results = service.search_songs("Nevermind")
    assert len(results) == 1
    assert results[0].title == "Smells Like Teen Spirit"


def test_search_artist_alias(service):
    # 'Grohlton' is an alias for Dave Grohl (Identity 1).
    # Should find at minimum: Grohlton Theme + group songs
    results = service.search_songs("Grohlton")
    song_names = [s.title for s in results]
    assert "Grohlton Theme" in song_names
    assert "Smells Like Teen Spirit" in song_names
    assert "Everlong" in song_names


def test_search_identity_resolution(service):
    """LAW: Searching for 'Dave Grohl' should return Nirvana songs."""
    results = service.search_songs("Dave Grohl")
    song_names = [s.title for s in results]

    assert "Dual Credit Track" in song_names
    assert "Joint Venture" in song_names
    assert "Smells Like Teen Spirit" in song_names
    assert "Everlong" in song_names


def test_search_alias_expansion(service):
    """LAW: Searching for an alias (Grohlton) must find their groups (Nirvana/Foo Fighters)."""
    results = service.search_songs("Grohlton")
    song_names = [s.title for s in results]

    assert "Grohlton Theme" in song_names
    assert "Smells Like Teen Spirit" in song_names
    assert "Everlong" in song_names


def test_search_no_results(service):
    results = service.search_songs("NonexistentArtist")
    assert len(results) == 0
