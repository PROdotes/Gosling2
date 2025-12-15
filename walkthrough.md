# Walkthrough: Library Drag & Drop (Issue #8)

## 🎯 Goal
Enable users to drag audio files directly into the Library table to import them.
**Requirement**: Add visual feedback (Empty State label) and tests.

## 🏗️ Changes Implemented

### 1. `LibraryWidget` Updates
*   **Empty State Overlay**: Added a centered label *"Drag audio files here to import"* that appears when the library is empty.
*   **Event Filter**: Installed an event filter on `QTableView` to catch Drag/Drop events even when the table handles mouse interaction.
*   **Drag Logic**: Validates incoming drags (checks for `.mp3` extension).
*   **Drop Logic**: Imports dropped files using the existing `import_files_list` method.

### 2. New Tests
*   **File**: `tests/unit/presentation/widgets/test_library_widget_drag_drop.py`
*   **Coverage**:
    *   `test_drag_enter_valid_mp3`: Ensures MP3s are accepted.
    *   `test_drag_enter_invalid_extension`: Ensures `.txt` files are ignored.
    *   `test_empty_state_visibility_toggles`: Verifies label hides/shows based on data presence.

## 🧪 Verification Results

### Automated Tests
Ran the full widget suite:
```bash
py -m pytest tests/unit/presentation/widgets/
```
**Result**: `======= 64 passed, 6 warnings in 0.66s =======` ✅

### Manual Verification Checklist
1.  **Empty Library**: Launch app. Verify "Drag audio files..." text is centered.
2.  **Drag File**: Drag `song.mp3` over table. Verify:
    *   Cursor accepts it.
    *   **Border turns Green**.
3.  **Drop File**: Release. Verify:
    *   Song appears in table.
    *   Empty Label disappears.
    *   **Popup shows "Imported X file(s)"**.
4.  **ZIP Import (Success)**:
    *   Create `test.zip` with `new_song.mp3`.
    *   Drop `test.zip`.
    *   Verify: `new_song.mp3` appears in folder, `test.zip` is **DELETED**, song appears in app.
5.  **ZIP Import (Collision)**:
    *   Create `test.zip` with `existing_song.mp3` (where `existing_song.mp3` is already in folder).
    *   Drop `test.zip`.
    *   Verify: **Warning Popup** appears, `test.zip` is **NOT DELETED**, file is **NOT overwritten**.
6.  **Bad File**: Drag `notes.txt`. Verify cursor rejects it (no border).

### Automated Tests coverage
-   **Security**: `test_zip_slip_prevention` ensures files with `..` are ignored.
-   **Robustness**: `test_bad_zip_file` and `test_delete_zip_error` ensure app doesn't crash on corrupt files or locked file errors.
