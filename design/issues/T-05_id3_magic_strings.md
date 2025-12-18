---
tags:
  - id3
  - refactor
  - deduplication
status: planned
priority: high
---

# T-05: Eliminate ID3 Magic Strings

## Problem
ID3 frame codes (TPE1, TIT2, etc.) are duplicated across multiple files:
- `id3_frames.json` - canonical source (should be ONLY source)
- `yellberus.py` - duplicates frame codes in FieldDef.id3_frame
- `metadata_service.py` - hardcodes frame codes for read/write
- `metadata_viewer_dialog.py` - maps frames to UI

This violates DRY and creates drift risk.

## Goal
**`id3_frames.json` is the ONLY source of ID3 frame definitions.**

All other code should:
1. Reference the JSON for frame descriptions
2. Reference Yellberus for field→frame mappings

## Implementation Checklist

### Phase 1: Enhance id3_frames.json
- [ ] Add field name mappings: `"TPE1": {"description": "...", "field": "performers"}`
- [ ] Keep backward compatible with current format

### Phase 2: Create ID3 Helper Module
- [ ] Create `src/core/id3_registry.py`
- [ ] Load and cache `id3_frames.json`
- [ ] Provide lookup: `get_frame_for_field("performers")` → "TPE1"
- [ ] Provide reverse: `get_field_for_frame("TPE1")` → "performers"

### Phase 3: Refactor MetadataService
- [ ] Replace hardcoded `"TPE1"` with `id3_registry.get_frame_for_field("performers")`
- [ ] Remove magic strings from read/write logic

### Phase 4: Refactor Yellberus
- [ ] Remove `id3_frame` from FieldDef (or make it reference the registry)
- [ ] Update validate_schema() to use registry

### Phase 5: Refactor metadata_viewer_dialog.py
- [ ] Remove hardcoded frame lists
- [ ] Use registry for lookups

## Affected Files
- `src/core/yellberus.py` - Remove id3_frame strings, use registry lookup
- `src/business/services/metadata_service.py` - Replace hardcoded frame codes
- `src/presentation/widgets/metadata_viewer_dialog.py` - Use registry for frame lookups

> [!NOTE]
> Tests and design docs can keep hardcoded strings - they're for documentation/testing purposes.
