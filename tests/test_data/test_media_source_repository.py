import pytest
from src.data.media_source_repository import MediaSourceRepository
from src.models.domain import MediaSource


@pytest.fixture
def repo(populated_db):
    return MediaSourceRepository(populated_db)


class TestMediaSourceRepositoryReads:
    def test_get_by_path_valid(self, repo):
        # Song 1 from populated_db: /path/1
        source = repo.get_by_path("/path/1")
        assert source is not None
        assert source.id == 1
        assert isinstance(source, MediaSource)
        assert source.media_name == "Smells Like Teen Spirit"
        assert source.duration_s == 200.0  # From populated_db SourceDuration

    def test_get_by_path_not_found(self, repo):
        source = repo.get_by_path("/ghost/path")
        assert source is None

    def test_get_by_hash_valid(self, repo):
        # Song 1 from populated_db: hash_1
        source = repo.get_by_hash("hash_1")
        assert source is not None
        assert source.id == 1
        assert source.audio_hash == "hash_1"

    def test_get_by_hash_not_found(self, repo):
        source = repo.get_by_hash("no_such_hash")
        assert source is None
