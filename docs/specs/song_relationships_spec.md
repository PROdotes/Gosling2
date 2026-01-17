# Song Relationship Feature Implementation Plan

## Overview

This plan details the implementation of a song relationship system for Gosling2, enabling users to link songs together (remixes, samples, covers, medleys). The system will support **directed relationships** with bidirectional visibility - meaning both songs know about each other, but there's always a clear parent/child directionality.

## Supported Relationship Types

1. **Remix** - Link remixes to original versions (Original = Parent, Remix = Child)
2. **Sample** - Link songs that sample from other songs (Sampled Song = Parent, Sampling Song = Child)
3. **Cover** - Link cover versions to originals (Original = Parent, Cover = Child)
4. **Medley/Mashup** - Link medleys to multiple source songs (Source Songs = Parents, Medley = Child)
5. **Parody** - Link parodies to the original song (Original = Parent, Parody = Child)
6. **Version** - Link alternate versions (Instrumental, Acapella, Radio Edit) to the main track (Main Track = Parent, Version = Child)

## Parent/Child Directionality

**Key Concept:** While relationships are **queryable bidirectionally** (both songs see each other), they are **stored directionally** with clear parent/child semantics:

- **SourceSongID** = Child (the derivative work: remix, cover, sample-user, medley, parody, instrumental)
- **TargetSongID** = Parent (the original: source material, sampled song, main mix)

**Why this matters:**
- User creates relationship FROM the child TO the parent
- Example: "This remix (child) is based on Original Song (parent)"
- Database stores: `SourceSongID=RemixID, TargetSongID=OriginalID`
- Display labels adapt:
  - When viewing **child**: "remixes → Original Song"
  - When viewing **parent**: "remixed by ← Remix Song"

**Visual Indicators:**
- Forward arrow (→) shown when viewing child pointing to parent
- Backward arrow (←) shown when viewing parent pointing to child
- Icons differentiate: 🎧 Remix, 🎹 Sample, 🎤 Cover, 🎶 Medley, 🎭 Parody, 💿 Version

---

## Database Schema

### New Tables

#### RelationshipTypes (Lookup Table)
```sql
CREATE TABLE RelationshipTypes (
    TypeID INTEGER PRIMARY KEY,
    TypeName TEXT NOT NULL UNIQUE,
    Direction TEXT CHECK(Direction IN ('forward', 'reverse', 'bidirectional')),
    ForwardLabel TEXT,    -- 'remixes', 'samples from', 'covers'
    ReverseLabel TEXT     -- 'remixed by', 'sampled in', 'covered by'
)
```

**Default Data:**
- Remix: "remixes" / "remixed by"
- Sample: "samples from" / "sampled in"
- Cover: "covers" / "covered by"
- Medley: "includes" / "included in"
- Parody: "parodies" / "parodied by"
- Version: "version of" / "has version" (e.g. Instrumental -> Main Mix)

#### SongRelationships (Junction Table)
```sql
CREATE TABLE SongRelationships (
    RelationshipID INTEGER PRIMARY KEY AUTOINCREMENT,
    SourceSongID INTEGER NOT NULL,
    TargetSongID INTEGER NOT NULL,
    TypeID INTEGER NOT NULL,
    Notes TEXT,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (SourceSongID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE,
    FOREIGN KEY (TargetSongID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE,
    FOREIGN KEY (TypeID) REFERENCES RelationshipTypes(TypeID),
    UNIQUE(SourceSongID, TargetSongID, TypeID)
)

-- Indexes
CREATE INDEX idx_songrels_source ON SongRelationships(SourceSongID);
CREATE INDEX idx_songrels_target ON SongRelationships(TargetSongID);
CREATE INDEX idx_songrels_type ON SongRelationships(TypeID);
```

**Key Design Decisions:**
- **Store directionally** with clear parent/child semantics:
  - SourceSongID = Child (derivative: remix, cover, sampling song)
  - TargetSongID = Parent (original: source material, sampled song)
- **Query bidirectionally** (WHERE SourceSongID = ? OR TargetSongID = ?)
- **Display with context**: Labels show direction based on perspective
  - Viewing child shows: "→ remixes Parent Song"
  - Viewing parent shows: "← remixed by Child Song"
- **CASCADE delete** ensures cleanup when songs deleted
- **UNIQUE constraint** prevents duplicate relationships

---

## Data Models

### New Model Classes

#### RelationshipType Model
**File:** [src/data/models/relationship_type.py](src/data/models/relationship_type.py) (NEW)

```python
@dataclass
class RelationshipType:
    type_id: Optional[int]
    type_name: str
    direction: str  # 'forward', 'reverse', 'bidirectional'
    forward_label: str
    reverse_label: str
```

#### SongRelationship Model
**File:** [src/data/models/song_relationship.py](src/data/models/song_relationship.py) (NEW)

```python
@dataclass
class SongRelationship:
    relationship_id: Optional[int]
    source_song_id: int
    target_song_id: int
    type_id: int
    notes: Optional[str]
    created_at: Optional[datetime]

    # Denormalized fields (from joins)
    type_name: Optional[str]
    forward_label: Optional[str]
    reverse_label: Optional[str]
    target_song_title: Optional[str]
    target_song_artist: Optional[str]

    def get_display_label(self, perspective_song_id: int) -> str:
        """
        Get label from perspective of a specific song.

        Returns directional label with arrow:
        - If viewing child: "→ remixes Original Song by Artist"
        - If viewing parent: "← remixed by Remix Song by DJ"
        """
```

#### Song Model Update
**File:** [src/data/models/song.py](src/data/models/song.py:34) (MODIFY)

Add field:
```python
relationships: List[dict] = field(default_factory=list)
```

---

## Repository Layer

### SongRelationshipRepository
**File:** [src/data/repositories/song_relationship_repository.py](src/data/repositories/song_relationship_repository.py) (NEW)

Extends `GenericRepository[SongRelationship]` with:

**Type Management:**
- `get_all_types()` - Get all relationship types for pickers
- `get_type_by_name(type_name)` - Lookup by name

**CRUD Operations:**
- `get_by_id(relationship_id)` - Fetch single with joins
- `_insert_db()` - Create with validation (prevents self-links)
- `_update_db()` - Update relationship
- `_delete_db()` - Delete relationship

**Queries:**
- `get_relationships_for_song(song_id)` - Bidirectional query (WHERE SourceSongID = ? OR TargetSongID = ?)
- `get_related_songs(song_id, type)` - Get IDs of related songs
- `relationship_exists(source, target, type)` - Duplicate check
- `would_create_cycle(source, target, type)` - Cycle detection

### Database Migration
**File:** [src/data/database.py](src/data/database.py:420) (MODIFY)

Add to `_ensure_schema()` after existing table creations:
- CREATE TABLE RelationshipTypes
- INSERT default relationship types
- CREATE TABLE SongRelationships
- CREATE indexes

---

## Service Layer

### SongRelationshipService
**File:** [src/business/services/song_relationship_service.py](src/business/services/song_relationship_service.py) (NEW)

**Key Methods:**

**Type Management:**
- `get_all_types()` - For UI pickers
- `get_type_by_name(name)` - Type lookup

**CRUD:**
- `create_relationship(source_id, target_id, type_name, notes, batch_id)` - Create with validation
  - Validates: self-links, duplicates, type existence
  - Returns created SongRelationship
- `delete_relationship(relationship_id, batch_id)` - Remove relationship
- `update_notes(relationship_id, notes, batch_id)` - Update notes

**Queries:**
- `get_relationships_for_song(song_id)` - All relationships for a song
- `get_related_songs(song_id, type)` - IDs of related songs
- `get_relationship_tree(root_id, max_depth)` - Tree structure for visualization

**Bulk:**
- `remove_all_relationships_for_song(song_id, batch_id)` - Cleanup utility

### LibraryService Integration
**File:** [src/business/services/library_service.py](src/business/services/library_service.py:32) (MODIFY)

Add to `__init__`:
```python
self.relationship_service = SongRelationshipService()
```

Add delegation methods:
```python
def get_song_relationships(self, song_id):
def create_song_relationship(self, source_id, target_id, type_name, notes):
def delete_song_relationship(self, relationship_id):
```

---

## UI Components

### Entity Registry Update
**File:** [src/core/entity_registry.py](src/core/entity_registry.py:44) (MODIFY)

Add to EntityType enum:
```python
SONG_RELATIONSHIP = "song_relationship"
```

Add to ENTITY_REGISTRY:
```python
EntityType.SONG_RELATIONSHIP: EntityConfig(
    editor_dialog="song_relationship_dialog.SongRelationshipDialog",
    picker_dialog="song_relationship_dialog.SongRelationshipPickerDialog",
    service_attr="relationship_service",
    icon_fn=lambda e: {'Remix': '🎧', 'Sample': '🎹', 'Cover': '🎤', 'Medley': '🎶'}.get(e.type_name, '🔗'),
    display_fn=lambda e: e.get_display_label(None),
    supports_create=True,
    supports_remove=True,
)
```

### Context Adapter
**File:** [src/core/context_adapters.py](src/core/context_adapters.py) (MODIFY)

Add `SongRelationshipAdapter` class:

```python
class SongRelationshipAdapter(ContextAdapter):
    """Adapter for managing song relationships in EntityListWidget"""

    def __init__(self, song, relationship_service, library_service, refresh_fn):
        # Store services and song

    def get_children(self) -> List[int]:
        # Return IDs of related songs

    def get_child_data(self) -> List[tuple]:
        # Return chip data: (rel_id, label, icon, is_mixed, is_inherited, tooltip, zone, is_primary)
        # Label with directional arrows:
        #   Child view: "→ remixes Original Song by Artist"
        #   Parent view: "← remixed by Remix Song by DJ"

    def link(self, target_song_id: int, **kwargs) -> bool:
        # Create relationship (requires relationship_type kwarg)
        # Shows error dialog for validation failures

    def unlink(self, relationship_id: int) -> bool:
        # Delete relationship by ID

    def get_excluded_ids(self) -> set:
        # Exclude current song + already-related songs from picker
```

### Song Relationship Picker Dialog
**File:** [src/presentation/dialogs/song_relationship_dialog.py](src/presentation/dialogs/song_relationship_dialog.py) (NEW)

**Layout:**
- Relationship Type dropdown (Remix, Sample, Cover, Medley)
- Search field with live results
- Song list (title - artist format)
- Notes field (optional context)
- Cancel / Create buttons

**Signals:**
- `relationship_created(target_song_id, type_name, notes)` - Emitted on Create

**Logic:**
- Live search as user types (min 2 chars)
- Excludes already-related songs and current song
- Double-click or Create button to confirm

### Relationship Graph Widget
**File:** [src/presentation/widgets/relationship_graph_widget.py](src/presentation/widgets/relationship_graph_widget.py) (NEW)

**Display Format:**
- QTreeWidget grouped by relationship type
- Expandable type nodes: "Remix (3)", "Sample (1)"
- Song items show: artist - title
- Notes displayed as child items with 📝 icon

**Signals:**
- `relationship_clicked(relationship_id)` - Click on relationship
- `song_clicked(song_id)` - Click on song

### Side Panel Integration
**File:** [src/presentation/widgets/side_panel_widget.py](src/presentation/widgets/side_panel_widget.py:55) (MODIFY)

**Changes:**

1. Add to `__init__`:
```python
self.relationship_service = SongRelationshipService()
```

2. Add to `_build_fields()` after attributes section:
```python
# Relationships section (only for single song)
if len(self.current_songs) == 1:
    relationship_struct = self._build_relationship_section()
    if relationship_struct:
        add_group([relationship_struct], "Relationships", show_line=True, compact=False)
```

3. Add new method `_build_relationship_section()`:
```python
def _build_relationship_section(self):
    """Build EntityListWidget for relationships"""
    song = self.current_songs[0]
    adapter = SongRelationshipAdapter(song, self.relationship_service, self.library_service, refresh_fn)
    relationship_widget = EntityListWidget(
        service_provider=self,
        entity_type=EntityType.SONG_RELATIONSHIP,
        layout_mode=LayoutMode.CLOUD,
        context_adapter=adapter,
        allow_add=True, allow_remove=True, allow_edit=True
    )
    return relationship_widget
```

---

## Implementation Sequence

### Phase 1: Database Foundation
1. ✅ Update [database.py](src/data/database.py) - Add tables to `_ensure_schema()`
2. ✅ Create [relationship_type.py](src/data/models/relationship_type.py) model
3. ✅ Create [song_relationship.py](src/data/models/song_relationship.py) model
4. ✅ Update [song.py](src/data/models/song.py) - Add relationships field
5. ✅ Test migration - Run app, verify tables created, check seed data

### Phase 2: Repository Layer
6. ✅ Create [song_relationship_repository.py](src/data/repositories/song_relationship_repository.py)
7. ✅ Implement CRUD methods with GenericRepository pattern
8. ✅ Implement bidirectional queries
9. ✅ Write unit tests for repository
10. ✅ Test with manual SQL inserts

### Phase 3: Service Layer
11. ✅ Create [song_relationship_service.py](src/business/services/song_relationship_service.py)
12. ✅ Implement validation logic (self-links, duplicates)
13. ✅ Update [library_service.py](src/business/services/library_service.py) - Add delegation
14. ✅ Write service unit tests

### Phase 4: UI Registry & Adapter
15. ✅ Update [entity_registry.py](src/core/entity_registry.py) - Add SONG_RELATIONSHIP
16. ✅ Create SongRelationshipAdapter in [context_adapters.py](src/core/context_adapters.py)
17. ✅ Test adapter with mock service

### Phase 5: UI Dialogs
18. ✅ Create [song_relationship_dialog.py](src/presentation/dialogs/song_relationship_dialog.py) - Picker
19. ✅ Implement search functionality
20. ✅ Create [relationship_graph_widget.py](src/presentation/widgets/relationship_graph_widget.py)
21. ✅ Test dialogs standalone

### Phase 6: Side Panel Integration
22. ✅ Update [side_panel_widget.py](src/presentation/widgets/side_panel_widget.py)
23. ✅ Add relationship section to field builder
24. ✅ Wire EntityListWidget with adapter
25. ✅ Test full flow: add/remove relationships

### Phase 7: Polish
26. ✅ Add error dialogs for validation failures
27. ✅ Add context menu for "View Relationship Graph"
28. ✅ Handle bulk selection (disable for multi-song)
29. ✅ Add loading indicators

### Phase 8: Testing
30. ✅ Integration tests - Full user flows
31. ✅ Edge case tests - Cycles, deleted songs, orphans
32. ✅ Performance tests - 1000+ relationships

---

## Key Design Decisions

### Directionality Strategy
- **Store directionally** with parent/child semantics:
  - SourceSongID = Child (derivative work)
  - TargetSongID = Parent (source material)
- **Query bidirectionally** (WHERE SourceSongID = ? OR TargetSongID = ?)
- **Display with arrows** adapts to perspective:
  - Child view: `→ remixes Parent Song`
  - Parent view: `← remixed by Child Song`
  - Implementation: `get_display_label(perspective_song_id)`

**Why:**
- Clear parent/child semantics (user always knows who is original vs derivative)
- Avoids data duplication (store once)
- Prevents sync issues (single source of truth)
- Simpler audit logging (one record per relationship)

### No Yellberus Integration
- Relationships are **entity associations**, not field values
- Don't appear in library table columns
- Managed via EntityListWidget in detail panel only

**Why:** Relationships don't need column headers, filters, or portable export

### Cascade Deletes
- ON DELETE CASCADE on foreign keys
- When song deleted, relationships auto-removed
- Audit log captures deletions

**Why:** Prevents orphaned relationships, maintains data integrity

### Validation Rules
- ✅ Prevent self-links (song → itself)
- ✅ Prevent duplicate relationships (same source, target, type)
- ❌ Allow cycles (A→B, B→A) - user may want bidirectional sample relationships
- 🔄 Max depth limit (3 levels) in graph widget prevents infinite loops

---

## Data Flow

### Creating a Relationship

```
User clicks "Add Relationship" in side panel
    ↓
SongRelationshipPickerDialog opens
    ↓
User searches for target song, selects type, adds notes
    ↓
Dialog emits relationship_created(target_id, type, notes)
    ↓
SongRelationshipAdapter.link(target_id, relationship_type=type, notes=notes)
    ↓
SongRelationshipService.create_relationship(source_id, target_id, type, notes)
    ↓ (validation: self-link, duplicate, type exists)
SongRelationshipRepository.insert(relationship, batch_id)
    ↓ (GenericRepository pattern with audit logging)
Database INSERT + AuditLogger.log_change()
    ↓
Adapter calls refresh_fn() → UI updates with new chip
```

### Viewing Relationships

```
Side panel displays song
    ↓
_build_relationship_section() creates EntityListWidget
    ↓
SongRelationshipAdapter.get_child_data()
    ↓
SongRelationshipService.get_relationships_for_song(song_id)
    ↓
SongRelationshipRepository.get_relationships_for_song(song_id)
    ↓ (Query both directions: WHERE SourceSongID = ? OR TargetSongID = ?)
Returns List[SongRelationship] with joined type/song data
    ↓
Adapter formats as chips: icon + label (perspective-aware)
    ↓
EntityListWidget renders chips in CLOUD layout
```

---

## Critical Files

### Must Create (NEW files):
1. [src/data/models/relationship_type.py](src/data/models/relationship_type.py)
2. [src/data/models/song_relationship.py](src/data/models/song_relationship.py)
3. [src/data/repositories/song_relationship_repository.py](src/data/repositories/song_relationship_repository.py)
4. [src/business/services/song_relationship_service.py](src/business/services/song_relationship_service.py)
5. [src/presentation/dialogs/song_relationship_dialog.py](src/presentation/dialogs/song_relationship_dialog.py)
6. [src/presentation/widgets/relationship_graph_widget.py](src/presentation/widgets/relationship_graph_widget.py)

### Must Modify (EXISTING files):
1. [src/data/database.py](src/data/database.py:420) - Add tables to _ensure_schema()
2. [src/data/models/song.py](src/data/models/song.py:34) - Add relationships field
3. [src/business/services/library_service.py](src/business/services/library_service.py:32) - Add relationship_service
4. [src/core/entity_registry.py](src/core/entity_registry.py:44) - Add SONG_RELATIONSHIP
5. [src/core/context_adapters.py](src/core/context_adapters.py) - Add SongRelationshipAdapter
6. [src/presentation/widgets/side_panel_widget.py](src/presentation/widgets/side_panel_widget.py:55) - Add relationship section

---

## Testing Strategy

### Unit Tests
- **Repository**: CRUD, bidirectional queries, validation, cascade deletes
- **Service**: create with validation, duplicate rejection, bulk operations
- **Adapter**: get_children, get_child_data, link/unlink

### Integration Tests
- Full flow: select song → add relationship → verify DB → remove
- Edge cases: self-link (fail), duplicate (fail), delete song (cascade)
- Bidirectional views: verify labels correct from both perspectives

### Manual Testing Checklist
- [ ] Create each relationship type (Remix, Sample, Cover, Medley)
- [ ] View relationship from both songs (bidirectional)
- [ ] Edit relationship notes
- [ ] Delete relationship
- [ ] Delete song with relationships (cascade)
- [ ] Search for songs in picker
- [ ] Open relationship graph tree view
- [ ] Verify audit log entries
- [ ] Test with 100+ relationships (performance)

---

## Verification

### End-to-End Test Flow
1. Launch Gosling2
2. Select a song in library (e.g., "Original Song")
3. In right panel, scroll to "Relationships" section
4. Click "Add Relationship" button
5. In picker dialog:
   - Select "Remix" from dropdown
   - Search for target song (e.g., "Remix Version")
   - Add notes: "Club remix with extended intro"
   - Click "Create Relationship"
6. Verify chip appears: "🎧 → remixes Remix Version by DJ Name"
   - Note the **forward arrow (→)** indicating child pointing to parent
7. Click on chip → target song loads in editor
8. Switch to target song view (the remix)
9. Verify reverse relationship shows: "🎧 ← remixed by Original Song by Artist"
   - Note the **backward arrow (←)** indicating parent pointing back to child
   - This confirms bidirectional visibility with clear directionality
10. Right-click chip → "View Relationship Graph" → tree dialog opens
11. Delete relationship via Ctrl+Click on chip
12. Verify relationship removed from both songs
13. Check database: `SELECT * FROM SongRelationships` (should be empty)
14. Check audit log: `SELECT * FROM ChangeLog WHERE LogTableName='SongRelationships'` (should show INSERT + DELETE)

### Success Criteria
- ✅ Relationships persist to database correctly
- ✅ Bidirectional display works (correct labels from both perspectives)
- ✅ Validation prevents self-links and duplicates
- ✅ Cascade delete removes relationships when song deleted
- ✅ Audit logging captures all changes
- ✅ UI is responsive and intuitive (EntityListWidget pattern)
- ✅ Graph view displays relationship hierarchy correctly

---

## Future Enhancements (Post-MVP)

1. **Advanced Graph Visualization** - Node-edge diagram with Qt Charts/GraphViz
2. **Relationship Timeline** - Chronological history view
3. **Bulk Operations** - "Make all tracks on Album X sample Album Y"
4. **Import/Export** - CSV import for bulk relationships
5. **Custom Relationship Types** - User-defined types via settings
6. **Smart Suggestions** - ML-based detection of samples/covers
7. **Transitive Queries** - "Find all songs that sample songs covered by X"
8. **Statistics Dashboard** - "Most remixed artist", "Most sampled song"

---

## Notes

- All database operations use existing audit logging (fail-secure pattern)
- Follows GenericRepository pattern for consistency
- Reuses EntityListWidget pattern (like albums, artists, tags)
- No schema migration tool needed - tables auto-created on next app launch
- Relationships NOT exported to ID3 tags (internal metadata only)
- Search performance acceptable for <10k songs; FTS5 optimization available for larger libraries

## Future Consideration: Version Folding (The "Cleaner Library" Goal)

User Request: "It's annoying to see 5 rows for the same song (Main, Instrumental, Acapella). I want to quickly find them, but not clutter the view."

**Concept:**
Using the `Version` relationship type (Main Track = Parent, Instrumental = Child), we can eventually implement **"Version Folding"** in the main library grid.

**Workflow:**
1. **Link:** User links "Song A (Instrumental)" to "Song A" as a **Version**.
2. **Fold:** The Library Widget detects this hierarchy.
3. **Display:** 
   - The grid hides the Instrumental row.
   - The Main Track row shows a `[+Versions]` badge or icon.
   - Clicking the badge expands to show the satellite versions.

**Benefit:**
This allows users to keep their library clean without manually renaming files or relying on "Title Suffixes" (which look messy), matching the behavior of premium players like Roon.
