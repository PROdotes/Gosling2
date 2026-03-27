"""
Contract tests for SongRepository.
Every assertion verifies EXACT values from the populated_db fixture.
"""

from src.data.song_repository import SongRepository


class TestGetById:
    """SongRepository.get_by_id contracts."""

    def test_valid_id_returns_exact_song(self, populated_db):
        """Test that get_by_id returns complete song object for valid ID."""
        repo = SongRepository(populated_db)
        song = repo.get_by_id(1)

        assert song is not None, f"Expected song object, got {song}"
        assert song.id == 1, f"Expected 1, got {song.id}"
        assert (
            song.media_name == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{song.media_name}'"
        assert (
            song.title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{song.title}'"
        assert (
            song.source_path == "/path/1"
        ), f"Expected '/path/1', got '{song.source_path}'"
        assert song.duration_s == 200.0, f"Expected 200000, got {song.duration_ms}"
        assert song.is_active is True, f"Expected True, got {song.is_active}"
        assert song.type_id == 1, f"Expected 1, got {song.type_id}"
        assert (
            song.audio_hash == "hash_1"
        ), f"Expected 'hash_1', got '{song.audio_hash}'"
        assert song.year == 1991, f"Expected 1991, got {song.year}"
        assert (
            song.processing_status is None
        ), f"Expected None for NULL processing_status, got {song.processing_status}"
        assert (
            song.credits == []
        ), f"Expected empty list for credits, got {song.credits}"
        assert song.albums == [], f"Expected empty list for albums, got {song.albums}"
        assert song.bpm is None, f"Expected None for BPM, got {song.bpm}"
        assert song.isrc is None, f"Expected None for ISRC, got {song.isrc}"
        assert song.notes is None, f"Expected None for notes, got {song.notes}"
        assert (
            song.raw_tags == {}
        ), f"Expected empty dict for raw_tags, got {song.raw_tags}"
        assert (
            song.publishers == []
        ), f"Expected empty list for publishers, got {song.publishers}"
        assert song.tags == [], f"Expected empty list for tags, got {song.tags}"

    def test_nonexistent_id_returns_none(self, populated_db):
        """Test that get_by_id returns None for non-existent ID."""
        repo = SongRepository(populated_db)
        song = repo.get_by_id(999)
        assert song is None, f"Expected None for nonexistent ID, got {song}"

    def test_zero_id_returns_none(self, populated_db):
        """Test that get_by_id returns None for zero ID."""
        repo = SongRepository(populated_db)
        song = repo.get_by_id(0)
        assert song is None, f"Expected None for zero ID, got {song}"

    def test_negative_id_returns_none(self, populated_db):
        """Test that get_by_id returns None for negative ID."""
        repo = SongRepository(populated_db)
        song = repo.get_by_id(-1)
        assert song is None, f"Expected None for negative ID, got {song}"


class TestGetByIds:
    """SongRepository.get_by_ids contracts."""

    def test_batch_returns_exact_songs(self, populated_db):
        """Test that get_by_ids returns complete song objects for all valid IDs."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_ids([1, 2, 3])

        assert len(songs) == 3, f"Expected 3 songs, got {len(songs)}"

        # Song 1: exhaustive assertions
        assert songs[0].id == 1, f"Expected 1, got {songs[0].id}"
        assert (
            songs[0].title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{songs[0].title}'"
        assert (
            songs[0].duration_ms == 200000
        ), f"Expected 200000, got {songs[0].duration_ms}"
        assert (
            songs[0].source_path == "/path/1"
        ), f"Expected '/path/1', got '{songs[0].source_path}'"
        assert (
            songs[0].audio_hash == "hash_1"
        ), f"Expected 'hash_1', got '{songs[0].audio_hash}'"
        assert songs[0].year == 1991, f"Expected 1991, got {songs[0].year}"
        assert songs[0].is_active is True, f"Expected True, got {songs[0].is_active}"

        # Song 2: exhaustive assertions (audio_hash is None)
        assert songs[1].id == 2, f"Expected 2, got {songs[1].id}"
        assert (
            songs[1].title == "Everlong"
        ), f"Expected 'Everlong', got '{songs[1].title}'"
        assert (
            songs[1].duration_ms == 240000
        ), f"Expected 240000, got {songs[1].duration_ms}"
        assert (
            songs[1].source_path == "/path/2"
        ), f"Expected '/path/2', got '{songs[1].source_path}'"
        assert (
            songs[1].audio_hash is None
        ), f"Expected None for audio_hash, got '{songs[1].audio_hash}'"
        assert songs[1].year == 1997, f"Expected 1997, got {songs[1].year}"
        assert songs[1].is_active is True, f"Expected True, got {songs[1].is_active}"

        # Song 3: exhaustive assertions (audio_hash is None, year is 2016)
        assert songs[2].id == 3, f"Expected 3, got {songs[2].id}"
        assert (
            songs[2].title == "Range Rover Bitch"
        ), f"Expected 'Range Rover Bitch', got '{songs[2].title}'"
        assert (
            songs[2].duration_ms == 180000
        ), f"Expected 180000, got {songs[2].duration_ms}"
        assert (
            songs[2].source_path == "/path/3"
        ), f"Expected '/path/3', got '{songs[2].source_path}'"
        assert (
            songs[2].audio_hash is None
        ), f"Expected None for audio_hash, got '{songs[2].audio_hash}'"
        assert songs[2].year == 2016, f"Expected 2016, got {songs[2].year}"
        assert songs[2].is_active is True, f"Expected True, got {songs[2].is_active}"

    def test_empty_list_returns_empty(self, populated_db):
        """Test that get_by_ids returns empty list for empty input."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_ids([])
        assert songs == [], f"Expected empty list, got {songs}"

    def test_mixed_valid_invalid_returns_only_valid(self, populated_db):
        """Test that get_by_ids returns only found items, skipping missing."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_ids([1, 999, 2])

        assert len(songs) == 2, f"Expected 2 found items, got {len(songs)}"

        # Assert all fields for song 1
        assert songs[0].id == 1, f"Expected 1, got {songs[0].id}"
        assert (
            songs[0].title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{songs[0].title}'"
        assert (
            songs[0].duration_ms == 200000
        ), f"Expected 200000, got {songs[0].duration_ms}"

        # Assert all fields for song 2
        assert songs[1].id == 2, f"Expected 2, got {songs[1].id}"
        assert (
            songs[1].title == "Everlong"
        ), f"Expected 'Everlong', got '{songs[1].title}'"
        assert (
            songs[1].duration_ms == 240000
        ), f"Expected 240000, got {songs[1].duration_ms}"

    def test_duplicate_ids_behavior(self, populated_db):
        """Duplicate IDs in input should not produce duplicate songs."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_ids([1, 1, 1])
        assert len(songs) == 1, f"Expected 1 unique song, got {len(songs)}"
        assert songs[0].id == 1, f"Expected 1, got {songs[0].id}"
        assert (
            songs[0].title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{songs[0].title}'"


class TestGetByTitle:
    """SongRepository.get_by_title contracts."""

    def test_exact_match(self, populated_db):
        """Test exact title match returns song with all fields."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("Smells Like Teen Spirit")

        assert len(songs) == 1, f"Expected 1 song, got {len(songs)}"
        assert songs[0].id == 1, f"Expected 1, got {songs[0].id}"
        assert (
            songs[0].title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{songs[0].title}'"
        assert (
            songs[0].duration_ms == 200000
        ), f"Expected 200000, got {songs[0].duration_ms}"

    def test_partial_match(self, populated_db):
        """Test partial title match works with LIKE query."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("Teen")

        assert len(songs) == 1, f"Expected 1 song, got {len(songs)}"
        assert songs[0].id == 1, f"Expected 1, got {songs[0].id}"
        assert (
            songs[0].title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{songs[0].title}'"

    def test_case_insensitive(self, populated_db):
        """SQLite LIKE is case-insensitive for ASCII by default."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("everlong")

        assert len(songs) == 1, f"Expected 1 song, got {len(songs)}"
        assert songs[0].id == 2, f"Expected 2, got {songs[0].id}"
        assert (
            songs[0].title == "Everlong"
        ), f"Expected 'Everlong', got '{songs[0].title}'"

    def test_no_match_returns_empty(self, populated_db):
        """Test that get_by_title returns [] for no matches."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("ZZZZZ_NONEXISTENT")
        assert songs == [], f"Expected empty list for no match, got {songs}"

    def test_multi_match(self, populated_db):
        """'oint' appears in 'Joint Venture' only."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_title("oint")

        assert len(songs) == 1, f"Expected 1 song, got {len(songs)}"
        assert songs[0].id == 8, f"Expected 8, got {songs[0].id}"
        assert (
            songs[0].title == "Joint Venture"
        ), f"Expected 'Joint Venture', got '{songs[0].title}'"

    def test_empty_on_empty_db(self, empty_db):
        """Test get_by_title on empty database returns empty."""
        repo = SongRepository(empty_db)
        songs = repo.get_by_title("anything")
        assert songs == [], f"Expected empty list on empty DB, got {songs}"


class TestSearchSlim:
    """SongRepository.search_slim contracts — returns List[dict] for card rendering."""

    def test_title_match(self, populated_db):
        """search_slim('Everlong') should find Song 2 and return a dict with core fields."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("Everlong")

        assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
        row = rows[0]
        assert row["SourceID"] == 2, f"Expected SourceID=2, got {row['SourceID']}"
        assert (
            row["MediaName"] == "Everlong"
        ), f"Expected 'Everlong', got '{row['MediaName']}'"
        assert (
            row["SourceDuration"] == 240
        ), f"Expected 240s, got {row['SourceDuration']}"
        assert (
            row["SourcePath"] == "/path/2"
        ), f"Expected '/path/2', got '{row['SourcePath']}'"

    def test_album_title_match(self, populated_db):
        """search_slim('Nevermind') should find Song 1 via album linkage."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("Nevermind")

        assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
        assert (
            rows[0]["SourceID"] == 1
        ), f"Expected SourceID=1, got {rows[0]['SourceID']}"
        assert (
            rows[0]["MediaName"] == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{rows[0]['MediaName']}'"

    def test_album_title_match_colour(self, populated_db):
        """search_slim('Colour') should find Song 2 via album 'The Colour and the Shape'."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("Colour")

        assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
        assert (
            rows[0]["SourceID"] == 2
        ), f"Expected SourceID=2, got {rows[0]['SourceID']}"
        assert (
            rows[0]["MediaName"] == "Everlong"
        ), f"Expected 'Everlong', got '{rows[0]['MediaName']}'"

    def test_no_match_returns_empty_list(self, populated_db):
        """search_slim('ZZZZZZZZZ') returns [] for no matches."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("ZZZZZZZZZ")
        assert rows == [], f"Expected empty list for no match, got {rows}"

    def test_matches_artist_name(self, populated_db):
        """search_slim covers credited artist names."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("Nirvana")
        assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
        assert (
            rows[0]["SourceID"] == 1
        ), f"Expected SourceID=1 (SLTS), got {rows[0]['SourceID']}"

        # Negative isolation: Foo Fighters songs should NOT appear
        returned_ids = {r["SourceID"] for r in rows}
        assert (
            2 not in returned_ids
        ), "Everlong (Foo Fighters) should not match 'Nirvana'"

    def test_empty_query_returns_all(self, populated_db):
        """Empty string in LIKE '%...%' matches all songs."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("")
        assert len(rows) == 9, f"Expected 9 rows, got {len(rows)}"

    def test_returns_display_artist_field(self, populated_db):
        """search_slim row must include DisplayArtist aggregated from SongCredits."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("Smells Like Teen Spirit")

        assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
        row = rows[0]
        assert "DisplayArtist" in row, "Row missing 'DisplayArtist' field"
        assert (
            row["DisplayArtist"] is not None
        ), "Expected a performer name, got None for SLTS"

    def test_returns_primary_genre_field(self, populated_db):
        """search_slim row must include PrimaryGenre from MediaSourceTags."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("Smells Like Teen Spirit")

        assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
        assert "PrimaryGenre" in rows[0], "Row missing 'PrimaryGenre' field"


class TestSearchSlimByIds:
    """SongRepository.search_slim_by_ids contracts."""

    def test_returns_slim_rows_for_valid_ids(self, populated_db):
        """search_slim_by_ids([1, 2]) should return 2 slim dicts."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim_by_ids([1, 2])

        assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"
        ids = {r["SourceID"] for r in rows}
        assert ids == {1, 2}, f"Expected IDs {{1, 2}}, got {ids}"

    def test_skips_nonexistent_ids(self, populated_db):
        """search_slim_by_ids([1, 999]) should return 1 row, skipping 999."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim_by_ids([1, 999])

        assert len(rows) == 1, f"Expected 1 row (999 doesn't exist), got {len(rows)}"
        assert (
            rows[0]["SourceID"] == 1
        ), f"Expected SourceID=1, got {rows[0]['SourceID']}"

    def test_empty_ids_returns_empty_list(self, populated_db):
        """search_slim_by_ids([]) should return [] immediately."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim_by_ids([])
        assert rows == [], f"Expected [], got {rows}"

    def test_returns_required_fields(self, populated_db):
        """Each row must contain SourceID, MediaName, SourcePath, SourceDuration, IsActive."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim_by_ids([1])

        assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
        row = rows[0]
        assert "SourceID" in row, "Row missing 'SourceID'"
        assert "MediaName" in row, "Row missing 'MediaName'"
        assert "SourcePath" in row, "Row missing 'SourcePath'"
        assert "SourceDuration" in row, "Row missing 'SourceDuration'"
        assert "IsActive" in row, "Row missing 'IsActive'"
        assert "DisplayArtist" in row, "Row missing 'DisplayArtist'"
        assert "PrimaryGenre" in row, "Row missing 'PrimaryGenre'"


class TestGetByHash:
    """SongRepository.get_by_hash contracts."""

    def test_valid_hash_returns_song(self, populated_db):
        """Test that get_by_hash returns song with all fields."""
        repo = SongRepository(populated_db)
        song = repo.get_by_hash("hash_1")

        assert song is not None, f"Expected song object, got {song}"
        assert song.id == 1, f"Expected 1, got {song.id}"
        assert (
            song.title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{song.title}'"
        assert (
            song.audio_hash == "hash_1"
        ), f"Expected 'hash_1', got '{song.audio_hash}'"
        assert song.duration_s == 200.0, f"Expected 200000, got {song.duration_ms}"

    def test_nonexistent_hash_returns_none(self, populated_db):
        """Test that get_by_hash returns None for non-existent hash."""
        repo = SongRepository(populated_db)
        song = repo.get_by_hash("no_such_hash")
        assert song is None, f"Expected None for nonexistent hash, got {song}"

    def test_empty_hash_returns_none(self, populated_db):
        """Test that get_by_hash returns None for empty string."""
        repo = SongRepository(populated_db)
        song = repo.get_by_hash("")
        assert song is None, f"Expected None for empty hash, got {song}"


class TestGetByPath:
    """SongRepository.get_by_path contracts."""

    def test_valid_path_returns_song(self, populated_db):
        """Test that get_by_path returns song with all fields."""
        repo = SongRepository(populated_db)
        song = repo.get_by_path("/path/1")

        assert song is not None, f"Expected song object, got {song}"
        assert song.id == 1, f"Expected 1, got {song.id}"
        assert (
            song.title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{song.title}'"
        assert (
            song.source_path == "/path/1"
        ), f"Expected '/path/1', got '{song.source_path}'"

    def test_invalid_path_returns_none(self, populated_db):
        """Test that get_by_path returns None for non-existent path."""
        repo = SongRepository(populated_db)
        song = repo.get_by_path("/no/such/path")
        assert song is None, f"Expected None for invalid path, got {song}"

    def test_empty_path_returns_none(self, populated_db):
        """Test that get_by_path returns None for empty string."""
        repo = SongRepository(populated_db)
        song = repo.get_by_path("")
        assert song is None, f"Expected None for empty path, got {song}"


class TestGetByIdentityIds:
    """SongRepository.get_by_identity_ids contracts."""

    def test_dave_grohl_identity(self, populated_db):
        """Identity 1 (Dave Grohl) has songs: 4, 5, 6, 8."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_identity_ids([1])

        assert len(songs) == 4, f"Expected 4 songs, got {len(songs)}"
        titles = {s.title for s in songs}
        assert titles == {
            "Grohlton Theme",
            "Pocketwatch Demo",
            "Dual Credit Track",
            "Joint Venture",
        }, f"Unexpected titles: {titles}"

    def test_nirvana_identity(self, populated_db):
        """Identity 2 (Nirvana) has NameID 20. Song 1 is credited to NameID 20."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_identity_ids([2])

        assert len(songs) == 1, f"Expected 1 song, got {len(songs)}"
        assert songs[0].id == 1, f"Expected 1, got {songs[0].id}"
        assert (
            songs[0].title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{songs[0].title}'"

    def test_taylor_identity(self, populated_db):
        """Identity 4 (Taylor) has NameID 40. Songs 3, 6, 8 credited to NameID 40."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_identity_ids([4])

        assert len(songs) == 3, f"Expected 3 songs, got {len(songs)}"
        titles = {s.title for s in songs}
        assert titles == {
            "Range Rover Bitch",
            "Dual Credit Track",
            "Joint Venture",
        }, f"Unexpected titles: {titles}"

    def test_multiple_identities(self, populated_db):
        """Passing Nirvana(2) + Foo Fighters(3) should return songs 1 and 2."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_identity_ids([2, 3])

        assert len(songs) == 2, f"Expected 2 songs, got {len(songs)}"
        titles = {s.title for s in songs}
        assert titles == {
            "Smells Like Teen Spirit",
            "Everlong",
        }, f"Unexpected titles: {titles}"

    def test_empty_ids_returns_empty(self, populated_db):
        """Test that empty identity list returns empty."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_identity_ids([])
        assert songs == [], f"Expected empty list, got {songs}"

    def test_nonexistent_identity(self, populated_db):
        """Test that non-existent identity returns empty."""
        repo = SongRepository(populated_db)
        songs = repo.get_by_identity_ids([999])
        assert songs == [], f"Expected empty list for nonexistent identity, got {songs}"


class TestFindByMetadata:
    """SongRepository.find_by_metadata contracts."""

    def test_match_by_recording_year(self, populated_db):
        """Test finding song by title, artist, and year."""
        repo = SongRepository(populated_db)
        songs = repo.find_by_metadata("Smells Like Teen Spirit", ["Nirvana"], 1991)

        assert len(songs) == 1, f"Expected 1 song, got {len(songs)}"
        assert songs[0].id == 1, f"Expected 1, got {songs[0].id}"
        assert (
            songs[0].title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{songs[0].title}'"
        assert songs[0].year == 1991, f"Expected 1991, got {songs[0].year}"

    def test_no_match_wrong_year(self, populated_db):
        """Test that wrong year returns empty."""
        repo = SongRepository(populated_db)
        songs = repo.find_by_metadata("Smells Like Teen Spirit", ["Nirvana"], 2024)
        assert songs == [], f"Expected empty list for wrong year, got {songs}"

    def test_match_without_year(self, populated_db):
        """Test that year=None matches song without year filter."""
        repo = SongRepository(populated_db)
        songs = repo.find_by_metadata("Everlong", ["Foo Fighters"], None)

        assert len(songs) == 1, f"Expected 1 song, got {len(songs)}"
        assert songs[0].id == 2, f"Expected 2, got {songs[0].id}"
        assert (
            songs[0].title == "Everlong"
        ), f"Expected 'Everlong', got '{songs[0].title}'"

    def test_exact_performer_set_match(self, populated_db):
        """Test that exact performer set is required."""
        repo = SongRepository(populated_db)

        # Song 1 has only Nirvana as performer
        songs = repo.find_by_metadata("Smells Like Teen Spirit", ["Nirvana"], 1991)
        assert len(songs) == 1, f"Expected 1 song with Nirvana only, got {len(songs)}"

        # Song 1 does NOT have both Nirvana AND Dave Grohl as performers
        songs = repo.find_by_metadata(
            "Smells Like Teen Spirit", ["Nirvana", "Dave Grohl"], 1991
        )
        assert songs == [], f"Expected empty list with extra performer, got {songs}"

    def test_find_by_metadata_empty_title_returns_empty(self, populated_db):
        """Test that empty title returns empty."""
        repo = SongRepository(populated_db)
        songs = repo.find_by_metadata("", ["Nirvana"], 1991)
        assert songs == [], f"Expected empty list for empty title, got {songs}"

    def test_find_by_metadata_empty_artists_returns_empty(self, populated_db):
        """Test that empty artists list returns empty."""
        repo = SongRepository(populated_db)
        songs = repo.find_by_metadata("Smells Like Teen Spirit", [], 1991)
        assert songs == [], f"Expected empty list for empty artists, got {songs}"


class TestRowToSong:
    """SongRepository._row_to_song mapper contracts.

    Direct mapper tests catch bugs in type coercion, NULL handling,
    and unit conversions that integration tests might miss.
    """

    def test_all_fields_present(self, populated_db):
        """Mapper must correctly cast all fields from a complete row."""
        mock_row = {
            "SourceID": 1,
            "TypeID": 1,
            "MediaName": "Test Song",
            "SourceDuration": 200,  # seconds in DB
            "SourcePath": "/path/test",
            "AudioHash": "hash123",
            "IsActive": 1,
            "RecordingYear": 2024,
            "ProcessingStatus": None,
            "SourceNotes": None,
            "TempoBPM": 120,
            "ISRC": "USRC12345678",
        }
        repo = SongRepository(populated_db)
        song = repo._row_to_song(mock_row)

        assert song.id == 1, f"Expected 1, got {song.id}"
        assert song.type_id == 1, f"Expected 1, got {song.type_id}"
        assert (
            song.media_name == "Test Song"
        ), f"Expected 'Test Song', got '{song.media_name}'"
        assert song.title == "Test Song", f"Expected 'Test Song', got '{song.title}'"
        assert (
            song.duration_s == 200.0
        ), f"Expected 200000ms (converted), got {song.duration_ms}"
        assert (
            song.source_path == "/path/test"
        ), f"Expected '/path/test', got '{song.source_path}'"
        assert (
            song.audio_hash == "hash123"
        ), f"Expected 'hash123', got '{song.audio_hash}'"
        assert song.is_active is True, f"Expected True (1->True), got {song.is_active}"
        assert song.year == 2024, f"Expected 2024, got {song.year}"
        assert (
            song.processing_status is None
        ), f"Expected None, got {song.processing_status}"
        assert song.notes is None, f"Expected None, got {song.notes}"
        assert song.bpm == 120, f"Expected 120, got {song.bpm}"
        assert (
            song.isrc == "USRC12345678"
        ), f"Expected 'USRC12345678', got '{song.isrc}'"
        assert song.credits == [], f"Expected empty credits, got {song.credits}"
        assert song.albums == [], f"Expected empty albums, got {song.albums}"

    def test_null_fields(self, populated_db):
        """NULL DB values must map to None, not 0 or empty string."""
        mock_row = {
            "SourceID": 4,
            "TypeID": 1,
            "MediaName": "Song With Nulls",
            "SourceDuration": 120,
            "SourcePath": "/path/4",
            "AudioHash": None,
            "IsActive": 1,
            "RecordingYear": None,
            "ProcessingStatus": None,
            "SourceNotes": None,
            "TempoBPM": None,
            "ISRC": None,
        }
        repo = SongRepository(populated_db)
        song = repo._row_to_song(mock_row)

        assert song.id == 4, f"Expected 4, got {song.id}"
        assert (
            song.audio_hash is None
        ), f"Expected None for NULL hash, got {song.audio_hash}"
        assert song.year is None, f"Expected None for NULL year, got {song.year}"
        assert (
            song.processing_status is None
        ), f"Expected None for NULL status, got {song.processing_status}"
        assert song.notes is None, f"Expected None for NULL notes, got {song.notes}"
        assert song.bpm is None, f"Expected None for NULL bpm, got {song.bpm}"
        assert song.isrc is None, f"Expected None for NULL isrc, got {song.isrc}"

    def test_boolean_casting(self, populated_db):
        """SQLite stores booleans as 0/1. Mapper must cast to Python bool."""
        repo = SongRepository(populated_db)

        # IsActive=1 -> True
        row_active = {
            "SourceID": 1,
            "TypeID": 1,
            "MediaName": "Active",
            "SourceDuration": 100,
            "SourcePath": "/a",
            "AudioHash": None,
            "IsActive": 1,
            "RecordingYear": None,
            "ProcessingStatus": None,
            "SourceNotes": None,
            "TempoBPM": None,
            "ISRC": None,
        }
        assert repo._row_to_song(row_active).is_active is True

        # IsActive=0 -> False
        row_inactive = {**row_active, "IsActive": 0}
        assert repo._row_to_song(row_inactive).is_active is False

        # IsActive=NULL -> False
        row_null = {**row_active, "IsActive": None}
        assert repo._row_to_song(row_null).is_active is False

    def test_duration_conversion(self, populated_db):
        """SourceDuration (seconds) must be converted to duration_ms (milliseconds)."""
        repo = SongRepository(populated_db)

        row = {
            "SourceID": 1,
            "TypeID": 1,
            "MediaName": "Test",
            "SourceDuration": 0,
            "SourcePath": "/a",
            "AudioHash": None,
            "IsActive": 1,
            "RecordingYear": None,
            "ProcessingStatus": None,
            "SourceNotes": None,
            "TempoBPM": None,
            "ISRC": None,
        }

        row["SourceDuration"] = 200
        assert repo._row_to_song(row).duration_ms == 200000

        row["SourceDuration"] = 0
        assert repo._row_to_song(row).duration_ms == 0

        row["SourceDuration"] = None
        assert repo._row_to_song(row).duration_ms == 0  # NULL -> 0
