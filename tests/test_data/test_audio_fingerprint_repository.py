import numpy as np

from src.data.audio_fingerprint_repository import AudioFingerprintRepository


def _blob(n=1400):
    return np.arange(n, dtype="<u4").tobytes()


class TestAudioFingerprintRepository:
    def test_get_missing_returns_none(self, populated_db):
        repo = AudioFingerprintRepository(populated_db)
        with repo._get_connection() as conn:
            assert repo.get_fingerprint(7, conn) is None

    def test_set_then_get_roundtrips(self, populated_db):
        repo = AudioFingerprintRepository(populated_db)
        blob = _blob()
        with repo._get_connection() as conn:
            rows = repo.set_fingerprint(7, blob, 236.0, 180, conn)
            conn.commit()
        assert rows == 1

        with repo._get_connection() as conn:
            fingerprint, duration, cap = repo.get_fingerprint(7, conn)
        assert fingerprint == blob
        assert np.array_equal(np.frombuffer(fingerprint, dtype="<u4"), np.arange(1400))
        assert duration == 236.0
        assert cap == 180

    def test_failed_attempt_stores_null_fingerprint(self, populated_db):
        repo = AudioFingerprintRepository(populated_db)
        with repo._get_connection() as conn:
            repo.set_fingerprint(7, None, None, None, conn)
            conn.commit()

        with repo._get_connection() as conn:
            result = repo.get_fingerprint(7, conn)
        # Distinct from a missing row: the row exists, its fingerprint is NULL.
        assert result == (None, None, None)

    def test_set_replaces_existing_row(self, populated_db):
        repo = AudioFingerprintRepository(populated_db)
        with repo._get_connection() as conn:
            repo.set_fingerprint(7, None, None, None, conn)
            repo.set_fingerprint(7, _blob(10), 100.0, 180, conn)
            conn.commit()

        with repo._get_connection() as conn:
            fingerprint, duration, _ = repo.get_fingerprint(7, conn)
        assert np.array_equal(np.frombuffer(fingerprint, dtype="<u4"), np.arange(10))
        assert duration == 100.0

        with repo._get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM AudioFingerprints WHERE SourceID = 7"
            ).fetchone()[0]
        assert count == 1

    def test_write_produces_no_changelog_rows(self, populated_db):
        repo = AudioFingerprintRepository(populated_db)
        with repo._get_connection() as conn:
            before = conn.execute("SELECT COUNT(*) FROM ChangeLog").fetchone()[0]
            repo.set_fingerprint(7, _blob(), 236.0, 180, conn)
            conn.commit()
            after = conn.execute("SELECT COUNT(*) FROM ChangeLog").fetchone()[0]
        assert after == before

    def test_deleting_source_cascades(self, populated_db):
        repo = AudioFingerprintRepository(populated_db)
        with repo._get_connection() as conn:
            repo.set_fingerprint(7, _blob(), 236.0, 180, conn)
            conn.execute("DELETE FROM MediaSources WHERE SourceID = 7")
            conn.commit()
            remaining = conn.execute(
                "SELECT COUNT(*) FROM AudioFingerprints WHERE SourceID = 7"
            ).fetchone()[0]
        assert remaining == 0
