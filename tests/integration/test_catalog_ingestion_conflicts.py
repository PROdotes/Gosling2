import pytest
import os
from src.services.catalog_service import CatalogService
from src.models.exceptions import ReingestionConflictError


class TestCatalogIngestionConflicts:
    """Integration tests for reactive ghost detection in the Service Layer."""

    def test_ingest_file_raises_reingestion_conflict_on_ghost_match(
        self, populated_db, tmp_path
    ):
        """
        When a file matches a soft-deleted record's hash, CatalogService must raise
        a ReingestionConflictError with the ghost's metadata.
        """
        service = CatalogService(populated_db)
        source_id = 1  # Song 1: hash_1, Smells Like Teen Spirit, 200s

        # 1. Soft delete the existing song
        # Use simple SQL to simulate the state since we are testing the service's reaction
        # (CatalogService.delete_song also works, but repo SQL is more isolating)
        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET IsDeleted = 1 WHERE SourceID = ?", (source_id,)
        )
        # Also simulate hard-link deletion (since CatalogService.delete_song does this)
        conn.execute("DELETE FROM SongCredits WHERE SourceID = ?", (source_id,))
        conn.commit()
        conn.close()

        # 2. Create a dummy staged file that matches the ghost hash
        staged_file = tmp_path / "restored.mp3"
        staged_file.write_text("dummy content")
        staged_path = str(staged_file)

        # We need to mock the hash because calculate_audio_hash is slow/real
        # But for an integration test, we can just make a real file and ensure the service sees it.
        # Actually, let's just use the real calculate_audio_hash result if we use a real file.
        # But wait, we want 'hash_1'. If we want the test to pass reliably, we can mock the calculater.

        from unittest.mock import patch

        # 3. Execution
        with patch(
            "src.services.catalog_service.calculate_audio_hash", return_value="hash_1"
        ):
            with pytest.raises(ReingestionConflictError) as exc_info:
                service.ingest_file(staged_path)

        # 4. Exhaustive Contract Assertions (Rule 1: Engineers think about the data)
        err = exc_info.value
        assert err.ghost_id == 1, f"Expected 1, got {err.ghost_id}"
        assert (
            err.title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{err.title}'"
        assert err.duration_s == 200.0, f"Expected 200.0, got {err.duration_s}"
        assert err.status_code == 409, f"Expected 409, got {err.status_code}"

        expected_msg = (
            "song with that hash already exists, Smells Like Teen Spirit, 200.0"
        )
        assert (
            err.message == expected_msg
        ), f"Expected '{expected_msg}', got '{err.message}'"

        # 5. Side Effects
        # Staged file should NOT have been deleted if it's a conflict (user might want to keep it)
        # Actually, current ingest_file deletes it on ALREADY_EXISTS.
        # But for conflicts, maybe we keep it for the resolution?
        # User said: "throw an error... wait for the frontend to say yes/no"
        # If we delete the file, the frontend can't resume.
        # So it should STAY in staging.
        assert os.path.exists(
            staged_path
        ), "Staged file must survive conflict for later resolution"

    def test_ingest_file_raises_reingestion_conflict_on_hash_collision_at_different_path(
        self, populated_db, tmp_path
    ):
        """
        Verify that a bit-identical file (same hash) at a DIFFERENT path also triggers
        the ghost conflict error instead of a stealth duplicate.
        """
        service = CatalogService(populated_db)
        source_id = 1  # hash_1

        # 1. Soft delete ghost
        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET IsDeleted = 1 WHERE SourceID = ?", (source_id,)
        )
        conn.commit()
        conn.close()

        # 2. Try ingesting at DIFFERENT path but SAME hash
        new_staged_file = tmp_path / "moved.mp3"
        new_staged_file.write_text("dummy")
        new_staged_path = str(new_staged_file)

        from unittest.mock import patch

        with patch(
            "src.services.catalog_service.calculate_audio_hash", return_value="hash_1"
        ):
            with pytest.raises(ReingestionConflictError) as exc_info:
                service.ingest_file(new_staged_path)

        assert exc_info.value.ghost_id == 1
