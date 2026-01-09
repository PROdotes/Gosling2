---
tags:
  - plan/roadmap
  - type/strategy
  - status/active
---

# 🗺️ Roadmap to Alpha 0.1.0

**Goal**: A "Feature Complete" metadata editor capable of safe Legacy Sync (Gosling 1 parity).
**Status**: Active Construction
**ETA**: End of Week

---

## 🚦 Milestones & Estimates

**Total Remaining to 0.1.0**: ~14 Hours (approx. 2 full days)

### ✅ Milestone 0: The Foundation (Completed)
*   [x] **Schema Core**: Songs, MediaSources, Contributors.
*   [x] **Yellberus**: Data Integrity Guard.
*   [x] **Field Editor**: UI & Persistence.
*   [x] **Unified Artist**: M2M Logic.

### 🔧 Milestone 1: Schema Fix (Critical)
*Status: COMPLETED (Dec 23)*
*   [x] **Greatest Hits Fix** (~2.0 h)
    *   *Task*: Schema Change (AlbumArtist) + Logic Update.
    *   *Criticality*: High (Data Corruption). Must fix before test consolidation.
*   [x] **Dynamic ID3 Write (T-38)** (~3.0 h)
    *   *Task*: Logic Refactor (JSON-driven writing).
    *   *Criticality*: Blocker (Regression found & fixed).

### 🧹 Milestone 2: The Cleanup
*Status: COMPLETED (Dec 24)*
*   [x] **T-04 Test Consolidation** (~3.0 h)
    *   *Status*: **Done** — All layers consolidated (Data, Business, Presentation). Test count: 363.
    *   *Why*: Merging 56 files makes future features faster/safer.
    *   *Risk*: Low (Boring work).
*   [x] **T-46 Proper Album Editor** (~3.5 h) (Dec 29)
    *   *Status*: **Done**. Four-pane manager (Album, Context, Inspector, Sidecar) implemented.
    *   *Ref*: T-46.
*   [x] **T-55 Custom Field Sections** (~2.0 h) (Dec 30)
    *   *Status*: **Done**. Fields grouped by logic (Core, Classification, Credits, etc.).
    *   *Ref*: T-55.

### 🛠️ Milestone 3: Usable UI (Backlog Enabler)
*Status: Required for processing 400-song backlog*
*   [x] **Side Panel Alpha** (~3.0 h)
    *   *Task*: Basic metadata editor panel (Genre, Artist, Album, Done).
    *   *Status*: **Done** (Validation + Edit + Staging + Dirty Row Highlight).
    *   *Ref*: T-12.
*   [x] **Legacy Shortcuts** (~1.0 h)
    *   *Task*: `Ctrl+D` (Done), `Ctrl+S` (Save), `Ctrl+R` (Rename Placeholder).
    *   *Status*: **Done**.
    *   *Ref*: T-31.
*   [x] **Dynamic ID3 Read (T-44)** (~1.5 h) - **CRITICAL**
    *   *Task*: Fix hardcoded `get_text_list` in `metadata_service.py` (read path).
    *   *Why*: Currently inconsistent with `write_tags` (dynamic).
    *   *Status*: **Done** (Completed by noir detective → Sheila → Seraphim).
*   [x] **Auto-Renamer** (~3.5 h)
    *   *Task*: Port Genre/Year rules + `shutil.move` logic.
    *   *Complexity*: High (File System Risk). Rules documented in `LEGACY_LOGIC.md`.
    *   *Status*: **Done** (Service + UI Gates implemented).
*   [x] **Radio Automation Layout (T-49)** (~4.0 h)
    *   *Task*: Pivot to Frameless Workstation (Master Deck, Dual Splitters, Hist Sidebar).
    *   *Status*: **Done** (Industrial Chassis + Masters Console).
*   [x] **Surgical Right-Channel (T-54)** (~2.0 h)
    *   *Task*: Split-view focus for Editor/Playlist combo.
    *   *Note*: Shift from " Spotify Tabs" to "Workstation Dashboard" focus.

### 🚧 Milestone 4: Data Integrity
*Status: COMPLETED (Dec 25)*
*   [x] **Duplicate Detection** (~2.5 h)
    *   *Task*: Tiered Import Check (ISRC -> Hash -> Meta).
    *   *Complexity*: Medium.

### 🔮 Milestone 5: The Final Sprint (0.1.0)
*Status: Queue (Prioritized)*
*   [x] **Filter Tree Search & State Persistence** (~2.0 h)
    *   *Task*: Main search filters both table and filter tree; expansion state persists across restarts.
    *   *Status*: **Done** - Implemented recursive tree filtering with QSettings persistence.
*   [x] **Decade Filtering** (Filter Tree & Search)
    *   *Task*: Ungrouped years in tree + Virtual Decade nodes + Smart "1990s" search logic.
    *   *Status*: **Done**.
*   [x] **T-61 Universal Tag Picker** (Search/Tree Dialog)
    *   *Status*: **Done** - Implemented "Speed Mode", Global Search, and Auto-Context Switching.
*   [x] **Status Deck Implementation (T-92)**
    *   *Task*: Implemented consolidated "Status Deck" column (GlowLED Shapes/Colors) and "Active" Toggle with Atomic Save.
    *   *Status*: **Done**.
*   [x] [**T-70 Artist Selector**](tasks/T-70_artist_manager_plan.md) (Database-backed Picker)
*   [x] **Multi-Album Infrastructure** (T-22/T-63)
    *   *Status*: **Core Schema & Logic Done**.
    *   *Ref*: `PROPOSAL_MULTI_ALBUM_INFRASTRUCTURE.md`.
*   [x] **Audit Log (History)** (T-05) (~1.0 h)
    *   *Task*: Record INSERT/UPDATE events and expose via UI.
    *   *Status*: **Done** - Full stack implementation (Repo, Service, Dialog) working and tested.
*   [ ] **Advanced Rule Editor** (T-82) (~2.0 h)
    *   *Task*: UI for managing `rules.json` (Genre Routing, Profiles) inside Settings.
*   [x] **Settings UI** (T-52) (~1.5 h)
    *   *Task*: UI for Root Directory, Renaming Rules, Transcoding, and Metadata defaults.
*   [x] **Dynamic Renaming Rules** (T-50) (~2.0 h)
    *   *Task*: Externalize hardcoded 'Patriotic/Cro' logic to config file.
*   [x] **UI Polish & Icon (T-53)**
    *   *Task*: SVG Icon fix & Settings Entry Point (T-57).
*   [x] **Tag Verification** (T-51) (~1.0 h)
    *   *Task*: Verify `TXXX:GOSLING_DONE` and ID3 writes.
    *   *Status*: **Done** - Verified dual-write (TKEY legacy + TXXX modern) working correctly.
*   [x] **Background Import** (T-68) (~2.0 h)
    *   *Task*: Move file operations to worker thread to prevent UI freeze.
    *   *Why*: Required for Release Criteria #1 (Import 1k songs).
    *   *Status*: **Done** - Implemented via `ImportWorker(QThread)` in `library_widget.py`.
*   [x] **Virtual File System (VFS)** (T-90)
    *   *Task*: Index ZIP contents without explosion; virtual playback via temp files.
    *   *Status*: **Done** - Full implementation (Core, Import, Playback, UI Pip).
*   [x] **"Show Truncated" Filter (T-102)** (~2.0 h) 🔴 *Gosling 1 Parity*
    *   *Task*: Filter songs missing Composer/Publisher. Weekly workflow essential.
*   [x] **ZAMP Search Button (T-103)** (~0.5 h) 🔴 *Gosling 1 Parity*
    *   *Task*: Add ZAMP.hr to web search buttons for Croatian rights lookup.
*   [ ] **Completeness Indicator (T-104)** (~2.0 h)
    *   *Task*: Visual marker in grid showing missing required fields.
*   [x] **Quick Lookup (T-105)** (~1.0 h)
    *   *Task*: Ctrl+F focuses search box for fast Title+Artist lookup.
*   [ ] **Inline Edit (T-03)** (~2.0 h)
    *   *Task*: Edit cells directly in grid. Critical for CD batch workflow.

---

## 🔄 Milestone 7: v0.2 Refactor Run

*Status: Planned after 0.1 workflow is solid*

> **Goal:** Clean up LLM-generated code debt. Form over function.

*   [ ] **T-28 Leviathans Split**
    *   `library_widget` (2032→7 modules), `main_window` (zip logic → VFS service), etc.
*   [ ] **Async Background Save (T-62)**
    *   Move save/renaming operations to background thread.
*   [ ] **MS Access Migration** (v0.2+)
    *   Import 50k songs from legacy database.
    *   Bidirectional sync with old automation app.

---

## 📉 Technician's Corner (Tech Debt)
*Non-blocking, but beneficial.*

*   [x] **Generic Repository** (~2.0 h): Refactor repetitive CRUD code.
    *   *Status*: **Done** - Core ABC and SongRepository integration complete.
*   [x] **ID3 Logic Extraction** (~1.0 h): Deduplicate JSON lookup.
*   [x] [**Unified Input Dialog**](tasks/T-85_universal_input_dialog.md) (T-85):
    *   *Status*: **Done** — Consolidated `TagPickerDialog`, `ArtistCreatorDialog`, and `QInputDialog` into the generalized `EntityPickerDialog`.
    *   *Result*: Standardized "Morning Logic" UI, eliminated code duplication, and removed 100% of ad-hoc `QInputDialog` usage.
-   [x] **T-79 QSS Optimization**: Centralize remaining hardcoded styles.
-   [x] [**T-81 Restore Web Search**](tasks/T-81_restore_web_search.md): Restore web search with Settings Manager persistence.
*   [x] **Album Manager QSS Refactor**: Move hardcoded styles/layout tweaks from Python to `theme.qss` for cleaner separation.
*   [x] **UX Issue**: "Create New Album" button in Album Manager is confusing for users. Redesign needed.

---

## 🏁 Release Criteria (0.1.0)
1.  Can Import 1,000 songs without crashing.
2.  Detects duplicates accurately.
3.  Renames files to correct folder structure on Save.
4.  Writes all ID3 tags (including custom ones) verified.
5.  Persists all changes to DB with History log.



### 🚀 Milestone 6: Post-Alpha Refinements (Tomorrow/Future)
*   [x] **Fix & Silence Test Suite (TOP PRIORITY)**
    *   *Task*: Fix 33 Failures / 17 Errors caused by recent refactors.
    *   *Status*: **Done** - All Unit and Integration tests confirmed passing.
    *   [x] **Silence interactive popups** (e.g. `add_alias`) to restore "Law of Silence".
    *   [x] **Repository Hardening**: Backfilled tests for `TagRepository` (Merge/Workflow) and `GenericRepository` (Audit Transactions).
*   [x] **Album Artist M2M Schema** (T-91)
    *   *Task*: Upgrade `Albums.AlbumArtist` from text to `AlbumContributors` (M2M) table.
    *   *Status*: **Done** — Full M2M integration completed, including UI Picker and streamlined display logic.
*   [x] **Album Publisher Backend catch-up**
    *   *Task*: Ensure Album Manager "Tags" UI correctly writes multiple rows to `AlbumPublishers`.
    *   *Status*: **Done**. Verified delegate logic in `AlbumRepository` and `PublisherRepository`.
*   [x] **Wire up Chips inside Album Manager**
    *   *Task*: Make clicking Artist/Publisher chips *inside* the Album Editor open their respective Managers (currently does nothing).
    *   *Status*: **Done** - Connected chip signals to `ArtistDetailsDialog` and `PublisherDetailsDialog` in `AlbumManagerDialog`.
    *   *Bug*: Clicking Inherited Publisher on Side Panel incorrectly triggers "Add New" dialog instead of just focusing the Album Editor.
    *   *Refactor*: "Add Album" flow in Side Panel needs audit (prone to crashes if services missing).
*   [x] **Safe Save Logic (Tag/DB Sync)**
    *   *Observation*: Fixed desync risk where tags were written before DB success.
    *   *Status*: **Done** - `ExportService` now follows DB-First, ID3-Second protocol. Verified by `test_db_failure_skips_id3`.
*   [x] **Tag Editing Improvements**
    *   *Bug*: "Ghost Conflict" - Renaming tag seems to create the new tag *before* checking for conflict, triggering false positive "Exists".
    *   *Feature*: **True Rename** - Renaming "Rock" -> "Rockk" currently creates new "Rockk" tag (link swap) instead of renaming the ID itself. Need "Rename vs Create New" logic.
    *   *Feature*: **Category Mutability** - Allow changing a tag's category (e.g. Mood:Jazz -> Genre:Jazz) directly in the UI.
*   [x] **Bug: Duration Import Zero**
    *   *Observation*: "Duration isn't getting imported from the song."
    *   *Cause*: `SongRepository.insert` schema mismatch (missing Duration/Notes in INSERT stmt).
    *   *Status*: **Fixed** - Added regression test `test_insert_persists_full_object` and updated query.
*   [x] **UX: Chip Instant Save?**
    *   *Observation*: Users expect removing a chip to be "final/instant".
    *   *Status*: **Done** - Refactored to `EntityListWidget` which provides instant-reflex saving for Side Panel and relational managers (M2M).
*   [x] **UX: Chip Sorting Stability & Primary Genre**
    *   *Observation*: Adding "B" to "E" causes "B" to jump to front (Alphabetical auto-sort). Also primary genre (index 0) was lost on refresh.
    *   *Status*: **Done** - Implemented "Append Mode" in `EntityListWidget` + `ORDER BY rowid` in DB + Atomic `set_primary` save logic.
*   [x] **Verify Multi-Edit Logic**
    *   *Task*: Tests confirmed adding/removing tags in multi-select mode correctly uses intersection/union logic.
*   [x] **Tech Debt Audit (Genre/Mood)**
    *   *Audit*: Search for and remove lingering hardcoded "Genre/Mood" logic (Tech Debt) in favor of generic `TagService`.
*   [x] **Bug: Filter Tree LED Disappears**
    *   *Issue*: Clearing the search bar causes the checkbox LEDs in the filter tree to vanish.
*   [x] **Bug: Publisher Multi-Edit & RecordingPublishers Implementation**
    *   *Issue*: Publisher multi-editing fails because backend logic for `RecordingPublishers` (Song-Level) was missing.
    *   *Status*: **Done** — Implemented `RecordingPublishers` M2M table, ID-based `SongSyncService` priority, and "Effective View" waterfall logic (Grid = Inheritance, Editor = Direct links).
    *   *Reference*: T-180.
*   [x] [**Universal "Data Editor" Refactor**](tasks/T-85_universal_input_dialog.md) (T-85)
    *   *Status*: **Done** (Absorbed into `EntityPickerDialog`).
*   [x] **Unify Entity Creation UI**
    *   *Task*: Ensure all "Add Person" buttons (Creator, Artist, Group Member) use the standard `EntityPickerDialog` UI (same as Composer).
    *   *Goal*: Eliminate formatting discrepancies between different creation dialogs.
*   [x] **Bug: Ghost Chips (Staging/Parsing)**
    *   *Report*: "Ika MatančevićVedran Cvetojević Werone," should create 2 people... but we don't have time to look into that... i just wanna know why it created a person that i can't delete in the composers"
    *   *Analysis*: Parsing failure created a composite entity (bad name) which got staged. Immediate delete works on DB, but Staging buffer (from the paste) revives it in UI.
*   [x] **Bug: Publisher Creation Missing**
    *   *Report*: "can't add a publisher... prolly due to missing create..."
    *   *Issue*: Publisher Picker likely lacks "Create New" button or logic to handle non-existent publishers.
    *   *Status*: **Fixed** - Removed type check logic in `EntityPickerDialog` that ignored typeless entities (Publishers).


##  Pending Work Estimates
Quick reference for remaining tasks.

| Priority | Task | Estimate |
| :--- | :--- | :--- |
| Low | Advanced Rule Editor (New Feature) | ~2.0h |
| Low | Filename -> Metadata Parser (Custom Patterns) | ~2.5h |

**Total Critical Path:** 0.0h (Release Candidate Ready)
**Total All:** ~2.5h
