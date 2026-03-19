"""
Contract tests for AlbumRepository, SongCreditRepository, SongAlbumRepository,
AlbumCreditRepository, TagRepository, and BaseRepository.
"""
import sqlite3
import pytest
from src.data.album_repository import AlbumRepository
from src.data.song_credit_repository import SongCreditRepository
from src.data.song_album_repository import SongAlbumRepository
from src.data.album_credit_repository import AlbumCreditRepository
from src.data.tag_repository import TagRepository
from src.data.base_repository import BaseRepository


# ===================================================================
# AlbumRepository
# ===================================================================
class TestAlbumRepositoryGetAll:
    def test_returns_both_albums_in_order(self, populated_db):
        repo = AlbumRepository(populated_db)
        albums = repo.get_all()
        assert len(albums) == 2
        # ORDER BY AlbumTitle COLLATE NOCASE ASC
        assert albums[0].title == "Nevermind"
        assert albums[0].id == 100
        assert albums[0].release_year == 1991
        assert albums[1].title == "The Colour and the Shape"
        assert albums[1].id == 200
        assert albums[1].release_year == 1997

    def test_empty_db(self, empty_db):
        repo = AlbumRepository(empty_db)
        assert repo.get_all() == []


class TestAlbumRepositorySearch:
    def test_exact_match(self, populated_db):
        repo = AlbumRepository(populated_db)
        albums = repo.search("Nevermind")
        assert len(albums) == 1
        assert albums[0].id == 100

    def test_partial_match(self, populated_db):
        repo = AlbumRepository(populated_db)
        albums = repo.search("Colour")
        assert len(albums) == 1
        assert albums[0].title == "The Colour and the Shape"

    def test_no_match(self, populated_db):
        repo = AlbumRepository(populated_db)
        assert repo.search("ZZZZZ") == []


class TestAlbumRepositoryGetById:
    def test_valid_id(self, populated_db):
        repo = AlbumRepository(populated_db)
        album = repo.get_by_id(100)
        assert album is not None
        assert album.title == "Nevermind"
        assert album.release_year == 1991

    def test_nonexistent(self, populated_db):
        repo = AlbumRepository(populated_db)
        assert repo.get_by_id(999) is None


class TestAlbumRepositoryGetSongIds:
    def test_nevermind_songs(self, populated_db):
        """Nevermind (100) contains Song 1."""
        repo = AlbumRepository(populated_db)
        song_ids = repo.get_song_ids_by_album(100)
        assert song_ids == [1]

    def test_tcats_songs(self, populated_db):
        """TCATS (200) contains Song 2."""
        repo = AlbumRepository(populated_db)
        song_ids = repo.get_song_ids_by_album(200)
        assert song_ids == [2]

    def test_nonexistent_album(self, populated_db):
        repo = AlbumRepository(populated_db)
        assert repo.get_song_ids_by_album(999) == []


class TestAlbumRepositoryGetSongIdsForAlbums:
    def test_batch_both_albums(self, populated_db):
        repo = AlbumRepository(populated_db)
        result = repo.get_song_ids_for_albums([100, 200])
        assert result[100] == [1]
        assert result[200] == [2]

    def test_empty_input(self, populated_db):
        repo = AlbumRepository(populated_db)
        assert repo.get_song_ids_for_albums([]) == {}


# ===================================================================
# SongCreditRepository
# ===================================================================
class TestSongCreditRepository:
    def test_single_credit_song(self, populated_db):
        """Song 1 (SLTS) has one credit: Nirvana (NameID=20), Performer."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([1])
        assert len(credits) == 1
        assert credits[0].source_id == 1
        assert credits[0].name_id == 20
        assert credits[0].display_name == "Nirvana"
        assert credits[0].role_name == "Performer"
        assert credits[0].role_id == 1
        assert credits[0].identity_id == 2  # Nirvana's OwnerIdentityID
        assert credits[0].is_primary is True

    def test_dual_credit_song(self, populated_db):
        """Song 6 has Dave Grohl (Performer) + Taylor Hawkins (Composer)."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([6])
        assert len(credits) == 2

        credit_map = {c.display_name: c for c in credits}
        assert "Dave Grohl" in credit_map
        assert "Taylor Hawkins" in credit_map
        assert credit_map["Dave Grohl"].role_name == "Performer"
        assert credit_map["Taylor Hawkins"].role_name == "Composer"

    def test_joint_performer_song(self, populated_db):
        """Song 8 (Joint Venture) has Dave + Taylor both as Performer."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([8])
        assert len(credits) == 2
        assert all(c.role_name == "Performer" for c in credits)
        names = {c.display_name for c in credits}
        assert names == {"Dave Grohl", "Taylor Hawkins"}

    def test_zero_credit_song(self, populated_db):
        """Song 7 (Hollow Song) has no credits."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([7])
        assert credits == []

    def test_alias_credit(self, populated_db):
        """Song 4 credited to Grohlton (NameID=11, alias of Dave, NOT primary)."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([4])
        assert len(credits) == 1
        assert credits[0].display_name == "Grohlton"
        assert credits[0].is_primary is False
        assert credits[0].identity_id == 1  # Dave's identity

    def test_empty_input(self, populated_db):
        repo = SongCreditRepository(populated_db)
        assert repo.get_credits_for_songs([]) == []

    def test_batch_multiple_songs(self, populated_db):
        """Batch fetch credits for songs 1, 2, 3 in one call."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([1, 2, 3])
        assert len(credits) == 3  # one credit per song
        names = {c.display_name for c in credits}
        assert names == {"Nirvana", "Foo Fighters", "Taylor Hawkins"}

    def test_null_role_raises_value_error(self, populated_db):
        """Contract: NULL RoleID must raise ValueError."""
        conn = sqlite3.connect(populated_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 as SourceID, 2 as CreditedNameID, NULL as RoleID, "
            "'Test' as DisplayName, 1 as IsPrimaryName, 1 as OwnerIdentityID, 'Performer' as RoleName"
        )
        row = cursor.fetchone()
        conn.close()

        repo = SongCreditRepository(populated_db)
        with pytest.raises(ValueError, match="Database integrity error"):
            repo._row_to_song_credit(row)


# ===================================================================
# SongAlbumRepository
# ===================================================================
class TestSongAlbumRepository:
    def test_song_1_album(self, populated_db):
        """Song 1 -> Nevermind (100), Track 1, Primary."""
        repo = SongAlbumRepository(populated_db)
        assocs = repo.get_albums_for_songs([1])
        assert len(assocs) == 1
        assert assocs[0].source_id == 1
        assert assocs[0].album_id == 100
        assert assocs[0].album_title == "Nevermind"
        assert assocs[0].track_number == 1
        assert assocs[0].is_primary is True
        assert assocs[0].release_year == 1991

    def test_song_2_album(self, populated_db):
        """Song 2 -> TCATS (200), Track 11."""
        repo = SongAlbumRepository(populated_db)
        assocs = repo.get_albums_for_songs([2])
        assert len(assocs) == 1
        assert assocs[0].album_title == "The Colour and the Shape"
        assert assocs[0].track_number == 11

    def test_song_without_album(self, populated_db):
        """Song 3 (Range Rover Bitch) has no album."""
        repo = SongAlbumRepository(populated_db)
        assocs = repo.get_albums_for_songs([3])
        assert assocs == []

    def test_empty_input(self, populated_db):
        repo = SongAlbumRepository(populated_db)
        assert repo.get_albums_for_songs([]) == []


# ===================================================================
# AlbumCreditRepository
# ===================================================================
class TestAlbumCreditRepository:
    def test_nevermind_credits(self, populated_db):
        """Nevermind (100) has Nirvana (NameID=20) as Performer."""
        repo = AlbumCreditRepository(populated_db)
        credits = repo.get_credits_for_albums([100])
        assert len(credits) == 1
        assert credits[0].album_id == 100
        assert credits[0].display_name == "Nirvana"
        assert credits[0].role_name == "Performer"

    def test_tcats_credits(self, populated_db):
        """TCATS (200) has Foo Fighters (NameID=30) as Performer."""
        repo = AlbumCreditRepository(populated_db)
        credits = repo.get_credits_for_albums([200])
        assert len(credits) == 1
        assert credits[0].display_name == "Foo Fighters"

    def test_batch_both_albums(self, populated_db):
        repo = AlbumCreditRepository(populated_db)
        credits = repo.get_credits_for_albums([100, 200])
        assert len(credits) == 2
        names = {c.display_name for c in credits}
        assert names == {"Nirvana", "Foo Fighters"}

    def test_empty_input(self, populated_db):
        repo = AlbumCreditRepository(populated_db)
        assert repo.get_credits_for_albums([]) == []


# ===================================================================
# TagRepository
# ===================================================================
class TestTagRepository:
    def test_song_1_tags(self, populated_db):
        """Song 1 has Grunge(1/Genre), Energetic(2/Mood), English(5/Jezik)."""
        repo = TagRepository(populated_db)
        results = repo.get_tags_for_songs([1])
        assert len(results) == 3

        tags = {tag.name: tag for _, tag in results}
        assert "Grunge" in tags
        assert tags["Grunge"].category == "Genre"
        assert tags["Grunge"].id == 1
        assert "Energetic" in tags
        assert tags["Energetic"].category == "Mood"
        assert "English" in tags
        assert tags["English"].category == "Jezik"

    def test_song_2_tags(self, populated_db):
        """Song 2 has only 90s(3/Era)."""
        repo = TagRepository(populated_db)
        results = repo.get_tags_for_songs([2])
        assert len(results) == 1
        _, tag = results[0]
        assert tag.name == "90s"
        assert tag.category == "Era"

    def test_song_with_no_tags(self, populated_db):
        """Song 3 (Range Rover Bitch) has no tags."""
        repo = TagRepository(populated_db)
        results = repo.get_tags_for_songs([3])
        assert results == []

    def test_primary_flag(self, populated_db):
        """Song 9 has Grunge (NOT primary) and Alt Rock (IS primary)."""
        repo = TagRepository(populated_db)
        results = repo.get_tags_for_songs([9])
        assert len(results) == 2

        tags = {tag.name: tag for _, tag in results}
        assert tags["Grunge"].is_primary is False
        assert tags["Alt Rock"].is_primary is True

    def test_batch_multiple_songs(self, populated_db):
        """Songs 1 + 2 should return 4 total tag associations."""
        repo = TagRepository(populated_db)
        results = repo.get_tags_for_songs([1, 2])
        assert len(results) == 4  # 3 for song 1 + 1 for song 2

    def test_empty_input(self, populated_db):
        repo = TagRepository(populated_db)
        assert repo.get_tags_for_songs([]) == []


# ===================================================================
# BaseRepository
# ===================================================================
class TestBaseRepositoryLogChange:
    def test_noop_when_values_equal(self, mock_db_path):
        """_log_change should NOT write if old == new."""
        repo = BaseRepository(mock_db_path)
        with repo._get_connection() as conn:
            cursor = conn.cursor()
            repo._log_change(cursor, "Songs", 1, "TempoBPM", "120", "120", "batch-1")
            count = cursor.execute("SELECT COUNT(*) FROM ChangeLog").fetchone()[0]
            assert count == 0

    def test_writes_when_values_differ(self, mock_db_path):
        """_log_change MUST write when old != new."""
        repo = BaseRepository(mock_db_path)
        with repo._get_connection() as conn:
            cursor = conn.cursor()
            repo._log_change(cursor, "Songs", 1, "TempoBPM", "120", "130", "batch-1")
            row = cursor.execute(
                "SELECT LogTableName, RecordID, LogFieldName, OldValue, NewValue, BatchID FROM ChangeLog"
            ).fetchone()
            assert row is not None
            assert row[0] == "Songs"
            assert row[1] == 1
            assert row[2] == "TempoBPM"
            assert row[3] == "120"
            assert row[4] == "130"
            assert row[5] == "batch-1"

    def test_none_to_value(self, mock_db_path):
        """_log_change should record None -> 'Hello'."""
        repo = BaseRepository(mock_db_path)
        with repo._get_connection() as conn:
            cursor = conn.cursor()
            repo._log_change(cursor, "Songs", 1, "Notes", None, "Hello", "batch-2")
            row = cursor.execute("SELECT OldValue, NewValue FROM ChangeLog").fetchone()
            assert row[0] is None
            assert row[1] == "Hello"
