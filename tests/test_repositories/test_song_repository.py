"""
Contract tests for SongRepository.
Every assertion verifies EXACT values from the populated_db fixture.
"""
from src.data.song_repository import SongRepository


class TestGetById:
    """SongRepository.get_by_id contracts."""

    def test_valid_id_returns_exact_song(self, populated_db):
        repo = SongRepository(populated_db)
        song = repo.get_by_id(1)

        assert song is not None
        assert song.id == 1
        assert song.media_name == "Smells Like Teen Spirit"
        assert song.title == "Smells Like Teen Spirit"  # property alias
        assert song.source_path == "/path/1"
        assert song.duration_ms == 200000  # 200 seconds * 1000
        assert song.is_active is True
        assert song.type_id == 1

    def test_each_song_has_correct_duration_conversion(self, populated_db):
        """Contract: SourceDuration (seconds) * 1000 = duration_ms."""
        repo = SongRepository(populated_db)
        expected = {
            1: 200000,   # 200s
            2: 240000,   # 240s
            3: 180000,   # 180s
            4: 120000,   # 120s
            5: 180000,   # 180s
            6: 300000,   # 300s
            7: 10000,    # 10s
            8: 180000,   # 180s
            9: 100000,   # 100s
        }
        for song_id, expected_ms in expected.items():
            song = repo.get_by_id(song_id)
            assert song is not None, f"Song {song_id} not found"
            assert song.duration_ms == expected_ms, (
                f"Song {song_id}: expected {expected_ms}ms, got {song.duration_ms}ms"
            )

    def test_nonexistent_id_returns_none(self, populated_db):
        repo = SongRepository(populated_db)
        assert repo.get_by_id(999) is None

    def test_zero_id_returns_none(self, populated_db):
        repo = SongRepository(populated_db)
        assert repo.get_by_id(0) is None

    def test_negative_id_returns_none(self, populated_db):
        repo = SongRepository(populated_db)
        assert repo.get_by_id(-1) is None


class TestGetByIds:
    """SongRepository.get_by_ids contracts."""

    def test_batch_returns_exact_songs(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.get_by_ids([1, 2, 3])

        assert len(songs) == 3
        titles = {s.title for s in songs}
        assert titles == {"Smells Like Teen Spirit", "Everlong", "Range Rover Bitch"}

    def test_empty_list_returns_empty(self, populated_db):
        repo = SongRepository(populated_db)
        assert repo.get_by_ids([]) == []

    def test_mixed_valid_invalid_returns_only_valid(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.get_by_ids([1, 999, 2])
        assert len(songs) == 2
        titles = {s.title for s in songs}
        assert titles == {"Smells Like Teen Spirit", "Everlong"}

    def test_all_nine_songs_returned(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.get_by_ids([1, 2, 3, 4, 5, 6, 7, 8, 9])
        assert len(songs) == 9
        titles = {s.title for s in songs}
        assert titles == {
            "Smells Like Teen Spirit", "Everlong", "Range Rover Bitch",
            "Grohlton Theme", "Pocketwatch Demo", "Dual Credit Track",
            "Hollow Song", "Joint Venture", "Priority Test",
        }

    def test_duplicate_ids_behavior(self, populated_db):
        """Duplicate IDs in input should not produce duplicate songs (SQL IN behavior)."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_ids([1, 1, 1])
        assert len(songs) == 1
        assert songs[0].title == "Smells Like Teen Spirit"


class TestGetByTitle:
    """SongRepository.get_by_title contracts."""

    def test_exact_match(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("Smells Like Teen Spirit")
        assert len(songs) == 1
        assert songs[0].id == 1

    def test_partial_match(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("Teen")
        assert len(songs) == 1
        assert songs[0].title == "Smells Like Teen Spirit"

    def test_case_insensitive(self, populated_db):
        """SQLite LIKE is case-insensitive for ASCII by default."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("everlong")
        assert len(songs) == 1
        assert songs[0].title == "Everlong"

    def test_no_match_returns_empty(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("ZZZZZ_NONEXISTENT")
        assert songs == []

    def test_multi_match(self, populated_db):
        """'o' appears in multiple titles: Everlong, Grohlton Theme, Pocketwatch Demo, Hollow Song, Priority Test, Joint Venture, Zero... """
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("oint")
        assert len(songs) == 1
        assert songs[0].title == "Joint Venture"

    def test_empty_on_empty_db(self, empty_db):
        repo = SongRepository(empty_db)
        songs = repo.get_by_title("anything")
        assert songs == []


class TestSearchSurface:
    """SongRepository.search_surface contracts (title + album title search)."""

    def test_title_match(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.search_surface("Everlong")
        assert len(songs) == 1
        assert songs[0].id == 2

    def test_album_title_match(self, populated_db):
        """Searching for album name 'Nevermind' should find Song 1 (linked to that album)."""
        repo = SongRepository(populated_db)
        songs = repo.search_surface("Nevermind")
        assert len(songs) == 1
        assert songs[0].id == 1
        assert songs[0].title == "Smells Like Teen Spirit"

    def test_album_title_match_colour(self, populated_db):
        """Searching for 'Colour' should find Song 2 via album 'The Colour and the Shape'."""
        repo = SongRepository(populated_db)
        songs = repo.search_surface("Colour")
        assert len(songs) == 1
        assert songs[0].id == 2
        assert songs[0].title == "Everlong"

    def test_no_match(self, populated_db):
        repo = SongRepository(populated_db)
        songs = repo.search_surface("ZZZZZZZZZ")
        assert songs == []

    def test_does_not_match_artist_name(self, populated_db):
        """Surface search only covers titles/albums, NOT artist names."""
        repo = SongRepository(populated_db)
        songs = repo.search_surface("Nirvana")
        assert songs == []

    def test_empty_query_returns_all(self, populated_db):
        """Empty string in LIKE '%...%' matches everything."""
        repo = SongRepository(populated_db)
        songs = repo.search_surface("")
        assert len(songs) == 9


class TestGetByIdentityIds:
    """SongRepository.get_by_identity_ids contracts."""

    def test_dave_grohl_identity(self, populated_db):
        """Identity 1 (Dave Grohl) has NameIDs 10, 11, 12, 33.
        Songs credited to those: 4(Grohlton/11), 5(Late!/12), 6(Dave/10), 8(Dave/10)."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_identity_ids([1])
        titles = {s.title for s in songs}
        assert titles == {
            "Grohlton Theme", "Pocketwatch Demo", "Dual Credit Track", "Joint Venture",
        }

    def test_nirvana_identity(self, populated_db):
        """Identity 2 (Nirvana) has NameID 20. Song 1 is credited to NameID 20."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_identity_ids([2])
        assert len(songs) == 1
        assert songs[0].title == "Smells Like Teen Spirit"

    def test_taylor_identity(self, populated_db):
        """Identity 4 (Taylor) has NameID 40. Songs 3, 6, 8 credited to NameID 40."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_identity_ids([4])
        titles = {s.title for s in songs}
        assert titles == {"Range Rover Bitch", "Dual Credit Track", "Joint Venture"}

    def test_multiple_identities(self, populated_db):
        """Passing Nirvana(2) + Foo Fighters(3) should return songs 1 and 2."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_identity_ids([2, 3])
        titles = {s.title for s in songs}
        assert titles == {"Smells Like Teen Spirit", "Everlong"}

    def test_empty_ids_returns_empty(self, populated_db):
        repo = SongRepository(populated_db)
        assert repo.get_by_identity_ids([]) == []

    def test_nonexistent_identity(self, populated_db):
        repo = SongRepository(populated_db)
        assert repo.get_by_identity_ids([999]) == []
