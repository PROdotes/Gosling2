---
tags:
  - layer/ui
  - domain/tags
  - status/planned
  - type/widget
  - size/medium
links:
  - "[[PROPOSAL_FIELD_REGISTRY]]"
  - "[[PROPOSAL_METADATA_EDITOR]]"
---
# Architectural Proposal: Tag Editor Widget

## Objective
Create a reusable UI component for managing many-to-many relationships (Genres, Performers, Composers) with a modern chip/token interface.

---

## 📍 Phase 1: Basic Chips (Foundation)

**Goal:** Visual chip input with core interactions.

**Scope:**
- Text entry converts to graphical chips on Enter
- Chips display as rounded rectangles with 'X' button
- Backspace from empty input deletes last chip

**Implementation:**
- `QFrame` mimicking a `QLineEdit`
- `FlowLayout` for wrapping chips to next line
- `QChip` widget = `QLabel` + `QToolButton`

**Complexity:** 2 · **Estimate:** 1-2 days

### Checklist
- [ ] Implement `FlowLayout` (PyQt recipe)
- [ ] Create `QChip` visual component
- [ ] Build `TagInputWidget` container
- [ ] Handle Enter to create chip
- [ ] Handle Backspace to delete last
- [ ] Handle X button to remove specific

### Visual Style
- **Label-style chips:** Colored background, rounded corners (pill shape)
- Remove button (x) inside the chip
- Semantic colors (e.g., green for Language, blue for Genre) as seen in mockups

### Interaction
- Click "Add Tag" → Opens chip input/dropdown
- Type and filtered list appears
- Enter to create/add
- Click 'x' on chip to remove specific

---

## 📍 Phase 2: Smart Chips (Feature)

**Goal:** Database integration with autocomplete and creation workflow.

**Scope:**
- `QCompleter` with genre/performer suggestions
- ID normalization: widget stores IDs, displays names
- Create-new workflow when typing unknown value

**Implementation:**
- Connect to `BaseRepository` for lookup
- `set_ids([10, 45])` → displays "House", "Techno"
- `get_ids()` → returns `[10, 45]`
- Prompt on unknown: "Create new Genre 'Space Jazz'?"

**Complexity:** 3 · **Estimate:** 2 days

**Depends on:** Basic Chips, Field Registry

### Checklist
- [ ] Add `QCompleter` integration
- [ ] Connect to Repository for ID/Name lookup
- [ ] Implement `set_ids()` / `get_ids()`
- [ ] Unknown value detection
- [ ] Create-new confirmation dialog
- [ ] `get_text()` fallback for ID3 export

---

## Usage in Metadata Editor
```python
# In Registry logic
if field.name == "genres":
    widget = TagInputWidget(repository=GenreRepository)
    widget.set_allow_creation(True)
```

The editor generates this widget automatically for fields marked as `RELATIONAL` + `MANY_TO_MANY` in the Registry.
