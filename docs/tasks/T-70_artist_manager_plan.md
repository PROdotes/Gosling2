# T-70: Artist Manager & Chip-Based Selector

## 🎯 Objective

Create a **database-backed Artist Manager** with a new **ChipTrayWidget** for the Side Panel. This replaces free-text artist entry with a structured, searchable, editable system that supports:

- **Unified Artist Identity** (Aliases, Group Memberships)
- **Type Enforcement** (`person` or `group`)
- **Chip-based UI** for multi-artist fields (reusable for Albums/Tags later)

**References:**
- `docs/DATABASE.md` — Schema rules for Contributors
- `src/presentation/dialogs/publisher_manager_dialog.py` — UI pattern to mirror
- `src/data/repositories/contributor_repository.py` — Existing identity graph logic

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Side Panel                                                                  │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Performers: [👤 Elvis ×] [👥 The Beatles ×]  [ + ]                      │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                ↓ click chip body    ↓ click ×        ↓ click +              │
│         ArtistDetailsDialog    Confirm → Unlink   ArtistPickerWidget       │
└─────────────────────────────────────────────────────────────────────────────┘

ArtistPickerWidget (Popup)          ArtistDetailsDialog (Modal)
┌───────────────────────────┐       ┌────────────────────────────────────┐
│ SELECT OR CREATE ARTIST   │       │ ARTIST: The Beatles                │
├───────────────────────────┤       ├────────────────────────────────────┤
│ 🔍 [Find Artist...     ]  │       │ Name: [The Beatles            ]    │
├───────────────────────────┤       │ Sort:  [Beatles, The          ]    │
│ 👤 Elvis Presley          │       │ Type:  (•) Group  ( ) Person       │
│ 👥 The Beatles       ←    │       ├────────────────────────────────────┤
│ 👤 Dua Lipa               │       │ MEMBERS: (only if Group)           │
│ 👤 John Lennon            │       │ ┌──────────────────────────────┐   │
├───────────────────────────┤       │ │ 👤 John Lennon               │   │
│ [ Create New Artist (+) ] │       │ │ 👤 Paul McCartney            │   │
└───────────────────────────┘       │ │ 👤 George Harrison           │   │
        ↓ single-click              │ └──────────────────────────────┘   │
   Chip added, popup closes         │ [ + Add Member ]                   │
                                    ├────────────────────────────────────┤
                                    │ ALIASES:                           │
                                    │ ┌──────────────────────────────┐   │
                                    │ │ The Fab Four                 │   │
                                    │ │ Beatles                      │   │
                                    │ └──────────────────────────────┘   │
                                    │ [ + Add Alias ]                    │
                                    ├────────────────────────────────────┤
                                    │          [ Cancel ]  [ Save ]      │
                                    └────────────────────────────────────┘
```

---

## 📦 Component Specifications

### 1. `ChipTrayWidget` (Generic, Reusable)
**File:** `src/presentation/widgets/chip_tray_widget.py`

A wrapping **Flow Layout** tray of removable chips with an Add button. Designed for narrow side panels.

#### Visual Layout (Flow/Wrap)
```
┌──────────────────────────────────────────┐
│ [🎤 The Beatles ×] [🎤 Elvis Presley ×]  │
│ [🎤 Dua Lipa ×] [ + ]                    │  ← Wraps to next line
└──────────────────────────────────────────┘
```

#### Multi-Selection Behavior (Batch Edit)
When multiple songs are selected:
- **Common Identity**: If all selected songs share an artist, show as a normal chip.
- **Mixed Identities**: If artists differ across selection, show common chips + a special `[ 🔀 N Mixed ]` chip.
- **Header Label**: Update to `PERFORMERS (3 MIXED)` to clarify state.

#### API
```python
class ChipTrayWidget(QWidget):
    # Signals
    chip_clicked = pyqtSignal(int, str)          # (entity_id, label) → Edit
    chip_remove_requested = pyqtSignal(int, str) # (entity_id, label) → Remove
    add_requested = pyqtSignal()                 # → Open picker
    
    def __init__(self, 
                 confirm_removal: bool = True,
                 confirm_template: str = "Remove '{label}'?",
                 add_tooltip: str = "Add",
                 parent=None): ...
    
    def add_chip(self, entity_id: int, label: str, icon: QIcon = None, is_mixed: bool = False) -> None: ...
    def set_chips(self, items: List[Tuple[int, str, Optional[QIcon], bool]]) -> None: ...
```

#### Interaction Table
| Action | Zone | Result |
|--------|------|--------|
| Click | Chip body | Emit `chip_clicked` → Parent opens editor |
| Click | × button | If `confirm_removal`: show dialog → Emit `chip_remove_requested` |
| Click | + button | Emit `add_requested` → Parent opens picker |
| Hover | Chip | Subtle highlight, tooltip if label truncated |

#### Implementation Detail: Layout
**MUST** use a **FlowLayout** (wrapping) rather than a horizontal box. This ensures the Side Panel vertical rhythm is preserved and avoids horizontal scrollbars.

#### Configuration
| Use Case | `confirm_removal` | Why |
|----------|-------------------|-----|
| Artist Chips | `True` | Persistent link, accidental removal is bad |
| Album Chips | `True` | Same reason |
| Filter Chips | `False` | Transient, quick dismissal expected |

---

### 2. `ArtistPickerWidget` (Single-Select Popup)
**File:** `src/presentation/dialogs/artist_manager_dialog.py`

Mirrors `PublisherPickerWidget`. Embedded in a popup triggered by the chip tray's `+` button.

#### Layout
```
┌─────────────────────────────────────┐
│  SELECT OR CREATE ARTIST            │
├─────────────────────────────────────┤
│  🔍 [Find Artist...              ]  │  ← Live search filter
├─────────────────────────────────────┤
│  👤 Elvis Presley                   │
│  👥 The Beatles              ← sel  │  ← Type icons (Person/Group)
│  👤 Dua Lipa                        │
│  👤 John Lennon                     │
├─────────────────────────────────────┤
│  [ Create New Artist (+) ]          │  ← Toggles to "Edit Selected"
└─────────────────────────────────────┘
```

#### Behavior
| Action | Result |
|--------|--------|
| Single-click list item | Emit `artist_selected(id, name)`, close popup, add chip |
| Double-click list item | Open `ArtistDetailsDialog` for that artist |
| Click "Create New" | Open `ArtistCreatorDialog` → On save, add chip |
| Click "Edit Selected" | Open `ArtistDetailsDialog` for selected item |
| Right-click item | Context menu: "Edit...", "Delete" |
| Type in search box | Live filter list by name + aliases |

#### Signals
```python
artist_selected = pyqtSignal(int, str)  # (contributor_id, name)
```

---

### 3. `ArtistCreatorDialog` (Quick Add)
**File:** `src/presentation/dialogs/artist_manager_dialog.py`

Minimal dialog for quickly adding a new artist with required fields.

#### Layout
```
┌────────────────────────────────────┐
│         NEW ARTIST                 │
├────────────────────────────────────┤
│  Name: [                        ]  │
│                                    │
│  Type:  (•) Person   ( ) Group     │  ← Radio buttons, default Person
├────────────────────────────────────┤
│       [ Cancel ]    [ Create ]     │
└────────────────────────────────────┘
```

#### Logic
- **Name** → Required, used for `ContributorName`
- **Type** → `person` (default) or `group`. **No heuristics** — user must choose.
- **SortName** → Auto-generated by repository (`_generate_sort_name`)
- On Create → Calls `ContributorRepository.create()` → Returns new `Contributor`

---

### 4. `ArtistDetailsDialog` (Full Editor)
**File:** `src/presentation/dialogs/artist_manager_dialog.py`

The "Pro" editor for complete artist management.

#### Layout (Varies by Type)
```
┌────────────────────────────────────────────────┐
│  ARTIST: The Beatles                           │
├────────────────────────────────────────────────┤
│  Name:      [The Beatles                    ]  │
│  Sort Name: [Beatles, The                   ]  │
│  Type:      (•) Group   ( ) Person             │  ← Safety Gate for changes
├────────────────────────────────────────────────┤
│  MEMBERS:  (visible only if Type = Group)      │
│  ┌────────────────────────────────────────┐    │
│  │ 👤 John Lennon                         │    │  ← QListWidget
│  │ 👤 Paul McCartney                      │    │  ← Double-click → Open their dialog
│  │ 👤 George Harrison                     │    │  ← Right-click → "Remove from group"
│  │ 👤 Ringo Starr                         │    │
│  └────────────────────────────────────────┘    │
│  [ + Add Member ]                              │  ← Opens Person picker (not Group)
├────────────────────────────────────────────────┤
│  GROUPS:  (visible only if Type = Person)      │
│  ┌────────────────────────────────────────┐    │
│  │ 👥 The Beatles                         │    │  ← Groups this person belongs to
│  │ 👥 Plastic Ono Band                    │    │  ← Double-click → Open group dialog
│  └────────────────────────────────────────┘    │
│  [ + Add to Group ]                            │  ← Opens Group picker (not Person)
├────────────────────────────────────────────────┤
│  ALIASES:                                      │
│  ┌────────────────────────────────────────┐    │
│  │ The Fab Four                           │    │  ← QListWidget of alias strings
│  │ Beatles                                │    │  ← Double-click → Inline rename
│  └────────────────────────────────────────┘    │  ← Right-click → "Delete Alias"
│  [ + Add Alias ]                               │  ← Opens simple text input dialog
├────────────────────────────────────────────────┤
│               [ Cancel ]    [ Save ]           │
└────────────────────────────────────────────────┘
```

#### Type-Switching Safety Gate
If the user attempts to switch Type (Group ↔ Person):
1. Dialog counts existing memberships via `Repo.get_member_count()`.
2. If count > 0, show Warning: *"Changing this Group to a Person will remove N current members. Are you sure?"*
3. Only proceed if user confirms.

#### Identity Conflict & Alias Protection
- Use `Repo.validate_identity(name)` before saving.
- If name exists as an Alias of another artist, block creation and suggest linking instead.

---

### 5. `ContributorRepository` Upgrade
**File:** `src/data/repositories/contributor_repository.py`

Add full CRUD operations.

#### New Methods
```python
def create(self, name: str, type: str = 'person', sort_name: str = None) -> Contributor:
    """Create new contributor. Auto-generates sort_name if not provided."""
    
def update(self, contributor: Contributor) -> bool:
    """Update name, sort_name, type."""
    
def delete(self, contributor_id: int) -> bool:
    """Delete contributor and cascade to aliases, memberships, roles."""
    
def search(self, query: str) -> List[Contributor]:
    """Search by name or alias (case-insensitive, partial match)."""
    
def get_or_create(self, name: str, type: str = 'person') -> Tuple[Contributor, bool]:
    """Get existing or create new. Returns (contributor, was_created)."""

def get_by_id(self, contributor_id: int) -> Optional[Contributor]:
    """Fetch single contributor by ID."""

def get_members(self, group_id: int) -> List[Contributor]:
    """Get all Person members of a Group."""

def get_groups(self, person_id: int) -> List[Contributor]:
    """Get all Groups a Person belongs to."""

def add_member(self, group_id: int, person_id: int) -> bool:
    """Add a Person to a Group."""

def remove_member(self, group_id: int, person_id: int) -> bool:
    """Remove a Person from a Group."""

def get_aliases(self, contributor_id: int) -> List[str]:
    """Get all alias names for a contributor."""

def add_alias(self, contributor_id: int, alias: str) -> int:
    """Add an alias. Returns AliasID."""

def update_alias(self, alias_id: int, new_name: str) -> bool:
    """Rename an alias."""

def delete_alias(self, alias_id: int) -> bool:
    """Delete an alias."""

def validate_identity(self, name: str) -> Tuple[bool, str]:
    """Check if name exists as Primary or Alias. Returns (is_conflict, details)."""

def get_member_count(self, contributor_id: int) -> int:
    """Return count of associated group memberships."""

### 🛡️ Identity Safeguards
To prevent fragmented data (e.g., "The Beatles" existing as both a name and an alias for a different ID):

| Scenario | Logic | Result |
|----------|-------|--------|
| **Create "X"** | "X" is already a `ContributorName` | Return existing ID |
| **Create "X"** | "X" is already an `AliasName` for ID 5 | Return ID 5 (Avoids duplication) |
| **Rename "X" to "Y"**| "Y" exists as an Alias for "Z" | Error: "Identity Conflict" |
| **Change Type** | Members exist for this ID | Prompt Safety Gate (Warning) |
```

#### Sort Name Logic
```python
def _generate_sort_name(self, name: str) -> str:
    """
    Generate sort-friendly name.
    Examples:
    - "The Beatles" → "Beatles, The"
    - "A Flock of Seagulls" → "Flock of Seagulls, A"
    - "DJ Khaled" → "DJ Khaled" (no change)
    """
    for article in ['The ', 'A ', 'An ']:
        if name.startswith(article):
            return f"{name[len(article):]}, {article.strip()}"
    return name
```

---

### 6. Side Panel Integration
**File:** `src/presentation/widgets/side_panel_widget.py`

Replace the current Artist text field with a `ChipTrayWidget`.

#### Before (Current)
```python
self.txt_performer = GlowLineEdit()  # Free text
```

#### After (New)
```python
self.chip_performers = ChipTrayWidget(
    confirm_removal=True,
    confirm_template="Remove '{label}' from this song?",
    add_tooltip="Add Performer"
)
self.chip_performers.chip_clicked.connect(self._open_artist_details)
self.chip_performers.chip_remove_requested.connect(self._remove_performer)
self.chip_performers.add_requested.connect(self._open_artist_picker)
```

#### Handler Methods
```python
def _open_artist_picker(self):
    """Open ArtistPickerWidget popup."""
    popup = ArtistPickerPopup(self.contributor_repo, parent=self)
    popup.artist_selected.connect(self._on_artist_selected)
    popup.exec()

def _on_artist_selected(self, artist_id: int, artist_name: str):
    """Add selected artist chip and link to song."""
    # 1. Add chip to UI
    icon = self._get_type_icon(artist_id)
    self.chip_performers.add_chip(artist_id, artist_name, icon)
    # 2. Stage the link for save
    self._staged_performers.add(artist_id)
    self._mark_dirty()

def _open_artist_details(self, artist_id: int, name: str):
    """Open full ArtistDetailsDialog."""
    artist = self.contributor_repo.get_by_id(artist_id)
    dialog = ArtistDetailsDialog(artist, self.contributor_repo, parent=self)
    if dialog.exec():
        self._refresh_performer_chips()

def _remove_performer(self, artist_id: int, name: str):
    """Unlink performer from song."""
    self.chip_performers.remove_chip(artist_id)
    self._staged_performers.discard(artist_id)
    self._mark_dirty()
```

---

### 7. Search Integration (Performance Optimized)
**File:** `src/presentation/models/library_filter_proxy_model.py`

Use `resolve_identity_graph()` for artist searches, but optimized to prevent UI lag.

#### The "Once-per-Search" Pattern
1. **User Types**: GlowLineEdit emits `textChanged`.
2. **Resolution**: `LibraryWidget` calls `repo.resolve_identity_graph(query)` **once**.
3. **Caching**: Store the resulting `Set[str]` in the Proxy Model as `self._active_identity_filter`.
4. **Filtering**: `filterAcceptsRow` performs a high-speed $O(1)$ set lookup.

```python
def filterAcceptsRow(self, source_row, source_parent):
    if not self._active_identity_filter:
        return True
    
    # Fast set lookup across song performers
    song_artists = self._get_song_artist_names(source_row)
    return any(name in self._active_identity_filter for name in song_artists)
```

---

## 🛠️ Robustness & Performance Refinements

- **Flow Layout**: Chips wrap to match width, ensuring Side Panel vertical rhythm.
- **Identity Protection**: Prevent creating "The Beatles" if it exists as an alias for "Beatles".
- **Safety Gates**: Group ↔ Person switching requires confirmation if members exist.
- **Glyph Iconography**: Use `QPainter` or SVGs for 👤/👥 to ensure "Pro Console" glow scales perfectly.
- **Cached Search**: Identity expansion happens once per keystroke, not for 1,000+ rows separately.

---

## 📜 Implementation Steps

### Phase 1: Foundation (~3.5h)
| # | Task | Est. | Status |
|---|------|------|--------|
| 1.1 | ✅ Fix `Contributor` model (add `type` field) | 0.5h | ✅ Done |
| 1.2 | ✅ Create `ChipTrayWidget` (Flow Layout) | 1.5h | ✅ Done |
| 1.3 | ✅ Add CRUD to `ContributorRepository` | 1.5h | ✅ Done |

### Phase 2: Dialogs (~4.0h)
| # | Task | Est. | Status |
|---|------|------|--------|
| 2.1 | Create `ArtistCreatorDialog` | 1.0h | ✅ Done |
| 2.2 | Create `ArtistPickerWidget` (mirror PublisherPickerWidget) | 1.5h | ✅ Done |
| 2.3 | Create `ArtistDetailsDialog` with Member/Alias management | 1.5h | ✅ Done |

### Phase 3: Integration (~3.5h)
| # | Task | Est. | Status |
|---|------|------|--------|
| 3.1 | ✅ Replace Side Panel Artist field with `ChipTrayWidget` | 1.5h | ✅ Done |
| 3.2 | ✅ Wire up chip signals to picker/editor/save flow | 1.0h | ✅ Done |
| 3.3 | ✅ Integrate `resolve_identity_graph()` with filter proxy | 1.0h | ✅ Done |

### Phase 4: Polish (~1.0h)
| # | Task | Est. | Status |
|---|------|------|--------|
| 4.1 | ✅ Add type icons (Person 👤 / Group 👥) | 0.5h | ✅ Done |
| 4.2 | ✅ QSS styling for chips (Pro Console aesthetic) | 0.5h | ✅ Done |

**Total Estimated: ~12 hours**

---

## ⚖️ Design Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Chip vs. Concatenated Button | **Chips** | Reusable for Albums/Tags, better UX |
| Removal Confirmation | **Yes** for entity links | Prevent accidental data loss (no Undo yet) |
| Type Selection | **Manual** (no heuristics) | User must explicitly choose Person/Group |
| Associations Display | **QListWidget** | Enables double-click edit, right-click menu |
| Picker Mode | **Single-select** | Simpler, add one artist at a time |
| Popup vs. Full Dialog | **Popup** for picker | Faster workflow, less modal fatigue |

---

## 🔗 Dependencies

- ✅ `Contributors.Type` column (exists in `database.py`)
- ✅ `ContributorAliases` table (exists in `database.py`)
- ✅ `GroupMembers` table (exists in `database.py`)
- ✅ `resolve_identity_graph()` method (exists in `contributor_repository.py`)
- ⬜ `PublisherPickerWidget` pattern reference (exists, will mirror)

---

## 🧪 Test Considerations

| Area | Test Focus |
|------|------------|
| `ChipTrayWidget` | Add/remove chips, confirmation dialog, signals |
| `ContributorRepository` | CRUD operations, `get_or_create`, membership constraints |
| `ArtistDetailsDialog` | Type change with existing memberships, alias CRUD |
| Integration | Chip ↔ Picker ↔ Database round-trip |
| Search | `resolve_identity_graph` expansion in filter proxy |
