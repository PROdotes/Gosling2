import pytest
from src.data.song_repository import SongRepository

class TestSearchDeep:
    """SongRepository.search_deep contracts (exhaustive cross-field search)."""

    def test_search_by_year(self, populated_db):
        """Deep search for '1991' should find Smells Like Teen Spirit."""
        repo = SongRepository(populated_db)
        # 1991 is not in the title or artist name (Nirvana)
        results = repo.search("1991")
        
        assert len(results) == 1, f"Expected 1 match for year '1991', got {len(results)}"
        song = results[0]
        assert song.id == 1, f"Expected song 1, got {song.id}"
        assert song.title == "Smells Like Teen Spirit", f"Expected 'Smells Like Teen Spirit', got '{song.title}'"

    def test_search_partial_year(self, populated_db):
        """Deep search for '199' should find all 90s songs via CAST(RecordingYear AS TEXT)."""
        repo = SongRepository(populated_db)
        results = repo.search("199")
        
        # 1991, 1997, 1992 -> 3 songs
        assert len(results) == 3, f"Expected 3 matches for '199', got {len(results)}"
        ids = {s.id for s in results}
        assert 1 in ids, "Song 1 (1991) missing"
        assert 2 in ids, "Song 2 (1997) missing"
        assert 5 in ids, "Song 5 (1992) missing"

    def test_search_by_artist_name_performer(self, populated_db):
        """Deep search for 'Nirvana' should find song 1."""
        repo = SongRepository(populated_db)
        results = repo.search("Nirvana")
        
        assert len(results) == 1, f"Expected 1 match for artist 'Nirvana', got {len(results)}"
        assert results[0].id == 1, f"Expected song 1, got {results[0].id}"
        
        # Negative isolation: Foo Fighters should NOT match "Nirvana"
        returned_ids = {s.id for s in results}
        assert 2 not in returned_ids, "Everlong (Foo Fighters) should not be in Nirvana search results"

    def test_search_by_legal_name(self, populated_db):
        """Deep search for 'David Eric' should find Dave's songs."""
        repo = SongRepository(populated_db)
        results = repo.search("David Eric")
        
        # Dave (ID 1) is credited on 4, 6, 8 (also 5 via Late!)
        # Let's count from conftest: 4, 6, 8. (Late! is ID 12 which belongs to ID 1)
        # Wait, if I join i.LegalName via ArtistNames an, I found the Identity.
        # So any NameID belonging to Identity 1 will find the song.
        # Dave is credited on 4, 6, 8. Late! (12) on 5.
        # So it should find 4, 5, 6, 8.
        assert len(results) == 4, f"Expected 4 matches for 'David Eric', got {len(results)}"
        ids = {s.id for s in results}
        assert {4, 5, 6, 8}.issubset(ids), f"Missing songs for Dave, got {ids}"

    def test_search_by_album_title(self, populated_db):
        """Deep search for 'Nevermind' should find song 1."""
        repo = SongRepository(populated_db)
        results = repo.search("Nevermind")
        
        assert len(results) == 1, f"Expected 1 match for album 'Nevermind', got {len(results)}"
        assert results[0].id == 1, f"Expected song 1, got {results[0].id}"

    def test_search_case_insensitive(self, populated_db):
        """Deep search should be case-insensitive (LIKE protocol)."""
        repo = SongRepository(populated_db)
        results = repo.search("teen spirit")
        
        assert len(results) == 1, f"Expected 1 match for 'teen spirit', got {len(results)}"
        assert results[0].id == 1, f"Expected song 1, got {results[0].id}"

    def test_search_by_isrc(self, populated_db):
        """Deep search for ISRC 'ISRC123' should find Hollow Song."""
        repo = SongRepository(populated_db)
        results = repo.search("ISRC123")
        
        assert len(results) == 1, f"Expected 1 match for ISRC 'ISRC123', got {len(results)}"
        assert results[0].id == 7, f"Expected song 7, got {results[0].id}"
        assert results[0].isrc == "ISRC123", f"Expected 'ISRC123', got '{results[0].isrc}'"

    def test_search_by_role_is_ignored(self, populated_db):
        """Deep search for Role 'Composer' should NOT match by role name (Categorical noise reduction)."""
        repo = SongRepository(populated_db)
        # Roles: 1: Performer, 2: Composer
        results = repo.search("Composer")
        
        # Searching the role name itself should return nothing now
        assert len(results) == 0, f"Expected 0 matches for role 'Composer', got {len(results)}"

    def test_search_by_publisher(self, populated_db):
        """Deep search for Publisher 'DGC Records' should find song 1."""
        repo = SongRepository(populated_db)
        results = repo.search("DGC")
        
        assert len(results) == 1, f"Expected 1 match for publisher 'DGC', got {len(results)}"
        assert results[0].id == 1, f"Expected song 1, got {results[0].id}"
        assert results[0].title == "Smells Like Teen Spirit", f"Expected 'Smells Like Teen Spirit', got '{results[0].title}'"

    def test_search_by_tag(self, populated_db):
        """Deep search for Tag 'Grunge' should find multiple songs."""
        repo = SongRepository(populated_db)
        # conftest.py: Song 1 (Grunge), Song 9 (Grunge, NOT primary)
        results = repo.search("Grunge")
        
        assert len(results) == 2, f"Expected 2 matches for tag 'Grunge', got {len(results)}"
        ids = {s.id for s in results}
        assert 1 in ids, "Song 1 (Grunge) missing from results"
        assert 9 in ids, "Song 9 (Grunge) missing from results"

    def test_no_match_returns_empty(self, populated_db):
        """Non-existent query returns empty list."""
        repo = SongRepository(populated_db)
        results = repo.search("ZZZZZZ_NO_MATCH")
        assert results == [], f"Expected empty list, got {results}"

    def test_empty_query_returns_all(self, populated_db):
        """Empty query matches everything."""
        repo = SongRepository(populated_db)
        results = repo.search("")
        # populated_db has 9 songs
        assert len(results) == 9, f"Expected all 9 songs, got {len(results)}"
