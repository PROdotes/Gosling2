import sqlite3
from src.data.media_source_repository import MediaSourceRepository


class TestRowToSource:
    """MediaSourceRepository._row_to_source mapper contracts.

    Direct mapper tests catch bugs in type coercion, NULL handling,
    and field name mismatches.
    """

    def test_all_fields_present(self, populated_db):
        """Mapper must correctly cast all fields from a complete row."""
        mock_row = {
            "SourceID": 1,
            "TypeID": 1,
            "MediaName": "Smells Like Teen Spirit",
            "SourceDuration": 200.0,
            "SourcePath": "/path/1",
            "AudioHash": "hash_1",
            "IsActive": 1,
            "ProcessingStatus": None,
        }
        repo = MediaSourceRepository(populated_db)
        source = repo._row_to_source(mock_row)

        assert source.id == 1, f"Expected 1, got {source.id}"
        assert source.type_id == 1, f"Expected 1, got {source.type_id}"
        assert (
            source.media_name == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{source.media_name}'"
        assert (
            source.source_path == "/path/1"
        ), f"Expected '/path/1', got '{source.source_path}'"
        assert source.duration_s == 200.0, f"Expected 200.0, got {source.duration_s}"
        assert (
            source.duration_ms == 200000
        ), f"Expected 200000, got {source.duration_ms}"
        assert (
            source.audio_hash == "hash_1"
        ), f"Expected 'hash_1', got '{source.audio_hash}'"
        assert source.is_active is True, f"Expected True, got {source.is_active}"
        assert (
            source.processing_status is None
        ), f"Expected None, got {source.processing_status}"
        assert source.notes is None, f"Expected None, got {source.notes}"

    def test_null_fields(self, populated_db):
        """NULL DB values must map to None, not 0 or empty string."""
        mock_row = {
            "SourceID": 4,
            "TypeID": 1,
            "MediaName": "Grohlton Theme",
            "SourceDuration": 120.0,
            "SourcePath": "/path/4",
            "AudioHash": None,
            "IsActive": 1,
            "ProcessingStatus": None,
        }
        repo = MediaSourceRepository(populated_db)
        source = repo._row_to_source(mock_row)

        assert source.id == 4, f"Expected 4, got {source.id}"
        assert (
            source.audio_hash is None
        ), f"Expected None for NULL hash, got {source.audio_hash}"
        assert (
            source.processing_status is None
        ), f"Expected None for NULL status, got {source.processing_status}"

    def test_null_duration_maps_to_zero(self, populated_db):
        """NULL SourceDuration must not crash - must map to 0.0."""
        mock_row = {
            "SourceID": 1,
            "TypeID": 1,
            "MediaName": "Test",
            "SourceDuration": None,
            "SourcePath": "/a",
            "AudioHash": None,
            "IsActive": 1,
            "ProcessingStatus": None,
        }
        repo = MediaSourceRepository(populated_db)
        source = repo._row_to_source(mock_row)

        assert source.duration_s == 0.0, f"Expected 0.0, got {source.duration_s}"
        assert source.duration_ms == 0, f"Expected 0, got {source.duration_ms}"

    def test_duration_conversion(self, populated_db):
        """SourceDuration (seconds) must be preserved as float with ms property."""
        repo = MediaSourceRepository(populated_db)

        row = {
            "SourceID": 1,
            "TypeID": 1,
            "MediaName": "Test",
            "SourceDuration": 200.0,
            "SourcePath": "/a",
            "AudioHash": None,
            "IsActive": 1,
            "ProcessingStatus": None,
        }

        row["SourceDuration"] = 200.0
        assert repo._row_to_source(row).duration_ms == 200000

        row["SourceDuration"] = 0.0
        assert repo._row_to_source(row).duration_ms == 0

        row["SourceDuration"] = None
        assert repo._row_to_source(row).duration_ms == 0

    def test_boolean_casting(self, populated_db):
        """SQLite stores booleans as 0/1. Mapper must cast to Python bool."""
        repo = MediaSourceRepository(populated_db)

        base_row = {
            "SourceID": 1,
            "TypeID": 1,
            "MediaName": "Test",
            "SourceDuration": 100.0,
            "SourcePath": "/a",
            "AudioHash": None,
            "IsActive": 1,
            "ProcessingStatus": None,
        }

        # IsActive=1 -> True
        row_active = {**base_row, "IsActive": 1}
        assert repo._row_to_source(row_active).is_active is True

        # IsActive=0 -> False
        row_inactive = {**base_row, "IsActive": 0}
        assert repo._row_to_source(row_inactive).is_active is False

        # IsActive=NULL -> False
        row_null = {**base_row, "IsActive": None}
        assert repo._row_to_source(row_null).is_active is False


class TestGetByPath:
    """MediaSourceRepository.get_by_path contracts."""

    def test_valid_path_returns_source(self, populated_db):
        """Song 1 has SourcePath='/path/1'."""
        repo = MediaSourceRepository(populated_db)
        source = repo.get_by_path("/path/1")

        assert source is not None, f"Expected MediaSource, got {source}"
        assert source.id == 1, f"Expected 1, got {source.id}"
        assert (
            source.media_name == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{source.media_name}'"
        assert (
            source.source_path == "/path/1"
        ), f"Expected '/path/1', got '{source.source_path}'"
        assert source.type_id == 1, f"Expected 1, got {source.type_id}"

    def test_invalid_path_returns_none(self, populated_db):
        """Nonexistent path must return None."""
        repo = MediaSourceRepository(populated_db)
        source = repo.get_by_path("/no/such/path")
        assert source is None, f"Expected None for invalid path, got {source}"

    def test_empty_path_returns_none(self, populated_db):
        """Empty string must return None."""
        repo = MediaSourceRepository(populated_db)
        source = repo.get_by_path("")
        assert source is None, f"Expected None for empty path, got {source}"

    def test_soft_deleted_path_returns_none(self, populated_db):
        """Soft-deleted path must be hidden from lookup."""
        repo = MediaSourceRepository(populated_db)
        source_id = 1
        path = "/path/1"

        # 1. Soft delete
        with repo._get_connection() as conn:
            repo.soft_delete(source_id, conn)
            conn.commit()

        # 2. Lookup by path (should return None)
        source = repo.get_by_path(path)
        assert source is None, "Soft-deleted source should not be found by path"


class TestGetByHash:
    """MediaSourceRepository.get_by_hash contracts."""

    def test_valid_hash_returns_source(self, populated_db):
        """Song 1 has AudioHash='hash_1'."""
        repo = MediaSourceRepository(populated_db)
        source = repo.get_by_hash("hash_1")

        assert source is not None, f"Expected MediaSource, got {source}"
        assert source.id == 1, f"Expected 1, got {source.id}"
        assert (
            source.audio_hash == "hash_1"
        ), f"Expected 'hash_1', got '{source.audio_hash}'"
        assert (
            source.media_name == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{source.media_name}'"

    def test_nonexistent_hash_returns_none(self, populated_db):
        """Nonexistent hash must return None."""
        repo = MediaSourceRepository(populated_db)
        source = repo.get_by_hash("no_such_hash")
        assert source is None, f"Expected None for nonexistent hash, got {source}"

    def test_empty_hash_returns_none(self, populated_db):
        """Empty string must return None."""
        repo = MediaSourceRepository(populated_db)
        source = repo.get_by_hash("")
        assert source is None, f"Expected None for empty hash, got {source}"

    def test_soft_deleted_hash_returns_none(self, populated_db):
        """Soft-deleted hash must be hidden from lookup."""
        repo = MediaSourceRepository(populated_db)
        source_id = 1
        audio_hash = "hash_1"

        # 1. Soft delete
        with repo._get_connection() as conn:
            repo.soft_delete(source_id, conn)
            conn.commit()

        # 2. Lookup by hash (should return None)
        source = repo.get_by_hash(audio_hash)
        assert (
            source is None
        ), "Soft-deleted source should not be found by hash"


class TestDelete:
    """Verifies soft-delete protocol at the base level."""

    def test_soft_delete_marks_record_as_deleted_and_preserves_extension(
        self, populated_db
    ):
        repo = MediaSourceRepository(populated_db)
        # Song 1 (Smells Like Teen Spirit) exists in both MediaSources and Songs
        source_id = 1

        # 1. Verify existence in extension table (Songs)
        with repo._get_connection() as conn:
            res = conn.execute(
                "SELECT COUNT(*) FROM Songs WHERE SourceID = ?", (source_id,)
            ).fetchone()
            assert (
                res[0] == 1
            ), f"Expected song {source_id} to exist in Songs table before delete"

        # 2. Execute Soft Delete
        with repo._get_connection() as conn:
            result = repo.soft_delete(source_id, conn)
            conn.commit()

        # 3. Assert return value
        assert result is True, f"Expected True (deleted), got {result}"

        # 4. Verify record still exists but is marked deleted
        with repo._get_connection() as conn:
            res = conn.execute(
                "SELECT IsDeleted FROM MediaSources WHERE SourceID = ?", (source_id,)
            ).fetchone()
            assert res[0] == 1, "Expected IsDeleted = 1 after soft delete"

        # 5. Verify preservation in extension table (Songs) - CASCADE does not fire on UPDATE
        with repo._get_connection() as conn:
            res = conn.execute(
                "SELECT COUNT(*) FROM Songs WHERE SourceID = ?", (source_id,)
            ).fetchone()
            assert (
                res[0] == 1
            ), f"Expected extension record to be preserved after soft delete, got {res[0]}"

    def test_soft_delete_nonexistent_id_returns_false(self, populated_db):
        repo = MediaSourceRepository(populated_db)
        with repo._get_connection() as conn:
            result = repo.soft_delete(9999, conn)
            conn.commit()

        assert result is False, f"Expected False for nonexistent ID, got {result}"

    def test_insert_source_persists_core_fields(self, populated_db):
        from src.models.domain import Song

        repo = MediaSourceRepository(populated_db)

        # We can use Song as the model since it's a MediaSource
        source = Song(
            media_name="Universal Source",
            source_path="/music/universal.mp3",
            duration_s=60.0,
            audio_hash="universal_hash",
        )

        with repo._get_connection() as conn:
            new_id = repo.insert_source(source, "Song", conn)
            conn.commit()

        assert new_id > 0

        # Verify in DB
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM MediaSources WHERE SourceID = ?", (new_id,)
            ).fetchone()
            assert row is not None
            assert row["MediaName"] == "Universal Source"
            assert row["SourcePath"] == "/music/universal.mp3"
            assert (
                row["SourceDuration"] == 60.0
            ), f"Expected 60.0s, got {row['SourceDuration']}"
            assert row["AudioHash"] == "universal_hash"

            # Verify TypeID mapping
            res = conn.execute(
                "SELECT TypeID FROM Types WHERE TypeName = 'Song'"
            ).fetchone()
            assert res is not None
            type_id = res[0]
            assert row["TypeID"] == type_id
