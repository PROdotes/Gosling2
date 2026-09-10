import os
import subprocess

import numpy as np
import pytest

from src.engine.config import FFMPEG_PATH, FPCALC_PATH
from src.utils.audio_fingerprint import calculate_fingerprint

binaries_required = pytest.mark.skipif(
    not (os.path.exists(FFMPEG_PATH) and os.path.exists(FPCALC_PATH)),
    reason="bundled ffmpeg/fpcalc binaries not available",
)

SILENCE_FIXTURE = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "silence.mp3"
)


def _make_tone(path, seconds=40):
    """A real decodable MP3 with actual spectral content for fpcalc to fingerprint."""
    subprocess.run(
        [
            str(FFMPEG_PATH),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-q:a",
            "4",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


class TestCalculateFingerprint:
    def test_missing_file_returns_none(self):
        assert calculate_fingerprint("no_such_file_here.mp3") is None

    def test_silent_fixture_returns_none(self):
        # fpcalc emits "Empty fingerprint" and exits non-zero on pure silence.
        assert calculate_fingerprint(SILENCE_FIXTURE) is None

    @binaries_required
    def test_real_audio_returns_uint32_array_and_duration(self, tmp_path):
        tone = tmp_path / "tone.mp3"
        _make_tone(tone, seconds=40)

        result = calculate_fingerprint(str(tone))
        assert result is not None
        fingerprint, duration = result

        assert isinstance(fingerprint, np.ndarray)
        assert fingerprint.dtype == np.dtype("<u4")
        assert fingerprint.size > 0
        assert duration == pytest.approx(40, abs=1)

    @binaries_required
    def test_length_cap_truncates_long_input(self, tmp_path):
        short = tmp_path / "short.mp3"
        long = tmp_path / "long.mp3"
        _make_tone(short, seconds=60)
        _make_tone(long, seconds=400)

        short_result = calculate_fingerprint(str(short))
        long_result = calculate_fingerprint(str(long))
        assert short_result is not None and long_result is not None
        short_fp, _ = short_result
        long_fp, long_dur = long_result

        # 180s cap: the 400s track is fingerprinted only to the cap, so it does
        # not produce proportionally more items than the 60s one.
        assert long_fp.size < short_fp.size * 4
        assert long_dur == pytest.approx(400, abs=1)

    @binaries_required
    def test_deterministic(self, tmp_path):
        tone = tmp_path / "tone.mp3"
        _make_tone(tone, seconds=40)

        first_result = calculate_fingerprint(str(tone))
        second_result = calculate_fingerprint(str(tone))
        assert first_result is not None and second_result is not None
        first, _ = first_result
        second, _ = second_result
        assert np.array_equal(first, second)
