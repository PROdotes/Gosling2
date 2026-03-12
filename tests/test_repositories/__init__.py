from src.data.base_repository import BaseRepository
from src.data.song_repository import SongRepository
from src.data.song_credit_repository import SongCreditRepository


def test_song_repository_get_by_ids(populated_db):
    repo = SongRepository(populated_db)
    songs = repo.get_by_ids([1, 2])
    assert len(songs) == 2
    assert {s.title for s in songs} == {"Smells Like Teen Spirit", "Everlong"}


def test_song_repository_get_by_ids_empty(populated_db):
    """LAW: Batch-fetching with empty list returns empty list immediately."""
    repo = SongRepository(populated_db)
    assert repo.get_by_ids([]) == []


def test_base_repository_log_change(mock_db_path):
    """LAW: _log_change must write a record to ChangeLog only if value actually changes."""
    repo = BaseRepository(mock_db_path)
    batch_id = "test-batch-123"

    with repo._get_connection() as conn:
        cursor = conn.cursor()

        # 1. No change (old == new) -> No row should be added
        repo._log_change(cursor, "Songs", 1, "TempoBPM", "120", "120", batch_id)
        count = cursor.execute("SELECT COUNT(*) FROM ChangeLog").fetchone()[0]
        assert count == 0

        # 2. Actual change -> Row should be added
        repo._log_change(cursor, "Songs", 1, "TempoBPM", "120", "130", batch_id)
        row = cursor.execute(
            "SELECT LogTableName, RecordID, OldValue, NewValue FROM ChangeLog"
        ).fetchone()
        assert row is not None
        assert row[0] == "Songs"
        assert row[1] == 1
        assert row[2] == "120"
        assert row[3] == "130"


def test_song_credit_repository_is_primary(populated_db):
    """LAW: SongCreditRepository must correctly map IsPrimaryName boolean."""
    repo = SongCreditRepository(populated_db)

    # From conftest.py:
    # Dave Grohl (ID 10) is primary (1)
    # Grohlton (ID 11) is not primary (0)

    # Check Dave Grohl on Song 6
    results_6 = repo.get_credits_for_songs([6])
    credits_6 = {c.name_id: c for c in results_6}
    assert credits_6[10].is_primary is True
    assert credits_6[10].display_name == "Dave Grohl"

    # Check Grohlton on Song 4
    results_4 = repo.get_credits_for_songs([4])
    credits_4 = {c.name_id: c for c in results_4}
    assert credits_4[11].is_primary is False
    assert credits_4[11].display_name == "Grohlton"


def test_song_credit_repository_null_role(populated_db):
    """LAW: SongCreditRepository must raise ValueError if RoleID is missing."""
    import pytest
    import sqlite3

    # Generate a real sqlite3.Row with a NULL RoleID via an ephemeral SELECT
    conn = sqlite3.connect(populated_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 as SourceID, 2 as CreditedNameID, NULL as RoleID, 'Test' as DisplayName, 1 as IsPrimaryName"
    )
    row = cursor.fetchone()
    conn.close()

    repo = SongCreditRepository(populated_db)
    with pytest.raises(ValueError, match="Database integrity error"):
        repo._row_to_song_credit(row)


def test_song_album_repository_get_albums_empty(populated_db):
    from src.data.song_album_repository import SongAlbumRepository

    repo = SongAlbumRepository(populated_db)
    assert repo.get_albums_for_songs([]) == []


def test_publisher_repository_get_publishers(populated_db):
    from src.data.publisher_repository import PublisherRepository

    repo = PublisherRepository(populated_db)
    assert repo.get_publishers([]) == {}

    pubs = repo.get_publishers([1, 2])
    assert len(pubs) == 2
    assert pubs[1].name == "DGC Records"
    assert pubs[2].name == "Roswell Records"


def test_publisher_repository_get_publishers_for_songs_empty(populated_db):
    from src.data.publisher_repository import PublisherRepository

    repo = PublisherRepository(populated_db)
    assert repo.get_publishers_for_songs([]) == []


def test_tag_repository_get_tags_empty(populated_db):
    from src.data.tag_repository import TagRepository

    repo = TagRepository(populated_db)
    assert repo.get_tags_for_songs([]) == []
