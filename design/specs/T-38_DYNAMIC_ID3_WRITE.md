# T-38: Dynamic ID3 Write

> **Status**: 📋 Draft Spec  
> **Priority**: 5 (0.1 BLOCKER)  
> **Complexity**: 3  
> **Author**: Vesper  
> **Date**: 2025-12-23

---

## Problem Statement

The `MetadataService.write_tags()` method is currently hardcoded:
- Each ID3 frame (TIT2, TPE1, TCOM, etc.) is manually imported and written
- Adding new portable fields requires modifying `write_tags()` directly
- This violates the "single source of truth" principle established by Yellberus

**Contrast with READ side:**
- `extract_from_mp3()` and `Song.from_row()` use `id3_frames.json` dynamically
- Adding a new field only requires updating the JSON and Yellberus

**Immediate symptom:** `album_artist` (TPE2) was added to the registry but `write_tags()` doesn't write it.

---

## Proposed Solution

Refactor `write_tags()` to dynamically iterate over Yellberus portable fields and use `id3_frames.json` for frame mapping.

### High-Level Workflow

```
┌─────────────────────────────────────────────────────────┐
│                    write_tags(song)                      │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  1. Load id3_frames.json                                │
│     Build reverse lookup: field_name → frame_code       │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  2. For each field in yellberus.FIELDS:                 │
│     - Skip if portable=False                            │
│     - Get value via getattr(song, field.name)           │
│     - Skip if value is None/empty                       │
│     - Apply validation (year, ISRC, BPM, length)        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  3. Look up frame_code from reverse lookup              │
│     - If not found, skip (local field, not portable)    │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  4. Determine frame class from frame_code prefix:       │
│     - T*** → TextFrame (TIT2, TPE1, TCOM, etc.)         │
│     - TXXX:* → TXXX (custom text frames)                │
│     - Other → Handle specially or skip                  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  5. Write frame:                                        │
│     - Delete existing frame (delall)                    │
│     - Create new frame with encoding=3 (UTF-8)          │
│     - Handle list vs single value based on field_type   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  6. Save file (preserve ID3v1 if exists)                │
└─────────────────────────────────────────────────────────┘
```

---

## Edge Cases & Handling

### 1. List vs Text Fields
| Field Type | Example | Write Behavior |
|------------|---------|----------------|
| `TEXT` | title, album | `text=value` (single string) |
| `LIST` | performers, composers | `text=list_of_values` (mutagen handles multi-value) |

**Detection:** Check `field.field_type == FieldType.LIST`

### 2. Special Frames

| Frame | Handling |
|-------|----------|
| `TXXX:*` | Custom text frame, use `TXXX(desc=key, text=value)` |
| `TIPL` | Involved people list, special format `[(role, name), ...]` |
| `TDRC` | Recording time, write as string (e.g., "2023") |
| `TBPM` | BPM, write as string of integer |

### 3. Validation (Keep Existing Logic)

| Field | Validation | Action if Invalid |
|-------|------------|-------------------|
| `recording_year` | 1860 ≤ year ≤ current+1 | Skip write, log warning |
| `isrc` | CC-XXX-YY-NNNNN format | Skip write, log warning |
| `bpm` | > 0 | Skip write, log warning |
| `title` | ≤ 1000 chars | Truncate |
| Lists | Remove empty/None items | Clean before write |

### 4. Frames We Don't Manage (Passthrough)

These frames should be **preserved**, not deleted:
- `APIC` — Album art
- `COMM` — Comments
- `USLT` — Lyrics
- `PRIV` — Private frames
- Any frame not in `id3_frames.json`

**Implementation:** Only call `delall()` for frames we're about to write.

### 6. Legacy Author Union (TCOM)

To support legacy systems (Jazler) that only read `TCOM` for rights reporting (ZAMP):
- **Combines:** `composers` + `lyricists`
- **Writes to:** `TCOM` (as comma-separated string)
- **Also Writes:** `TEXT` (lyricists only) and `TCOM` (composers only - handled by union logic)
- **Logic:** `TCOM = join(unique(composers + lyricists))`

| Field | Primary Frame | Legacy/Compat Frame |
|-------|---------------|---------------------|
| `is_done` | `TXXX:GOSLING_DONE` | `TKEY` (legacy) |
| `producers` | `TIPL` | `TXXX:PRODUCER` |
| `recording_year` | `TYER` (Jazler req) | `TDRC` (modern) |

---

## Frame Class Mapping

Mutagen uses different classes for different frame types:

```python
FRAME_CLASSES = {
    'TIT2': TIT2,  # Title
    'TPE1': TPE1,  # Lead performer
    'TPE2': TPE2,  # Album artist ← NEW
    'TCOM': TCOM,  # Composer
    'TALB': TALB,  # Album
    'TCON': TCON,  # Genre
    'TDRC': TDRC,  # Recording date
    'TBPM': TBPM,  # BPM
    'TSRC': TSRC,  # ISRC
    'TEXT': TEXT,  # Lyricist
    'TIT1': TIT1,  # Content group (Groups)
    'TPUB': TPUB,  # Publisher ← Check if portable
    # ... etc
}
```

**Dynamic approach:** Import frame classes dynamically based on frame code prefix:
```python
from mutagen.id3 import Frames
frame_class = Frames.get(frame_code)
```

---

## Current Portable Fields in Yellberus

| Field Name | Frame Code | Type | Notes |
|------------|------------|------|-------|
| title | TIT2 | TEXT | |
| performers | TPE1 | LIST | |
| album_artist | TPE2 | TEXT | ← NEW |
| composers | TCOM | LIST | |
| lyricists | TEXT | LIST | |
| groups | TIT1 | LIST | |
| album | TALB | TEXT | |
| genre | TCON | TEXT | |
| recording_year | TDRC | INTEGER | |
| bpm | TBPM | INTEGER | |
| isrc | TSRC | TEXT | |
| producers | TIPL | LIST | Special format |
| publisher | TPUB | TEXT | Check portability |

---

## Implementation Steps

1. **Create helper function** to build field→frame reverse lookup
2. **Create frame writer function** that handles TEXT vs LIST vs special frames
3. **Replace hardcoded blocks** with loop over portable fields
4. **Keep validation logic** (year, ISRC, BPM, length)
5. **Keep dual-mode logic** for is_done and producers
6. **Add unit test** for album_artist roundtrip

---

## Exit Criteria

- [ ] `write_tags()` uses `id3_frames.json` for frame mapping
- [ ] All currently-written frames still work (regression test)
- [ ] New `album_artist` field writes `TPE2` correctly
- [ ] Unit test confirms write→read roundtrip for `album_artist`
- [ ] APIC and other unmanaged frames are preserved
- [ ] Validation logic unchanged

---

## Files to Modify

| File | Change |
|------|--------|
| `src/business/services/metadata_service.py` | Refactor `write_tags()` |
| `tests/unit/business/services/test_metadata_service.py` | Add album_artist roundtrip test |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Break existing write logic | Medium | High | Keep all current tests passing |
| Wrong encoding | Low | Medium | Use encoding=3 (UTF-8) consistently |
| Frame class not found | Low | Medium | Graceful skip with warning |
| Performance regression | Low | Low | Caching of JSON/lookup |

---

*Spec drafted by Vesper, 2025-12-23*
