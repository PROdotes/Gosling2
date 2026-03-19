import pytest
from fastapi import HTTPException
from src.engine.routers.catalog import get_song, search_songs
from src.data.song_repository import SongRepository
from src.data.song_credit_repository import SongCreditRepository
from src.data.song_album_repository import SongAlbumRepository
from src.data.publisher_repository import PublisherRepository
from src.data.tag_repository import TagRepository
from src.models.domain import Song
from src.models.view_models import SongView


@pytest.mark.asyncio
async def test_router_get_song_not_found(populated_db):
    """Router coverage: 404 for missing song."""
    import os

    os.environ["GOSLING_DB_PATH"] = populated_db
    with pytest.raises(HTTPException) as excinfo:
        await get_song(9999)
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_router_search_short_query_success(populated_db):
    """Router coverage: Single character query now allowed."""
    import os

    os.environ["GOSLING_DB_PATH"] = populated_db
    res = await search_songs(q="A")
    assert isinstance(res, list)


def test_repositories_empty_inputs(populated_db):
    """Repo coverage: Empty inputs return empty results."""
    db = populated_db
    assert SongRepository(db).get_by_ids([]) == []
    assert SongCreditRepository(db).get_credits_for_songs([]) == []
    assert SongAlbumRepository(db).get_albums_for_songs([]) == []
    assert PublisherRepository(db).get_publishers_for_songs([]) == []
    assert PublisherRepository(db).get_publishers_for_albums([]) == []
    assert TagRepository(db).get_tags_for_songs([]) == []


def test_song_display_artist_composer_only(populated_db):
    """Domain coverage: Song with credits but NO performers returns None."""
    import sqlite3
    from src.services.catalog_service import CatalogService

    # Insert a song with only a Composer
    conn = sqlite3.connect(populated_db)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration) VALUES (99, 1, 'Composer Only', '/path/99', 100)"
    )
    cursor.execute("INSERT INTO Songs (SourceID) VALUES (99)")
    cursor.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (99, 10, 2)"
    )  # Dave as Composer
    conn.commit()
    conn.close()

    service = CatalogService(populated_db)
    song = service.get_song(99)
    assert song is not None
    view = SongView.from_domain(song)
    assert view.display_artist is None  # Composers are not Performers


def test_domain_edge_cases(populated_db):
    """Domain coverage: duration_ms=0 and no credits."""

    # 1. duration_ms = 0
    song1 = Song(id=1, type_id=1, media_name="S1", source_path="P1", duration_ms=0)
    view1 = SongView.from_domain(song1)
    assert view1.formatted_duration == "0:00"

    # 2. no credits
    song2 = Song(
        id=2, type_id=1, media_name="S2", source_path="P2", duration_ms=1000, credits=[]
    )
    view2 = SongView.from_domain(song2)
    assert view2.display_artist is None


def test_publisher_repository_get_publishers(populated_db):
    """Repo coverage: get_publishers resolution."""
    from src.data.publisher_repository import PublisherRepository

    repo = PublisherRepository(populated_db)
    # The populated_db has IDs 1 (UMG), 2 (Island), 3 (IDJ), 4 (Roswell), 5 (Sub Pop), 10 (DGC)
    res = repo.get_publishers([1, 10])
    assert len(res) == 2
    assert res[1].name == "Universal Music Group"
    assert res[10].name == "DGC Records"

    assert repo.get_publishers([]) == {}


@pytest.mark.asyncio
async def test_router_get_song_success(populated_db):
    """Router coverage: Successful get_song hit."""
    import os

    os.environ["GOSLING_DB_PATH"] = populated_db
    from src.engine.routers.catalog import get_song

    res = await get_song(1)
    assert res.id == 1
    assert res.title == "Smells Like Teen Spirit"


def test_song_credit_repository_integrity_failure_mock(populated_db):
    """Repo coverage: Mocked DB integrity error for NULL RoleID."""
    from src.data.song_credit_repository import SongCreditRepository

    repo = SongCreditRepository(populated_db)
    mock_row = {
        "SourceID": 1,
        "CreditedNameID": 10,
        "RoleID": None,
        "RoleName": "P",
        "DisplayName": "D",
        "IsPrimaryName": 1,
    }
    with pytest.raises(ValueError) as excinfo:
        repo._row_to_song_credit(mock_row)
    assert "RoleID cannot be NULL" in str(excinfo.value)
