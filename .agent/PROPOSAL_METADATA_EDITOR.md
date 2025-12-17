# Architectural Proposal: Modern Metadata Editor

## Objective
Transition from "View-Only" comparisons to a robust, selection-aware editing interface.

## 1. Selection-Based Side Panel (The Explorer Style)
Implement a collapsible panel on the right side of the `MainWindow`.

- **Selection Logic:**
    - **Single Track:** Shows all fields. Edits apply to one track.
    - **Multi-Track:**
        - Fields with identical values (e.g., Album name) show the value.
        - Fields with different values (e.g., Track Title) show *"Multiple Values"*.
        - Editing a field in this state applies the change to **all selected tracks**.

## 1.5 Radio Broadcast Timing & Type Selection
As per `plan_database.md`, the editor must handle broadcast-specific logic:

- **Timing Metadata:**
    - `CueIn` / `CueOut`: Trim silence from start/end.
    - `Intro`: Time until vocals start (countdown for DJs).
    - `HookIn` / `HookOut`: Specific "hooks" for previews.
- **Entity Type:**
    - A mandatory dropdown: `Song`, `Jingle`, `Spot`, `VoiceTrack`, `Bed`.
    - **UX:** Selecting "Jingle" might hide unnecessary fields like "ISRC" or "Composer".

- **Visual Cues (Future):**
    - A mini-waveform to visually set these cue points.

## 2. Inline Editing (MetadataViewerDialog)
Upgrade the existing `MetadataViewerDialog` to support manual entry.

- **Interaction:**
    - Cells in the "Library (Database)" column become `QTableWidget` editable cells.
    - **Visual Feedback:** 
        - Default: White.
        - Modified (Unsaved): **Orange** 🟠.
        - Conflict (Different from File): **Red** 🔴.
- **The "Staging" Concept:**
    - Changes in the UI are kept in a local dictionary until "Apply" is clicked.
    - This allows "Review Before Commit" behavior.

## 3. Integration with Field Registry
The Editor should be **Dynamic**:
- It iterates the `Field Registry`.
- If a field is marked `is_editable=True`, the UI generates a widget for it.
- If it's a "Genre," it produces a Tag Editor.
- If it's a "Publisher," it produces a Tree Search.

## 4. Archivist & Audit Integration (The "Log" Connection)

The Editor serves as the primary gateway to the `Transaction Log`.

- **Identity Tracking:** The UI includes an optional "User/Process" field.
    - Default: "GUI User"
    - Allows manual override: "Import Script", "Audit Fix", etc.
- **Computed Metadata:** "Date Added" and "Last Modified" fields are displayed in the panel, computed on-the-fly from the `ChangeLog` table.
- **Integrated History:** A "History" tab or drawer allows the user to see every past change to the selected song(s) without leaving the editor.

## 5. Smart Collection Operations (Librarian Logic)

When performing bulk edits on list-based fields (Genres, Performers, Composers), the editor will offer three operational modes:

### A. Overwrite Mode (Standard)
- **Behavior:** Replaces all existing values in the selected tracks with the new entry.
- **Example:** Select 10 songs -> Set Genre to "Jazz" -> All 10 songs now have *only* "Jazz".

### B. Append Mode (Additive)
- **Behavior:** Adds the new value to the existing list for each track, skipping duplicates.
- **Example:** Select "Electronic" and "House" tracks -> Append "Live" -> Tracks become ["Electronic", "Live"] and ["House", "Live"].

### C. Remove Mode (Subtractive)
- **Behavior:** Removes the specified value from any selected track that currently contains it.
- **Example:** Select 50 tracks -> Remove "Temporary" tag -> Any track with "Temporary" in its list has that specific tag removed; other tags remain untouched.

### D. Sync Comparison
- **Batching:** All bulk edits are grouped under a single `BatchID` in the Transaction Log for easy one-click restoration.

## 6. Design Aesthetics & UX (The "Pro" Look)

To avoid a "spreadsheet nightmare" while maintaining high-end power, the editor will follow these design principles (Mockup Reference #1):

### A. Progressive Disclosure
- **Core Info:** Top section shows Title, Artist, Album, and BPM.
- **Advanced Metadata:** Collapsible "Details" drawer for ISRC, Producers, Composers, etc.
- **Embedded History:** A scrollable "timeline" footer at the bottom of the panel showing recent edits for the selection.

### B. Visual Feedback (The "Gosling" Language)
- **Glassmorphism:** Semi-transparent panel with frosted background for a premium, modern feel.
- **Staging Indicators:** Small vibrant **Orange Dots** (🟠) next to labels to indicate unsaved/staged changes.
- **Sync Warnings:** Labels turn **Vibrant Red** 🔴 if the database value is currently different from the physical file tags.
- **Multi-Selection Focus:** When multiple tracks are selected, the panel transitions to "Bulk Mode" with distinct icons for Append/Remove operations.

### C. Typography & Hierarchy
- **System Fonts:** Use Inter or San Francisco for perfect readability.
- **Hierarchy:** High-contrast labels (Light Grey) versus inputs (Pure White) to reduce eye strain in dimly lit studio/radio environments.
