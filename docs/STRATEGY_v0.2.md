# v0.2 REFACTOR STRATEGY: THE STRANGLER FIG

## 1. THE MISSION
To migrate `Gosling2` from a monolithic script (`app.py`, `library_widget.py`) to a Layered Architecture (`src/core`, `src/data`, `src/business`, `src/presentation`) without losing a single feature or breaking a single user workflow.

## 2. THE SAFETY NET (THE "GOLDEN SUITE")
Before ANY refactoring begins, we must ensure strict test coverage of the *spec*, not just the *code*.
*   [ ] **The Gap Analysis**: Compare `TESTING.md` specs vs. actual `tests/`. Identify missing scenarios.
    *   *The Script checks for presence. The Agent checks for MEANING.*
*   [ ] **The "Golden" Tests**: Ensure we have High-Level Integration tests for:
    *   **Import**: Zip -> Extract -> Parse -> DB -> UI Refresh.
    *   **Edit**: UI Change -> DB Update -> ID3 Update -> Readback Verify.
    *   **Search**: Query Syntax -> SQL Translation -> Result Display.
*   **RULE**: If a feature is not tested, it does not exist. Write the test first.

## 3. THE FEATURE CENSUS (SCOPE LOCK)
We must explicitly list all features to ensure Parity.
*   **Core**:
    *   [ ] Zip Import (Atomic, Cleanup on success)
    *   [ ] Metadata Extraction (ID3v2.4 enforcement)
    *   [ ] Duplicate Handling (Strict Rejection)
*   **UI / UX**:
    *   [ ] Library Table (Sorting, Coloring, Selection)
    *   [ ] Context Menus (Right-click actions)
    *   [ ] "Yelling" Validation (Red/Blue/Green highlights)
    *   [ ] Side Panel Editor (Bulk Edit logic)
*   **Pending Features (v0.1 Finalization)**:
    *   [ ] **Duplicate Detection**: (ISRC -> Hash -> Meta).
    *   [ ] **Settings UI**: Root Dir & Configurable Rules.
    *   [ ] **Dynamic Renaming**: Move 'Patriotic' logic to config.
    *   [ ] **Audit Log**: History of changes.
    *   [ ] **UX Polish**: Dark Mode & Styling.
    *   [ ] **Album Entity Editor**: Relational Picker/Editor for Albums & Publishers.

## 4. THE MIGRATION PROTOCOL (EXECUTION)
We follow the **Strangler Fig Pattern**: build the new system *alongside* the old one, gradually routing functionality over.

### Phase A: The Foundations (No UI Changes)
1.  **Data Layer**: Solidify `src/data/database.py` and `repositories`.
2.  **Core Adapters**: Extract `ID3Adapter` from `yellberus`.
3.  **VERIFY**: Run Unit Tests on new modules.

### Phase B: The Service Layer (Logic Injection)
1.  **Service Creation**: Build `ImportService`, `LibraryService`, `EditService`.
2.  **Route Switching**:
    *   Modify `app.py` to instantiate the Service.
    *   Replace *one* function call (e.g., `import_zip()`) to use the Service.
    *   **VERIFY**: Run the Golden Suite. The App should behave identically.

### Phase C: The UI Decoupling (The "Dumb" UI)
1.  **Component Split**: Break `library_widget.py` into smaller views (e.g., `TableView`, `FilterBar`).
2.  **Logic Removal**: Move all logic from `PyQt` slots into `src/presentation` ViewModels or Controllers.
3.  **VERIFY**: Manual UI testing + Widget Tests.

## 5. AGENT HANDOFF PROTOCOL
A Refactor is a marathon, not a sprint.
*   **The Checkpoint**: If you context window is filling, you MUST write your current status to `MIGRATION_LOG.md`.
    *   *e.g. "Moved `TrackRepository`. Tested. Next: `AlbumRepository`."*
*   **The Baton**: The next agent reads `MIGRATION_LOG.md` and resumes exactly where you left off.
*   **No "Cowboy Coding"**: Do not start Phase C while Phase A is broken.

## 6. THE "KILL ON SIGHT" LIST
Files that must eventually be deleted or emptied:
*   `yellberus.py` (Its logic moves to `src/core/validation` and `src/data/models`)
*   `library_widget.py` (Too large. Split into `src/presentation/components/`)
*   The old `app.py` (Replaced by a clean `main.py` entry point)
## 7. REFACTORING BACKLOG (v0.2 CANDIDATES)
These are targeted refactors to improve abstraction and reduce boilerplate, scheduled for the v0.2 transition.

*   **Dialog/Picker Consolidation**:
    *   **Issue**: `ArtistPickerDialog`, `PublisherPickerDialog`, etc. share high logic overlap.
    *   **Goal**: Consolidate into a `DialogFactory` or a generic `EntityPickerDialog`.
*   **ChipTray Abstraction Leak**:
    *   **Issue**: `ChipTrayWidget` exposes internal tuple structure `(id, label, icon...)` to consumers.
    *   **Goal**: Encapsulate internals. Consumers should handle simple lists or objects; `ChipTray` should manage its own mapping and display logic.
*   **Smart Playlist Infrastructure**:
    - **Issue**: String-based JSON/MIME payloads for Drag & Drop are heavy and brittle.
    - **Goal**: Shift to **Identity-Based Intake**. Store full data dictionaries or DB references per item. This is the prerequisite for Cue In/Out, Album Art, and advanced playback marker support.
