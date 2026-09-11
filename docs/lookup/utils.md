# Utilities Layer
*Location: `src/utils/`*

**Responsibility**: Generic, low-level helper functions.

---

## Audio Hashing
*Location: `src/utils/audio_hash.py`*
**Responsibility**: Calculate consistent file identities based on audio frames.

### calculate_audio_hash(filepath: str) -> str
Calculates SHA256 of MPEG audio frames, skipping ID3 tags.
- Skips ID3v2 header (synchsafe size resolution).
- Skips ID3v1 footer (last 128 bytes).
- Returns 64-character hex string.

---

## Acoustic Fingerprinting
*Location: `src/utils/audio_fingerprint.py`*
**Responsibility**: Chromaprint acoustic fingerprint of a file via the bundled `fpcalc` (`FPCALC_PATH`). Used by the ingest path to feed later duplicate detection.

### calculate_fingerprint(filepath: str) -> tuple[np.ndarray, float] | None
Shells `fpcalc -raw -length 180` and parses its `FINGERPRINT`/`DURATION` lines.
- Returns the raw fingerprint as a little-endian `uint32` array plus the reported duration in seconds.
- No trimming or normalisation; alignment is handled at comparison time.
- Returns `None` on any failure (fpcalc missing, non-zero exit, unparseable/empty output). Callers treat `None` as "attempted and failed".
- `FINGERPRINT_LENGTH_CAP = 180` is exported alongside it (the `-length` value, stored per row).

---

## Acoustic Fingerprint Matching
*Location: `src/utils/audio_fingerprint_match.py`*
**Responsibility**: Compare fingerprints from `audio_fingerprint.py` (Part 2A - pure, standalone; no DB access, no writes).

### score(fp_a, fp_b) -> float | None
Acoustic similarity of two fingerprints, 0.0-1.0.
- Numpy XOR/popcount, `1 - popcount(a XOR b) / (32 * overlap)`, best of a bounded offset slide (`OFFSET_WINDOW_ITEMS = 120`, ~15s).
- Returns `None` - "not comparable" - if no offset reaches `MIN_OVERLAP_ITEMS = 50`. Not a score of zero; collapsing the two would make "too short to compare" look like "confidently unrelated".

### find_matches(fp, duration_s, candidates, threshold) -> list[tuple[int, float]]
Scores `fp` against `candidates` (`(song_id, fingerprint, duration_s)` tuples), best first, at or above `threshold`.
- Duration pre-filter `DURATION_PREFILTER_S = 16.0` (must be >= the offset window in seconds, or it silently discards true matches before `score()` ever sees them).
- Skips anything under `MIN_COMPARABLE_DURATION_S = 30.0` (query or candidate) before scoring - closes the hub-song risk (idents/stings matching everything) by construction.
- Pure function - caller owns fetching candidates and picking/tuning `threshold`.

---

## Text Normalization & Diacritics
*Location: `src/utils/text.py`*
**Responsibility**: Unified diacritic-stripping for filesystem paths, search indices, and client-server communication (Phase 3.1).

### strip_diacritics(text: str) -> str
Reduces text to ASCII, preserving casing. Used by filing paths.
- Applies custom transliteration map for chars NFKD cannot decompose (Đ→Dj, ß→ss, Æ→Ae, etc.).
- NFKD-normalizes and drops combining marks.
- **Casing preserved**: MÖTLEY CRÜE → MOTLEY CRUE (capital M and C).
- Safe for filesystem paths (never introduces illegal characters).

### normalize_for_search(text: str) -> str
Reduces text to lowercase ASCII. Used by search shadows and query normalization.
- Calls `strip_diacritics()` then `.lower()`.
- Returns diacritic-stripped lowercase: MÖTLEY CRÜE → motley crue.
- **Read-write symmetry**: Both write paths (mutators) and read paths (services) use this function.

## JSON Loaders
*Location: `src/utils/json_loaders.py`*

### load_transliterations() -> dict[str, str]
Loads custom transliteration map from `json/transliterations.json`. Returns empty dict if file missing or unreadable.
