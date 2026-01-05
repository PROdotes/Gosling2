# Tag Category Refactoring Plan

## Objective
Remove all hardcoded references to "Genre" and "Mood" tag categories and make the system fully data-driven from `id3_frames.json`.

## Current State

### ✅ Already Data-Driven
- **MetadataService.extract_from_mp3** (lines 247-260): Reads tag categories from JSON
- **MetadataService.write_tags** (lines 409-432): Writes tag categories dynamically from JSON

### ❌ Hardcoded References to Remove

#### 1. **side_panel_widget.py**
- **Line 618**: `category='Genre'` - Hardcoded when creating Genre tags
- **Line 621**: `category='Mood'` - Hardcoded when creating Mood tags
- **Line 1123**: `default_cat = 'Mood' if field_name == 'mood' else 'Genre'` - Hardcoded category selection
- **Line 1185**: `target_field = 'genre' if cat.lower() == 'genre' else 'mood'` - Hardcoded field mapping
- **Lines 1699-1700**: Icon mapping dictionary with Genre/Mood icons
- **Line 1711**: Color mapping with "Mood" color

#### 2. **filter_widget.py**
- **Lines 550-551**: Icon mapping dictionary with Genre/Mood icons
- **Line 800**: Duplicate icon mapping for Genre/Mood/Status

#### 3. **tag_picker_dialog.py**
- **Line 103**: `default_category="Genre"` - Hardcoded default
- **Lines 161-162**: Icon mapping dictionary with Genre/Mood icons
- **Lines 174-175**: Color mapping dictionary with Genre/Mood colors
- **Line 367**: `categories = {"Genre", "Mood"}` - **CRITICAL**: Hardcoded category set
- **Lines 450-451**: Duplicate icon mapping

#### 4. **renaming_service.py**
- **Line 31**: `if cat.lower() == "genre"` - Hardcoded genre check
- **Line 111**: `if cat.lower() == "genre"` - Duplicate hardcoded genre check

#### 5. **MetadataService** (metadata_service.py)
- **Line 162**: `COMPLEX_FIELDS = {..., 'genre', 'mood'}` - Genre/Mood in exclusion list (may be legacy)

## Current JSON Access Patterns (Problem)

**3 different places load `id3_frames.json` independently:**

1. **`MetadataService._get_id3_map()`** (metadata_service.py, lines 20-34)
   - ✅ Has caching via `_id3_map` class variable
   - Used by: `extract_from_mp3()`, `write_tags()`, `Song.from_row()`
   
2. **`MetadataViewerDialog._populate_table()`** (metadata_viewer_dialog.py, lines 100-113)
   - ❌ Loads JSON fresh every time dialog opens
   - ❌ No caching
   - ❌ Duplicate path resolution logic
   
3. **`yellberus.py` validation functions** (lines 570-578, 647-649)
   - ❌ Loads JSON for validation checks
   - ❌ No caching
   - ❌ Duplicate path resolution logic

**Issues:**
- Performance overhead from multiple file reads
- Inconsistent path resolution across modules
- No centralized place to add tag category logic
- Difficult to mock/test

## Proposed Solution

### Phase 1: Create ID3Registry Service (Foundation)
Create `src/core/registries/id3_registry.py` as the **single source of truth** for all ID3 frame data:

```python
class ID3Registry:
    """
    Centralized registry for ID3 frame mappings and tag categories.
    Loads from id3_frames.json once and caches in memory.
    """
    
    _data = None
    
    @classmethod
    def _load(cls):
        """Load and cache id3_frames.json."""
        if cls._data is None:
            # Load JSON with proper path resolution
            # Cache in cls._data
            pass
    
    @classmethod
    def get_frame_map(cls) -> dict:
        """Get all ID3 frame definitions."""
        cls._load()
        return {k: v for k, v in cls._data.items() if k != 'tag_categories'}
        
    @classmethod
    def get_tag_categories(cls) -> dict:
        """Get all tag category definitions (Genre, Mood, etc)."""
        cls._load()
        return cls._data.get('tag_categories', {})
        
    @classmethod
    def get_category_icon(cls, category: str, default: str = "📦") -> str:
        """Get icon for a tag category."""
        cats = cls.get_tag_categories()
        return cats.get(category, {}).get('icon', default)
        
    @classmethod
    def get_category_color(cls, category: str, default: str = "#888888") -> str:
        """Get color for a tag category."""
        cats = cls.get_tag_categories()
        return cats.get(category, {}).get('color', default)
        
    @classmethod
    def get_id3_frame(cls, category: str) -> Optional[str]:
        """Get ID3 frame code for a tag category (e.g., 'Genre' -> 'TCON')."""
        cats = cls.get_tag_categories()
        return cats.get(category, {}).get('id3_frame')
        
    @classmethod
    def get_all_category_names(cls) -> List[str]:
        """Get list of all valid category names."""
        return list(cls.get_tag_categories().keys())
        
    @classmethod
    def is_valid_category(cls, category: str) -> bool:
        """Check if category exists in registry."""
        return category in cls.get_tag_categories()
```

**Refactor existing code to use ID3Registry:**
- `MetadataService._get_id3_map()` → Use `ID3Registry.get_frame_map()`
- `metadata_viewer_dialog.py` → Use `ID3Registry.get_frame_map()`
- `yellberus.py` validation → Use `ID3Registry.get_frame_map()`

### Phase 2: Extend `id3_frames.json`
Add a new top-level `tag_categories` section:

```json
{
  "tag_categories": {
    "Genre": {
      "id3_frame": "TCON",
      "icon": "🏷️",
      "color": "#FFB84D",
      "description": "Musical genre classification"
    },
    "Mood": {
      "id3_frame": "TMOO",
      "icon": "✨",
      "color": "#32A8FF",
      "description": "Emotional mood or atmosphere"
    },
    "Status": {
      "id3_frame": null,
      "icon": "📋",
      "color": "#888888",
      "description": "Internal workflow status",
      "internal_only": true
    },
    "Custom": {
      "id3_frame": null,
      "icon": "🏷️",
      "color": "#888888",
      "description": "User-defined tags",
      "default": true
    }
  },
  "TCON": {
    "description": "Content type (Genre)",
    "tag_category": "Genre",
    "type": "list"
  },
  "TMOO": {
    "description": "Mood",
    "tag_category": "Mood",
    "type": "list"
  }
  // ... rest of existing frames
}
```

### Phase 3: Refactor Hardcoded Category References
Replace all hardcoded dictionaries and checks with `ID3Registry` calls:

**3.1 side_panel_widget.py:**
```python
# Before:
category='Genre'
default_cat = 'Mood' if field_name == 'mood' else 'Genre'
cat_icons = {"Genre": "🏷️", "Mood": "✨", ...}

# After:
category = ID3Registry.get_category_for_field(field_name)  # New helper
icon = ID3Registry.get_category_icon(category)
```

**3.2 filter_widget.py:**
```python
# Before:
cat_icons = {"Genre": "🏷️", "Mood": "✨", "Status": "📋"}

# After:
icon = ID3Registry.get_category_icon(cat_name)
```

**3.3 tag_picker_dialog.py:**
```python
# Before:
categories = {"Genre", "Mood"}
default_category = "Genre"

# After:
categories = ID3Registry.get_all_category_names()
default_category = categories[0] if categories else "Custom"
```

**3.4 renaming_service.py:**
```python
# Before:
if cat.lower() == "genre":

# After:
if ID3Registry.get_id3_frame(cat) == "TCON":  # More explicit
# OR create a helper: ID3Registry.is_genre_category(cat)
```

### Phase 4: Update Tests
- Remove hardcoded "Genre"/"Mood" from test fixtures where possible
- Add tests for dynamic category loading

## Breaking Changes
None - this is a backward-compatible refactoring. Existing Genre/Mood tags will continue to work.

## Benefits
1. **User extensibility**: Users can add custom tag categories with ID3 mappings
2. **Maintainability**: Single source of truth for category metadata
3. **Consistency**: All UI components use same icons/colors
4. **Future-proof**: Easy to add new categories (e.g., "Instrument", "Era", "Language")

## Files to Modify

### New Files:
1. `src/core/registries/__init__.py` - **NEW**: Registries package
2. `src/core/registries/id3_registry.py` - **NEW**: Centralized ID3 frame and tag category registry

### Modified Files:
2. `src/resources/id3_frames.json` - Add tag_categories section
3. `src/business/services/metadata_service.py` - Use ID3Registry instead of _get_id3_map
4. `src/presentation/widgets/metadata_viewer_dialog.py` - Use ID3Registry instead of direct JSON load
5. `src/core/yellberus.py` - Use ID3Registry for validation
6. `src/presentation/widgets/side_panel_widget.py` - Replace hardcoded category refs
7. `src/presentation/widgets/filter_widget.py` - Replace hardcoded category refs
8. `src/presentation/dialogs/tag_picker_dialog.py` - Replace hardcoded category refs
9. `src/business/services/renaming_service.py` - Replace hardcoded category refs

### Documentation:
10. `docs/ARCH_TAGS_UNIFICATION.md` - Update with ID3Registry architecture

## Implementation Order

### ✅ Phase 0: Planning (Complete)
- [x] Audit all hardcoded Genre/Mood references
- [x] Identify all JSON access points
- [x] Document current issues and proposed solution

### ✅ Phase 1: Create ID3Registry (Foundation) - COMPLETE
**Goal:** Centralize all JSON access before adding tag categories

1. ✅ Create `src/core/registries/` folder structure
2. ✅ Create `src/core/registries/id3_registry.py` with full implementation
3. ✅ Add unit tests for ID3Registry (12 tests, all passing)
4. ✅ Refactor `MetadataService` to use `ID3Registry.get_frame_map()`
5. ✅ Refactor `metadata_viewer_dialog.py` to use `ID3Registry.get_frame_map()`
6. ✅ Refactor `yellberus.py` validation to use `ID3Registry.get_frame_map()`
7. ✅ Run all tests to ensure no regressions (38 passed in metadata/registry tests)

### ✅ Phase 2: Extend JSON Schema - COMPLETE
**Goal:** Add tag category definitions to the data model

1. ✅ Extend `id3_frames.json` with `tag_categories` section
2. ✅ Add Genre, Mood, Status, Custom categories with metadata (icons, colors, ID3 frames)
3. ✅ Verify ID3Registry loads new structure correctly
4. ✅ Update tests to validate new JSON schema (12 tests, all passing)

### ✅ Phase 3: Refactor UI Components - COMPLETE
**Goal:** Remove all hardcoded category references

1. ✅ Refactor `tag_picker_dialog.py` (hardcoded category set, icons, colors)
2. ✅ Refactor `filter_widget.py` (icon mappings)
3. ✅ Refactor `side_panel_widget.py` (icon/color mappings, category logic)
4. ✅ App runs successfully with dynamic categories from ID3Registry

### ✅ Phase 4: Refactor Business Logic - COMPLETE
**Goal:** Make business services category-agnostic

1. ✅ Refactor `song_repository.py` (hardcoded "Genre" default → uses ID3Registry)
2. ✅ Refactor `renaming_service.py` (2 hardcoded genre checks → uses ID3Registry)
3. ✅ Remove legacy genre/mood field handling from `side_panel_widget.py` (dead code)
4. ✅ All hardcoded category references eliminated

### ✅ Phase 5: Documentation & Cleanup - COMPLETE
**Goal:** Update docs and verify everything works

1. [x] Update `ARCH_TAGS_UNIFICATION.md` with ID3Registry pattern
2. [x] Add examples of how to add custom tag categories
3. [x] Run full test suite
4. [x] Manual UI testing with real files
