import pytest
import os
from src.services.catalog_service import CatalogService
from src.models.exceptions import ReingestionConflictError
from tests.conftest import _connect


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

        conn = _connect(populated_db)
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
            "src.services.ingestion_service.calculate_audio_hash", return_value="hash_1"
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

        conn = _connect(populated_db)
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
            "src.services.ingestion_service.calculate_audio_hash", return_value="hash_1"
        ):
            with pytest.raises(ReingestionConflictError) as exc_info:
                service.ingest_file(new_staged_path)

        assert exc_info.value.ghost_id == 1


class TestResolveConflict:
    """Tests for resolve_conflict - reactivating ghost records with new metadata."""

    def test_resolve_conflict_happy_path_reactivates_ghost_with_new_metadata(
        self, populated_db, tmp_path, test_audio_file
    ):
        """
        When resolve_conflict is called with valid ghost_id and staged_path:
        1. MediaSources: IsDeleted=0, all fields updated with new metadata
        2. Songs: TempoBPM, RecordingYear, ISRC updated
        3. Old relationships deleted, new relationships inserted
        4. File stays in staging (no move operation)
        5. Returns {"status": "INGESTED", "song": <complete SongView>}
        """
        service = CatalogService(populated_db)
        ghost_id = 1  # Song 1: "Smells Like Teen Spirit", hash_1, 200s, 1991

        # 1. Soft-delete the existing song to create a ghost
        import shutil

        conn = _connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET IsDeleted = 1 WHERE SourceID = ?", (ghost_id,)
        )
        conn.execute("DELETE FROM SongCredits WHERE SourceID = ?", (ghost_id,))
        conn.commit()
        conn.close()

        # 2. Copy real test audio file to staging with UUID name
        staged_file = tmp_path / "uuid_staged_file.mp3"
        shutil.copy(test_audio_file, staged_file)
        staged_path = str(staged_file)

        # 3. Execute - using REAL file and REAL metadata extraction
        result = service.resolve_conflict(ghost_id, staged_path)

        # 4. Exhaustive Assertions on Return Value
        assert (
            result["status"] == "INGESTED"
        ), f"Expected 'INGESTED', got {result['status']}"
        assert "song" in result, "Result missing 'song' field"
        assert result["song"] is not None, "Expected song object, got None"

        song = result["song"]
        assert song.id == ghost_id, f"Expected ID {ghost_id}, got {song.id}"
        # The actual metadata will come from the test_audio_file, which we know from fixtures
        assert song.media_name is not None, "Expected media_name to be set, got None"
        assert song.duration_s > 0, f"Expected duration > 0, got {song.duration_s}"
        assert song.audio_hash is not None, "Expected audio_hash to be set, got None"
        assert song.is_active is False, f"Expected False, got {song.is_active}"

        # 5. Database Side Effects - Verify IsDeleted=0
        conn = _connect(populated_db)
        row = conn.execute(
            "SELECT MediaName, IsDeleted, SourceDuration, AudioHash FROM MediaSources WHERE SourceID = ?",
            (ghost_id,),
        ).fetchone()
        conn.close()

        assert row is not None, f"Ghost record {ghost_id} should still exist in DB"
        assert row[1] == 0, f"Expected IsDeleted=0, got {row[1]}"
        assert row[2] > 0, f"Expected duration > 0, got {row[2]}"
        assert row[3] is not None, "Expected hash to be set, got None"

        # 6. File stays in staging (no move operation)
        assert os.path.exists(
            staged_path
        ), f"Staged file should remain in staging, but is missing at {staged_path}"

    def test_resolve_conflict_nonexistent_ghost_id_returns_error(
        self, populated_db, tmp_path
    ):
        """
        When ghost_id doesn't exist in database, resolve_conflict returns error.
        """
        service = CatalogService(populated_db)
        ghost_id = 999  # Does not exist

        staged_file = tmp_path / "staged.mp3"
        staged_file.write_text("content")
        staged_path = str(staged_file)

        result = service.resolve_conflict(ghost_id, staged_path)

        assert result["status"] == "ERROR", f"Expected 'ERROR', got {result['status']}"
        assert "message" in result, "Result missing 'message' field"
        # Staged file should remain (not deleted on error)
        assert os.path.exists(staged_path), "Staged file should remain after error"

    def test_resolve_conflict_missing_staged_file_returns_error(
        self, populated_db, tmp_path
    ):
        """
        When staged_path doesn't exist, resolve_conflict returns error immediately.
        """
        service = CatalogService(populated_db)
        ghost_id = 1

        # Soft-delete to create ghost

        conn = _connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET IsDeleted = 1 WHERE SourceID = ?", (ghost_id,)
        )
        conn.commit()
        conn.close()

        fake_path = str(tmp_path / "nonexistent.mp3")

        result = service.resolve_conflict(ghost_id, fake_path)

        assert result["status"] == "ERROR", f"Expected 'ERROR', got {result['status']}"
        assert (
            result["message"] == "Staged file not found"
        ), f"Expected 'Staged file not found', got '{result['message']}'"

    def test_resolve_conflict_preserves_other_songs(
        self, populated_db, tmp_path, test_audio_file
    ):
        """
        Reactivating ghost_id=1 should NOT affect songs 2, 3, etc.
        """
        service = CatalogService(populated_db)
        ghost_id = 1

        # Soft-delete song 1
        import shutil

        conn = _connect(populated_db)
        conn.execute(
            "UPDATE MediaSources SET IsDeleted = 1 WHERE SourceID = ?", (ghost_id,)
        )
        conn.execute("DELETE FROM SongCredits WHERE SourceID = ?", (ghost_id,))
        conn.commit()
        conn.close()

        # Snapshot song 2 before reactivation
        from src.data.song_repository import SongRepository

        repo = SongRepository(populated_db)
        song_2_before = repo.get_by_id(2)
        assert song_2_before is not None, "Song 2 should exist before test"

        # Reactivate song 1 with real audio file
        staged_file = tmp_path / "staged.mp3"
        shutil.copy(test_audio_file, staged_file)
        staged_path = str(staged_file)

        service.resolve_conflict(ghost_id, staged_path)

        # Verify song 2 unchanged - ALL FIELDS
        song_2_after = repo.get_by_id(2)
        assert song_2_after is not None, "Song 2 should still exist after reactivation"
        assert (
            song_2_after.id == song_2_before.id
        ), f"Song 2 ID changed: {song_2_before.id} -> {song_2_after.id}"
        assert (
            song_2_after.media_name == song_2_before.media_name
        ), f"Song 2 media_name changed: {song_2_before.media_name} -> {song_2_after.media_name}"
        assert (
            song_2_after.duration_s == song_2_before.duration_s
        ), f"Song 2 duration changed: {song_2_before.duration_s} -> {song_2_after.duration_s}"
        assert (
            song_2_after.audio_hash == song_2_before.audio_hash
        ), f"Song 2 hash changed: {song_2_before.audio_hash} -> {song_2_after.audio_hash}"
        assert (
            song_2_after.source_path == song_2_before.source_path
        ), "Song 2 path changed"
        assert (
            song_2_after.is_active == song_2_before.is_active
        ), "Song 2 is_active changed"
        assert song_2_after.bpm == song_2_before.bpm, "Song 2 BPM changed"
        assert song_2_after.year == song_2_before.year, "Song 2 year changed"
        assert song_2_after.isrc == song_2_before.isrc, "Song 2 ISRC changed"
