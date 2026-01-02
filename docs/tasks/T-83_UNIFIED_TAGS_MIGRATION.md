# T-83: Unified Tags Migration

## Overview
Migrate from separate `genre`, `mood`, and `is_done` fields to a unified Tags system where all metadata tags go through the `Tags` + `MediaSourceTags` junction table.

## Current State
```
Song Model:
├── genre: Optional[str] = None      # Stored as MS.Genre column
├── mood: Optional[str] = None       # Stored as MS.Mood column  
├── is_done: bool = False            # Stored as MS.IsDone column
```

## Target State
```
Tags System:
├── Tags table (TagID, TagName, TagCategory)
│   ├── (1, "Rock", "Genre")
│   ├── (2, "Chill", "Mood")
│   ├── (3, "Ready", "Status")
│   └── (4, "Guitar", "Instrument")
│
├── MediaSourceTags junction (SourceID, TagID)
│   └── Links songs to any number of tags
│
└── Song Model:
    └── tags: List[Tag] (loaded via TagRepository)
```

## Benefits
- Unlimited tag categories (Genre, Mood, Status, Instrument, Theme, etc.)
- Multiple tags per category per song
- Consistent API for all tag operations
- Power user syntax works for all categories

---

## Migration Steps

### Phase 1: Model Changes
- [x] Tags table already exists
- [x] MediaSourceTags junction already exists
- [x] TagRepository already exists
- [ ] Remove `genre`, `mood` fields from Song model (defer - keep for ID3 compat)
- [ ] Convert `is_done: bool` to Status tags

### Phase 2: Data Migration
- [x] NOT NEEDED - using fresh test DB

### Phase 3: Repository Changes
- [x] TagRepository.get_tags_for_source() - already implemented
- [x] TagRepository.add_tag_to_source() - already implemented
- [x] TagRepository.remove_tag_from_source() - already implemented

### Phase 4: UI Changes (Side Panel)
- [x] Updated side_panel_widget _calculate_bulk_value to read ALL tags from TagRepository
- [x] Updated _on_add_button_clicked for tags to use TagRepository
- [x] Updated _on_chip_removed for tags to use TagRepository
- [x] Added category icon and zone helpers
- [ ] Update the "Ready/Pending" toggle to add/remove Status tags

### Phase 4b: Filter Widget
- [x] Added _add_unified_tags_filter() - dynamically creates tree from DB categories
- [x] Skipped old hardcoded genre/mood filters
- [x] Added tag filtering support in LibraryProxyModel._check_value_match
- [x] Uses TagRepository.get_tags_for_source() with caching

### Phase 5: ID3 Changes
- [ ] MetadataService.read_tags() should populate tags field
- [ ] MetadataService.write_tags() should read from tags field
- [ ] Map: TCON→Genre tags, TMOO→Mood tags

### Phase 6: Cleanup
- [ ] Remove deprecated columns from DB (or mark as legacy)
- [ ] Update yellberus.py field definitions
- [ ] Update tests

---

## Status Tag Design

**Option A: Binary Tags (Presence = True)**
- Tag "Ready" in category "Status" 
- Presence = song is ready
- Absence = song is pending

**Option B: Value Tags**
- Tag "Ready" or "Pending" in category "Status"
- More explicit but requires cleanup on toggle

**Recommendation**: Option A - simpler, matches how tags naturally work

---

## Backward Compatibility

For smooth migration, Song model can have computed properties:
```python
@property
def genre(self) -> Optional[str]:
    """Legacy accessor - returns first Genre tag."""
    genre_tags = [t for t in self._tags if t.category == 'Genre']
    return genre_tags[0].tag_name if genre_tags else None
```

---

## Open Questions
1. Should we keep MS.Genre/MS.Mood columns for ID3 sync? Or fully migrate?
2. How to handle multi-value genres in ID3 (TCON can have semicolons)?
3. UI: Do we need separate "Status" display or just chips in the tag tray?

