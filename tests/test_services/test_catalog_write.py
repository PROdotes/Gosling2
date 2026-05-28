import os
import shutil
import pytest
from pathlib import Path
from src.services.catalog_service import CatalogService
from src.services.mutation_coordinator import MutationCoordinator
from src.engine.routers.mutation_models import MutationRequest, DeleteSongItem
from src.engine.config import SONG_DEFAULT_YEAR
from tests.conftest import _connect


def _delete_song(
    db_path, song_id, delete_file=False, monkeypatch=None, staging_dir=None
):
    if monkeypatch and staging_dir is not None:
        monkeypatch.setattr(
            "src.services.mutation_coordinator.STAGING_DIR", str(staging_dir)
        )
    MutationCoordinator(db_path).apply(
        MutationRequest(
            delete=[DeleteSongItem(type="song", id=song_id, delete_file=delete_file)]
        )
    )


@pytest.fixture
def test_mp3(tmp_path):
    """Provides a tagged mp3 in a temp staging location."""
    # Ensure staging exists in tmp_path
    staging = tmp_path / "staging"
    staging.mkdir(parents=True, exist_ok=True)

    fixture_path = Path("tests/fixtures/silence.mp3")
    staged_file = staging / "ingest_test.mp3"
    shutil.copy(fixture_path, staged_file)

    # Add unique tags to avoid collisions with populated_db
    from mutagen.id3 import ID3, TIT2, TPE1, TDRC, TBP

    tags = ID3(str(staged_file))
    tags.add(TIT2(encoding=3, text=["Unique Ingest Title"]))
    tags.add(TPE1(encoding=3, text=["Unique Artist"]))
    tags.add(TDRC(encoding=3, text=["2024"]))
    tags.add(TBP(encoding=3, text=["120"]))
    tags.save()

    return str(staged_file)


@pytest.fixture
def unicode_mp3(tmp_path):
    """Provides an mp3 with unicode tags."""
    staging = tmp_path / "staging"
    staging.mkdir(parents=True, exist_ok=True)

    fixture_path = Path("tests/fixtures/silence.mp3")
    staged_file = staging / "unicode_test.mp3"
    shutil.copy(fixture_path, staged_file)

    from mutagen.id3 import ID3, TIT2, TPE1

    tags = ID3(str(staged_file))
    tags.add(TIT2(encoding=3, text=["日本語タイトル"]))
    tags.add(TPE1(encoding=3, text=["アーティスト"]))
    tags.save()

    return str(staged_file)


@pytest.fixture
def ingest_db(empty_db):
    """Seed empty_db with required Types/Roles for ingestion tests (local)."""

    conn = _connect(empty_db)
    conn.execute("INSERT INTO Types (TypeID, TypeName) VALUES (1, 'Song')")
    # Ingestion tests need Performer role
    conn.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (1, 'Performer')")
    conn.commit()
    conn.close()
    return empty_db


class TestCatalogServiceIngestFile:
    """CatalogService.ingest_file(staged_path) contracts."""

    def test_ingest_new_song_returns_complete_hydrated_object(
        self, ingest_db, test_mp3
    ):
        service = CatalogService(ingest_db)

        # 1. Ingest
        report = service.ingest_file(test_mp3)

        assert (
            report["status"] == "INGESTED"
        ), f"Ingestion failed: {report.get('message')}"
        song = report["song"]

        # EXHAUSTIVE ASSERTIONS (Every field in Song model)
        assert song.id is not None, "Expected DB-assigned ID"
        assert (
            song.title == "Unique Ingest Title"
        ), f"Expected 'Unique Ingest Title', got {song.title}"
        assert (
            song.source_path == test_mp3
        ), f"Expected {test_mp3}, got {song.source_path}"
        # silence.mp3 is ~2.27s
        assert 2.0 < song.duration_s < 3.0, f"Expected ~2.27s, got {song.duration_s}"
        assert song.audio_hash is not None, "Expected audio hash to be calculated"
        assert song.year == 2024, f"Expected 2024, got {song.year}"
        assert song.bpm == 120, f"Expected 120, got {song.bpm}"
        assert (
            song.is_active is False
        ), f"Expected default is_active=False, got {song.is_active}"
        assert (
            song.processing_status == 1
        ), f"Expected processing_status=1 after enrichment, got {song.processing_status}"

        # Verify in DB via a fresh read
        db_song = service.get_song(song.id)
        assert db_song is not None, "Song should be retrievable from DB"
        assert db_song.id == song.id
        assert db_song.title == song.title
        assert db_song.audio_hash == song.audio_hash

    def test_ingest_new_song_defaults_to_single_album_type(self, ingest_db, test_mp3):
        service = CatalogService(ingest_db)

        # 1. Ingest
        report = service.ingest_file(test_mp3)
        assert report["status"] == "INGESTED"
        song = report["song"]

        # 2. Verify Album Type is 'Single' (from config default)
        # Ingested song in report is from parser (relaxed), so we fetch from DB to see persistence
        db_song = service.get_song(song.id)
        assert db_song is not None
        assert len(db_song.albums) == 1
        album = db_song.albums[0]
        assert (
            album.album_type == "Single"
        ), f"Expected default 'Single', got {album.album_type}"

    def test_ingest_path_collision_outside_staging_preserves_file(
        self, populated_db, tmp_path, monkeypatch
    ):
        """In-place scan: file is outside staging — ALREADY_EXISTS must NOT delete it.

        This is the regression test for the 2026-04-28 incident where 117 live
        broadcast files were zeroed because os.remove() ran without checking _is_staged().
        """
        service = CatalogService(populated_db)

        # File lives OUTSIDE staging (simulates in-place NAS scan)
        external_dir = tmp_path / "nas" / "Songs" / "Cro" / "2026"
        external_dir.mkdir(parents=True, exist_ok=True)
        live_file = external_dir / "some artist - some song.mp3"
        live_file.write_bytes(b"Live broadcast file - must not be deleted")

        # STAGING_DIR points elsewhere
        staging = tmp_path / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("src.services.ingestion_service.STAGING_DIR", str(staging))

        # Update Song 1 in DB to point at this live file
        with service._song_repo.get_connection() as conn:
            conn.execute(
                "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
                (str(live_file),),
            )
            conn.commit()

        report = service.ingest_file(str(live_file))

        assert (
            report["status"] == "ALREADY_EXISTS"
        ), f"Expected ALREADY_EXISTS, got {report['status']}"
        assert report["match_type"] == "PATH"

        # Live file must survive
        assert os.path.exists(
            str(live_file)
        ), "Live file outside staging must NOT be deleted on ALREADY_EXISTS"

    def test_ingest_hash_collision_returns_already_exists(
        self, populated_db, test_mp3, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            "src.services.ingestion_service.STAGING_DIR", str(tmp_path / "staging")
        )
        service = CatalogService(populated_db)
        # Mock calculate_audio_hash to return Song 1's hash "hash_1"
        monkeypatch.setattr(
            "src.services.ingestion_service.calculate_audio_hash", lambda x: "hash_1"
        )

        report = service.ingest_file(test_mp3)

        # Report structure
        assert (
            report["status"] == "ALREADY_EXISTS"
        ), f"Expected ALREADY_EXISTS, got {report['status']}"
        assert (
            report["match_type"] == "HASH"
        ), f"Expected HASH, got {report['match_type']}"

        # Exhaustive song assertions
        song = report["song"]
        assert song.id == 1, f"Expected collision with Song 1, got {song.id}"
        assert (
            song.title == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got {song.title}"
        assert (
            song.source_path == "/path/1"
        ), f"Expected '/path/1', got {song.source_path}"
        assert song.duration_s == 200, f"Expected 200s, got {song.duration_s}"
        assert song.audio_hash == "hash_1", f"Expected 'hash_1', got {song.audio_hash}"
        assert song.year == 1991, f"Expected 1991, got {song.year}"
        assert song.bpm is None, f"Expected None for bpm, got {song.bpm}"
        assert song.isrc is None, f"Expected None for isrc, got {song.isrc}"
        assert song.is_active is True, f"Expected True, got {song.is_active}"
        assert (
            song.processing_status == 0
        ), f"Expected 0 (fixture default), got {song.processing_status}"

        # SIDE EFFECT: File should be deleted to prevent orphans
        assert not os.path.exists(
            test_mp3
        ), "Staged file should be deleted on hash collision"

    def test_ingest_missing_file_returns_error(self, ingest_db):
        service = CatalogService(ingest_db)
        report = service.ingest_file("ghost.mp3")
        assert report["status"] == "ERROR"
        assert "File not found" in report["message"]

    def test_ingest_unicode_metadata_handles_correctly(self, ingest_db, unicode_mp3):
        service = CatalogService(ingest_db)
        report = service.ingest_file(unicode_mp3)

        assert (
            report["status"] == "INGESTED"
        ), f"Expected INGESTED, got {report['status']}"

        # Exhaustive song assertions
        song = report["song"]
        assert song.id is not None, "Expected DB-assigned ID"
        assert (
            song.title == "日本語タイトル"
        ), f"Expected '日本語タイトル', got {song.title}"
        assert (
            song.source_path == unicode_mp3
        ), f"Expected {unicode_mp3}, got {song.source_path}"
        assert 2.0 < song.duration_s < 3.0, f"Expected ~2.27s, got {song.duration_s}"
        assert song.audio_hash is not None, "Expected audio hash to be calculated"
        assert (
            song.year == SONG_DEFAULT_YEAR
        ), f"Expected {SONG_DEFAULT_YEAR} for year, got {song.year}"
        assert song.bpm is None, f"Expected None for bpm, got {song.bpm}"
        assert (
            song.isrc == "USCGJ2326543"
        ), f"Expected 'USCGJ2326543' (inherited from fixture file), got {song.isrc}"
        assert (
            song.is_active is False
        ), f"Expected default is_active=False, got {song.is_active}"
        assert (
            song.processing_status == 1
        ), f"Expected processing_status=1 after enrichment, got {song.processing_status}"

    def test_ingest_failure_rolls_back_and_deletes_staged_file(
        self, ingest_db, test_mp3, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            "src.services.ingestion_service.STAGING_DIR", str(tmp_path / "staging")
        )
        service = CatalogService(ingest_db)

        # Induce a DB failure during insert by monkeypatching the repo's insert to raise
        def mock_insert(*args, **kwargs):
            raise Exception("DATABASE ATOMIC FAILURE")

        monkeypatch.setattr(service._song_repo, "insert", mock_insert)

        assert os.path.exists(test_mp3)

        report = service.ingest_file(test_mp3)

        assert report["status"] == "ERROR"
        assert "DATABASE ATOMIC FAILURE" in report["message"]

        # SIDE EFFECT: File should be deleted to prevent orphans
        assert not os.path.exists(
            test_mp3
        ), "Staged file should be deleted on ingestion failure"

        # SIDE EFFECT: DB should be empty (rolled back)
        all_songs = service.search_songs_slim("Unique Ingest Title")
        assert len(all_songs) == 0, "Database should be empty after rollback"


class TestCatalogServiceDeleteSong:
    """Delete song via MutationCoordinator contracts."""

    def test_delete_existing_song_in_staging_removes_record_and_file(
        self, ingest_db, test_mp3, monkeypatch
    ):
        service = CatalogService(ingest_db)
        report = service.ingest_file(test_mp3)
        assert (
            report["status"] == "INGESTED"
        ), f"Setup ingestion failed: {report.get('message')}"
        song_id = report["song"].id

        staging_dir = str(Path(test_mp3).parent)
        assert os.path.exists(test_mp3)

        _delete_song(
            ingest_db, song_id, monkeypatch=monkeypatch, staging_dir=staging_dir
        )

        assert service.get_song(song_id) is None
        assert not os.path.exists(test_mp3), "Physical staged file should be deleted"

    def test_delete_existing_song_NOT_in_staging_removes_record_only(
        self, populated_db, tmp_path, monkeypatch
    ):
        service = CatalogService(populated_db)
        real_temp_path = tmp_path / "external_library" / "song1.mp3"
        real_temp_path.parent.mkdir(parents=True, exist_ok=True)
        real_temp_path.write_bytes(b"External song data")

        with service._song_repo.get_connection() as conn:
            conn.execute(
                "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
                (str(real_temp_path),),
            )
            conn.commit()

        staging_dir = str(tmp_path / "staging")
        _delete_song(populated_db, 1, monkeypatch=monkeypatch, staging_dir=staging_dir)

        assert service.get_song(1) is None
        assert os.path.exists(
            real_temp_path
        ), "File OUTSIDE staging should NOT be deleted"

    def test_delete_nonexistent_id_raises(self, ingest_db):
        with pytest.raises(LookupError):
            _delete_song(ingest_db, 999)

    def test_delete_cascades_work_correctly(self, populated_db):
        """Deleting a song must cascade to SongCredits, SongAlbums, etc."""
        service = CatalogService(populated_db)
        song_id = 1  # SLTS

        with service._song_repo.get_connection() as conn:
            credits = conn.execute(
                "SELECT count(*) FROM SongCredits WHERE SourceID = ?", (song_id,)
            ).fetchone()[0]
            albums = conn.execute(
                "SELECT count(*) FROM SongAlbums WHERE SourceID = ?", (song_id,)
            ).fetchone()[0]
            assert credits > 0, "Setup: Song should have credits"
            assert albums > 0, "Setup: Song should have album associations"

        _delete_song(populated_db, song_id)

        assert service.get_song(song_id) is None, "Song should be deleted"

        with service._song_repo.get_connection() as conn:
            credits = conn.execute(
                "SELECT count(*) FROM SongCredits WHERE SourceID = ?", (song_id,)
            ).fetchone()[0]
            assert credits == 0, "SongCredits should be cascaded"

            albums = conn.execute(
                "SELECT count(*) FROM SongAlbums WHERE SourceID = ?", (song_id,)
            ).fetchone()[0]
            assert albums == 0, "SongAlbums should be cascaded"

        album = service.get_album(100)
        assert album is not None, "Album should NOT be deleted when song is removed"
        assert album.title == "Nevermind", f"Expected 'Nevermind', got {album.title}"

        identity = service.get_identity(2)
        assert (
            identity is not None
        ), "Identity should NOT be deleted when song is removed"
        assert (
            identity.display_name == "Nirvana"
        ), f"Expected 'Nirvana', got {identity.display_name}"

    def test_delete_with_delete_file_true_removes_library_file(
        self, populated_db, tmp_path, monkeypatch
    ):
        service = CatalogService(populated_db)
        real_temp_path = tmp_path / "external_library" / "song1.mp3"
        real_temp_path.parent.mkdir(parents=True, exist_ok=True)
        real_temp_path.write_bytes(b"External song data")

        with service._song_repo.get_connection() as conn:
            conn.execute(
                "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
                (str(real_temp_path),),
            )
            conn.commit()

        assert os.path.exists(real_temp_path)

        _delete_song(populated_db, 1, delete_file=True)

        assert service.get_song(1) is None
        assert not os.path.exists(
            real_temp_path
        ), "Library file should be deleted when delete_file=True"

    def test_delete_with_delete_file_false_preserves_library_file(
        self, populated_db, tmp_path, monkeypatch
    ):
        service = CatalogService(populated_db)
        real_temp_path = tmp_path / "external_library" / "song1.mp3"
        real_temp_path.parent.mkdir(parents=True, exist_ok=True)
        real_temp_path.write_bytes(b"External song data")

        with service._song_repo.get_connection() as conn:
            conn.execute(
                "UPDATE MediaSources SET SourcePath = ? WHERE SourceID = 1",
                (str(real_temp_path),),
            )
            conn.commit()

        assert os.path.exists(real_temp_path)

        _delete_song(populated_db, 1, delete_file=False)

        assert service.get_song(1) is None
        assert os.path.exists(
            real_temp_path
        ), "Library file should be preserved when delete_file=False"
