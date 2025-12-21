# T-18: Column Resilience & Persistence

**Status**: ✅ Complete (2025-12-21)  
**Parent Task**: T-17 Unified Artist View (Scope Extension)

## 🚨 The Problem
During T-17, two critical UI bugs emerged:
1.  **Ghost Columns**: Columns explicity hidden (e.g. `performers`, `groups`) would reappear after restarting the app because index-based persistence was fragile.
2.  **Reset-on-Filter**: When a user applied a filter, the table model was cleared. This caused `resizeColumnsToContents()` to trigger on empty/new data, obliterating any manual resizing the user had performed.

## 🛠️ The Solution

### 1. Robust Persistence (Named-Based)
We abandoned the index-based approach in favor of a robust Dictionary Map keyed by Field Name for both visibility and visual ordering.
- **Key**: `library/column_layouts` (Ensures a clean slate and logical naming).
- **Data Shape**:
  ```json
  {
      "order": ["title", "artist", "bpm"...],
      "hidden": { "is_done": true, "performers": true },
      "widths": { "title": 350, "artist": 200 }
  }
  ```
- **Logic**: `_load_column_layout` matches fields by NAME. If indices shift (due to registry changes), the settings still apply correctly to the right fields.

### 2. Atomic Lifecycle (The "Population Hook")
To prevent layout resets during search or filtering, we centralized all model updates into a single atomic sequence in `_populate_table`:
1.  **Freeze**: Set `_suppress_layout_save = True` (Blocks Qt's automatic signals from talking to the registry).
2.  **Snapshot**: `_save_column_layout()` (Captures the exact current widths/order before the table is destroyed).
3.  **Wipe & Build**: `model.clear()` and repopulate the data.
4.  **Restore**: `_load_column_layout()` (Re-applies the saved snapshot by field identity).
5.  **Thaw**: `_suppress_layout_save = False` (Ready for manual user actions again).

This ensures the user perceives zero change in layout, even though the entire view was destroyed and recreated.

## 📦 Components Modified

### `SettingsManager`
- Updated signature of `set_column_layout` to accept `widths: dict`.
- Updated docstring to emphasize the necessity of "Save Before Clear".

### `LibraryWidget`
- **`_save_column_layout`**: Now iterates `table_view.columnWidth(i)` and saves to `widths` map.
- **`_load_column_layout`**: Reads `widths` map and applies `setColumnWidth(i, w)`.
- **`load_library`**: Moved `resizeColumnsToContents()` to run *before* loading visibility.
- **Resize Signals**: Connected `header.sectionMoved` and `header.sectionResized` to `_save_column_layout` for immediate persistence.

## 📝 Future Notes
- Any new component doing similar list updates must follow the **Save -> Clear -> Populate -> Load** pattern to preserve user state.
