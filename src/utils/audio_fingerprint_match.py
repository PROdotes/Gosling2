import numpy as np

# Bounded offset search, in fingerprint items (~7.9 items/sec). +-30 was tested
# and silently drops true matches whose lead-in differs by more than ~3.8s;
# +-120 (~15s) is the settled value - see docs/todo/duplicate_detection.md,
# "The real constraint is the offset bound, not the fingerprint".
OFFSET_WINDOW_ITEMS = 120

# A candidate offset is only considered if it produces at least this much
# overlap. Below ~50 items the score is not meaningful - a handful of items
# can align by chance and produce a spuriously high score. This is also what
# keeps short/generic audio (idents, stings) out of scoring: a 3s clip has 3
# items and can never clear this floor.
MIN_OVERLAP_ITEMS = 50

# Do not compare audio shorter than this. Resolves the hub-song risk (short
# generic audio matching everything) by construction - short audio is simply
# out of scope for acoustic matching, not capped or suppressed after scoring.
MIN_COMPARABLE_DURATION_S = 30.0

# Duration pre-filter width. Must be >= the offset window in seconds, or the
# pre-filter silently discards true matches before they are ever scored (a
# +-3s pre-filter against a +-120-item/~15s window did exactly that).
DURATION_PREFILTER_S = 16.0


def score(fp_a: np.ndarray, fp_b: np.ndarray) -> float | None:
    """
    Acoustic similarity of two Chromaprint fingerprints, 0.0-1.0.

    Slides fp_b against fp_a across +-OFFSET_WINDOW_ITEMS and, for each offset
    that produces at least MIN_OVERLAP_ITEMS of overlap, scores it as
    1 - popcount(a XOR b) / (32 * overlap). Returns the best score found.

    Returns None - "not comparable" - if no offset in the window reaches the
    minimum overlap (fingerprints too short, or too different in length for
    any offset to align them). This is a third state, not a score of zero:
    collapsing it into 0.0 would make "too short to compare" indistinguishable
    from "confidently unrelated".
    """
    # All offsets are scored in one vectorized pass. At offset o, fp_a[i] is
    # paired with fp_b[i - o]. fp_b is zero-padded by the window on both sides
    # so that row i of the sliding view holds fp_b[i - o] for every o (column
    # t = W - o). A padded pair XORs against zero and contributes
    # popcount(fp_a[i]); those rows form a prefix and suffix of each column,
    # so they are subtracted with prefix sums instead of masked out.
    w = OFFSET_WINDOW_ITEMS
    len_a, len_b = len(fp_a), len(fp_b)
    pad_right = max(len_a + w - len_b, 0) + w
    b_padded = np.concatenate(
        [np.zeros(w, dtype=fp_b.dtype), fp_b, np.zeros(pad_right, dtype=fp_b.dtype)]
    )
    b_windows = np.lib.stride_tricks.sliding_window_view(b_padded, 2 * w + 1)[:len_a]
    all_bits = np.bitwise_count(fp_a[:, None] ^ b_windows).sum(axis=0, dtype=np.int64)

    offsets = np.arange(w, -w - 1, -1)
    lo = np.clip(offsets, 0, len_a)
    hi = np.clip(offsets + len_b, lo, len_a)
    a_bits_cum = np.concatenate(
        [[0], np.cumsum(np.bitwise_count(fp_a), dtype=np.int64)]
    )
    set_bits = all_bits - a_bits_cum[lo] - (a_bits_cum[len_a] - a_bits_cum[hi])
    overlap = hi - lo

    usable = overlap >= MIN_OVERLAP_ITEMS
    if not usable.any():
        return None
    scores = 1.0 - set_bits[usable] / (32 * overlap[usable])
    return float(scores.max())


def find_matches(
    fp: np.ndarray,
    duration_s: float,
    candidates: list[tuple[int, np.ndarray, float]],
    threshold: float,
) -> list[tuple[int, float]]:
    """
    Score `fp` against a list of (song_id, fingerprint, duration_s) candidates
    and return the ones at or above `threshold`, best first.

    Duration pre-filter (+-DURATION_PREFILTER_S) narrows the candidate set
    before the expensive offset scan. Anything shorter than
    MIN_COMPARABLE_DURATION_S - the query or a candidate - is skipped
    entirely; short audio cannot reach MIN_OVERLAP_ITEMS in score() anyway,
    but skipping here avoids scanning it at all.

    No DB access, no writes - pure function. The caller owns fetching
    candidates and choosing/tuning `threshold`.
    """
    if duration_s < MIN_COMPARABLE_DURATION_S:
        return []

    matches: list[tuple[int, float]] = []
    for song_id, cand_fp, cand_duration in candidates:
        if cand_duration < MIN_COMPARABLE_DURATION_S:
            continue
        if abs(cand_duration - duration_s) > DURATION_PREFILTER_S:
            continue

        candidate_score = score(fp, cand_fp)
        if candidate_score is not None and candidate_score >= threshold:
            matches.append((song_id, candidate_score))

    matches.sort(key=lambda pair: pair[1], reverse=True)
    return matches
