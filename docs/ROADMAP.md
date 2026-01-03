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
*   [ ] **T-61 Universal Tag Picker** (Search/Tree Dialog)
*   [x] [**T-70 Artist Selector**](tasks/T-70_artist_manager_plan.md) (Database-backed Picker)
*   [x] **Multi-Album Infrastructure** (T-22/T-63)
    *   *Status*: **Core Schema & Logic Done**.
    *   *Ref*: `PROPOSAL_MULTI_ALBUM_INFRASTRUCTURE.md`.
*   [ ] **Audit Log (History)** (T-05) (~1.0 h)
    *   *Task*: Record INSERT/UPDATE events.
*   [ ] **Settings UI** (T-52) (~1.5 h)
    *   *Task*: UI for Root Directory & Rules.
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

---

## 📉 Technician's Corner (Tech Debt)
*Non-blocking, but beneficial.*

*   [ ] **Generic Repository** (~2.0 h): Refactor repetitive CRUD code.
*   [x] **ID3 Logic Extraction** (~1.0 h): Deduplicate JSON lookup.
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
