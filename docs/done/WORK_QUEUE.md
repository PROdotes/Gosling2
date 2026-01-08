---
tags:
  - type/queue
  - status/active
---

# 👷 Agent Work Queue

**Objective**: Reach Alpha 0.1.0 (Feature Complete for Backlog Processing).
**Strategy**: Split large features into atomic, verifiable chunks.

---

## 🏗️ Priority 1: Backlog Enablement Tools (Milestone 3)
*Blocking the user from processing their 400-song backlog.*

### Task 1: Side Panel (Metadata Editor)
**Spec**: `docs/proposals/PROPOSAL_METADATA_EDITOR.md`
**Why**: Currently, editing requires right-click -> Properties. We need a persistent side panel for rapid editing.
*   **Subtask A: UI Scaffold**
    *   Create `src/presentation/widgets/metadata_editor_panel.py`.
    *   Implement layout: Title, Artist, Album, Genre, Year, Status (Done/Active).
    *   Integrate into `MainWindow` (right dock area).
*   **Subtask B: Selection Binding**
    *   Connect `LibraryWidget.selectionChanged` -> `MetadataEditorPanel.load_song(song)`.
    *   Handle "Multiple Selection" (disable fields or show "<Various>").
*   **Subtask C: Save Logic**
    *   Implement "Apply" button or "Auto-save on Deselect" logic.
    *   Call `MetadataService.update_song()`.

### Task 2: Auto-Renamer (File System)
**Spec**: `docs/proposals/PROPOSAL_RENAMING_SERVICE.md`
**Why**: Files need to move to `\\onair\Genre\` when marked "Done".
*   **Subtask A: Rules Engine**
    *   Create `src/business/services/renaming_service.py`.
    *   Implement logic from `LEGACY_LOGIC.md`:
        *   `{Genre}/{Year?}/{Artist} - {Title}.mp3`
        *   Handle duplicates (append `_1`, `_2`).
*   **Subtask B: Integration**
    *   Trigger on "Save" if `Auto-Move` is enabled in settings.

### Task 3: Legacy Shortcuts
**Spec**: `docs/issues/T-31_legacy_shortcuts.md`
*   **Subtask A**: Implement Global Shortcuts in `MainWindow`.
    *   `Ctrl+D`: Toggle "Is Done" status for selected song(s).
    *   `Ctrl+S`: Save changes (if Editor is focused).

---

## 🛡️ Priority 2: Data Integrity Guards (Milestone 4)
*Preventing bad data from entering the system.*

### Task 4: Duplicate Detection
**Spec**: TBD (See `ROADMAP.md` Milestone 4)
*   **Subtask A: Hash Calculation**
    *   Add `Hash` column to `MediaSources` (if not exists, check Schema).
    *   Compute SHA-256 (first 1MB) on Import.
*   **Subtask B: Import Gatekeeper**
    *   Modify `LibraryService.import_files`:
        *   Check ISRC.
        *   Check Hash.
        *   Check (Artist + Title) similarity.
    *   Prompt user on collision.

---

## 🧹 Priority 3: Tech Debt & Polish (Milestone 5)
*Low priority, pick up if blocked.*

### Task 5: Core Coverage Injection (Missing Files)
**Criticality**: High (Code exists but has NO tests).
*   **Subtask A: Logger**
    *   [x] Create `tests/unit/core/test_logger.py`.
    *   [x] Cover: `_setup`, `get`, `info`, `error`.
*   **Subtask B: Publisher Repository**
    *   [x] Create `tests/unit/data/repositories/test_publisher_repository.py`.
    *   [x] Cover: `get_with_descendants` (recursive logic), `create`, `delete`.
*   **Subtask C: Tag Repository**
    *   [x] Create `tests/unit/data/repositories/test_tag_repository.py`.
    *   [x] Cover: `add_tag_to_source`, `get_all_by_category`.

### Task 6: Edge Case Coverage
**References**: `validation_report.txt` (or recent 81% audit)
*   **Subtask A: Metadata Viewer Dialog**
    *   Add tests for "Write Error" dialogs.
    *   Add tests for "Validation Failed" dialogs.
*   **Subtask B: Playlist Widget**
    *   Add tests for `dragEnterEvent` with invalid mime types.

### Task 6: UI Polish
*   **Subtask A**: Apply a dark theme (QPalette or StyleSheet).
*   **Subtask B**: Unified Button Styling (Padding, Borders).

---

### Task 7: Test Inventory Enforcer (Tooling)
**Spec**: `docs/specs/TOOL_TEST_INVENTORY.md`
**Goal**: Automate "The Law of Inventory" so users don't have to manual check.
*   **Subtask A: Enhance Audit Tool**
    *   Modify `tools/audit_test_coverage.py` or create `tools/lint_tests.py`.
    *   Fail (Exit code 1) if:
        *   Any `src/*.py` has no matching `tests/unit/test_*.py`.
        *   Coverage < 80%.
    *   Print a "Hit List" of missing files.

## 📝 Instructions for Agents

1.  **Pick a Task**: Read the top-most unassigned task.
2.  **Read Specs**: Check `docs/proposals/` for valid specs. If missing, create a skeletal spec.
3.  **Create Logic**: Implement Business Layer first.
4.  **Create UI**: Implement Presentation Layer second.
5.  **Verify**: Run `pytest` and manual verification.
6.  **Mark Done**: Update this file (`[x]`) and `ROADMAP.md`.
