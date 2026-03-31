"""
Tests for PublisherRepository CRUD methods
============================================
add_song_publisher, remove_song_publisher, update_publisher

populated_db publishers:
  PublisherID=1:  "Universal Music Group"  parent=NULL
  PublisherID=2:  "Island Records"         parent=1
  PublisherID=3:  "Island Def Jam"         parent=2
  PublisherID=4:  "Roswell Records"        parent=NULL
  PublisherID=5:  "Sub Pop"                parent=NULL
  PublisherID=10: "DGC Records"            parent=1

RecordingPublishers:
  Song 1 -> DGC Records (10)
  Song 2 -> Roswell Records (4) (via Album 200)
  Songs 3-9: no recording publishers
"""

from src.data.publisher_repository import PublisherRepository


class TestAddSongPublisher:
    def test_add_existing_publisher_to_song(self, populated_db):
        """Add an existing publisher to Song 3 — should create link, not duplicate Publisher row."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            result = repo.add_song_publisher(3, "Sub Pop", conn)
            conn.commit()

        assert (
            result.id == 5
        ), f"Expected PublisherID=5 (existing Sub Pop), got {result.id}"
        assert result.name == "Sub Pop", f"Expected name='Sub Pop', got '{result.name}'"

        # Verify no duplicate Publisher row
        with repo._get_connection() as conn:
            rows = conn.execute(
                "SELECT PublisherID FROM Publishers WHERE PublisherName = 'Sub Pop'"
            ).fetchall()
            assert (
                len(rows) == 1
            ), f"Expected 1 Sub Pop row (no duplicate), got {len(rows)}"

        # Verify link created
        publishers = repo.get_publishers_for_songs([3])
        assert (
            len(publishers) == 1
        ), f"Expected 1 publisher on Song 3, got {len(publishers)}"
        assert (
            publishers[0][1].id == 5
        ), f"Expected PublisherID=5, got {publishers[0][1].id}"

    def test_add_new_publisher_creates_row(self, populated_db):
        """Add a brand-new publisher to Song 3 — should create Publisher row and link."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            result = repo.add_song_publisher(3, "Interscope Records", conn)
            conn.commit()

        assert (
            result.name == "Interscope Records"
        ), f"Expected name='Interscope Records', got '{result.name}'"
        assert result.id is not None, "Expected id to be set, got None"

        publishers = repo.get_publishers_for_songs([3])
        assert (
            len(publishers) == 1
        ), f"Expected 1 publisher on Song 3, got {len(publishers)}"
        assert (
            publishers[0][1].name == "Interscope Records"
        ), f"Expected 'Interscope Records', got '{publishers[0][1].name}'"

    def test_add_publisher_idempotent_on_duplicate(self, populated_db):
        """Adding the same publisher twice should not create duplicate RecordingPublishers rows."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_song_publisher(3, "Sub Pop", conn)
            repo.add_song_publisher(3, "Sub Pop", conn)
            conn.commit()

        publishers = repo.get_publishers_for_songs([3])
        sub_pop = [p for _, p in publishers if p.name == "Sub Pop"]
        assert (
            len(sub_pop) == 1
        ), f"Expected 1 Sub Pop link (idempotent), got {len(sub_pop)}"

    def test_add_publisher_does_not_affect_other_songs(self, populated_db):
        """Adding a publisher to Song 3 should not affect Song 1's publishers."""
        repo = PublisherRepository(populated_db)
        before = repo.get_publishers_for_songs([1])

        with repo._get_connection() as conn:
            repo.add_song_publisher(3, "Sub Pop", conn)
            conn.commit()

        after = repo.get_publishers_for_songs([1])
        assert len(after) == len(
            before
        ), f"Song 1 publisher count should not change: expected {len(before)}, got {len(after)}"


class TestRemoveSongPublisher:
    def test_remove_publisher_deletes_link(self, populated_db):
        """Remove DGC Records from Song 1 — link should be gone, Publisher record should remain."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            repo.remove_song_publisher(
                1, 10, conn
            )  # Remove DGC Records (ID=10) from Song 1
            conn.commit()

        publishers = repo.get_publishers_for_songs([1])
        assert (
            len(publishers) == 0
        ), f"Expected 0 publishers on Song 1 after remove, got {len(publishers)}"

        # Publisher record persists
        pub = repo.get_by_id(10)
        assert (
            pub is not None
        ), "Expected Publisher record (ID=10) to persist after link removal"
        assert (
            pub.name == "DGC Records"
        ), f"Expected name='DGC Records', got '{pub.name}'"

    def test_remove_publisher_does_not_affect_other_songs(self, populated_db):
        """Removing DGC Records from Song 1 should not affect other songs."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_song_publisher(3, "DGC Records", conn)
            conn.commit()

        with repo._get_connection() as conn:
            repo.remove_song_publisher(1, 10, conn)
            conn.commit()

        publishers_song3 = repo.get_publishers_for_songs([3])
        assert (
            len(publishers_song3) == 1
        ), f"Expected Song 3 to still have 1 publisher, got {len(publishers_song3)}"
        assert (
            publishers_song3[0][1].id == 10
        ), f"Expected DGC Records on Song 3, got {publishers_song3[0][1].id}"


class TestUpdatePublisher:
    def test_update_publisher_name(self, populated_db):
        """Update a publisher's name — should change PublisherName in Publishers table."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_publisher(5, "Sub Pop Records", conn)
            conn.commit()

        pub = repo.get_by_id(5)
        assert (
            pub.name == "Sub Pop Records"
        ), f"Expected name='Sub Pop Records', got '{pub.name}'"

    def test_update_publisher_is_global(self, populated_db):
        """Updating DGC Records (ID=10) should reflect on all songs linked to it."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_publisher(10, "DGC Records (Updated)", conn)
            conn.commit()

        publishers_song1 = repo.get_publishers_for_songs([1])
        assert (
            publishers_song1[0][1].name == "DGC Records (Updated)"
        ), f"Expected updated name on Song 1, got '{publishers_song1[0][1].name}'"

    def test_update_publisher_does_not_affect_other_publishers(self, populated_db):
        """Updating Sub Pop should not affect Roswell Records."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_publisher(5, "Sub Pop Renamed", conn)
            conn.commit()

        roswell = repo.get_by_id(4)
        assert (
            roswell.name == "Roswell Records"
        ), f"Expected 'Roswell Records' unchanged, got '{roswell.name}'"


class TestSetParent:
    def test_set_parent_assigns_parent_id(self, populated_db):
        """Set PublisherID=5 (Sub Pop, parent=NULL) to have parent=1 (Universal Music Group)."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            repo.set_parent(5, 1, conn)
            conn.commit()

        publisher = repo.get_by_id(5)
        assert (
            publisher.parent_id == 1
        ), f"Expected parent_id=1, got {publisher.parent_id}"
        assert (
            publisher.name == "Sub Pop"
        ), f"Expected name='Sub Pop' unchanged, got '{publisher.name}'"

    def test_clear_parent_sets_null(self, populated_db):
        """Clear parent from PublisherID=10 (DGC Records, parent=1) → parent=NULL."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            repo.set_parent(10, None, conn)
            conn.commit()

        publisher = repo.get_by_id(10)
        assert (
            publisher.parent_id is None
        ), f"Expected parent_id=None after clear, got {publisher.parent_id}"
        assert (
            publisher.name == "DGC Records"
        ), f"Expected name='DGC Records' unchanged, got '{publisher.name}'"

    def test_set_parent_nonexistent_publisher_raises(self, populated_db):
        """set_parent on a nonexistent publisher_id should raise LookupError."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            import pytest

            with pytest.raises(LookupError):
                repo.set_parent(9999, 1, conn)

    def test_set_parent_does_not_affect_other_publishers(self, populated_db):
        """Changing parent of publisher 5 must not touch publisher 4."""
        repo = PublisherRepository(populated_db)

        with repo._get_connection() as conn:
            repo.set_parent(5, 1, conn)
            conn.commit()

        roswell = repo.get_by_id(4)
        assert (
            roswell.parent_id is None
        ), f"Expected Roswell Records parent_id=None unchanged, got {roswell.parent_id}"
