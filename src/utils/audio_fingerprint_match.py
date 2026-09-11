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
    best: float | None = None
    for offset in range(-OFFSET_WINDOW_ITEMS, OFFSET_WINDOW_ITEMS + 1):
        if offset >= 0:
            a = fp_a[offset:]
            b = fp_b[: len(a)]
        else:
            b = fp_b[-offset:]
            a = fp_a[: len(b)]
        overlap = min(len(a), len(b))
        if overlap < MIN_OVERLAP_ITEMS:
            continue
        a = a[:overlap]
        b = b[:overlap]

        xor = np.bitwise_xor(a, b)
        set_bits = int(np.unpackbits(xor.view(np.uint8)).sum())
        candidate_score = 1.0 - set_bits / (32 * overlap)

        if best is None or candidate_score > best:
            best = candidate_score

    return best


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
