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

### Transliteration Map
*Location: `json/transliterations.json`*
Custom character mappings for atomic characters NFKD normalization cannot decompose:
- Slavic: Đ→Dj, Č→C, Š→S, Ž→Z
- German: ß→ss
- Ligatures: Æ→Ae, Œ→Oe
- Map is loaded at startup; missing file defaults to empty map (graceful degradation).

### JSON Loaders
*Location: `src/utils/json_loaders.py`*

#### load_transliterations() -> dict[str, str]
Loads custom transliteration map from `json/transliterations.json`. Returns empty dict if file missing or unreadable.
