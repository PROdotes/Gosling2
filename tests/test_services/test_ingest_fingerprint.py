"""
Integration: the ingest path records an acoustic-fingerprint row for every
source whose final audio is settled. NO MOCKING - real fpcalc, real SQLite.
"""

import os
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

from src.engine.config import FFMPEG_PATH, FPCALC_PATH
from src.services.catalog_service import CatalogService
from tests.conftest import _connect

binaries_required = pytest.mark.skipif(
    not (os.path.exists(FFMPEG_PATH) and os.path.exists(FPCALC_PATH)),
    reason="bundled ffmpeg/fpcalc binaries not available",
)


@pytest.fixture
def ingest_db(empty_db):
    conn = _connect(empty_db)
    conn.execute("INSERT INTO Types (TypeID, TypeName) VALUES (1, 'Song')")
    conn.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (1, 'Performer')")
    conn.commit()
    conn.close()
    return empty_db


def _fingerprint_row(db_path, source_id):
    conn = _connect(db_path)
    try:
        return conn.execute(
            "SELECT Fingerprint, DurationS, LengthCap FROM AudioFingerprints "
            "WHERE SourceID = ?",
            (source_id,),
        ).fetchone()
    finally:
        conn.close()


def _tone_mp3(path: Path, seconds=40, freq=440, title="Tone Track") -> str:
    subprocess.run(
        [
            str(FFMPEG_PATH),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq}:duration={seconds}",
            "-metadata",
            f"title={title}",
            "-metadata",
            "artist=Tone Artist",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return str(path)


class TestIngestFileFingerprint:
    @binaries_required
    def test_real_audio_stores_fingerprint(self, ingest_db, tmp_path):
        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        staged = _tone_mp3(staging / "tone.mp3", seconds=40)

        report = CatalogService(ingest_db).ingest_file(staged)
        assert report["status"] == "INGESTED", report.get("message")
        source_id = report["song"].id

        row = _fingerprint_row(ingest_db, source_id)
        assert row is not None, "expected an AudioFingerprints row"
        blob, duration_s, length_cap = row
        assert blob is not None
        fp = np.frombuffer(blob, dtype="<u4")
        assert fp.size > 0
        assert duration_s == pytest.approx(40, abs=1)
        assert length_cap == 180

    def test_undecodable_audio_records_failed_attempt(self, ingest_db, tmp_path):
        # silence.mp3 makes fpcalc emit "Empty fingerprint" and exit non-zero.
        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        staged = staging / "silent.mp3"
        shutil.copy("tests/fixtures/silence.mp3", staged)
        from mutagen.id3 import ID3, TIT2, TPE1

        tags = ID3(str(staged))
        tags.add(TIT2(encoding=3, text=["Silent Ingest"]))
        tags.add(TPE1(encoding=3, text=["Nobody"]))
        tags.save()

        report = CatalogService(ingest_db).ingest_file(str(staged))
        assert report["status"] == "INGESTED", report.get("message")
        source_id = report["song"].id

        row = _fingerprint_row(ingest_db, source_id)
        assert row is not None, "a failed attempt must still leave a row"
        blob = row[0]
        assert blob is None, "failed fpcalc run stores a NULL fingerprint"


class TestWavConversionFingerprint:
    def _stage_wav(self, tmp_path, stem="Wav Song"):
        staging = tmp_path / "staging"
        staging.mkdir(exist_ok=True)
        wav = staging / f"{stem}.wav"
        with wave.open(str(wav), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(44100)
            f.writeframes(b"\x00\x00" * 4410)
        return wav

    def test_wav_ingest_defers_fingerprint_until_finalize(self, ingest_db, tmp_path):
        service = CatalogService(ingest_db)
        wav = self._stage_wav(tmp_path)

        result = service.ingest_wav_as_converting(str(wav))
        source_id = result["song"].id

        # Provisional WAV audio: no fingerprint attempt yet.
        assert _fingerprint_row(ingest_db, source_id) is None

    @binaries_required
    def test_finalize_stores_fingerprint_from_converted_mp3(self, ingest_db, tmp_path):
        service = CatalogService(ingest_db)
        wav = self._stage_wav(tmp_path)
        result = service.ingest_wav_as_converting(str(wav))
        source_id = result["song"].id

        mp3 = _tone_mp3(wav.with_suffix(".mp3"), seconds=35, freq=330)
        service.finalize_wav_conversion(source_id, mp3)

        row = _fingerprint_row(ingest_db, source_id)
        assert row is not None
        blob, duration_s, length_cap = row
        assert blob is not None
        assert duration_s == pytest.approx(35, abs=1)
        assert length_cap == 180
