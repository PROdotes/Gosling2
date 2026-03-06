from src.data.song_repository import SongRepository
from src.services.catalog_service import CatalogService


def test_repository_get_by_title_matches(populated_db):
    """Verify that SongRepository can find a song by title."""
    repo = SongRepository(populated_db)

    # Query for 'Everlong'
    songs = repo.get_by_title("Everlong")

    assert len(songs) >= 1
    assert songs[0].title == "Everlong"
    assert songs[0].id == 2  # Based on conftest.py:L106


def test_catalog_service_search_hydrates_credits(populated_db):
    """Verify that CatalogService hydrates search results with credits."""
    service = CatalogService(populated_db)

    # Query for 'Everlong'
    songs = service.search_songs("Everlong")

    assert len(songs) >= 1
    song = songs[0]
    assert song.title == "Everlong"

    # Verify credits are attached
    assert len(song.credits) >= 1
    credit_names = [c.display_name for c in song.credits]
    assert "Foo Fighters" in credit_names


def test_catalog_service_search_no_results(populated_db):
    """Verify empty list for non-matching queries."""
    service = CatalogService(populated_db)
    songs = service.search_songs("NonExistentSong")
    assert len(songs) == 0
