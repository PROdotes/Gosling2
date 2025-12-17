# Gosling2 - Current Tasks (Dec 17th)

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

3.  **[Issue #3] Edit Song Metadata & File Organization** (Logic - High Priority) - **ACTIVE**
    *   **Goal**: Full parity with legacy "Save" functionality.
    *   **Sub-tasks**:
        *   [x] **Context Menu**: "Done" / "Not Done" toggling with validation. ✅
        *   [x] **Validation Logic**: Preventing incomplete songs from being marked "Done". ✅
        *   [ ] **Schema Update**: Add `Album`, `Publisher`, `Genre` to SQLite. (`ISRC` is ✅ Implemented).
        *   [ ] **Album Management**: Implement Albums table with many-to-many FileAlbums (songs on multiple albums/compilations).
        *   [ ] **Publisher Hierarchy**: Implement Publishers table with self-referencing parent relationships (subsidiaries).
        *   [ ] **Album-Publisher Link**: Link publishers to albums (via AlbumPublishers), not directly to songs.
        *   [ ] **Genre Filter Tree**: Add genre filtering to FilterWidget (click "House" → show all House songs).
        *   [ ] **Genre Tag Editor**: Implement tag-style genre editor with autocomplete (comma-separated UI, normalized storage).
        *   [ ] **Publisher Filter Tree**: Flat alphabetical list with search, hierarchical query support.
        *   [ ] **"Done" Flag**: Implement `TKEY` read/write (stores "true" or " ") for compatibility.
        *   [ ] **Renaming Service**: Port the `generateNewFilename` logic (Genre + Year folder structure) to a new service.
        *   [ ] **Metadata Write**: Connect `MetadataService` to write tags using `mutagen`.
    *   **Why**: Completes the feature we started today and ensures library backward compatibility.

**Backlog (Harder / Later)**:
*   [Issue #7] Broadcast Automation (Complex timing logic).
*   [Feat] Advanced Search Syntax (Parser implementation):
    *   Support field-specific queries: `genre:house`, `year:2020`, `bpm:>120`
    *   Support multi-value fields: `genres:house,electronic` (songs with both)
    *   Support boolean operators: `genre:house AND year:2020`

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
