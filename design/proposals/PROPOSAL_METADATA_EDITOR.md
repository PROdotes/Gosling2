# Proposal: Persistent Metadata Editor Panel (Milestone 3, Task 1)

## 1. Objective
Replace the slow "Right Click -> Properties" workflow with a persistent, always-visible side panel ("Inspector" style) to enable rapid "Edit -> Next" processing of the 400-song backlog.

## 2. Problem Statement
Currently, to edit a song's metadata, the user must:
1. Right-click a song.
2. Select "Properties".
3. Wait for the dialog.
4. Edit fields.
5. Click Save.
6. Close dialog.
This is too slow for processing hundreds of files.

## 3. Solution Design
A `MetadataEditorPanel` docked to the right side of the `MainWindow`.

### 3.1 UI Layout
Vertical form layout containing specific high-priority fields:

| Field Label | Widget Type | Behavior |
|:---|:---|:---|
| **Title** | `QLineEdit` | Text input. |
| **Artist** | `QLineEdit` | Text input (future: Autocomplete). |
| **Album** | `QLineEdit` | Text input (future: Autocomplete). |
| **Genre** | `QComboBox` | Dropdown with `TCON` values (plus "Speech", "Commercial"). |
| **Year** | `QSpinBox` | Numeric (1900-2100). |
| **Status** | `QCheckBox` | "Done" (IsDone=1). |
| **Path** | `QLabel` | Read-only path (truncated / elided). |

**Buttons:**
*   **Apply Changes** (Enabled only when dirty).
*   **Discard** (Revert to selection).

### 3.2 Interaction Model
1.  **Selection**: When `LibraryWidget` selection changes:
    *   If 0 songs selected: Clear panel, disable fields.
    *   If 1 song selected: Load song data into fields. Store original `Song` object.
    *   If >1 songs selected:
        *   If values match (e.g. same Album), show value.
        *   If values differ, show `<Various>`.
        *   Editing a field applies to ALL selected songs (Batch Edit).
2.  **Dirty State**:
    *   Changing any field sets `_dirty = True` and enables "Apply".
    *   Attempting to change selection while `_dirty` shows a "Save changes?" prompt (or auto-saves based on config, default to Prompt).

### 3.3 Architecture
*   **Class**: `src.presentation.widgets.metadata_editor_panel.MetadataEditorPanel` (inherits `QWidget` or `QDockWidget`).
*   **Signals**: 
    *   `dataChanged()`: Emitted after successful save to refresh Library view.
*   **Dependencies**: `MetadataService`, `SongRepository`.

## 4. Implementation Plan
1.  **Scaffold**: Create the widget class and layout.
2.  **Data Loading**: Implement `load_song(song: Song)`.
3.  **Data Saving**: Implement `save_changes()`.
4.  **Integration**: Add to `MainWindow` and connect `selectionChanged`.
5.  **Polishing**: Add batch editing logic (Phase 2).

## 5. Security & Validation
*   Validate schema using `yellberus` rules (e.g. Year must be int).
*   Prevent saving empty Titles.
