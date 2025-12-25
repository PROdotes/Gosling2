---
tags:
  - layer/core
  - domain/audio
  - status/planned
  - type/service
  - size/medium
links:
  - "[[PROPOSAL_FIELD_REGISTRY]]"
  - "[[PROPOSAL_METADATA_EDITOR]]"
---
# Architectural Proposal: Metadata-Driven Renaming Service

## Objective
Implement a service to automatically organize physical files on disk based on their database metadata.

## 1. The Naming Formula (Standard)
The service will use a customizable pattern (stored in `SettingsManager`):
- **Base Pattern:** `{Genre}/{Year}/{Artist} - {Title}.mp3`
- **Fallback:** If Genre or Year is missing, use "Uncategorized" and "Unknown Year".

## 2. Core Features

### A. Automatic Path Calculation
- A method `calculate_target_path(song)` that returns the "Ideal" absolute path.
- **Sanitization:** Stripping illegal NTFS/Linux characters (`/ \ : * ? " < > |`).

### B. The "Relocation" Operation
- **Mode:** **MOVE ONLY**.
- **Mechanism:** `shutil.move` (cross-platform, handles different drives).
- **Atomicity:** The operation must verify the new file exists before unlinking the old, or rely on `shutil`'s built-in atomic guarantees where available.

### C. Conflict Resolution
- **Strategy:** **STRICT FAIL**.
- **No Magic:** We do NOT auto-increment filenames (`file (1).mp3`).
- **Check:** Before renaming, check if `target_path` exists.
- **Result:** If target exists, the specific file operation **FAILS** and notifies the user. The source file is untouched.

- **Integrity Check:** Verify the target file exists and is readable before deleting the source.

## 3. Safety Gates (The "Green Light" Protocol)
*Spec: Step 193*
Before any rename operation is permitted (Context Menu or Button), the following conditions MUST be met:
1.  **Completeness**: The Song MUST be marked as `is_done = True` (or `Status=Done`). This ensures we are not renaming files based on partial or incorrect metadata.
2.  **Cleanliness**: The Song MUST NOT have unsaved changes (`is_dirty = False`). The file on disk and the database record must match the UI state. We perform operations on *persisted* data only.
3.  **Uniqueness**: The `target_path` MUST NOT already exist. We perform an `os.path.exists()` check *at the moment the menu opens*.

## 4. On-Demand UI Feedback via Context Menu
*Spec: Step 275*
The 'Rename File(s)' button in the Library Context Menu will employ specific logic:
1.  **Opening Menu (Event)**:
    - Iterate all selected songs.
    - Check Gates 1 (Done) & 2 (Clean).
    - **Calculate Target Paths** for all selected items.
    - Check Gate 3 (Uniqueness).
2.  **Button State**:
    - **Enabled**: All gates passed.
    - **Disabled**: ANY gate fails.
3.  **Feedback (Tooltip/Text)**:
    - "Disabled: Files must be marked DONE"
    - "Disabled: Unsaved changes pending"
    - "Disabled: Target 'Z:\Songs\...' already exists"

## 5. Integration Points

### A. The "Done" Trigger
- When a song is marked as `is_done = True`, the UI should prompt: *"Move file to organization folder?"*

### B. The Batch Re-organizer
- A tool in the "Tools" menu: **"Organize Entire Library"**.
- Loops through every song, calculates the ideal path, and moves files into the tidy folder structure.

## 4. Workflows
1. **User Edits Genre:** Artist changes from "Pop" to "Jazz".
2. **Registry/Service Alert:** *"Genre changed. File is currently in /Pop/. Move to /Jazz/?"*
3. **Execution:** UI shows a progress bar as the file is physically relocated.


---

## 6. BluePrint: Technical Design (Mandatory)
*Spec: Step 299*

### A. Class Structure: `src/business/services/renaming_service.py`

```python
class RenamingService:
    def __init__(self, settings_manager):
        self.settings = settings_manager

    def calculate_target_path(self, song: Song) -> str:
        """
        Generates the ideal absolute path based on song metadata and strict patterns.
        - Pattern: {Genre}/{Year}/{Artist} - {Title}.mp3
        - Normalizes illegal characters.
        - Handles 'Uncategorized' fallback.
        """
        pass

    def check_conflict(self, target_path: str) -> bool:
        """
        Returns True if target_path exists on disk.
        """
        return os.path.exists(target_path)

    def rename_song(self, song: Song, target_path: str = None) -> bool:
        """
        Executes the move.
        1. Validate Constraints (Done/Clean/Conflict).
        2. Create parent directories.
        3. shutil.move(src, dst).
        4. Update Song model 'path' attribute.
        5. Return Success/Failure.
        (Note: Does NOT commit to DB. Caller must save the updated path to DB).
        """
        pass

    def _sanitize(self, component: str) -> str:
        """Internal helper to strip bad chars."""
        pass
```

### B. Integration Points

1.  **`LibraryWidget` (Context Menu)**
    - *Dependency*: Injects `RenamingService`.
    - *Logic*: Calls `calculate_target_path` + `check_conflict` inside `_show_table_context_menu` to set Button State.
    - *Action*: Calls `rename_song` -> If success -> `library_service.update_song(song)`.

2.  **`SidePanelWidget` (Live Editing)**
    - *Dependency*: Injects `RenamingService`.
    - *UI Component*: `lbl_projected_path` (Monospace, below Header).
    - *Logic*: On `textChanged` (debounced) or `staged_changes` update -> Calls `calculate_target_path` (using *staged* values).
    - *Feedback*:
        - Update `lbl_projected_path.setText(target_path)`.
        - If `check_conflict` is True -> `btn_save.setStyleSheet(RED)` + Label Color Red.


3.  **`LibraryService` / `SongRepository`**
    - Needs to handle the DB update of the new `Path`.

### C. Test Strategy
## 🚀 "Tomorrow" Tasks
- [x] Create `RenamingService` in `src/business/services/`.
- [x] Implement `sanitize_filename()` utility.
- [x] Build the `target_path` generator logic.
- [x] Create unit tests with mock file systems (`unittest.mock`).
- [x] Integrate `RenamingService` into `LibraryWidget` (Context Menu).
- [x] Integrate `RenamingService` into `SidePanelWidget` (Projected Path & Conflict Red Button).

