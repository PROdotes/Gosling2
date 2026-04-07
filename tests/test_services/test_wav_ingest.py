"""
Tests for WAV ingestion redesign:
  - MetadataParser.parse: filename-stem fallback when no title tag
  - CatalogService.ingest_wav_as_converting
  - CatalogService.finalize_wav_conversion

Populated DB reference (from conftest):
    Song 1:  "Smells Like Teen Spirit"  Performers: [Nirvana]      Year: 1991
    Song 2:  "Everlong"                 Performers: [Foo Fighters]  Year: 1997
    ... (no WAV songs — all fixtures are MP3)
"""

import shutil
import wave
from pathlib import Path

import pytest

from src.services.catalog_service import CatalogService
from src.services.metadata_parser import MetadataParser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wav(path: Path, title_stem: str = "My WAV Track") -> Path:
    """
    Write a minimal valid WAV file to `path`.
    Uses the stdlib `wave` module — no ffmpeg required.
    The filename stem is `title_stem` so we can assert the fallback.
    """
    wav_path = path / f"{title_stem}.wav"
    with wave.open(str(wav_path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        # ~0.1 s of silence
        f.writeframes(b"\x00\x00" * 4410)
    return wav_path


@pytest.fixture
def ingest_db(empty_db):
    """Seed empty_db with Types + Roles needed for ingestion."""
    import sqlite3

    conn = sqlite3.connect(empty_db)
    conn.execute("INSERT INTO Types (TypeID, TypeName) VALUES (1, 'Song')")
    conn.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (1, 'Performer')")
    conn.commit()
    conn.close()
    return empty_db


@pytest.fixture
def staged_wav(tmp_path):
    """A real WAV file staged in tmp_path/staging/. Filename stem = 'Cool Song Name'."""
    staging = tmp_path / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    return _make_wav(staging, title_stem="Cool Song Name")


@pytest.fixture
def second_staged_wav(tmp_path):
    """A second unique WAV for duplicate tests."""
    staging = tmp_path / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    return _make_wav(staging, title_stem="Another WAV Song")


# ---------------------------------------------------------------------------
# MetadataParser — filename-stem title fallback
# ---------------------------------------------------------------------------


class TestMetadataParserFilenameStemFallback:
    def test_wav_without_title_tag_uses_filename_stem(self, tmp_path):
        wav = _make_wav(tmp_path, title_stem="My WAV Track")
        parser = MetadataParser()
        # WAV has no ID3 title tag — raw_metadata is empty
        song = parser.parse({}, str(wav))
        assert (
            song.media_name == "My WAV Track"
        ), f"Expected 'My WAV Track' from filename stem, got '{song.media_name}'"

    def test_mp3_with_title_tag_uses_tag_not_stem(self, tmp_path):
        # When a title tag IS present, the stem fallback must NOT override it
        parser = MetadataParser()
        fake_path = tmp_path / "some_stem_name.mp3"
        song = parser.parse({"TIT2": ["Tagged Title"]}, str(fake_path))
        assert (
            song.media_name == "Tagged Title"
        ), f"Expected 'Tagged Title' from tag, got '{song.media_name}'"

    def test_empty_title_tag_uses_filename_stem(self, tmp_path):
        # Edge: TIT2 present but empty string → still fall back to stem
        parser = MetadataParser()
        fake_path = tmp_path / "stem_title.mp3"
        song = parser.parse({"TIT2": [""]}, str(fake_path))
        assert (
            song.media_name == "stem_title"
        ), f"Expected 'stem_title' from stem, got '{song.media_name}'"


# ---------------------------------------------------------------------------
# CatalogService.ingest_wav_as_converting
# ---------------------------------------------------------------------------


class TestIngestWavAsConverting:
    def test_new_wav_returns_converting_status(self, ingest_db, staged_wav):
        service = CatalogService(ingest_db)
        result = service.ingest_wav_as_converting(str(staged_wav))
        assert (
            result["status"] == "CONVERTING"
        ), f"Expected status CONVERTING, got {result['status']}"

    def test_new_wav_returns_song_with_id(self, ingest_db, staged_wav):
        service = CatalogService(ingest_db)
        result = service.ingest_wav_as_converting(str(staged_wav))
        song = result["song"]
        assert song.id is not None, "Expected a DB-assigned ID"

    def test_new_wav_song_has_processing_status_3(self, ingest_db, staged_wav):
        service = CatalogService(ingest_db)
        result = service.ingest_wav_as_converting(str(staged_wav))
        song = result["song"]
        assert (
            song.processing_status == 3
        ), f"Expected processing_status=3 (Converting), got {song.processing_status}"

    def test_new_wav_song_title_is_filename_stem(self, ingest_db, staged_wav):
        service = CatalogService(ingest_db)
        result = service.ingest_wav_as_converting(str(staged_wav))
        song = result["song"]
        assert (
            song.media_name == "Cool Song Name"
        ), f"Expected 'Cool Song Name' from stem, got '{song.media_name}'"

    def test_new_wav_persisted_in_db(self, ingest_db, staged_wav):
        service = CatalogService(ingest_db)
        result = service.ingest_wav_as_converting(str(staged_wav))
        song_id = result["song"].id
        db_song = service.get_song(song_id)
        assert db_song is not None, "Song should be retrievable from DB after ingest"
        assert (
            db_song.processing_status == 3
        ), f"Expected DB processing_status=3, got {db_song.processing_status}"

    def test_new_wav_source_path_stored_correctly(self, ingest_db, staged_wav):
        service = CatalogService(ingest_db)
        result = service.ingest_wav_as_converting(str(staged_wav))
        song = result["song"]
        assert song.source_path == str(
            staged_wav
        ), f"Expected source_path={staged_wav}, got {song.source_path}"

    def test_duplicate_wav_returns_already_exists(
        self, ingest_db, staged_wav, tmp_path
    ):
        service = CatalogService(ingest_db)
        # Ingest first time
        service.ingest_wav_as_converting(str(staged_wav))
        # Stage an identical copy
        staging = tmp_path / "staging2"
        staging.mkdir(parents=True, exist_ok=True)
        dup = staging / "Cool Song Name.wav"
        shutil.copy(staged_wav, dup)
        result = service.ingest_wav_as_converting(str(dup))
        assert result["status"] in (
            "ALREADY_EXISTS",
            "MATCHED_HASH",
        ), f"Expected duplicate to be rejected, got {result['status']}"

    def test_duplicate_wav_staged_file_is_cleaned_up(
        self, ingest_db, staged_wav, tmp_path
    ):
        service = CatalogService(ingest_db)
        service.ingest_wav_as_converting(str(staged_wav))
        staging = tmp_path / "staging2"
        staging.mkdir(parents=True, exist_ok=True)
        dup = staging / "Cool Song Name.wav"
        shutil.copy(staged_wav, dup)
        service.ingest_wav_as_converting(str(dup))
        assert not dup.exists(), "Duplicate staged WAV should be cleaned up"


# ---------------------------------------------------------------------------
# CatalogService.finalize_wav_conversion
# ---------------------------------------------------------------------------


class TestFinalizeWavConversion:
    def test_finalize_updates_source_path(self, ingest_db, staged_wav, tmp_path):
        service = CatalogService(ingest_db)
        result = service.ingest_wav_as_converting(str(staged_wav))
        song_id = result["song"].id

        mp3_path_obj = staged_wav.with_suffix(".mp3")
        mp3_path_obj.write_text("fake mp3 content")
        mp3_path = str(mp3_path_obj)
        service.finalize_wav_conversion(song_id, mp3_path)

        db_song = service.get_song(song_id)
        assert (
            db_song.source_path == mp3_path
        ), f"Expected source_path={mp3_path}, got {db_song.source_path}"

    def test_finalize_sets_processing_status_to_1(self, ingest_db, staged_wav):
        service = CatalogService(ingest_db)
        result = service.ingest_wav_as_converting(str(staged_wav))
        song_id = result["song"].id

        mp3_path_obj = staged_wav.with_suffix(".mp3")
        mp3_path_obj.write_text("fake mp3 content")
        mp3_path = str(mp3_path_obj)
        service.finalize_wav_conversion(song_id, mp3_path)

        db_song = service.get_song(song_id)
        assert (
            db_song.processing_status == 1
        ), f"Expected processing_status=1 after finalize, got {db_song.processing_status}"

    def test_finalize_other_fields_unchanged(self, ingest_db, staged_wav):
        service = CatalogService(ingest_db)
        result = service.ingest_wav_as_converting(str(staged_wav))
        song_id = result["song"].id
        original_title = result["song"].media_name

        mp3_path_obj = staged_wav.with_suffix(".mp3")
        mp3_path_obj.write_text("fake mp3 content")
        mp3_path = str(mp3_path_obj)
        service.finalize_wav_conversion(song_id, mp3_path)

        db_song = service.get_song(song_id)
        assert (
            db_song.media_name == original_title
        ), f"Expected title '{original_title}' to be unchanged, got '{db_song.media_name}'"
