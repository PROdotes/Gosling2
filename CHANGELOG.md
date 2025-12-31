# Changelog

All notable changes to the **Gosling2** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] - 2025-12-24

### Added
- **Split-Search Module**: Replaced singular 'WEB' button with a dedicated 'Affinity' module (Magnifier + Dropdown) for clearer separation of Search Action vs Provider Selection.
- **Validation Feedback**: Hovering over the disabled 'PENDING' button now displays a specific checklist of missing fields or errors.
- **Window State Logic**: Title bar icons now react to OS window state changes (Maximize/Restore).
- **GlowFactory Refactor**: Split monolithic `glow_factory.py` into modular package `src/presentation/widgets/glow/`. ([T-47])
- **GlowFactory Refactor (T-47)**:
    - **Modular Architecture**: Split monolithic `glow_factory.py` into `glow/` package (`base`, `button`, `line_edit`, `combo_box`, `led`).
    - **Visual Unity**: Unified interaction states (Amber Border on Hover/Focus) across Inputs and Buttons.
    - **GlowLED**: Implemented dynamic status indicator component with property-driven animation.
    - **Fixes**: Resolved Dropdown focus-dimming ("Sticky Glow"), Missing Arrow icons (Absolute Path), and "Clown Conflict" on colored buttons.
- **T-55: The Chip Bay (Visuals)**:
    - Implemented "Pro Audio" aesthetic for Filter Chips (Chunky, Tactile, Gradient).
    - Added Semantic Coloring logic (Blue=Artist, Orange=Genre, Pink=Jingle, etc.).
    - Fixed padding and typography (Em Space) for perfect visual balance.
    - Updated `VISUAL_STYLE_GUIDE.md` to deprecate "Arcanum" style.
- **Right Panel Architecture (The Command Deck)**:
    - Implemented `RightPanelWidget` Facade Pattern (Header, Splitter, Footer).
    - Integrated `PlaylistWidget`, `HistoryDrawer` (Hidden), and `SidePanelWidget` (Hidden/Toggleable).
    - **UI Toggles**: Added Log `[H]`, Edit `[SURGERY]`, and Compact `[=]` modes.

### Changed
- **Playlist Logic**:
    - **MoveAction**: Internal drag-and-drop now strictly reorders songs (no duplicates).
    - **Single Selection**: Enforced `SingleSelection` mode for safety.
    - **External Drag**: Dragging from Playlist to Library now performs a "Delete Source" (Remove from Playlist) action, properly decreasing song count.
- **Library Widget**:
    - **Drag Safety**: Internal Table-to-Table drags are now ignored to prevent re-import loops.
- **Editor**:
    - **Scroll Preservation**: Side Panel now keeps scroll position after Save/Reload.
    - **Save Logic**: Fixed `AttributeError` by decoupling `main_window` from direct `side_panel` access.
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
