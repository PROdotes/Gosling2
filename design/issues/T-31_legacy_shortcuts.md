---
tags:
  - type/feature
  - domain/ui
  - status/open
links:
  - design/reference/LEGACY_LOGIC.md
---

# T-31: Legacy Keyboard Shortcuts

**Objective**: Restore the "muscle memory" workflow of Gosling 1 by implementing critical keyboard shortcuts.

## Requirements

### 1. The "Done" Toggle (`Ctrl + D`)
*   **Context**: Active in `LibraryWidget`, `MetadataViewer`, or main window.
*   **Action**: 
    1.  Toggle the `is_done` status of the **currently selected song(s)**.
    2.  Update the UI (Checkbox/Color).
    3.  **Optional**: Auto-save immediately? (Legacy behavior: No, user hit Ctrl+S after).
*   **Visual Feedback**: Row should likely turn green or show a checkmark immediately.

### 2. The "Save" Trigger (`Ctrl + S`)
*   **Context**: Global (Main Window).
*   **Action**: 
    1.  Trigger `MetadataService.write_tags()`.
    2.  Trigger `SongRepository.update()`.
    3.  If `RenamingService` is active, trigger file move.
*   **Feedback**: "Saved X songs" status bar message.

### 3. Navigation (`Space` / `Enter`)
*   **Space**: Play/Pause current track (Global).
*   **Enter**: 
    *   If cell selected: Edit.
    *   If row selected: Play? (Needs decision).

## Implementation Tips
*   Use `QAction` with `setShortcut()` attached to the Main Window to ensure global capture.
*   Route signals to `LibraryWidget.save_selection()` and `LibraryWidget.toggle_done()`.
