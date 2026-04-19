from src.data.song_repository import SongRepository
from src.data.song_credit_repository import SongCreditRepository


class TestDelete:
    """Verifies soft delete with visibility filtering and link severance."""

    def test_soft_delete_makes_song_unretrievable_and_severs_links(self, populated_db):
        repo = SongRepository(populated_db)
        credit_repo = SongCreditRepository(populated_db)

        # Song 1 (Smells Like Teen Spirit) has credits
        song_id = 1

        # 1. Verify existence + credits
        song = repo.get_by_id(song_id)
        assert song is not None, f"Song {song_id} should exist before delete"
        credits = credit_repo.get_credits_for_songs([song_id])
        assert len(credits) > 0, "Song 1 should have credits in populated_db"

        # 2. Execute soft delete protocol
        with repo._get_connection() as conn:
            # We must severed links manually while the anchor row remains
            repo.delete_song_links(song_id, conn)
            result = repo.soft_delete(song_id, conn)
            conn.commit()

        # 3. Assert return value
        assert result is True, f"Expected True (deleted), got {result}"

        # 4. Verify song is HIDDEN (MediaSources + Songs join filters it)
        assert (
            repo.get_by_id(song_id) is None
        ), f"Song {song_id} should be unretrievable after soft delete"

        # 5. Verify credits are PURGED (Manual links HARD delete)
        with repo._get_connection() as conn:
            res = conn.execute(
                "SELECT COUNT(*) FROM SongCredits WHERE SourceID = ?", (song_id,)
            ).fetchone()
            assert res[0] == 0, f"Expected 0 credits after link purge, got {res[0]}"

        # 6. Verify record actually PERESERVED (Sanity check for Undo support)
        with repo._get_connection() as conn:
            res = conn.execute(
                "SELECT COUNT(*) FROM MediaSources WHERE SourceID = ?", (song_id,)
            ).fetchone()
            assert res[0] == 1, "MediaSource anchor should endure soft delete"

    def test_soft_delete_nonexistent_song_returns_false(self, populated_db):
        repo = SongRepository(populated_db)
        song_id = 9999

        with repo._get_connection() as conn:
            result = repo.soft_delete(song_id, conn)
            conn.commit()

        assert result is False, f"Expected False for nonexistent ID, got {result}"
