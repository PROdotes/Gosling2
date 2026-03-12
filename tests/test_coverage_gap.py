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
async def test_router_search_short_query(populated_db):
    """Router coverage: 400 for short query."""
    import os

    os.environ["GOSLING_DB_PATH"] = populated_db
    with pytest.raises(HTTPException) as excinfo:
        await search_songs(q="A")
    assert excinfo.value.status_code == 400


def test_repositories_empty_inputs(populated_db):
    """Repo coverage: Ensure empty input paths are executed."""
    db = populated_db
    SongRepository(db).get_by_ids([])
    SongCreditRepository(db).get_credits_for_songs([])
    SongAlbumRepository(db).get_albums_for_songs([])
    PublisherRepository(db).get_publishers_for_songs([])
    PublisherRepository(db).get_publishers_for_albums([])
    TagRepository(db).get_tags_for_songs([])


def test_song_display_artist_fallback(populated_db):
    """Domain coverage: Song with credits but NO performers."""
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
    view = SongView.from_domain(song)
    assert view.display_artist == "Dave Grohl"


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
    # The populated_db has IDs 1, 2, 3
    res = repo.get_publishers([1, 2])
    assert len(res) == 2
    assert res[1].name == "DGC Records"

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


def test_base_repository_log_change(populated_db):
    """BaseRepository coverage: Audit logging logic."""
    from src.data.base_repository import BaseRepository
    import sqlite3

    repo = BaseRepository(populated_db)
    conn = sqlite3.connect(populated_db)
    cursor = conn.cursor()

    # Create ChangeLog table if it doesn't exist (it should be in schema)
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS ChangeLog (LogTableName TEXT, RecordID INTEGER, LogFieldName TEXT, OldValue TEXT, NewValue TEXT, BatchID TEXT)"
    )

    # 1. No change (should return early)
    repo._log_change(cursor, "Songs", 1, "Notes", "Test", "Test", "B1")

    # 2. Real change
    repo._log_change(cursor, "Songs", 1, "Notes", "Old", "New", "B2")

    # 3. Change with None
    repo._log_change(cursor, "Songs", 1, "Notes", None, "New", "B3")

    conn.commit()
    conn.close()
