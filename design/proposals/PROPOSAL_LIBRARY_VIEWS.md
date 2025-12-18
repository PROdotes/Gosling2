# Architectural Proposal: Library Views

## Objective
Implement content filtering and multiple layout strategies for the music library.

---

## 📍 Phase 1: Type Tabs (Quick Win)

**Goal:** Filter library by content type (Music, Jingles, Commercials, etc.)

**Scope:**
- Horizontal tab bar at the top of the library
- Categories: `All`, `Music`, `Jingles`, `Commercials`, `Speech`
- Clicking a tab applies `WHERE Type = '...'` filter

**Implementation:**
- Add `QTabBar` or `QButtonGroup` above `LibraryWidget`
- Connect tab change signal to filter proxy
- Store last-used tab in `SettingsManager`

**Complexity:** 1 · **Estimate:** 1 day

### Checklist
- [ ] Add tab bar widget to library header
- [ ] Connect to `QSortFilterProxyModel`
- [ ] Persist selection in settings
- [ ] Add "All" option that clears filter

---

## 📍 Phase 2: View Modes (Feature)

**Goal:** Multiple layout strategies for different workflows.

**Scope:**
- **Detail View** — `QTableView`, 10+ columns, for auditing/editing
- **Grid View** — `QListView` IconMode, large album art, for browsing
- **Compact View** — Single-line rows, for playlist building

**Implementation:**
- Wrap views in `QStackedWidget`
- Share the same `LibraryModel`
- Custom `QStyledItemDelegate` for Grid card rendering
- Zoom slider for icon size (64px–256px)

**Complexity:** 4 · **Estimate:** 3-4 days

**Depends on:** Field Registry (for tooltip fields)

### Checklist
- [ ] Add view toggle buttons to library header
- [ ] Create `QStackedWidget` container
- [ ] Implement Grid delegate with album art
- [ ] Add zoom slider
- [ ] Persist view preference in settings

---

## Integration with Field Registry
- Grid View tooltips show fields marked `is_primary=True` in the Registry
- Detail View columns are generated from Registry

---

## 📍 Phase 3: Column Customization

**Goal:** Let users reorder, show/hide, and save column layouts.

**Scope:**
- Drag columns to reorder
- Right-click header to show/hide columns
- Save column order + visibility to `SettingsManager`
- **Loadouts (optional):** Multiple saved configurations (e.g., "Editing", "Browsing", "Metadata Audit")

**Implementation:**
- `QHeaderView.setSectionsMovable(True)` — Enables column dragging
- `QHeaderView.sectionMoved` signal → save order to settings
- Context menu on header → toggle visibility
- Loadouts: Store as named presets in settings

**Settings Structure:**
```json
{
  "column_layouts": {
    "_current": ["FilePath", "Name", "Performer", "Duration", "IsDone"],
    "Editing": ["Name", "Performer", "Composer", "Publisher", "IsDone"],
    "Metadata Audit": ["FilePath", "Name", "Genre", "Language", "ISRC"]
  }
}
```

**Complexity:** 2 · **Estimate:** 1-2 days

### Checklist
- [ ] Enable `setSectionsMovable(True)`
- [ ] Save column order on move
- [ ] Add context menu for show/hide columns
- [ ] Persist visibility settings
- [ ] (Optional) Loadout selector dropdown
- [ ] (Optional) "Save as Loadout" dialog

