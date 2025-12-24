# Changelog

All notable changes to the **Gosling2** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] - 2025-12-24

### Added
- **Side Panel Editor**: Full implementation of the metadata editor panel (Task T-12).
    - Supports single and bulk editing of all mapped Yellberus fields.
    - Implemented `FieldDef` awareness for correct widget types (Text, Checkbox, etc.).
    - Added "Staged Changes" system with explicit Save/Discard workflow.
    - Added `Ctrl+S` shortcut to trigger Side Panel save.
- **Validation System**:
    - **Strict Year Validation**: Prevents saving years < 1860 or > Current+1.
    - **ISRC Validation**: Enforces standard 12-char alphanumeric format.
    - **Unified Artist Rule**: "MARK DONE" button is disabled unless `Performers` OR `Groups` is present.
    - **Feedback**: Users receive `QMessageBox` warnings on validation failure; invalid rows remain staged.
- **Selection Resilience**:
    - Library table now preserves row selection across data reloads.
    - Fixed "Auto-Advance" interference to respect user selection.

### Changed
- **Repository Logic (Refactor)**:
    - `SongRepository._sync_publisher`: Now performs a "Clear & Replace" operation to support creating/deleting publishers cleanly.
    - `SongRepository._sync_album`: Now performs a "Clear & Replace" operation to prevent songs accumulating multiple albums.
    - `SongRepository.get_by_id` & `get_by_path`: Added missing `Genre` subquery to ensure Genre data appears in the editor.
- **Field Definitions (Yellberus)**:
    - Reordered `FIELDS` list to prioritized core metadata (Artist, Title, Album) at the top.
    - Removed duplicate logic and cleaned up old schema definitions.
- **UI Improvements**:
    - Increased font size and padding in Side Panel for better readability.
    - "MARK DONE" button is now disabled by default on load.

### Fixed
- **Crash Fixes**:
    - Fixed `AttributeError: MetadataService.FIELDS_MAP` by removing phantom reference.
    - Fixed `RuntimeError: dictionary changed size` during iteration in `clear_staged`.
    - Fixed `AttributeError: SongRepository.get_by_id` by implementing the missing method.
    - Fixed `TypeError` when comparing string years (e.g. "2028") to integers by implementing type coercion in `MainWindow`.
    - Fixed "Paranoid Validation": Removed duplicate logic checking for year 1860 in `MainWindow`.
- **Data Integrity**:
    - Fixed "Append Bug" for Publishers and Albums where editing would add new values but keep old ones.
    - Fixed missing Genre display in Side Panel.
    - **Dynamic ID3 Fix**: Patched `MetadataService` to correctly read `TCON` (Genre) and `TPUB` (Publisher) frames using dynamic lookup instead of ignoring them.
- **Workflow**:
    - **Legacy Shortcuts**: Added `Ctrl+S` (Save) and `Ctrl+D` (Toggle Done) to Side Panel.
    - **Optimistic Save Fix**: `MainWindow` now writes ID3 tags *before* DB commit to prevent "Ghost Data" on file-write failure.

## [v0.0.1] - Pre-Alpha
- Initial features...
