# Architectural Proposal: Metadata Editor

## Objective
Transition from view-only metadata display to a robust editing interface.

---

## 📍 Phase 1: Inline Edit (Quick Win)

**Goal:** Make the existing `MetadataViewerDialog` editable.

**Scope:**
- Cells in the "Library (Database)" column become editable
- Visual feedback: Orange = modified, Red = conflict with file
- "Apply" button commits changes

**Implementation:**
- Set `QTableWidget` cells to editable
- Track changes in local dictionary (staging)
- On Apply: call `MetadataService.write_tags()`

**Complexity:** 2 · **Estimate:** 1 day

### Checklist
- [ ] Make dialog cells editable
- [ ] Add staging dictionary for unsaved changes
- [ ] Visual indicators (orange/red)
- [ ] Apply button with save logic

---

## 📍 Phase 2: Side Panel (Feature)

**Goal:** Collapsible panel on the right side of MainWindow.

**Scope:**
- Single-track selection: shows all fields
- Fields driven by Field Registry
- Progressive disclosure: Core info visible, advanced in drawer

**Implementation:**
- Add `QDockWidget` to MainWindow right side
- Connect to library selection signal
- Generate widgets from Registry (`is_editable=True`)

**Complexity:** 3 · **Estimate:** 2-3 days

**Depends on:** Field Registry

### Checklist
- [ ] Create `MetadataPanel` widget
- [ ] Add as dock widget to MainWindow
- [ ] Connect to selection change
- [ ] Generate fields from Registry
- [ ] Core vs Advanced collapsible sections

---

## 📍 Phase 3: Bulk Edit (Advanced)

**Goal:** Multi-select editing with smart operations.

**Scope:**
- Multi-track: identical values shown, different = "Multiple Values"
- Collection operations: Overwrite, Append, Remove modes
- All edits grouped under single `BatchID` in Transaction Log

**Implementation:**
- Extend Side Panel for multi-selection
- Mode toggle (Overwrite/Append/Remove)
- Batch transaction wrapping

**Complexity:** 4 · **Estimate:** 3-4 days

**Depends on:** Side Panel, Transaction Log

### Checklist
- [ ] Multi-selection detection
- [ ] "Multiple Values" placeholder
- [ ] Mode toggle buttons
- [ ] Append/Remove logic for list fields
- [ ] BatchID grouping for undo

---

## Radio Timing Fields
Per `plan_database.md`, the editor must handle:
- `CueIn` / `CueOut` (trim silence)
- `Intro` (countdown for DJs)
- `HookIn` / `HookOut` (preview hooks)
- `Type` dropdown (Song, Jingle, Spot, etc.)

*These are added to the Registry and appear in the panel automatically.*

---

## Design Notes
- **Glassmorphism:** Semi-transparent panel with frosted background
- **Staging Indicators:** Orange dots next to modified fields
- **Typography:** Inter or San Francisco, high-contrast for studio use
