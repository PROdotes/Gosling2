from src.data.song_repository import SongRepository
from src.data.song_credit_repository import SongCreditRepository


class TestDelete:
    """Verifies hard delete with cascade effects."""

    def test_delete_existing_song_removes_from_both_tables(self, populated_db):
        repo = SongRepository(populated_db)
        credit_repo = SongCreditRepository(populated_db)

        # Song 1 (Smells Like Teen Spirit) has credits
        song_id = 1

        # 1. Verify existence + credits
        song = repo.get_by_id(song_id)
        assert song is not None, f"Song {song_id} should exist before delete"
        credits = credit_repo.get_credits_for_songs([song_id])
        assert len(credits) > 0, "Song 1 should have credits in populated_db"

        # 2. Execute Delete
        with repo._get_connection() as conn:
            result = repo.delete(song_id, conn)
            conn.commit()

        # 3. Assert return value
        assert result is True, f"Expected True (deleted), got {result}"

        # 4. Verify song is gone (MediaSources + Songs via cascade)
        assert (
            repo.get_by_id(song_id) is None
        ), f"Song {song_id} should be None after delete"

        # 5. Verify credits are gone (Cascade verify)
        # Note: SongCreditRepository uses a join, so if the song is gone from MediaSources,
        # but the credits table itself might have orphans if PRAGMA foreign_keys is OFF.
        # But we enabled it in BaseRepository.
        with repo._get_connection() as conn:
            res = conn.execute(
                "SELECT COUNT(*) FROM SongCredits WHERE SourceID = ?", (song_id,)
            ).fetchone()
            assert res[0] == 0, f"Expected 0 credits after cascade delete, got {res[0]}"

    def test_delete_nonexistent_song_returns_false(self, populated_db):
        repo = SongRepository(populated_db)
        song_id = 9999

        with repo._get_connection() as conn:
            result = repo.delete(song_id, conn)
            conn.commit()

        assert result is False, f"Expected False for nonexistent ID, got {result}"
