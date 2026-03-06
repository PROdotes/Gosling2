from src.data.song_credit_repository import SongCreditRepository
from src.data.song_repository import SongRepository


def test_song_credit_repo_empty_input(mock_db_path):
    """Verify 100% coverage by hitting empty input branch."""
    repo = SongCreditRepository(mock_db_path)
    assert repo.get_credits_for_songs([]) == []


def test_song_repo_empty_input(mock_db_path):
    """Verify 100% coverage for batch-fetch with empty input."""
    repo = SongRepository(mock_db_path)
    assert repo.get_by_ids([]) == []
