import os
import subprocess

import numpy as np
import pytest

from src.engine.config import FFMPEG_PATH, FPCALC_PATH
from src.utils.audio_fingerprint import calculate_fingerprint
from src.utils.audio_fingerprint_match import (
    DURATION_PREFILTER_S,
    MIN_COMPARABLE_DURATION_S,
    MIN_OVERLAP_ITEMS,
    OFFSET_WINDOW_ITEMS,
    find_matches,
    score,
)

binaries_required = pytest.mark.skipif(
    not (os.path.exists(FFMPEG_PATH) and os.path.exists(FPCALC_PATH)),
    reason="bundled ffmpeg/fpcalc binaries not available",
)


def _make_tone(path, seconds):
    """A real decodable MP3 with actual spectral content for fpcalc."""
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


def _random_fingerprint(length: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2**32, size=length, dtype=np.uint64).astype("<u4")


class TestScore:
    def test_identical_fingerprints_score_one(self):
        fp = _random_fingerprint(300, seed=1)
        assert score(fp, fp) == pytest.approx(1.0)

    def test_unrelated_fingerprints_score_near_noise_floor(self):
        fp_a = _random_fingerprint(300, seed=1)
        fp_b = _random_fingerprint(300, seed=2)
        result = score(fp_a, fp_b)
        assert result is not None
        # Independent random bits: ~0.5 expected, nowhere near a match band.
        assert 0.4 < result < 0.6

    def test_offset_within_window_is_recovered(self):
        # fp_b is fp_a with a 40-item lead-in prepended (e.g. silence before
        # the same content) - well inside the +-120 item window.
        fp_a = _random_fingerprint(300, seed=1)
        lead_in = _random_fingerprint(40, seed=99)
        fp_b = np.concatenate([lead_in, fp_a])

        result = score(fp_a, fp_b)
        assert result == pytest.approx(1.0)

    def test_offset_beyond_window_is_not_recovered(self):
        # Shift larger than the +-120 item window: the true alignment is out
        # of reach, so the best the scan finds is noise-floor territory - the
        # documented "recall cliff", not a lower-but-honest score.
        fp_a = _random_fingerprint(500, seed=1)
        lead_in = _random_fingerprint(OFFSET_WINDOW_ITEMS + 50, seed=99)
        fp_b = np.concatenate([lead_in, fp_a])

        result = score(fp_a, fp_b)
        assert result is not None
        assert result < 0.6

    def test_too_short_for_minimum_overlap_is_not_comparable(self):
        fp_a = _random_fingerprint(MIN_OVERLAP_ITEMS - 1, seed=1)
        fp_b = _random_fingerprint(MIN_OVERLAP_ITEMS - 1, seed=1)
        assert score(fp_a, fp_b) is None

    def test_minimum_overlap_boundary_is_comparable(self):
        fp = _random_fingerprint(MIN_OVERLAP_ITEMS, seed=1)
        assert score(fp, fp) == pytest.approx(1.0)


class TestFindMatches:
    def test_below_minimum_duration_query_returns_no_matches(self):
        fp = _random_fingerprint(200, seed=1)
        candidates = [(1, fp, 60.0)]
        result = find_matches(
            fp, MIN_COMPARABLE_DURATION_S - 1, candidates, threshold=0.5
        )
        assert result == []

    def test_candidate_below_minimum_duration_is_skipped(self):
        fp = _random_fingerprint(200, seed=1)
        candidates = [(1, fp, MIN_COMPARABLE_DURATION_S - 1)]
        result = find_matches(fp, 60.0, candidates, threshold=0.5)
        assert result == []

    def test_duration_prefilter_excludes_far_candidates(self):
        fp = _random_fingerprint(200, seed=1)
        query_duration = 60.0
        candidates = [
            (1, fp, query_duration + DURATION_PREFILTER_S + 1),  # excluded
            (2, fp, query_duration + DURATION_PREFILTER_S - 1),  # included
        ]
        result = find_matches(fp, query_duration, candidates, threshold=0.5)
        assert [song_id for song_id, _ in result] == [2]

    def test_matches_are_sorted_best_first_and_thresholded(self):
        fp = _random_fingerprint(300, seed=1)
        unrelated = _random_fingerprint(300, seed=2)
        lead_in = _random_fingerprint(40, seed=99)
        near_match = np.concatenate([lead_in, fp])

        candidates = [
            (1, unrelated, 60.0),
            (2, fp, 60.0),  # perfect match
            (3, near_match, 60.0),  # slightly lower due to overlap trim
        ]
        result = find_matches(fp, 60.0, candidates, threshold=0.9)

        assert [song_id for song_id, _ in result] == [2, 3]
        assert result[0][1] >= result[1][1]

    def test_no_db_access_pure_function(self):
        # Sanity check on the contract, not the implementation: repeated
        # calls with the same inputs give the same result (no hidden state).
        fp = _random_fingerprint(200, seed=1)
        candidates = [(1, fp, 60.0)]
        first = find_matches(fp, 60.0, candidates, threshold=0.5)
        second = find_matches(fp, 60.0, candidates, threshold=0.5)
        assert first == second


@binaries_required
class TestRealAudioViaFpcalc:
    """
    End-to-end sanity check against real fpcalc output, not just synthetic
    numpy arrays. Reproduces the shape of the documented cases (same
    recording re-encoded, and two unrelated tracks) - not the exact measured
    scores, since those came from real music, not sine tones.
    """

    def test_same_source_reencoded_scores_high(self, tmp_path):
        source = tmp_path / "source.mp3"
        _make_tone(source, seconds=45)

        reencoded = tmp_path / "reencoded.mp3"
        subprocess.run(
            [
                str(FFMPEG_PATH),
                "-v",
                "error",
                "-i",
                str(source),
                "-b:a",
                "96k",
                str(reencoded),
            ],
            check=True,
            capture_output=True,
        )

        fp_a = calculate_fingerprint(str(source))
        fp_b = calculate_fingerprint(str(reencoded))
        assert fp_a is not None and fp_b is not None

        result = score(fp_a[0], fp_b[0])
        assert result is not None
        assert result > 0.9

    def test_lead_in_silence_within_window_still_matches(self, tmp_path):
        source = tmp_path / "source.mp3"
        _make_tone(source, seconds=45)

        prepended = tmp_path / "prepended.mp3"
        subprocess.run(
            [
                str(FFMPEG_PATH),
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "anullsrc",
                "-i",
                str(source),
                "-filter_complex",
                "[0:a]atrim=duration=5[si];[si][1:a]concat=n=2:v=0:a=1[out]",
                "-map",
                "[out]",
                "-q:a",
                "4",
                str(prepended),
            ],
            check=True,
            capture_output=True,
        )

        fp_a = calculate_fingerprint(str(source))
        fp_b = calculate_fingerprint(str(prepended))
        assert fp_a is not None and fp_b is not None

        result = score(fp_a[0], fp_b[0])
        assert result is not None
        assert result > 0.9
