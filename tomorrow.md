# Plan for Tomorrow

**Current State**:
- **Strict Schema Awareness** is fully active ("The Yelling Mechanism").
- **Drag & Drop Import** (Issue #8) is **COMPLETED**.
- **Metadata Viewer** is implemented but read-only.
- **Database** is secured against silent schema drift.

**Priorities for Next Session (Easy Wins First)**:

1.  **[Refactor] Centralize Settings Manager** (Warm-up)
    *   **Goal**: Fix the scattered `QSettings` usage.
    *   **Why**: Quick mechanical cleanup to get the brain working. Ensures testing consistency.

2.  **[Refactor] Test Suite Audit** (Cleanup)
    *   **Goal**: Check for redundant fixtures, duplicated mocks, and opportunities to simplify property verification.
    *   **Why**: We added a LOT of tests recently. Good to prune/optimize before adding more.

3.  **[Issue #6] Library View Modes** (Visual)
    *   **Goal**: "Edit Mode" vs "Broadcast Mode" toggle.
    *   **Why**: Leveraging recent UI work. High impact, low logic complexity.

3.  **[Issue #3] Edit Song Metadata** (Logic)
    *   **Goal**: Enable "Save" button in Metadata Viewer.
    *   **Why**: Completes the feature we started today.

**Backlog (Harder / Later)**:
*   [Issue #7] Broadcast Automation (Complex timing logic).
*   [Feat] Advanced Search Syntax (Parser implementation).

**Design & Assets**:
*   [ ] **Review Icon Vector Work**: The conceptual sheets are saved in `resources/design/`. Need to manually refine the selected "Cabinet + Note" icon into a proper SVG/Vector format.

**Suggestion**: Start with the **Settings Manager** cleanup to clear the debt, then reward yourself with the **View Modes** UI work.

### Refactoring Candidates
- [ ] **Refactor library_widget.py** (28KB - High Complexity)
    *   **Issues**: 
        *   Giant "God Class" handling UI, detailed drag/drop logic, ZIP extraction, file system, `QSettings` state, and complex context menus.
        *   `_process_zip_file` (L201) contains critical business logic that belongs in `LibraryService`.
        *   Mixed abstraction levels: raw SQL-like column handling mixed with high-level UI events.
        *   Duplicated `QSettings` key logic for column visibility.
    *   **Plan**: Extract `ZipImportHandler`, move `scan_directory` logic to Service, and create a `LibraryTableView` helper class to manage columns.

- [ ] **Refactor song_repository.py** (13KB)
    *   **Issues**:
        *   Contains raw SQL strings that are becoming unmanageable.
        *   `_sync_contributor_roles` (L97) is a complex nested logic block inside a repository.
        *   Partial duplication between single-item fetches and list fetches.
    *   **Plan**: Introduce a Query Builder or named SQL constants. Move complex sync logic to a Domain Service or use a transaction helper context manager.

- [ ] **Refactor playback_service.py** (12KB)
    *   **Issues**:
        *   Complex state management for Crossfading (`_start_crossfade`, `_on_crossfade_tick`, `_stop_crossfade`).
        *   Direct management of `QMediaPlayer` pairs (`player1`/`player2`) makes the code fragile and hard to test.
        *   Timer-based logic is coupled tightly with playback state.
    *   **Plan**: Extract `Crossfader` into a separate class. Create a `DualDeckPlayer` abstraction that manages the swapping internally, exposing a simple `play(track, transition=Crossfade)` interface.
