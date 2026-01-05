# 🏗️ Proposal: Smart Entity Widgets (Unified Chip System)

> **Goal**: Eliminate ~600 lines of duplicated chip/list boilerplate by creating a self-routing `EntityListWidget` that knows how to display, edit, add, and remove entities without parent dialogs needing to wire up handlers.

## 🚨 CRITICAL PREREQUISITES (Added Jan 5 2026)

**T-91 (Album Artist M2M Schema) MUST BE DONE FIRST.**
*   **Why**: We cannot build a universal ID-based widget if `Album.album_artist` is still a text string. We need to migrate it to an `AlbumContributors` table so it has a real Artist ID.
*   **Impact**: Attempting to implement the UI before the Schema change will result in "String Mode" hacks that we'll just have to delete later.

**Architecture Corrections (from review):**

1.  **Use `ContextAdapter`**: Do not pass raw parent objects (Songs/Albums) to the widget. The widget doesn't know if it's editing a Song, Album, Artist, or Publisher. Pass an adapter that handles `link(child_id)` and `unlink(child_id)` for that specific parent type.

2.  **No String Matching for Special Cases**: Do NOT check `"Status:" in label` to detect Status tags. This breaks with i18n (e.g., "Estado:" in Spanish). Always look up the entity by ID and check `tag.category == "Status"` from the database object.

3.  **STACK Mode Must Wrap QListWidget**: Do NOT use `VBoxLayout.addWidget()` for STACK mode. A layout with 100 `QWidget` instances is slow. `QListWidget` uses a flyweight/delegate pattern that handles thousands of items efficiently. STACK mode should internally use `QListWidget` with custom item widgets, not a layout loop.

4.  **No Drag-and-Drop Reordering Required**: Album tracklists and other lists do not need manual reordering. Either don't sort (preserve insertion order) or sort alphabetically. This simplifies STACK implementation.

---

## 1. The Problem: Copy-Paste Click Handlers Everywhere

Every time we use `ChipTrayWidget` or a `QListWidget` for entity references, we write the same boilerplate:

| Location | Fields | Lines of Boilerplate |
|:---------|:-------|:---------------------|
| `SidePanelWidget` | performers, composers, producers, lyricists, publisher, album, tags | ~400 lines (`_handle_tag_click` alone is 190 lines) |
| `AlbumManagerDialog` | artists (tray), publishers (tray), songs (list) | ~130 lines |
| `ArtistDetailsDialog` | aliases (list), members (list) | ~100 lines |
| `PublisherDetailsDialog` | children/subsidiaries (list) | ~50 lines |
| **Total** | | **~680 lines** |

### What This Boilerplate Looks Like

Every chip field requires:

```python
# 1. Create widget (3 lines)
self.tray_artist = ChipTrayWidget(confirm_removal=True, ...)
layout.addWidget(self.tray_artist)

# 2. Connect chip_clicked → Open editor (15-30 lines)
self.tray_artist.chip_clicked.connect(self._on_artist_chip_clicked)

def _on_artist_chip_clicked(self, chip_id, label):
    artist = self.contributor_service.get_by_id(chip_id)
    if not artist: return
    diag = ArtistDetailsDialog(artist, self.contributor_service, 
                               context_song=self.current_song,
                               allow_remove_from_context=True, parent=self)
    result = diag.exec()
    if result == 2:  # Remove requested
        self._on_chip_removed('performers', chip_id, label)
    if result == 3:  # Data changed, sync required
        self._refresh_data()
        self.filter_refresh_requested.emit()

# 3. Connect chip_remove_requested → Unlink logic (10-20 lines)
self.tray_artist.chip_remove_requested.connect(self._on_artist_removed)

def _on_artist_removed(self, chip_id, label):
    for song in self.current_songs:
        current = getattr(song, 'performers', [])
        new_list = [p for p in current if p != label]
        self._stage_change('performers', new_list)
    self._refresh_field_values()

# 4. Connect add button → Open picker (15-25 lines)  
self.tray_artist.add_requested.connect(self._on_add_artist)

def _on_add_artist(self):
    diag = ArtistPickerDialog(self.contributor_service, parent=self)
    if diag.exec():
        selected = diag.get_selected()
        if selected:
            self._add_name_to_selection('performers', selected.name)

# 5. Populate chips → Conversion logic (10-20 lines)
def _populate_artist_chips(self):
    chips = []
    for name in self.current_song.performers:
        artist, _ = self.contributor_service.get_or_create(name)
        icon = "👤" if artist.type == "person" else "👥"
        chips.append((artist.contributor_id, name, icon, False, False, "", "amber", False))
    self.tray_artist.set_chips(chips)
```

**That's ~65 lines per field**, copied with minor variations into every dialog.

---

## 2. The Solution: Self-Routing `EntityListWidget`

A single widget class that encapsulates all chip/list behavior:

```python
class EntityListWidget(QWidget):
    """Smart chip tray that knows how to handle its own entities."""
    
    # Signals for parent notification (optional hooks)
    data_changed = pyqtSignal()  # Something was added/removed/edited
    
    def __init__(self, 
                 service_provider: ServiceProvider,
                 entity_type: EntityType,
                 layout_mode: LayoutMode = LayoutMode.CLOUD,
                 context_adapter: ContextAdapter = None,  # Handles parent relationship
                 allow_add: bool = True,
                 allow_remove: bool = True,
                 allow_edit: bool = True,
                 parent=None):
        ...
```

### The ContextAdapter Pattern

**The widget doesn't know what parent entity it's attached to.** It only knows:
- "I display a list of X entities"
- "When Remove is clicked, I call `adapter.unlink(child_id)`"
- "When Add is clicked, I call `adapter.link(child_id)`"

The **adapter** knows the parent entity and how to perform the operation:

```python
class ContextAdapter(ABC):
    """Abstract interface for parent-child relationship management."""
    
    @abstractmethod
    def get_children(self) -> List[int]:
        """Return IDs of currently linked child entities."""
        pass
    
    @abstractmethod
    def link(self, child_id: int) -> bool:
        """Link a child entity to the parent. Returns success."""
        pass
    
    @abstractmethod
    def unlink(self, child_id: int) -> bool:
        """Unlink a child entity from the parent. Returns success."""
        pass
    
    @abstractmethod
    def get_parent_for_dialog(self) -> Any:
        """Return parent entity for dialog context (e.g., 'Remove from this song' button)."""
        pass
```

### Usage Examples (Different Contexts)

```python
# SidePanel: Editing a Song's performers
# Context = Song, Relationship = Song → Artists
self.tray_performers = EntityListWidget(
    self.services,
    EntityType.ARTIST,
    context_adapter=SongFieldAdapter(self.current_songs, 'performers', self.contributor_service)
)

# AlbumManager: Editing an Album's artists
# Context = Album, Relationship = Album → Artists  
self.tray_album_artists = EntityListWidget(
    self.services,
    EntityType.ARTIST,
    context_adapter=AlbumArtistAdapter(self.current_album, self.album_service)
)

# PublisherDetails: Editing a Publisher's subsidiaries
# Context = Publisher, Relationship = Publisher → Children
self.tray_children = EntityListWidget(
    self.services,
    EntityType.PUBLISHER,
    layout_mode=LayoutMode.STACK,
    context_adapter=PublisherChildAdapter(self.publisher, self.publisher_service)
)

# ArtistDetails: Editing an Artist's aliases
# Context = Artist, Relationship = Artist → Aliases
self.tray_aliases = EntityListWidget(
    self.services,
    EntityType.ALIAS,
    layout_mode=LayoutMode.STACK,
    context_adapter=ArtistAliasAdapter(self.artist, self.contributor_service)
)
```

**The widget code is identical in all cases.** Only the adapter changes.

---

## 3. Core Architecture

### 3.1 Entity Type Registry

Central mapping of entity types to their behaviors:

```python
class EntityType(Enum):
    ARTIST = "artist"
    PUBLISHER = "publisher"  
    ALBUM = "album"
    TAG = "tag"
    ALIAS = "alias"      # Inline edit only, no deep dialog
    SONG = "song"        # Future: link/unlink songs
    GROUP_MEMBER = "group_member"  # Artist membership

# Registry: EntityType → (EditorDialog, PickerDialog, Service accessor)
ENTITY_REGISTRY = {
    EntityType.ARTIST: EntityConfig(
        editor_class=ArtistDetailsDialog,
        picker_class=ArtistPickerDialog,
        service_attr="contributor_service",
        icon_fn=lambda e: "👤" if e.type == "person" else "👥",
        display_fn=lambda e: e.name,
    ),
    EntityType.PUBLISHER: EntityConfig(
        editor_class=PublisherDetailsDialog,
        picker_class=PublisherPickerDialog,
        service_attr="publisher_service",
        icon_fn=lambda e: "🏢",
        display_fn=lambda e: e.publisher_name,
    ),
    EntityType.TAG: EntityConfig(
        editor_class=TagPickerDialog,  # Reused for rename
        picker_class=TagPickerDialog,
        service_attr="tag_service",
        icon_fn=lambda e: get_tag_category_icon(e.category),
        display_fn=lambda e: f"{e.category}: {e.tag_name}",
        custom_click_handler="handle_tag_click",  # Special case hook
    ),
    # ... etc
}
```

### 3.2 Layout Modes

```python
class LayoutMode(Enum):
    CLOUD = "cloud"  # FlowLayout, horizontal wrap (current ChipTrayWidget)
    STACK = "stack"  # QListWidget with custom item widgets (NOT VBoxLayout)
```

| Mode | Visual | Used For |
|:-----|:-------|:---------|
| `CLOUD` | Chips flowing horizontally | Tags, Artists, Publishers in SidePanel |
| `STACK` | Vertical list with details | Songs in Album, Aliases in Artist, Subsidiaries in Publisher |

### 3.3 The Click Router (Internal)

```python
class EntityListWidget(QWidget):
    def _on_item_clicked(self, entity_id: int, label: str):
        """Internal: Route click to appropriate editor."""
        config = ENTITY_REGISTRY[self.entity_type]
        
        # Special case hook (e.g., Status tags show audit, not editor)
        if config.custom_click_handler:
            handler = getattr(self, config.custom_click_handler, None)
            if handler and handler(entity_id, label):
                return  # Handled by custom logic
        
        # Standard: Open the registered editor dialog
        service = getattr(self.services, config.service_attr)
        entity = service.get_by_id(entity_id)
        if not entity:
            return
            
        # Get context for "Remove from this song" button
        parent_entity = self.context_adapter.get_parent_for_dialog() if self.context_adapter else None
        
        dialog = config.editor_class(
            entity, 
            service,
            context_song=parent_entity,  # Adapter provides the right parent type
            allow_remove_from_context=self.allow_remove,
            parent=self
        )
        
        result = dialog.exec()
        self._handle_dialog_result(result, entity_id, label)
```

---

## 4. Special Cases & Hooks

### 4.1 The Status Tag Exception

Status tags (e.g., "Status: Unprocessed") don't open an editor—they show a validation audit.

**Solution**: `custom_click_handler` in the registry, using **ID-based lookup** (not string matching):

```python
EntityType.TAG: EntityConfig(
    ...
    custom_click_handler="handle_tag_click",
),

# In EntityListWidget or a TagListWidget subclass:
def handle_tag_click(self, entity_id: int, label: str) -> bool:
    """Returns True if handled, False to continue to default behavior."""
    # IMPORTANT: Look up by ID, not by parsing the label string!
    # This ensures i18n compatibility ("Status" vs "Estado" vs "État")
    tag = self.services.tag_service.get_by_id(entity_id)
    if tag and tag.category == "Status":
        self._show_validation_audit()
        return True  # Handled
    return False  # Continue to normal tag editor
```

### 4.2 Inherited Chips (Ghost Mode)

Publisher chips inherited from Album should be visually distinct and click to open Album Manager.

**Solution**: Chip metadata flag + click routing:

```python
# When setting chips, mark inheritance
chips.append((pub_id, name, "🔗", False, is_inherited=True, tooltip, zone, False))

# In click handler
def _on_item_clicked(self, entity_id, label):
    chip = self._get_chip_by_id(entity_id)
    if chip.is_inherited:
        # Redirect to Album Manager instead of Publisher editor
        self._open_album_manager(focus_publisher=True)
        return
    # ... normal handling
```

### 4.3 Context-Aware Removal

"Remove" means different things:
- In **SidePanel**: Unlink from current song(s), stage the change
- In **ArtistDetailsDialog**: Remove alias/membership from artist
- In **AlbumManagerDialog**: Unlink artist from album

**Solution**: This is exactly what `ContextAdapter` handles. Each adapter knows its parent:

```python
# SongFieldAdapter.unlink() → Removes from song.performers, stages change
# AlbumArtistAdapter.unlink() → Calls album_service.remove_artist(album_id, artist_id)
# ArtistAliasAdapter.unlink() → Calls contributor_service.delete_alias(alias_id)
# PublisherChildAdapter.unlink() → Sets child.parent_publisher_id = None
```

The widget just calls `self.context_adapter.unlink(entity_id)` — it doesn't need to know what kind of parent it's attached to.

---

## 5. EntityPickerDialog (Universal Search/Create/Rename)

The `TagPickerDialog` pattern is a proven UX for fast entity management. Generalize it to work for **all entity types**.

### 5.1 Common UX Pattern

```
┌─────────────────────────────────────┐
│ ADD/RENAME ENTITY                   │
├─────────────────────────────────────┤
│ [🎵 Genre] [💭 Mood] [📋 Status]... │  ← Type/Category buttons
├─────────────────────────────────────┤
│ [Search or prefix:value...       ]  │  ← Search with prefix support
├─────────────────────────────────────┤
│ ✏️ Rename to "NewName" in Mood      │  ← Edit mode only
│ ➕ Create "NewName" in Mood         │  ← If no exact match
│ 🎵 Pop (Genre)                      │
│ 🎵 Rock (Genre)                     │
│ ...                                 │
├─────────────────────────────────────┤
│ [Remove]        [Cancel] [SELECT]   │
└─────────────────────────────────────┘
```

### 5.2 Entity-Specific Behavior

| Aspect | Tags | Artists |
|:-------|:-----|:--------|
| **Type Buttons** | Categories: Genre, Mood, Status, Custom | Types: Person, Group, Alias |
| **Prefix Syntax** | `m:chill` → Mood, `genre:rock` → Genre | `alias:pink` → Aliases, `group:queen` → Groups |
| **New Types** | ✅ Can create (`vacation:beach`) | ❌ Cannot create (`clown:bob` = error) |
| **Create** | Creates tag with name + category | Creates artist with name + type |
| **Rename** | Renames tag, can change category | Renames artist, can change type?* |
| **Merge** | Tags can merge on conflict | Artists can merge on conflict |

*Artist type change (Person↔Group) has implications for memberships.

### 5.3 Configuration

```python
@dataclass
class PickerConfig:
    """Configuration for EntityPickerDialog behavior."""
    
    # Display
    title_add: str          # "Add Tag" / "Add Artist"
    title_edit: str         # "Rename Tag" / "Edit Artist"
    
    # Type/Category system
    type_buttons: List[str]             # ["Genre", "Mood", ...] or ["Person", "Group", "Alias"]
    type_icons: Dict[str, str]          # {"Genre": "🎵", "Person": "👤", ...}
    type_colors: Dict[str, str]         # Glow colors for each button
    allow_new_types: bool               # True for Tags, False for Artists
    
    # Prefix parsing
    prefix_map: Dict[str, str]          # {"g": "Genre", "m": "Mood"} or {"a": "Alias", "p": "Person"}
    
    # Actions
    allow_create: bool = True
    allow_rename: bool = True
    allow_remove: bool = True
    
    # Entity-specific
    service_attr: str                   # "tag_service" or "contributor_service"
    search_fn: str                      # Method name for searching
    get_all_fn: str                     # Method name for getting all by type
```

### 5.4 Usage

```python
# Tags - current TagPickerDialog behavior
tag_picker = EntityPickerDialog(
    service_provider=self.services,
    config=TAG_PICKER_CONFIG,
    target_entity=existing_tag,  # Edit mode
    parent=self
)

# Artists - new ArtistPicker using same UX
artist_picker = EntityPickerDialog(
    service_provider=self.services,
    config=ARTIST_PICKER_CONFIG,
    target_entity=existing_artist,  # Edit mode
    parent=self
)
```

### 5.5 Predefined Configs

```python
TAG_PICKER_CONFIG = PickerConfig(
    title_add="Add Tag",
    title_edit="Rename Tag",
    type_buttons=["Genre", "Mood", "Status", "Custom"],  # Dynamic from DB
    type_icons=ID3Registry.get_all_category_icons(),
    type_colors=ID3Registry.get_all_category_colors(),
    allow_new_types=True,  # Can create "vacation:beach"
    prefix_map={"g": "Genre", "m": "Mood", "s": "Status", "c": "Custom"},
    service_attr="tag_service",
    search_fn="search",
    get_all_fn="get_all_by_category",
)

ARTIST_PICKER_CONFIG = PickerConfig(
    title_add="Add Artist",
    title_edit="Edit Artist", 
    type_buttons=["Person", "Group", "Alias"],
    type_icons={"Person": "👤", "Group": "👥", "Alias": "📝"},
    type_colors={"Person": "#4FC3F7", "Group": "#81C784", "Alias": "#FFB74D"},
    allow_new_types=False,  # Cannot invent new types
    prefix_map={"p": "Person", "g": "Group", "a": "Alias"},
    service_attr="contributor_service",
    search_fn="search",
    get_all_fn="search",  # with type filter
)
```

---

## 6. Yellberus Integration (Phase 4)

Once `EntityListWidget` is stable, extend `FieldDef` to drive UI generation:

```python
@dataclass
class FieldDef:
    # ... existing fields ...
    
    # NEW: Entity widget hints
    entity_type: str = None        # 'artist', 'publisher', 'tag', etc.
    chip_layout: str = "cloud"     # 'cloud' or 'stack'
    allow_chip_add: bool = True
    allow_chip_remove: bool = True
```

**Then `SidePanelWidget._build_fields()` becomes:**

```python
for field_def in yellberus.FIELDS:
    if field_def.entity_type:
        # NOTE: ContextAdapter must be created by the parent, not auto-generated
        # Yellberus only provides defaults; parent creates appropriate adapter
        widget = EntityListWidget(
            self.services,
            EntityType(field_def.entity_type),
            layout_mode=LayoutMode(field_def.chip_layout),
            context_adapter=SongFieldAdapter(self.current_songs, field_def.name, ...),
            allow_add=field_def.allow_chip_add,
            allow_remove=field_def.allow_chip_remove,
        )
    elif field_def.field_type == FieldType.TEXT:
        widget = GlowLineEdit()
    # ... etc
    
    self._field_widgets[field_def.name] = widget
```

This is optional and comes AFTER the core widget is battle-tested.

---

## 6. Migration Plan

### Phase 1: The Foundation (T-91)
**Goal**: Unify Data Model.
1.  **Database**: Migrate `AlbumArtist` (String) -> `AlbumContributors` (M2M Table).
2.  **Repo**: Update `AlbumRepository` to support Add/Remove calls for this new relation.

### Phase 2: Entity Registry & Click Router
**Goal**: Centralize dialog mappings without changing widget structure.

1. Create `src/core/entity_registry.py`:
   - Define `EntityType` enum
   - Define `EntityConfig` dataclass
   - Create `ENTITY_REGISTRY` mapping
   
2. Create `EntityClickRouter` helper class:
   - Takes `ServiceProvider` and routes `(entity_type, entity_id)` to correct dialog
   - Used by existing widgets to DRY up click handlers

3. Refactor `SidePanelWidget`:
   - Replace `_handle_*_click` methods with router calls
   - Keep existing `ChipTrayWidget` instances (no widget changes yet)

### Phase 3: EntityListWidget
**Goal**: Build the unified widget.

1. Create `src/presentation/widgets/entity_list_widget.py`:
   - Wraps `ChipTrayWidget` (CLOUD mode) or `QListWidget` with custom delegates (STACK mode)
   - Uses `EntityClickRouter` internally
   - Handles add/remove via `ContextAdapter`

2. Refactor **one consumer** first: `ArtistDetailsDialog`
   - Replace `list_aliases` with `EntityListWidget(..., EntityType.ALIAS, LayoutMode.STACK)`
   - Replace `list_members` with `EntityListWidget(..., EntityType.GROUP_MEMBER, LayoutMode.STACK)`
   
3. If stable, expand to:
   - `PublisherDetailsDialog` (children list → chips)
   - `AlbumManagerDialog` (artist tray, publisher tray)
   - `SidePanelWidget` (all chip fields)

### Phase 4: Yellberus UI Hints
**Goal**: Make `SidePanelWidget._build_fields()` data-driven.

1. Add `entity_type` and `chip_layout` fields to `FieldDef`
2. Update Yellberus `FIELDS` list with new metadata
3. Refactor `_build_fields()` to use metadata instead of hardcoded logic

---

## 7. Open Questions

### Q1: Should `EntityListWidget` own the service, or receive callbacks?
**Recommendation**: Own the `ServiceProvider`. This is meant to be a "smart component" that can function autonomously. Testing requires mocking `ServiceProvider`, but that's acceptable.

### Q2: How do we handle fields that need different widgets in different contexts?
Example: `performers` is CLOUD chips in SidePanel but might be STACK in a bulk editor.

**Recommendation**: The `layout_mode` is passed at construction time, not stored in Yellberus. Yellberus only stores the *default* layout. Callers can override.

### Q3: What about the Tag Picker's "category prefix" feature?
The existing `TagPickerDialog` has smart prefix parsing (`m:chill` → Mood: Chill). This should be preserved.

**Recommendation**: `TagPickerDialog` remains a separate class. `EntityListWidget` with `EntityType.TAG` delegates to it for add/edit operations.

---

## 8. Success Metrics

| Metric | Before | After |
|:-------|:-------|:------|
| Lines of chip handler code | ~680 | ~80 |
| Time to add chips to new dialog | ~2 hours | ~10 minutes |
| Files touched to change click behavior | 4-5 | 1 (registry) |
| Duplicated logic across dialogs | High | Eliminated |

---

## 9. Files Affected

### New Files
- `src/core/entity_registry.py` - EntityType, EntityConfig, ENTITY_REGISTRY
- `src/presentation/widgets/entity_list_widget.py` - The unified widget

### Modified Files (Phase 1)
- `src/presentation/widgets/side_panel_widget.py` - Use router, simplify handlers

### Modified Files (Phase 2)
- `src/presentation/dialogs/artist_manager_dialog.py` - Use EntityListWidget
- `src/presentation/dialogs/publisher_manager_dialog.py` - Use EntityListWidget
- `src/presentation/dialogs/album_manager_dialog.py` - Use EntityListWidget

### Modified Files (Phase 3)
- `src/core/yellberus.py` - Add entity_type, chip_layout to FieldDef

---

## 10. Relation to Existing Tasks

| Task ID | Title | Relation |
|:--------|:------|:---------|
| T-85 | Universal Input Dialog | Subsumed - `EntityListWidget` replaces the "unified input" concept |
| T-70 | Artist Manager | Benefits from this - cleaner chip handling |
| T-63 | Publisher Hierarchy | Benefits - subsidiaries become chips |
| T-46 | Album Manager | Benefits - song list becomes smart list |

---

## Appendix A: Current Chip Handler Code Locations

For reference, here's where the duplicated logic currently lives:

### SidePanelWidget (~400 lines)
- `_on_chip_clicked` (line 708) - Router
- `_handle_tag_click` (lines 720-911) - 191 lines
- `_handle_publisher_click` (lines 913-956) - 43 lines
- `_handle_album_click` (lines 958-962) - 4 lines
- `_handle_contributor_click` (lines 964-1027) - 63 lines
- `_on_chip_removed` (lines 1029-1099) - 70 lines
- `_on_add_button_clicked` (lines 1101-1142) - 41 lines

### AlbumManagerDialog (~130 lines)
- `_on_artist_chip_clicked` (lines 745-778) - 33 lines
- `_on_publisher_chip_clicked` (lines 780-800) - 20 lines
- `_on_search_artist` (lines 726-743) - 17 lines (add logic)
- `_on_search_publisher` (lines 708-723) - 15 lines (add logic)
- Chip population in `_on_vault_item_clicked` - ~40 lines

### ArtistDetailsDialog (~100 lines)
- `_add_alias` (lines 799-903) - 104 lines (includes inline dialog creation!)
- `_show_alias_menu` (lines 905-926) - 21 lines
- `_add_member` (lines 960-981) - 21 lines
- `_show_member_menu` (lines 983-992) - 9 lines

### PublisherDetailsDialog (~50 lines)
- `_add_child` (lines 366-394) - 28 lines
- `_show_child_context_menu` (lines 338-352) - 14 lines
- `_remove_child_link` (lines 354-364) - 10 lines
