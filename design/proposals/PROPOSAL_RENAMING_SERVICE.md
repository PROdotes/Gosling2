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
- **Mode 1: Move.** Deletes the old file, creates the new one.
- **Mode 2: Copy.** Keeps the original, creates a clone in the target folder.
- **Safety:** Check if source and target are on the same drive (use `os.rename` for speed, fallback to `shutil.move`).

### C. Conflict Resolution
- If `House/2023/Beatles - Help.mp3` already exists:
- Increment filename: `House/2023/Beatles - Help (1).mp3`.
- **Integrity Check:** Verify the target file exists and is readable before deleting the source.

## 3. Integration Points

### A. The "Done" Trigger
- When a song is marked as `is_done = True`, the UI should prompt: *"Move file to organization folder?"*

### B. The Batch Re-organizer
- A tool in the "Tools" menu: **"Organize Entire Library"**.
- Loops through every song, calculates the ideal path, and moves files into the tidy folder structure.

## 4. Workflows
1. **User Edits Genre:** Artist changes from "Pop" to "Jazz".
2. **Registry/Service Alert:** *"Genre changed. File is currently in /Pop/. Move to /Jazz/?"*
3. **Execution:** UI shows a progress bar as the file is physically relocated.

## 🚀 "Tomorrow" Tasks
- [ ] Create `RenamingService` in `src/business/services/`.
- [ ] Implement `sanitize_filename()` utility.
- [ ] Build the `target_path` generator logic.
- [ ] Create unit tests with mock file systems (`pyfakefs`).
