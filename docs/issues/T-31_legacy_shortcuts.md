---
tags:
  - type/feature
  - domain/ui
  - status/open
links:
  - docs/reference/LEGACY_LOGIC.md
---

# T-31: Legacy Keyboard Shortcuts

**Objective**: Restore the "muscle memory" workflow of Gosling 1 by implementing critical keyboard shortcuts.

## Requirements

### 1. The "Done" Toggle (`Ctrl + D`)
*   **Context**: Active in the main library view (rows selected in `LibraryWidget`).
*   **Action**:
*   1.  Attempt to mark the **currently selected song(s)** as Done.
*   2.  Use existing Yellberus/validation logic to refuse Done for rows that are incomplete (missing mandatory fields/tags).
*   3.  For valid rows, update `is_done` in the database and refresh the table.
*   **Visual Feedback**: Done column updates immediately (checkbox/colour). If some rows could not be marked Done, show a short warning listing missing fields.

### 2. The "Save" Trigger (`Ctrl + S`)
*   **Context**: Global (Main Window), acts on the currently selected rows in the library table.
*   **Action**:
*   1.  For each selected song, persist current metadata to the database (`LibraryService.update_song`).
*   2.  Persist the same metadata to ID3 tags (`MetadataService.write_tags`).
*   3.  If a renamer is present and the song is marked Done, trigger a file move according to `LEGACY_LOGIC.md` (0.1 hook, implementation may land later).
*   **Rule**: Save **always works**—it does not decide or re-check Done, it simply persists whatever Done state exists.
*   **Feedback**: "Saved X songs" status bar message, with simple error reporting if some rows fail.

### 3. Navigation / Focus (`Ctrl + F`, `Space` / `Enter`)
*   **Ctrl + F**: Focus the search/filter bar and select its contents.
*   **Space**: Play/Pause current track (Global). *(Existing Playback widget behaviour; shortcut wiring TBD.)*
*   **Enter**:
*   *   If row selected in library: Add to playlist/play (follow current double-click semantics).

## Implementation Tips
*   Use `QAction` with `setShortcut()` attached to the Main Window to ensure global capture.
*   Route signals to `LibraryWidget.save_selection()` and `LibraryWidget.toggle_done()`.
