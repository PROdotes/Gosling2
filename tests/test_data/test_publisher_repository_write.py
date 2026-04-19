"""
Tests for PublisherRepository.insert_song_publishers (RED phase)
================================================================
Verifies get-or-create logic for Publishers table and link insertion into RecordingPublishers.
Uses populated_db which already has:
    Publishers: 1=Universal Music Group, 2=Island Records, 3=Island Def Jam,
                4=Roswell Records, 5=Sub Pop, 10=DGC Records
    RecordingPublishers: Song 1 -> DGC Records(10)
    Songs: 1-9 (various)
"""

import sqlite3
from src.data.publisher_repository import PublisherRepository
from src.models.domain import Publisher


class TestInsertSongPublishers:
    def test_insert_new_publisher_creates_row_and_link(self, populated_db):
        """Insert a brand-new publisher onto Song 3 (no publishers currently)."""
        repo = PublisherRepository(populated_db)

        publishers = [Publisher(name="Ninja Tune")]

        with repo._get_connection() as conn:
            repo.insert_song_publishers(3, publishers, conn)
            conn.commit()

        # Verify Publishers table
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT PublisherID, PublisherName FROM Publishers WHERE PublisherName = 'Ninja Tune'"
            ).fetchone()
            assert row is not None, "Expected 'Ninja Tune' publisher row to exist"
            assert (
                row["PublisherName"] == "Ninja Tune"
            ), f"Expected 'Ninja Tune', got '{row['PublisherName']}'"

        # Verify RecordingPublishers link
        result = repo.get_publishers_for_songs([3])
        assert len(result) == 1, f"Expected 1 publisher on Song 3, got {len(result)}"
        _, pub = result[0]
        assert pub.name == "Ninja Tune", f"Expected 'Ninja Tune', got '{pub.name}'"

    def test_insert_existing_publisher_reuses_id(self, populated_db):
        """Insert 'DGC Records' (already PublisherID=10) onto Song 3 — should reuse, not duplicate."""
        repo = PublisherRepository(populated_db)

        publishers = [Publisher(name="DGC Records")]

        with repo._get_connection() as conn:
            repo.insert_song_publishers(3, publishers, conn)
            conn.commit()

        # Verify no duplicate Publisher row
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT PublisherID FROM Publishers WHERE PublisherName = 'DGC Records' COLLATE UTF8_NOCASE"
            ).fetchall()
            assert (
                len(rows) == 1
            ), f"Expected 1 'DGC Records' row (reused), got {len(rows)}"
            assert (
                rows[0]["PublisherID"] == 10
            ), f"Expected PublisherID=10 (original), got {rows[0]['PublisherID']}"

        # Verify link
        result = repo.get_publishers_for_songs([3])
        assert len(result) == 1, f"Expected 1 publisher on Song 3, got {len(result)}"

    def test_insert_case_insensitive_reuse(self, populated_db):
        """'dgc records' (lowercase) should reuse existing 'DGC Records'."""
        repo = PublisherRepository(populated_db)

        publishers = [Publisher(name="dgc records")]

        with repo._get_connection() as conn:
            repo.insert_song_publishers(3, publishers, conn)
            conn.commit()

        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT PublisherID FROM Publishers WHERE PublisherName = 'DGC Records' COLLATE UTF8_NOCASE"
            ).fetchall()
            assert (
                len(rows) == 1
            ), f"Expected 1 publisher row (case-insensitive reuse), got {len(rows)}"

    def test_insert_empty_list_is_noop(self, populated_db):
        """Passing empty list should not crash or create any rows."""
        repo = PublisherRepository(populated_db)

        # Song 3 has no recording publishers before
        before = repo.get_publishers_for_songs([3])
        assert (
            len(before) == 0
        ), f"Expected 0 publishers on Song 3 before, got {len(before)}"

        with repo._get_connection() as conn:
            repo.insert_song_publishers(3, [], conn)
            conn.commit()

        after = repo.get_publishers_for_songs([3])
        assert (
            len(after) == 0
        ), f"Expected 0 publishers on Song 3 after empty insert, got {len(after)}"
