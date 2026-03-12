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
