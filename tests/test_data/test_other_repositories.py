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
        """get_all must return albums sorted by AlbumTitle COLLATE NOCASE ASC with all fields."""
        repo = AlbumRepository(populated_db)
        albums = repo.get_all()
        assert len(albums) == 2, f"Expected 2 albums, got {len(albums)}"

        # ORDER BY AlbumTitle COLLATE NOCASE ASC -> Nevermind before The Colour and the Shape
        assert albums[0].id == 100, f"Expected id=100, got {albums[0].id}"
        assert (
            albums[0].title == "Nevermind"
        ), f"Expected 'Nevermind', got '{albums[0].title}'"
        assert (
            albums[0].album_type is None
        ), f"Expected album_type=None, got {albums[0].album_type!r}"
        assert (
            albums[0].release_year == 1991
        ), f"Expected release_year=1991, got {albums[0].release_year}"
        assert (
            albums[0].publishers == []
        ), f"Expected publishers=[], got {albums[0].publishers}"
        assert albums[0].credits == [], f"Expected credits=[], got {albums[0].credits}"
        assert albums[0].songs == [], f"Expected songs=[], got {albums[0].songs}"

        assert albums[1].id == 200, f"Expected id=200, got {albums[1].id}"
        assert (
            albums[1].title == "The Colour and the Shape"
        ), f"Expected 'The Colour and the Shape', got '{albums[1].title}'"
        assert (
            albums[1].album_type is None
        ), f"Expected album_type=None, got {albums[1].album_type!r}"
        assert (
            albums[1].release_year == 1997
        ), f"Expected release_year=1997, got {albums[1].release_year}"
        assert (
            albums[1].publishers == []
        ), f"Expected publishers=[], got {albums[1].publishers}"
        assert albums[1].credits == [], f"Expected credits=[], got {albums[1].credits}"
        assert albums[1].songs == [], f"Expected songs=[], got {albums[1].songs}"

    def test_returns_empty_list_on_empty_db(self, empty_db):
        """get_all on an empty DB must return an empty list, not None or an error."""
        repo = AlbumRepository(empty_db)
        result = repo.get_all()
        assert result == [], f"Expected [], got {result!r}"


class TestAlbumRepositorySearch:
    def test_exact_match_returns_single_album(self, populated_db):
        """search('Nevermind') must return exactly one album with all fields populated."""
        repo = AlbumRepository(populated_db)
        albums = repo.search("Nevermind")
        assert len(albums) == 1, f"Expected 1 album, got {len(albums)}"
        assert albums[0].id == 100, f"Expected id=100, got {albums[0].id}"
        assert (
            albums[0].title == "Nevermind"
        ), f"Expected 'Nevermind', got '{albums[0].title}'"
        assert (
            albums[0].album_type is None
        ), f"Expected album_type=None, got {albums[0].album_type!r}"
        assert (
            albums[0].release_year == 1991
        ), f"Expected release_year=1991, got {albums[0].release_year}"
        assert (
            albums[0].publishers == []
        ), f"Expected publishers=[], got {albums[0].publishers}"
        assert albums[0].credits == [], f"Expected credits=[], got {albums[0].credits}"
        assert albums[0].songs == [], f"Expected songs=[], got {albums[0].songs}"

    def test_partial_match_returns_album(self, populated_db):
        """search('Colour') must match 'The Colour and the Shape' via LIKE with all fields."""
        repo = AlbumRepository(populated_db)
        albums = repo.search("Colour")
        assert len(albums) == 1, f"Expected 1 album, got {len(albums)}"
        assert albums[0].id == 200, f"Expected id=200, got {albums[0].id}"
        assert (
            albums[0].title == "The Colour and the Shape"
        ), f"Expected 'The Colour and the Shape', got '{albums[0].title}'"
        assert (
            albums[0].album_type is None
        ), f"Expected album_type=None, got {albums[0].album_type!r}"
        assert (
            albums[0].release_year == 1997
        ), f"Expected release_year=1997, got {albums[0].release_year}"
        assert (
            albums[0].publishers == []
        ), f"Expected publishers=[], got {albums[0].publishers}"
        assert albums[0].credits == [], f"Expected credits=[], got {albums[0].credits}"
        assert albums[0].songs == [], f"Expected songs=[], got {albums[0].songs}"

    def test_no_match_returns_empty_list(self, populated_db):
        """search('ZZZZZ') must return an empty list when no albums match."""
        repo = AlbumRepository(populated_db)
        result = repo.search("ZZZZZ")
        assert result == [], f"Expected [], got {result!r}"


class TestAlbumRepositoryGetById:
    def test_valid_id_returns_album_with_all_fields(self, populated_db):
        """get_by_id(100) must return the Nevermind album with every field set."""
        repo = AlbumRepository(populated_db)
        album = repo.get_by_id(100)
        assert album is not None, "Expected album, got None"
        assert album.id == 100, f"Expected id=100, got {album.id}"
        assert album.title == "Nevermind", f"Expected 'Nevermind', got '{album.title}'"
        assert (
            album.album_type is None
        ), f"Expected album_type=None, got {album.album_type!r}"
        assert (
            album.release_year == 1991
        ), f"Expected release_year=1991, got {album.release_year}"
        assert album.publishers == [], f"Expected publishers=[], got {album.publishers}"
        assert album.credits == [], f"Expected credits=[], got {album.credits}"
        assert album.songs == [], f"Expected songs=[], got {album.songs}"

    def test_nonexistent_id_returns_none(self, populated_db):
        """get_by_id(999) must return None for a non-existent album."""
        repo = AlbumRepository(populated_db)
        result = repo.get_by_id(999)
        assert result is None, f"Expected None, got {result!r}"


class TestAlbumRepositoryGetSongIds:
    def test_nevermind_contains_song_1(self, populated_db):
        """Nevermind (100) contains exactly Song 1."""
        repo = AlbumRepository(populated_db)
        song_ids = repo.get_song_ids_by_album(100)
        assert song_ids == [1], f"Expected [1], got {song_ids!r}"

    def test_tcats_contains_song_2(self, populated_db):
        """TCATS (200) contains exactly Song 2."""
        repo = AlbumRepository(populated_db)
        song_ids = repo.get_song_ids_by_album(200)
        assert song_ids == [2], f"Expected [2], got {song_ids!r}"

    def test_nonexistent_album_returns_empty_list(self, populated_db):
        """get_song_ids_by_album(999) must return [] for a non-existent album."""
        repo = AlbumRepository(populated_db)
        result = repo.get_song_ids_by_album(999)
        assert result == [], f"Expected [], got {result!r}"


class TestAlbumRepositoryGetSongIdsForAlbums:
    def test_batch_both_albums_returns_correct_mapping(self, populated_db):
        """Batch fetch for [100, 200] must map each album to its song IDs."""
        repo = AlbumRepository(populated_db)
        result = repo.get_song_ids_for_albums([100, 200])
        assert len(result) == 2, f"Expected 2 keys, got {len(result)}"
        assert result[100] == [
            1
        ], f"Expected [1] for album 100, got {result.get(100)!r}"
        assert result[200] == [
            2
        ], f"Expected [2] for album 200, got {result.get(200)!r}"

    def test_empty_input_returns_empty_dict(self, populated_db):
        """get_song_ids_for_albums([]) must return an empty dict."""
        repo = AlbumRepository(populated_db)
        result = repo.get_song_ids_for_albums([])
        assert result == {}, f"Expected {{}}, got {result!r}"


# ===================================================================
# SongCreditRepository
# ===================================================================
class TestSongCreditRepository:
    def test_single_credit_song_returns_one_credit_with_all_fields(self, populated_db):
        """Song 1 (SLTS) has one credit: Nirvana (NameID=20), Performer."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([1])
        assert len(credits) == 1, f"Expected 1 credit, got {len(credits)}"
        assert (
            credits[0].source_id == 1
        ), f"Expected source_id=1, got {credits[0].source_id}"
        assert (
            credits[0].name_id == 20
        ), f"Expected name_id=20, got {credits[0].name_id}"
        assert (
            credits[0].identity_id == 2
        ), f"Expected identity_id=2, got {credits[0].identity_id}"
        assert credits[0].role_id == 1, f"Expected role_id=1, got {credits[0].role_id}"
        assert (
            credits[0].role_name == "Performer"
        ), f"Expected role_name='Performer', got '{credits[0].role_name}'"
        assert (
            credits[0].display_name == "Nirvana"
        ), f"Expected display_name='Nirvana', got '{credits[0].display_name}'"
        assert (
            credits[0].is_primary is True
        ), f"Expected is_primary=True, got {credits[0].is_primary}"

    def test_dual_credit_song_returns_both_with_all_fields(self, populated_db):
        """Song 6 has Dave Grohl (Performer) + Taylor Hawkins (Composer)."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([6])
        assert len(credits) == 2, f"Expected 2 credits, got {len(credits)}"

        credit_map = {c.display_name: c for c in credits}
        assert (
            "Dave Grohl" in credit_map
        ), f"Expected 'Dave Grohl' in credits, got {list(credit_map.keys())}"
        assert (
            "Taylor Hawkins" in credit_map
        ), f"Expected 'Taylor Hawkins' in credits, got {list(credit_map.keys())}"

        dave = credit_map["Dave Grohl"]
        assert dave.source_id == 6, f"Expected source_id=6, got {dave.source_id}"
        assert dave.name_id == 10, f"Expected name_id=10, got {dave.name_id}"
        assert dave.identity_id == 1, f"Expected identity_id=1, got {dave.identity_id}"
        assert dave.role_id == 1, f"Expected role_id=1, got {dave.role_id}"
        assert (
            dave.role_name == "Performer"
        ), f"Expected role_name='Performer', got '{dave.role_name}'"
        assert (
            dave.is_primary is True
        ), f"Expected is_primary=True, got {dave.is_primary}"

        taylor = credit_map["Taylor Hawkins"]
        assert taylor.source_id == 6, f"Expected source_id=6, got {taylor.source_id}"
        assert taylor.name_id == 40, f"Expected name_id=40, got {taylor.name_id}"
        assert (
            taylor.identity_id == 4
        ), f"Expected identity_id=4, got {taylor.identity_id}"
        assert taylor.role_id == 2, f"Expected role_id=2, got {taylor.role_id}"
        assert (
            taylor.role_name == "Composer"
        ), f"Expected role_name='Composer', got '{taylor.role_name}'"
        assert (
            taylor.is_primary is True
        ), f"Expected is_primary=True, got {taylor.is_primary}"

    def test_joint_performer_song_returns_both_as_performer(self, populated_db):
        """Song 8 (Joint Venture) has Dave + Taylor both as Performer."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([8])
        assert len(credits) == 2, f"Expected 2 credits, got {len(credits)}"
        assert all(
            c.role_name == "Performer" for c in credits
        ), f"Expected all Performer, got {[c.role_name for c in credits]}"
        names = {c.display_name for c in credits}
        assert names == {
            "Dave Grohl",
            "Taylor Hawkins",
        }, f"Expected {{'Dave Grohl', 'Taylor Hawkins'}}, got {names}"

    def test_zero_credit_song_returns_empty_list(self, populated_db):
        """Song 7 (Hollow Song) has no credits."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([7])
        assert credits == [], f"Expected [], got {credits!r}"

    def test_alias_credit_returns_alias_name_not_primary(self, populated_db):
        """Song 4 credited to Grohlton (NameID=11, alias of Dave, NOT primary)."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([4])
        assert len(credits) == 1, f"Expected 1 credit, got {len(credits)}"
        assert (
            credits[0].source_id == 4
        ), f"Expected source_id=4, got {credits[0].source_id}"
        assert (
            credits[0].name_id == 11
        ), f"Expected name_id=11, got {credits[0].name_id}"
        assert (
            credits[0].identity_id == 1
        ), f"Expected identity_id=1, got {credits[0].identity_id}"
        assert credits[0].role_id == 1, f"Expected role_id=1, got {credits[0].role_id}"
        assert (
            credits[0].role_name == "Performer"
        ), f"Expected role_name='Performer', got '{credits[0].role_name}'"
        assert (
            credits[0].display_name == "Grohlton"
        ), f"Expected display_name='Grohlton', got '{credits[0].display_name}'"
        assert (
            credits[0].is_primary is False
        ), f"Expected is_primary=False, got {credits[0].is_primary}"

    def test_empty_input_returns_empty_list(self, populated_db):
        """get_credits_for_songs([]) must return an empty list."""
        repo = SongCreditRepository(populated_db)
        result = repo.get_credits_for_songs([])
        assert result == [], f"Expected [], got {result!r}"

    def test_batch_multiple_songs_returns_all_credits(self, populated_db):
        """Batch fetch credits for songs 1, 2, 3 in one call (one credit per song)."""
        repo = SongCreditRepository(populated_db)
        credits = repo.get_credits_for_songs([1, 2, 3])
        assert len(credits) == 3, f"Expected 3 credits, got {len(credits)}"
        names = {c.display_name for c in credits}
        assert names == {
            "Nirvana",
            "Foo Fighters",
            "Taylor Hawkins",
        }, f"Expected {{'Nirvana', 'Foo Fighters', 'Taylor Hawkins'}}, got {names}"

    def test_null_role_raises_value_error(self, populated_db):
        """Contract: NULL RoleID must raise ValueError with 'Database integrity error'."""
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
    def test_song_1_album_returns_association_with_all_fields(self, populated_db):
        """Song 1 -> Nevermind (100), Track 1, Primary."""
        repo = SongAlbumRepository(populated_db)
        assocs = repo.get_albums_for_songs([1])
        assert len(assocs) == 1, f"Expected 1 association, got {len(assocs)}"
        assert (
            assocs[0].source_id == 1
        ), f"Expected source_id=1, got {assocs[0].source_id}"
        assert (
            assocs[0].album_id == 100
        ), f"Expected album_id=100, got {assocs[0].album_id}"
        assert (
            assocs[0].track_number == 1
        ), f"Expected track_number=1, got {assocs[0].track_number}"
        assert (
            assocs[0].disc_number == 1
        ), f"Expected disc_number=1, got {assocs[0].disc_number!r}"
        assert (
            assocs[0].is_primary is True
        ), f"Expected is_primary=True, got {assocs[0].is_primary}"
        assert (
            assocs[0].album_title == "Nevermind"
        ), f"Expected album_title='Nevermind', got '{assocs[0].album_title}'"
        assert (
            assocs[0].album_type is None
        ), f"Expected album_type=None, got {assocs[0].album_type!r}"
        assert (
            assocs[0].release_year == 1991
        ), f"Expected release_year=1991, got {assocs[0].release_year}"
        assert (
            assocs[0].album_publishers == []
        ), f"Expected album_publishers=[], got {assocs[0].album_publishers}"
        assert assocs[0].credits == [], f"Expected credits=[], got {assocs[0].credits}"

    def test_song_2_album_returns_association_with_all_fields(self, populated_db):
        """Song 2 -> TCATS (200), Track 11."""
        repo = SongAlbumRepository(populated_db)
        assocs = repo.get_albums_for_songs([2])
        assert len(assocs) == 1, f"Expected 1 association, got {len(assocs)}"
        assert (
            assocs[0].source_id == 2
        ), f"Expected source_id=2, got {assocs[0].source_id}"
        assert (
            assocs[0].album_id == 200
        ), f"Expected album_id=200, got {assocs[0].album_id}"
        assert (
            assocs[0].track_number == 11
        ), f"Expected track_number=11, got {assocs[0].track_number}"
        assert (
            assocs[0].disc_number == 1
        ), f"Expected disc_number=1, got {assocs[0].disc_number!r}"
        assert (
            assocs[0].is_primary is True
        ), f"Expected is_primary=True, got {assocs[0].is_primary}"
        assert (
            assocs[0].album_title == "The Colour and the Shape"
        ), f"Expected album_title='The Colour and the Shape', got '{assocs[0].album_title}'"
        assert (
            assocs[0].album_type is None
        ), f"Expected album_type=None, got {assocs[0].album_type!r}"
        assert (
            assocs[0].release_year == 1997
        ), f"Expected release_year=1997, got {assocs[0].release_year}"
        assert (
            assocs[0].album_publishers == []
        ), f"Expected album_publishers=[], got {assocs[0].album_publishers}"
        assert assocs[0].credits == [], f"Expected credits=[], got {assocs[0].credits}"

    def test_song_without_album_returns_empty_list(self, populated_db):
        """Song 3 (Range Rover Bitch) has no album associations."""
        repo = SongAlbumRepository(populated_db)
        assocs = repo.get_albums_for_songs([3])
        assert assocs == [], f"Expected [], got {assocs!r}"

    def test_empty_input_returns_empty_list(self, populated_db):
        """get_albums_for_songs([]) must return an empty list."""
        repo = SongAlbumRepository(populated_db)
        result = repo.get_albums_for_songs([])
        assert result == [], f"Expected [], got {result!r}"


# ===================================================================
# AlbumCreditRepository
# ===================================================================
class TestAlbumCreditRepository:
    def test_nevermind_credits_returns_nirvana_performer(self, populated_db):
        """Nevermind (100) has Nirvana (NameID=20) as Performer with all fields."""
        repo = AlbumCreditRepository(populated_db)
        credits = repo.get_credits_for_albums([100])
        assert len(credits) == 1, f"Expected 1 credit, got {len(credits)}"
        assert (
            credits[0].album_id == 100
        ), f"Expected album_id=100, got {credits[0].album_id}"
        assert (
            credits[0].name_id == 20
        ), f"Expected name_id=20, got {credits[0].name_id}"
        assert (
            credits[0].identity_id == 2
        ), f"Expected identity_id=2, got {credits[0].identity_id}"
        assert credits[0].role_id == 1, f"Expected role_id=1, got {credits[0].role_id}"
        assert (
            credits[0].role_name == "Performer"
        ), f"Expected role_name='Performer', got '{credits[0].role_name}'"
        assert (
            credits[0].display_name == "Nirvana"
        ), f"Expected display_name='Nirvana', got '{credits[0].display_name}'"
        assert (
            credits[0].is_primary is True
        ), f"Expected is_primary=True, got {credits[0].is_primary}"

    def test_tcats_credits_returns_foo_fighters_performer(self, populated_db):
        """TCATS (200) has Foo Fighters (NameID=30) as Performer with all fields."""
        repo = AlbumCreditRepository(populated_db)
        credits = repo.get_credits_for_albums([200])
        assert len(credits) == 1, f"Expected 1 credit, got {len(credits)}"
        assert (
            credits[0].album_id == 200
        ), f"Expected album_id=200, got {credits[0].album_id}"
        assert (
            credits[0].name_id == 30
        ), f"Expected name_id=30, got {credits[0].name_id}"
        assert (
            credits[0].identity_id == 3
        ), f"Expected identity_id=3, got {credits[0].identity_id}"
        assert credits[0].role_id == 1, f"Expected role_id=1, got {credits[0].role_id}"
        assert (
            credits[0].role_name == "Performer"
        ), f"Expected role_name='Performer', got '{credits[0].role_name}'"
        assert (
            credits[0].display_name == "Foo Fighters"
        ), f"Expected display_name='Foo Fighters', got '{credits[0].display_name}'"
        assert (
            credits[0].is_primary is True
        ), f"Expected is_primary=True, got {credits[0].is_primary}"

    def test_batch_both_albums_returns_two_credits(self, populated_db):
        """Batch fetch for [100, 200] returns credits from both albums."""
        repo = AlbumCreditRepository(populated_db)
        credits = repo.get_credits_for_albums([100, 200])
        assert len(credits) == 2, f"Expected 2 credits, got {len(credits)}"
        names = {c.display_name for c in credits}
        assert names == {
            "Nirvana",
            "Foo Fighters",
        }, f"Expected {{'Nirvana', 'Foo Fighters'}}, got {names}"

    def test_empty_input_returns_empty_list(self, populated_db):
        """get_credits_for_albums([]) must return an empty list."""
        repo = AlbumCreditRepository(populated_db)
        result = repo.get_credits_for_albums([])
        assert result == [], f"Expected [], got {result!r}"


# ===================================================================
# TagRepository
# ===================================================================
class TestTagRepository:
    def test_song_1_tags_returns_three_tags_with_all_fields(self, populated_db):
        """Song 1 has Grunge(1/Genre), Energetic(2/Mood), English(5/Jezik)."""
        repo = TagRepository(populated_db)
        results = repo.get_tags_for_songs([1])
        assert len(results) == 3, f"Expected 3 tag results, got {len(results)}"

        tags = {tag.name: tag for _, tag in results}
        assert "Grunge" in tags, f"Expected 'Grunge' in tags, got {list(tags.keys())}"
        assert (
            tags["Grunge"].id == 1
        ), f"Expected id=1 for Grunge, got {tags['Grunge'].id}"
        assert (
            tags["Grunge"].category == "Genre"
        ), f"Expected category='Genre' for Grunge, got '{tags['Grunge'].category}'"
        assert (
            tags["Grunge"].is_primary is False
        ), f"Expected is_primary=False for Grunge, got {tags['Grunge'].is_primary}"

        assert (
            "Energetic" in tags
        ), f"Expected 'Energetic' in tags, got {list(tags.keys())}"
        assert (
            tags["Energetic"].id == 2
        ), f"Expected id=2 for Energetic, got {tags['Energetic'].id}"
        assert (
            tags["Energetic"].category == "Mood"
        ), f"Expected category='Mood' for Energetic, got '{tags['Energetic'].category}'"
        assert (
            tags["Energetic"].is_primary is False
        ), f"Expected is_primary=False for Energetic, got {tags['Energetic'].is_primary}"

        assert "English" in tags, f"Expected 'English' in tags, got {list(tags.keys())}"
        assert (
            tags["English"].id == 5
        ), f"Expected id=5 for English, got {tags['English'].id}"
        assert (
            tags["English"].category == "Jezik"
        ), f"Expected category='Jezik' for English, got '{tags['English'].category}'"
        assert (
            tags["English"].is_primary is False
        ), f"Expected is_primary=False for English, got {tags['English'].is_primary}"

    def test_song_2_tags_returns_single_tag_with_all_fields(self, populated_db):
        """Song 2 has only 90s(3/Era)."""
        repo = TagRepository(populated_db)
        results = repo.get_tags_for_songs([2])
        assert len(results) == 1, f"Expected 1 tag result, got {len(results)}"
        _, tag = results[0]
        assert tag.id == 3, f"Expected id=3, got {tag.id}"
        assert tag.name == "90s", f"Expected name='90s', got '{tag.name}'"
        assert tag.category == "Era", f"Expected category='Era', got '{tag.category}'"
        assert (
            tag.is_primary is False
        ), f"Expected is_primary=False, got {tag.is_primary}"

    def test_song_with_no_tags_returns_empty_list(self, populated_db):
        """Song 3 (Range Rover Bitch) has no tags."""
        repo = TagRepository(populated_db)
        results = repo.get_tags_for_songs([3])
        assert results == [], f"Expected [], got {results!r}"

    def test_primary_flag_on_song_9_tags(self, populated_db):
        """Song 9 has Grunge (NOT primary) and Alt Rock (IS primary)."""
        repo = TagRepository(populated_db)
        results = repo.get_tags_for_songs([9])
        assert len(results) == 2, f"Expected 2 tag results, got {len(results)}"

        tags = {tag.name: tag for _, tag in results}
        assert "Grunge" in tags, f"Expected 'Grunge' in tags, got {list(tags.keys())}"
        assert (
            tags["Grunge"].id == 1
        ), f"Expected id=1 for Grunge, got {tags['Grunge'].id}"
        assert (
            tags["Grunge"].category == "Genre"
        ), f"Expected category='Genre' for Grunge, got '{tags['Grunge'].category}'"
        assert (
            tags["Grunge"].is_primary is False
        ), f"Expected is_primary=False for Grunge, got {tags['Grunge'].is_primary}"

        assert (
            "Alt Rock" in tags
        ), f"Expected 'Alt Rock' in tags, got {list(tags.keys())}"
        assert (
            tags["Alt Rock"].id == 6
        ), f"Expected id=6 for Alt Rock, got {tags['Alt Rock'].id}"
        assert (
            tags["Alt Rock"].category == "Genre"
        ), f"Expected category='Genre' for Alt Rock, got '{tags['Alt Rock'].category}'"
        assert (
            tags["Alt Rock"].is_primary is True
        ), f"Expected is_primary=True for Alt Rock, got {tags['Alt Rock'].is_primary}"

    def test_batch_multiple_songs_returns_all_tag_associations(self, populated_db):
        """Songs 1 + 2 should return 4 total tag associations (3 for song 1, 1 for song 2)."""
        repo = TagRepository(populated_db)
        results = repo.get_tags_for_songs([1, 2])
        assert len(results) == 4, f"Expected 4 tag results, got {len(results)}"

    def test_empty_input_returns_empty_list(self, populated_db):
        """get_tags_for_songs([]) must return an empty list."""
        repo = TagRepository(populated_db)
        result = repo.get_tags_for_songs([])
        assert result == [], f"Expected [], got {result!r}"


# ===================================================================
# BaseRepository
# ===================================================================
# ===================================================================
# Mapper Tests: _row_to_album_credit
# ===================================================================
class TestRowToAlbumCredit:
    def test_all_fields_present(self, mock_db_path):
        mock_row = {
            "AlbumID": 100,
            "CreditedNameID": 20,
            "RoleID": 1,
            "DisplayName": "Nirvana",
            "IsPrimaryName": 1,
            "OwnerIdentityID": 2,
            "RoleName": "Performer",
        }
        repo = AlbumCreditRepository(mock_db_path)
        result = repo._row_to_album_credit(mock_row)
        assert result.album_id == 100
        assert result.name_id == 20
        assert result.identity_id == 2
        assert result.role_id == 1
        assert result.role_name == "Performer"
        assert result.display_name == "Nirvana"
        assert result.is_primary is True

    def test_null_fields(self, mock_db_path):
        mock_row = {
            "AlbumID": None,
            "CreditedNameID": None,
            "RoleID": None,
            "DisplayName": "Unknown",
            "IsPrimaryName": None,
            "OwnerIdentityID": None,
            "RoleName": "Unknown",
        }
        repo = AlbumCreditRepository(mock_db_path)
        result = repo._row_to_album_credit(mock_row)
        assert result.album_id is None
        assert result.name_id is None
        assert result.identity_id is None
        assert result.role_id is None
        assert result.is_primary is False


# ===================================================================
# Mapper Tests: _row_to_song_credit
# ===================================================================
class TestRowToSongCredit:
    def test_all_fields_present(self, mock_db_path):
        mock_row = {
            "SourceID": 1,
            "CreditedNameID": 10,
            "RoleID": 1,
            "DisplayName": "Dave Grohl",
            "IsPrimaryName": 1,
            "OwnerIdentityID": 1,
            "RoleName": "Performer",
        }
        repo = SongCreditRepository(mock_db_path)
        result = repo._row_to_song_credit(mock_row)
        assert result.source_id == 1
        assert result.name_id == 10
        assert result.identity_id == 1
        assert result.role_id == 1
        assert result.role_name == "Performer"
        assert result.display_name == "Dave Grohl"
        assert result.is_primary is True

    def test_null_fields(self, mock_db_path):
        mock_row = {
            "SourceID": None,
            "CreditedNameID": None,
            "RoleID": 1,
            "DisplayName": "Unknown",
            "IsPrimaryName": None,
            "OwnerIdentityID": None,
            "RoleName": "Unknown",
        }
        repo = SongCreditRepository(mock_db_path)
        result = repo._row_to_song_credit(mock_row)
        assert result.source_id is None
        assert result.name_id is None
        assert result.identity_id is None
        assert result.is_primary is False


# ===================================================================
# Mapper Tests: _row_to_song_album
# ===================================================================
class TestRowToSongAlbum:
    def test_all_fields_present(self, mock_db_path):
        mock_row = {
            "SourceID": 1,
            "AlbumID": 100,
            "TrackNumber": 1,
            "DiscNumber": 1,
            "IsPrimary": 1,
            "AlbumTitle": "Nevermind",
            "AlbumType": "Studio",
            "ReleaseYear": 1991,
        }
        repo = SongAlbumRepository(mock_db_path)
        result = repo._row_to_song_album(mock_row)
        assert result.source_id == 1
        assert result.album_id == 100
        assert result.track_number == 1
        assert result.disc_number == 1
        assert result.is_primary is True
        assert result.album_title == "Nevermind"
        assert result.album_type == "Studio"
        assert result.release_year == 1991
        assert result.album_publishers == []

    def test_null_fields(self, mock_db_path):
        mock_row = {
            "SourceID": None,
            "AlbumID": None,
            "TrackNumber": None,
            "DiscNumber": None,
            "IsPrimary": None,
            "AlbumTitle": "Unknown",
            "AlbumType": None,
            "ReleaseYear": None,
        }
        repo = SongAlbumRepository(mock_db_path)
        result = repo._row_to_song_album(mock_row)
        assert result.source_id is None
        assert result.album_id is None
        assert result.track_number is None
        assert result.disc_number is None
        assert result.is_primary is False
        assert result.album_type is None
        assert result.release_year is None


# ===================================================================
# Mapper Tests: _row_to_tag
# ===================================================================
class TestRowToTag:
    def test_all_fields_present(self, mock_db_path):
        mock_row = {
            "SourceID": 1,
            "IsPrimary": 1,
            "TagID": 1,
            "TagName": "Grunge",
            "TagCategory": "Genre",
        }
        repo = TagRepository(mock_db_path)
        result = repo._row_to_tag(mock_row)
        assert result.id == 1
        assert result.name == "Grunge"
        assert result.category == "Genre"
        assert result.is_primary is True

    def test_null_fields(self, mock_db_path):
        mock_row = {
            "SourceID": None,
            "IsPrimary": None,
            "TagID": None,
            "TagName": "Unknown",
            "TagCategory": None,
        }
        repo = TagRepository(mock_db_path)
        result = repo._row_to_tag(mock_row)
        assert result.id is None
        assert result.category is None
        assert result.is_primary is False


class TestBaseRepositoryLogChange:
    def test_noop_when_values_equal(self, mock_db_path):
        """_log_change must NOT write a row if old == new."""
        repo = BaseRepository(mock_db_path)
        with repo._get_connection() as conn:
            cursor = conn.cursor()
            repo._log_change(cursor, "Songs", 1, "TempoBPM", "120", "120", "batch-1")
            count = cursor.execute("SELECT COUNT(*) FROM ChangeLog").fetchone()[0]
            assert count == 0, f"Expected 0 ChangeLog rows for no-op, got {count}"

    def test_writes_when_values_differ_with_all_fields(self, mock_db_path):
        """_log_change MUST write all fields when old != new."""
        repo = BaseRepository(mock_db_path)
        with repo._get_connection() as conn:
            cursor = conn.cursor()
            repo._log_change(cursor, "Songs", 1, "TempoBPM", "120", "130", "batch-1")
            row = cursor.execute(
                "SELECT LogTableName, RecordID, LogFieldName, OldValue, NewValue, BatchID FROM ChangeLog"
            ).fetchone()
            assert row is not None, "Expected a ChangeLog row, got None"
            assert row[0] == "Songs", f"Expected LogTableName='Songs', got '{row[0]}'"
            assert row[1] == 1, f"Expected RecordID=1, got {row[1]}"
            assert (
                row[2] == "TempoBPM"
            ), f"Expected LogFieldName='TempoBPM', got '{row[2]}'"
            assert row[3] == "120", f"Expected OldValue='120', got '{row[3]}'"
            assert row[4] == "130", f"Expected NewValue='130', got '{row[4]}'"
            assert row[5] == "batch-1", f"Expected BatchID='batch-1', got '{row[5]}'"

    def test_none_to_value_records_null_old_value(self, mock_db_path):
        """_log_change must record NULL OldValue when transitioning from None to a value."""
        repo = BaseRepository(mock_db_path)
        with repo._get_connection() as conn:
            cursor = conn.cursor()
            repo._log_change(cursor, "Songs", 1, "Notes", None, "Hello", "batch-2")
            row = cursor.execute("SELECT OldValue, NewValue FROM ChangeLog").fetchone()
            assert row is not None, "Expected a ChangeLog row, got None"
            assert row[0] is None, f"Expected OldValue=None (NULL), got {row[0]!r}"
            assert row[1] == "Hello", f"Expected NewValue='Hello', got '{row[1]}'"
