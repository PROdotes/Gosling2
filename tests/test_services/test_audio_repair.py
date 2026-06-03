"""
Tests for src/services/audio_repair.py

Logic and error paths mock subprocess (matching test_converter.py). The single
happy-path test that needs a real re-mux is gated on the bundled ffmpeg binary.
"""

import os
import shutil
import struct
from unittest.mock import MagicMock, patch

import pytest
from mutagen.id3 import ID3, TIT2
from mutagen.mp3 import MP3, BitrateMode

from src.engine.config import FFMPEG_PATH
from src.services import audio_repair
from src.services.audio_repair import (
    _decoded_duration_seconds,
    _id3v2_size,
    has_trailing_junk,
    needs_xing_repair,
    repair_xing_header,
)

ffmpeg_required = pytest.mark.skipif(
    not os.path.exists(FFMPEG_PATH), reason="bundled ffmpeg binary not available"
)


class TestNeedsXingRepair:
    def test_no_xing_header_fixture_needs_repair(self, test_audio_file):
        # silence.mp3 is a real headerless file (BitrateMode.UNKNOWN).
        assert needs_xing_repair(test_audio_file) is True

    def test_non_mp3_extension_returns_false(self, tmp_path):
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"not an mp3")
        assert needs_xing_repair(str(wav)) is False

    def test_unreadable_file_returns_false(self, tmp_path):
        broken = tmp_path / "broken.mp3"
        broken.write_bytes(b"\x00\x01\x02 not a real mp3")
        assert needs_xing_repair(str(broken)) is False


class TestId3v2Size:
    def test_no_tag_returns_zero(self, tmp_path):
        f = tmp_path / "x.mp3"
        f.write_bytes(b"\xff\xfb" + b"\x00" * 100)
        assert _id3v2_size(str(f)) == 0

    def test_synchsafe_size_parsed(self, tmp_path):
        # ID3v2 header declaring a 1000-byte tag body (synchsafe: 0x07,0x68).
        body_size = (0 << 21) | (0 << 14) | (0x07 << 7) | 0x68  # == 1000
        assert body_size == 1000
        header = b"ID3\x04\x00\x00" + bytes([0, 0, 0x07, 0x68])
        f = tmp_path / "x.mp3"
        f.write_bytes(header + b"\x00" * 1000)
        assert _id3v2_size(str(f)) == 10 + 1000


class TestDecodedDurationSeconds:
    def _run(self, stderr_text):
        return MagicMock(stderr=stderr_text.encode())

    def test_parses_last_time_token(self):
        stderr = "frame... time=00:00:10.00 ...\nframe... time=00:02:30.96 speed=1x"
        with patch.object(
            audio_repair.subprocess, "run", return_value=self._run(stderr)
        ):
            assert _decoded_duration_seconds("any.mp3") == pytest.approx(150.96)

    def test_no_time_token_returns_none(self):
        with patch.object(
            audio_repair.subprocess, "run", return_value=self._run("no timing here")
        ):
            assert _decoded_duration_seconds("any.mp3") is None

    def test_ffmpeg_missing_returns_none(self):
        with patch.object(
            audio_repair.subprocess, "run", side_effect=FileNotFoundError
        ):
            assert _decoded_duration_seconds("any.mp3") is None


class TestHasTrailingJunk:
    def test_oversized_audio_region_flags_junk(self, tmp_path):
        # 26s decoded but a 7MB body cannot hold that at <=320kbps -> junk.
        f = tmp_path / "junk.mp3"
        f.write_bytes(b"\x00" * 7_000_000)
        with patch.object(audio_repair, "_decoded_duration_seconds", return_value=26.0):
            assert has_trailing_junk(str(f)) is True

    def test_normal_audio_region_is_clean(self, tmp_path):
        # 26s at ~320kbps ~= 1MB body -> well within ceiling.
        f = tmp_path / "ok.mp3"
        f.write_bytes(b"\x00" * 1_050_000)
        with patch.object(audio_repair, "_decoded_duration_seconds", return_value=26.0):
            assert has_trailing_junk(str(f)) is False

    def test_undecodable_returns_false(self, tmp_path):
        f = tmp_path / "x.mp3"
        f.write_bytes(b"\x00" * 7_000_000)
        with patch.object(audio_repair, "_decoded_duration_seconds", return_value=None):
            assert has_trailing_junk(str(f)) is False


class TestRepairRefusesAndFailsSafely:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(RuntimeError):
            repair_xing_header(str(tmp_path / "nope.mp3"))

    def test_trailing_junk_is_refused_untouched(self, tmp_path, test_audio_file):
        src = tmp_path / "junky.mp3"
        shutil.copyfile(test_audio_file, src)
        before = src.read_bytes()
        with patch.object(audio_repair, "has_trailing_junk", return_value=True):
            with pytest.raises(RuntimeError, match="trailing junk"):
                repair_xing_header(str(src))
        assert src.read_bytes() == before, "junk file must be left untouched"

    def test_ffmpeg_not_found_leaves_original(self, tmp_path, test_audio_file):
        src = tmp_path / "s.mp3"
        shutil.copyfile(test_audio_file, src)
        before = src.read_bytes()
        with patch.object(audio_repair, "has_trailing_junk", return_value=False):
            with patch.object(
                audio_repair.subprocess, "run", side_effect=FileNotFoundError
            ):
                with pytest.raises(RuntimeError, match="ffmpeg not found"):
                    repair_xing_header(str(src))
        assert src.read_bytes() == before
        assert not (tmp_path / "s.repair_tmp.mp3").exists()

    def test_ffmpeg_failure_leaves_original_and_cleans_temp(
        self, tmp_path, test_audio_file
    ):
        src = tmp_path / "s.mp3"
        shutil.copyfile(test_audio_file, src)
        before = src.read_bytes()

        def fake_run(cmd, **kwargs):
            # Simulate ffmpeg writing a partial temp then failing.
            (tmp_path / "s.repair_tmp.mp3").write_bytes(b"partial")
            return MagicMock(returncode=1, stderr=b"boom")

        with patch.object(audio_repair, "has_trailing_junk", return_value=False):
            with patch.object(audio_repair.subprocess, "run", side_effect=fake_run):
                with pytest.raises(RuntimeError, match="ffmpeg failed"):
                    repair_xing_header(str(src))
        assert src.read_bytes() == before
        assert not (tmp_path / "s.repair_tmp.mp3").exists(), "temp must be cleaned up"


@ffmpeg_required
class TestRepairHappyPath:
    def test_repair_adds_xing_and_preserves_tags(self, tmp_path, test_audio_file):
        src = tmp_path / "song.mp3"
        shutil.copyfile(test_audio_file, src)

        tags = ID3()
        tags.add(TIT2(encoding=3, text=["Probni Naslov"]))
        tags.save(str(src))

        assert needs_xing_repair(str(src)) is True
        original_length = MP3(str(src)).info.length

        new_duration = repair_xing_header(str(src))

        # Header is now valid: duration reported accurately, no longer UNKNOWN.
        assert MP3(str(src)).info.bitrate_mode != BitrateMode.UNKNOWN
        assert needs_xing_repair(str(src)) is False
        assert new_duration == pytest.approx(MP3(str(src)).info.length, abs=0.1)
        assert new_duration == pytest.approx(original_length, abs=0.5)

        # ID3 preserved byte-faithfully.
        assert ID3(str(src))["TIT2"].text == ["Probni Naslov"]

    def test_repaired_header_byte_count_is_consistent(self, tmp_path, test_audio_file):
        src = tmp_path / "song.mp3"
        shutil.copyfile(test_audio_file, src)
        repair_xing_header(str(src))

        data = src.read_bytes()
        off = _id3v2_size(str(src))
        head = data[off : off + 2000]
        marker = head.find(b"Xing")
        if marker < 0:
            marker = head.find(b"Info")
        assert marker >= 0, "repaired file must carry a Xing/Info header"
        flags = struct.unpack(">I", head[marker + 4 : marker + 8])[0]
        idx = marker + 8
        if flags & 1:  # frame count present
            idx += 4
        if flags & 2:  # byte count present
            byte_count = struct.unpack(">I", head[idx : idx + 4])[0]
            # byte_count should track the real audio region, not exceed the file.
            assert byte_count <= len(data) - off + 1
