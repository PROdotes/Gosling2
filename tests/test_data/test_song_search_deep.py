from src.data.song_repository import SongRepository


class TestSearchSlimDeepFields:
    """SongRepository.search_slim contracts for exhaustive cross-field search coverage.

    search_slim returns List[dict] with keys: SourceID, MediaName, SourcePath,
    SourceDuration, RecordingYear, TempoBPM, ISRC, IsActive, DisplayArtist, PrimaryGenre.
    """

    def test_search_by_year(self, populated_db):
        """'1991' matches Song 1 via RecordingYear CAST to TEXT."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("1991")

        assert len(rows) == 1, f"Expected 1 match for year '1991', got {len(rows)}"
        assert rows[0]["SourceID"] == 1, (
            f"Expected SourceID=1, got {rows[0]['SourceID']}"
        )
        assert rows[0]["MediaName"] == "Smells Like Teen Spirit", (
            f"Expected 'Smells Like Teen Spirit', got '{rows[0]['MediaName']}'"
        )

    def test_search_partial_year(self, populated_db):
        """'199' should match all 90s songs (1991, 1997, 1992) via CAST year LIKE."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("199")

        assert len(rows) == 3, f"Expected 3 matches for '199', got {len(rows)}"
        ids = {r["SourceID"] for r in rows}
        assert 1 in ids, "Song 1 (1991) missing"
        assert 2 in ids, "Song 2 (1997) missing"
        assert 5 in ids, "Song 5 (1992) missing"

    def test_search_by_artist_name_performer(self, populated_db):
        """'Nirvana' matches Song 1 via SongCredits DisplayName."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("Nirvana")

        assert len(rows) == 1, f"Expected 1 match for artist 'Nirvana', got {len(rows)}"
        assert rows[0]["SourceID"] == 1, (
            f"Expected SourceID=1, got {rows[0]['SourceID']}"
        )

        # Negative isolation
        returned_ids = {r["SourceID"] for r in rows}
        assert 2 not in returned_ids, (
            "Everlong (Foo Fighters) should not be in Nirvana search results"
        )

    def test_search_by_legal_name(self, populated_db):
        """'David Eric' matches songs via Identity.LegalName join."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("David Eric")

        assert len(rows) == 4, f"Expected 4 matches for 'David Eric', got {len(rows)}"
        ids = {r["SourceID"] for r in rows}
        assert {4, 5, 6, 8}.issubset(ids), f"Missing songs for Dave, got {ids}"

    def test_search_by_album_title(self, populated_db):
        """'Nevermind' matches Song 1 via SongAlbums/Albums join."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("Nevermind")

        assert len(rows) == 1, (
            f"Expected 1 match for album 'Nevermind', got {len(rows)}"
        )
        assert rows[0]["SourceID"] == 1, (
            f"Expected SourceID=1, got {rows[0]['SourceID']}"
        )

    def test_search_case_insensitive(self, populated_db):
        """LIKE search is case-insensitive."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("teen spirit")

        assert len(rows) == 1, f"Expected 1 match for 'teen spirit', got {len(rows)}"
        assert rows[0]["SourceID"] == 1, (
            f"Expected SourceID=1, got {rows[0]['SourceID']}"
        )

    def test_search_by_isrc(self, populated_db):
        """'ISRC123' matches Song 7 via Songs.ISRC field."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("ISRC123")

        assert len(rows) == 1, f"Expected 1 match for ISRC 'ISRC123', got {len(rows)}"
        assert rows[0]["SourceID"] == 7, (
            f"Expected SourceID=7, got {rows[0]['SourceID']}"
        )
        assert rows[0]["ISRC"] == "ISRC123", (
            f"Expected 'ISRC123', got '{rows[0]['ISRC']}'"
        )

    def test_search_by_role_is_ignored(self, populated_db):
        """'Composer' role name should NOT match (role is not a search field)."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("Composer")

        assert len(rows) == 0, (
            f"Expected 0 matches for role 'Composer', got {len(rows)}"
        )

    def test_search_by_publisher(self, populated_db):
        """'DGC' matches Song 1 via RecordingPublishers/Publishers join."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("DGC")

        assert len(rows) == 1, f"Expected 1 match for publisher 'DGC', got {len(rows)}"
        assert rows[0]["SourceID"] == 1, (
            f"Expected SourceID=1, got {rows[0]['SourceID']}"
        )
        assert rows[0]["MediaName"] == "Smells Like Teen Spirit", (
            f"Expected 'Smells Like Teen Spirit', got '{rows[0]['MediaName']}'"
        )

    def test_search_by_tag(self, populated_db):
        """'Grunge' matches via MediaSourceTags/Tags join."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("Grunge")

        assert len(rows) == 2, f"Expected 2 matches for tag 'Grunge', got {len(rows)}"
        ids = {r["SourceID"] for r in rows}
        assert 1 in ids, "Song 1 (Grunge) missing from results"
        assert 9 in ids, "Song 9 (Grunge) missing from results"

    def test_no_match_returns_empty(self, populated_db):
        """Non-existent query returns empty list."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("ZZZZZZ_NO_MATCH")
        assert rows == [], f"Expected empty list, got {rows}"

    def test_empty_query_returns_all(self, populated_db):
        """Empty query matches all 9 songs."""
        repo = SongRepository(populated_db)
        rows = repo.search_slim("")
        assert len(rows) == 9, f"Expected all 9 songs, got {len(rows)}"
