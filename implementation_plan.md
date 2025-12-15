# Implementation Plan - ZIP File Import

## Goal
Allow users to drop `.zip` files into the library. The app should automatically extract any `.mp3` files found inside the zip into the **same directory as the zip file**, then import them into the library.

## User Review Required
> [!IMPORTANT]
> **Duplicate Handling Strategy**:
> 1. **File System**: If `song.mp3` already exists in the destination folder, we **SKIP** extraction for that file (to preserve existing files).
> 2. **Database**: We use the existing `library_service.add_file` which already handles DB duplicates (likely by path or hash).

## Proposed Changes

### `src/presentation/widgets/library_widget.py`

#### [MODIFY] `dragEnterEvent`
- Allow `.zip` extension in addition to `.mp3`.

#### [MODIFY] `_process_zip_file(zip_path) -> list[str]`
**New Logic:**
1.  **Pre-check**: Open Zip, iterate all `.mp3` members.
2.  **Collision Detection**: Check if `os.path.join(base_dir, member)` exists for *any* file.
    -   If **Any Exists**:
        -   Show `QMessageBox.warning("File(s) already exist. Aborting.")`
        -   Return empty list (Do nothing).
3.  **Extraction**:
    -   If **None Exist**:
        -   Extract all MP3s.
        -   **Delete** the original `.zip` file (`os.remove(zip_path)`).
        -   Return list of extracted paths for import.

## Verification Plan

### Automated Tests
**File**: `tests/unit/presentation/widgets/test_library_widget_drag_drop.py`
**Global Mock**: Patch `QMessageBox` in the `widget` fixture to ensure no windows open during testing.

- **`test_drop_zip_extracts_and_deletes`**:
    -   Mock `os.path.exists` (False).
    -   Verify `extract` called.
    -   Verify `os.remove` called.
-   **`test_drop_zip_aborts_on_collision`**:
    -   Mock `os.path.exists` (True).
    -   Verify `extract` NOT called.
    -   Verify `os.remove` NOT called.
    -   Verify `QMessageBox.warning` called.
