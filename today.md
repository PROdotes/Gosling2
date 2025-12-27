# 📅 Daily Plan: Synchronization & Next Steps

**Date**: December 27, 2025
**Driver**: Antigravity
**Focus**: **State Discovery & Documentation Recovery**

---

## 🍳 Breakfast Session (Dec 27, 09:45)

### Fast Wins Delivered:
1.  **UI Polish (T-53)**:
    *   **Icon**: Swapped to SVG (`app_icon.svg`).
    *   **Issue**: SVG renders very small. Needs `QIcon` scaling fix or PNG export.

### ⚠️ Technical Debt Check:
*   **Distributed Colors**: The user noted that colors are defined in multiple places (`LibraryDelegate.TYPE_COLORS`, `Yellberus.FieldDef.color`, `FilterWidget` zone logic).
    *   *Action*: Need to unify these color definitions into a single "Theme Service" or "Visual Registry" to avoid mismatch.

### 🧠 To Explain Later (At Work):
1.  **Renaming Logic**:
    *   It loops *after* the save.
    *   Checks: `is_done=True` **AND** `current_path != target_path`.
    *   If Mismatch: Pops Dialog ("Rename X files?").
    *   If No: Saves data but leaves file in old place.
    *   If Yes: Moves file and updates DB path.
    *   *Note*: If you say "No", it will ask again next time you save (Nagware), because the path still mismatches.

### 💡 New Ideas:
*   **Settings Entry (T-57)**: Move the App Icon to Top-Left and use it as the button to open Settings.

### Next Priority:
*   **T-46 Proper Album Editor**: The big meal.

---

## 🧹 Afternoon Cleanup & Fixes (15:00)

### 1. Codebase Hygiene
- **Deleted Legacy Files**: Removed `SongController.java`, `debug_db_check.py`, and 10+ `.bak` files.
- **Documentation Repair**: Restored `TODAY.md` from corruption and removed hallucinated "Spy Button" (T-51) features.

### 2. UI Fixes & Polish
- [x] **T-53 App Icon**:
    - Fixed `app_icon.svg` viewBox (400x340) to resolve "tiny icon" issue.
    - Switched `app.py` to load `.svg` resource.
- [x] **T-57 Settings Entry Point**:
    - Split Window Header into **Icon Button** (Settings Trigger) and **Title Label** (Drag Handle).
    - Prevents accidental clicks when dragging the window.
    - Styled the button with hover effects (`theme.qss`).
- [x] **Filter Tree**:
    - Default collapsed state for all groups (including Status/Triage).

---

## 🧭 The Plan

### Phase 1: Documentation Repair
*   [x] **Update `today.md`**: Reset to accurate state (Dec 27).
*   [x] **Review `SidePanelWidget`**: Confirm its current capabilities to identify what lays ahead.

### Phase 2: Feature Work (Executed)
*   [x] **Status Visuals (Editor)**:
    *   Replaced "Done" Checkbox with **Status Pill** (Green "AIR" / Gray "PENDING").
*   [x] **Proper Album Editor (T-46)**:
    *   **Repository**: Added `search()` method to `AlbumRepository`.
    *   **Dialog**: Created `AlbumManagerDialog` (Search/Create/Select).
    *   **Integration**: Connected to `SidePanelWidget`.
*   [x] **Renaming Service Refactor**:
    *   Switched from hardcoded `rules.json` to `SettingsManager` patterns.
    *   Implemented proper token replacement (`{Artist}`, `{Album}`, `{Title}`, etc.).

### Phase 3: Verification (COMPLETE)
*   [x] **Album Manager**: FIXED. Resolved crashes and model mismatches. Added auto-population and autoselect.
*   [x] **Renaming Logic**: Verified. Network paths (`\\ONAIR\B\Songs`) and specialized genre rules (X-Mas, Acoustic, Club) are operational.

---

## 📝 Sessions Summary (Dec 27)
- **Album Fixes**: Stabilized `AlbumManagerDialog` with smart population and internal ID tracking.
- **Renaming Parity**: Restored legacy folder mappings in `rules.json` (akustika, clubbing).
- **New Task**: **T-63** added (Publisher Picker) to maintain data integrity.

**Next Priority**: 
1. **T-62**: Async Background Save (Prevent UI freeze during file moves).
2. **T-61**: Universal Tag Picker.
3. **Refactor**: Clean up `SidePanelWidget` staging logic.
