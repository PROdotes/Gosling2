import pytest
from src.v3core.services.catalog_service import CatalogService


def test_get_song_exists(populated_db):
    """LAW: Fetching a valid song ID returns the complete Song domain model."""
    service = CatalogService(populated_db)

    # 2 = Everlong in populated_db
    song = service.get_song(2)

    assert song is not None
    assert song.id == 2
    assert song.title == "Everlong"
    assert song.duration_ms == 240000

    # Verify credits hydration
    assert len(song.credits) == 1
    assert song.credits[0].display_name == "Foo Fighters"
    assert song.credits[0].role_id == 1


def test_get_song_multiple_credits(populated_db):
    """LAW: A song with multiple credits should be fully hydrated with all of them."""
    service = CatalogService(populated_db)
    song = service.get_song(6)

    assert song is not None
    assert len(song.credits) == 2

    # Check specific credits
    names = {c.display_name for c in song.credits}
    assert "Dave Grohl" in names
    assert "Taylor Hawkins" in names


def test_get_song_no_credits(populated_db):
    """LAW: A song with no credits should return an empty list of credits, not None or error."""
    service = CatalogService(populated_db)
    song = service.get_song(7)

    assert song is not None
    assert song.title == "Hollow Song"
    assert song.credits == []


def test_get_song_not_found(populated_db):
    """LAW: Fetching a non-existent ID returns None."""
    service = CatalogService(populated_db)
    song = service.get_song(999)
    assert song is None
