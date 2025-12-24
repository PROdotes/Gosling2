# 📅 Daily Plan: Schema Fix & Foundation

**Date**: December 24, 2025  
**Driver**: Antigravity (The Noir Detective)  
**Focus**: **Test Consolidation (T-04)** & **UI Bug Fixes**

---

## 🌅 Morning Startup
- [x] **Context Sync**: Read `AGENT_PROTOCOL.md`, `tasks.md`, previous `today.md`.
- [x] **Planning Session** (~1h): 
    - Revised phase order (schema before tests)
    - Expanded 0.1 scope to include Side Panel + Renamer for backlog processing
    - Created `VERSION_PLAN.md` (broad 0.1 → 1.0 strategy)
    - Logged T-33 (AI Playlist) and T-34 (MD Tagging Conventions)
    - Updated `ROADMAP.md` with revised milestones
- [ ] **Execute**: Phase 1 below.

---

## ⚔️ The Battle Plan: Schema First, Then Structure

**Theme**: Fix the data model before consolidating tests. Don't do double work.

**Revised by**: Vesper (The Jaded Archivist)  
**Rationale**: If we consolidate tests *then* change the schema, we rewrite those tests twice. Schema first.

---

### Phase 1: The "Greatest Hits" Fix — **Morning** (~2h)
*   **Goal**: STOP Albums from merging incorrectly.
*   **Why**: "Greatest Hits" (Queen) and "Greatest Hits" (ABBA) currently become one album. This is **data corruption**.
*   **Action**:
    *   Schema Update: Add `AlbumArtist` column or compound unique constraint to `Albums` table.
    *   Update `AlbumRepository` logic to use artist context.
*   **Exit Criteria**:
    - [x] Schema migration applied. ✅ `AlbumArtist` column added to Albums table.
    - [x] `AlbumRepository.get_or_create()` uses artist disambiguation. ✅ `find_by_key()` implemented.
    - [x] Manual test: Import two "Greatest Hits" albums from different artists → they remain separate. ✅ Verified via `inject_fixtures.py`.
    - [x] Unit tests added and passing (14 tests including Bobby Tables). ✅
    - [x] Documentation updated (`DATABASE.md`, `TOOLS.md`, `ARCHITECTURE.md`). ✅
    - [x] Follow-up logged: T-37 (Album Filter Disambiguation). ✅

---

### Phase 2: The "Pivot" (T-38) — **Afternoon**
*   **Goal**: Refactor `MetadataService` to remove hardcoded field mapping (T-38).
*   **Why**: Critical Blocker for 0.1.0 reliability.
*   **Exit Criteria**:
    - [x] `id3_frames.json` integrated.
    - [x] `write_tags` uses loop + special handling for Year/Producers.
    - [x] Sparse Update logic fixed (Critical Bug squashed).
    - [x] 16/16 tests passing (Legacy + New).
    - [x] `yellberus.py` REVERTED to pristine state.

---

### Phase 3: The "Clean Sweep" (T-04) — **COMPLETE** ✅
*   **Goal**: De-fragment the Test Suite (68 files → ~46 files).
*   **Status**: 100% complete

### Phase 4: Prioritizing Tooling (Milestone 3) — **IN_PROGRESS**
*   **Goal**: Enable backlog processing (Editor + Renamer).
*   **Action**:
    - [ ] Task 1: Side Panel Editor.
    - [ ] Task 2: Auto-Renamer.
    - [ ] Task 7: Test Inventory Tool.
*   **Action**:
    - [x] Create detailed Runbook (`design/specs/T04_TEST_CONSOLIDATION_PLAN.md`).
    - [x] Create `tests/README.md`.
    - [x] **Execute Consolidation (Data Layer)**. ✅
    - [x] **Fix Critical Hanging Test** (`test_library_widget.py`). ✅
    - [x] **Execute Consolidation (MetadataService)**. ✅
    - [x] **Execute Consolidation (Playback Service)**. ✅
    - [x] **Execute Consolidation (Presentation Layer)**: `LibraryWidget` and `PlaylistWidget` merged. ✅
    - [x] **Final Cleanup**: Move orphan integrity tests and run final coverage. ✅
*   **Exit Criteria**:
    - [x] Test file count reduced to target (Result: 46 files).
    - [x] All tests pass (`pytest` green).
    - [x] No orphaned test files in `/tests` (Clean!).

---

### Phase 4: The "Renamer" (File System) — **DEFERRED** ⏸️
*   **Status**: Pushed to a future session.
*   **Why**: File system operations deserve a fresh, full session—not a rushed afternoon.
*   **Prereqs**: Phase 1 (Greatest Hits) must be complete so album artist routing works correctly.

---

## 📅 The Horizon (0.1.0 Alpha)
See [ROADMAP.md](ROADMAP.md) for the full journey to Feature Completion.

---

## 📝 Notes & Findings
*   **Vesper's Observation**: Context order affects LLM reasoning. Sparky likely anchored on Britany's doc order.
*   **Workflow Context**: User has 400-song backlog waiting for processing. Workflow is:
    1. Import → 2. Filter "not done" → 3. Preview 10-20s → 4. Edit (Artist, Album, Genre) → 5. Mark Done → 6. Auto-move to `\\onair\b\songs`
*   **0.1 Scope Expansion**: Side Panel + Renamer are required for backlog workflow. Without them, 400 songs = 400 manual file moves.
*   **UI Scope**: Keep default PyQt6 styling for now. Dark theme + consistent buttons = 0.1. Custom tag picker = 1.0.

---

## 🔄 Handoff Note (Dec 24, 15:40)

**Session completed:** T-04 Test Consolidation (COMPLETE) ✅

### What Was Done This Session:
1.  **Test Suite Consolidated**:
    *   Files reduced from **68 → 46**.
    *   Full suite passing: `pytest` (397 tests passed).
    *   Orphans cleared, Integrity tests moved to correct folder.

2.  **Performance Optimization (Field Editor)**:
    *   Identified huge bottleneck in `test_field_editor.py` (~20s -> ~1.5s).
    *   Implemented `blockSignals` in `_populate_table` for UI speedup.
    *   Removed redundant teardown reloads.

3.  **Coverage Check**:
    *   `MetadataService`: 92% (Excellent).
    *   `FieldEditor` (UI): 75% (Logic covered, Persistence logic pending Mutations).

### Next Session TODO:
1.  **Create Mutation Tests**: `tests/unit/tools/test_field_editor_mutation.py` to cover `write_yellberus` (File System/Persistence).
2.  **Start Milestone 3**: Begin work on **Task 1: Side Panel Editor** (Backlog Processing).

### Key References:
- `TESTING.md`: Laws 1-7 (The Constitution).
- `design/specs/WORK_QUEUE.md`: The prioritized feature list.
