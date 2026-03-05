"""
Integration tests for the v3core Identity Service (The Grohlton Loop).

These tests hit the REAL gosling2.db. They are NOT unit tests — they verify
that the full pipeline (Name Search → Identity Expansion → Song Retrieval) works
against real data. If the DB is missing, tests are skipped.
"""
import os
import pytest
from pathlib import Path

DB_PATH = str(Path(__file__).parent.parent.parent / "sqldb" / "gosling2.db")

@pytest.fixture
def db_path():
    if not os.path.exists(DB_PATH):
        pytest.skip("Real gosling2.db not found — skipping integration tests.")
    return DB_PATH


@pytest.fixture
def identity_service(db_path):
    from src.v3core.services.identity_service import IdentityService
    return IdentityService(db_path)


class TestSongRetrieval:
    def test_get_by_id_returns_song(self, db_path):
        """Song #1 should always exist and return a valid Song model."""
        from src.v3core.data.song_repository import SongRepository
        repo = SongRepository(db_path)
        song = repo.get_by_id(1)
        assert song is not None
        assert song.id == 1
        assert song.title is not None
        assert song.duration_ms > 0

    def test_get_by_ids_batch(self, db_path):
        """Batch fetch should return the correct count."""
        from src.v3core.data.song_repository import SongRepository
        repo = SongRepository(db_path)
        songs = repo.get_by_ids([1, 2, 3])
        assert len(songs) == 3
        assert all(s.title is not None for s in songs)

    def test_get_by_ids_empty(self, db_path):
        """Empty input should return empty list without hitting the DB."""
        from src.v3core.data.song_repository import SongRepository
        repo = SongRepository(db_path)
        assert repo.get_by_ids([]) == []


class TestIdentityResolution:
    def test_name_search_returns_results(self, identity_service):
        """Searching for a common name should return at least one match."""
        songs = identity_service.resolve_name("Ivan")
        assert len(songs) > 0

    def test_name_search_returns_songs(self, identity_service):
        """All returned objects should be valid Song models."""
        songs = identity_service.resolve_name("Ivan")
        for song in songs:
            assert song.id > 0
            assert song.title is not None
            assert song.duration_ms > 0

    def test_name_search_no_duplicates(self, identity_service):
        """Returned song list should have no duplicate IDs."""
        songs = identity_service.resolve_name("Ivan")
        ids = [s.id for s in songs]
        assert len(ids) == len(set(ids))

    def test_unknown_name_returns_empty(self, identity_service):
        """A name that doesn't exist should return an empty list, not crash."""
        songs = identity_service.resolve_name("ZZZZZNOEXIST")
        assert songs == []

    def test_get_songs_for_identity_returns_list(self, db_path, identity_service):
        """get_songs_for_identity should return songs for a known identity."""
        from src.v3core.data.artist_name_repository import ArtistNameRepository
        name_repo = ArtistNameRepository(db_path)
        # Find the first linked artist and use their identity ID
        names = name_repo.find_by_string("Ivan")
        assert len(names) > 0
        identity_id = names[0].owner_identity_id
        songs = identity_service.get_songs_for_identity(identity_id)
        assert isinstance(songs, list)
