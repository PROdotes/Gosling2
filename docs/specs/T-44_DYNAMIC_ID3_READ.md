---
tags:
  - spec
  - docs/refactor
  - status/proposed
  - priority/critical
---

# T-44 Spec: Dynamic ID3 Read Refactor

## 1. The Problem
Currently, `MetadataService.extract_from_mp3` logic is brittle and inconsistent with `write_tags`:
1.  **Hardcoded Frame IDs**: It manually defines `TIT2`, `TPE1`, `TSRC` etc., ignoring the Source of Truth (`id3_frames.json`).
2.  **Inconsistent Handling**: Writing uses a dynamic loop based on JSON/FieldDefs; Reading uses a manual script.
3.  **Missing Features**: It fails to handle ID3v2.3 standard multi-value separators (e.g., `Artist A/Artist B` is read as one string).
4.  **Maintenance Risk**: Adding a new field to `id3_frames.json` requires code changes in **two** places (Read & Write logic).

## 2. The Solution
Refactor `extract_from_mp3` to dynamically iterate through the `id3_frames.json` (or Yellberus Field Definitions) to extract data, mirroring the `write_tags` logic.

### 2.1 Core Logic Flow
1.  **Load Mapping**: Load `id3_frames.json` into a lookup map: `{FrameID: FieldName}`.
2.  **Initialize Song**: Create a default `Song(source=path)`.
3.  **Dynamic Loop**: Iterate through all `ID3` tags found in the file.
4.  **Lookup**: For each tag (e.g., `TPE1`), check if it exists in our JSON mapping.
    *   If **Yes** (`producers`): Extract value, clean it, and set `song.producers`.
    *   If **No**: Preserve it! (We never discard data). It stays in the file during write operations because `write_tags` performs a **Sparse Update** (only deleting specific frames we overwrite, or ALL frames for that field ID). *Correction*: The Song model only holds schema-aware data. **The safety mechanism is in `write_tags`**: it relies on reading the original file (which contains the unknown tags) and only modifying the known fields. `extract_from_mp3` populates the Song model for the UI; it does not need to hold unknown binary blobs. The `write_tags` logic must ensure it does not blindly `audio.delete()` but rather uses `audio.tags.add/del` selectively. Validated: `write_tags` currently uses selective deletion (`audio.tags.delall(frame_id)`), so data safety is preserved by the filesystem, not the Song model.
5.  **Complex Field Handling**:
    *   **Dual-Mode Fields** (Year, Done, Producers) need special handlers *after* the loop or specific logic within it.
    *   **Multi-Value Splitting**: Explicitly handle `/` splitting for list fields (ID3v2.3 standard).

### 2.2 Detailed Changes

#### A. Centralized ID3 Map
Ensure `MetadataService` has a clean way to load the `Frame -> Field` map.
*   *Current*: `write_tags` loads it inside the method.
*   *Proposed*: Extract a helper `_load_id3_map()` or class-level cache.

#### B. The New `extract_from_mp3` Algorithm
```python
def extract_from_mp3(path: str, source_id: Optional[int] = None) -> Song:
    # 1. Basic File Info (MP3 Header)
    # ... existing duration/BPM logic ...

    # 2. Dynamic Tag Extraction
    song_data = {}
    
    # helper to clean/split
    def process_value(frame_val, field_type):
        # Handle string lists, slash splitting, etc.
        pass

    for frame_id in tags.keys():
        # Handle TXXX (e.g. TXXX:GOSLING_DONE)
        lookup_id = frame_id
        if frame_id.startswith("TXXX:"):
            # logic to match TXXX:Desc
            pass
            
        field_name = id3_map.get(lookup_id)
        if field_name:
             val = process_value(tags[frame_id], field_def.type)
             song_data[field_name] = val

    # 3. Apply Complex Overrides (The "Lens")
    # - IsDone logic (Legacy TKEY fallback)
    # - Year logic (TDRC vs TYER)
    # - Unified Artist logic (Groups vs Performers)
    
    return Song(**song_data)
```

## 3. Breaking Changes & Risks
*   **Risk**: The current "Manual" extraction might have subtle "features" (order preference) we might lose.
    *   *Mitigation*: The `COMPLEX_FIELDS` set (Step 2.1) allows us to exclude sensitive fields (Year, Done) from the generic loop and handle them manually for safety.
*   **Risk**: `mutagen` reads frames differently depending on version.
    *   *Mitigation*: Our `process_value` helper must be robust against `list` vs `text` types.

## 4. Implementation Plan
1.  **Refactor**: Modify `src/business/services/metadata_service.py`.
2.  **Verify**: Run `tests/unit/business/services/test_metadata_service.py`.
    *   *Goal*: The failing test `test_write_tags_roundtrip` (Split Issue) MUST pass.
3.  **Cleanup**: Remove the hardcoded block of `get_text_list("TIT2")` etc.

## 5. Success Criteria
*   [ ] `metadata_service.py` is < 300 lines (significant reduction).
*   [ ] Reading `Artist A/Artist B` correctly yields `['Artist A', 'Artist B']`.
*   [ ] All existing tests pass.
