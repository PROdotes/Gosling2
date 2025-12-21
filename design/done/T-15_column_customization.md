---
tags:
  - layer/ui
  - domain/table
  - status/done
  - type/task
  - size/small
links:
  - "[[PROPOSAL_LIBRARY_VIEWS]]"
  - "[[IDEA_column_loadouts]]"
---
# Column Customization

**Task ID:** T-15  
**Layer:** UI  
**Score:** 8  
**Status:** ✅ Done (Dec 18, 2024)

---

## Summary

Let users reorder columns, show/hide columns, and save layouts as presets.

---

## Requirements

### Core (MVP)
- [x] Drag columns to reorder
- [ ] Right-click header → show/hide columns
- [ ] Save column order + visibility to SettingsManager
- [ ] Restore on app launch

### Optional (Phase 2)
- [ ] Loadouts: Named presets (e.g., "Editing", "Browsing")
- [ ] "Reset to Default" option

---

## Implementation

### 1. Enable Column Reordering (1 line)

In `LibraryWidget.__init__()`:
```python
self.table.horizontalHeader().setSectionsMovable(True)
```

### 2. Save Column Order on Move

Connect to the `sectionMoved` signal:
```python
header = self.table.horizontalHeader()
header.sectionMoved.connect(self._on_column_moved)

def _on_column_moved(self, logical_index: int, old_visual: int, new_visual: int):
    """Save column order when user drags a column."""
    order = [header.logicalIndex(i) for i in range(header.count())]
    self.settings.set_value("library/column_order", order)
```

### 3. Save Column Visibility

```python
def _save_column_visibility(self):
    """Save which columns are hidden."""
    hidden = []
    for i in range(header.count()):
        if header.isSectionHidden(i):
            hidden.append(i)
    self.settings.set_value("library/hidden_columns", hidden)
```

### 4. Restore on Startup

In `LibraryWidget._init_table()`:
```python
def _restore_column_layout(self):
    # Restore order
    order = self.settings.get_value("library/column_order", [])
    if order:
        for visual_idx, logical_idx in enumerate(order):
            current_visual = header.visualIndex(logical_idx)
            header.moveSection(current_visual, visual_idx)
    
    # Restore visibility
    hidden = self.settings.get_value("library/hidden_columns", [])
    for col_idx in hidden:
        header.hideSection(col_idx)
```

### 5. Context Menu for Show/Hide

```python
header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
header.customContextMenuRequested.connect(self._show_header_context_menu)

def _show_header_context_menu(self, pos: QPoint):
    menu = QMenu(self)
    
    for i in range(header.count()):
        col_name = self.model.headerData(i, Qt.Orientation.Horizontal)
        action = menu.addAction(col_name)
        action.setCheckable(True)
        action.setChecked(not header.isSectionHidden(i))
        action.triggered.connect(lambda checked, idx=i: self._toggle_column(idx, checked))
    
    menu.addSeparator()
    menu.addAction("Reset to Default", self._reset_columns)
    
    menu.exec(header.mapToGlobal(pos))

def _toggle_column(self, index: int, visible: bool):
    if visible:
        header.showSection(index)
    else:
        header.hideSection(index)
    self._save_column_visibility()
```

---

## Settings Structure (Loadout-Ready)

Structure designed for future loadout support (see [[IDEA_column_loadouts]]):

```json
{
  "library/layouts": {
    "_active": "default",
    "default": {
      "columns": {
        "order": [0, 2, 1, 3, 4, 5, 6, 7, 8],
        "hidden": [6, 7, 8]
      }
    }
  }
}
```

**Key design decisions:**
- `order` includes ALL columns (even hidden ones keep their position)
- When unhiding column 2, it returns to its saved position, not the end
- Nested under `columns` so loadouts can later add `splitters`, `window`, etc.

**MVP Implementation:**
- Always read/write to `"default"` layout
- `_active` always set to `"default"`
- Future loadout feature just adds more named entries + UI to switch

---

## Checklist

### Setup
- [x] Add `setSectionsMovable(True)` to header init

### Persistence
- [x] Connect `sectionMoved` signal
- [x] Implement `_save_column_layout()` (was `_save_column_order`)
- [x] Implement `_load_column_layout()` (was `_restore_column_layout`)
- [x] Call restore on widget init (via `_load_column_visibility_states`)

### Context Menu
- [x] Enable custom context menu on header (already existed)
- [x] Build menu with checkable column names (already existed)
- [x] Implement `_toggle_column_visibility()` (updated to use new format)
- [x] Add "Reset to Default" action

### Testing
- [x] Test: Settings saved as nested structure under `library/layouts`
- [x] Test: Order array always includes all columns (never partial)
- [x] Test: Hidden column position preserved (hide 2 in [1,2,3], unhide → still at position 2)
- [x] Test: Multiple named layouts can be saved
- [x] Test: Drag column, restart app, order persists ✓
- [x] Test: Hide column, restart app, still hidden ✓
- [x] Test: Reset to default restores original layout ✓

### UX Enhancements (Bonus)
- [x] Custom `DropIndicatorHeaderView` with visual drop line
- [x] Semi-transparent drag preview
- [x] Context menu ordered by visual column position

---

## Files to Modify

| File | Changes |
|------|---------|
| `library_widget.py` | Add all column customization logic |
| `settings_manager.py` | No changes needed (uses existing API) |

---

## Estimate

| Task | Time |
|------|------|
| Enable reordering | 5 min |
| Save/restore order | 30 min |
| Context menu | 45 min |
| Testing | 30 min |
| **Total** | **~2 hours** |

---

## Links

- [[PROPOSAL_LIBRARY_VIEWS]] — Phase 3 (Column Customization)
