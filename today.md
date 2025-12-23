# 📅 Daily Plan: Schema Fix & Foundation

**Date**: December 23, 2025  
**Driver**: Vesper (The Jaded Archivist)  
**Focus**: **Greatest Hits Fix** → **Test Consolidation** (if time permits)

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

### Phase 2: The "Clean Sweep" (T-04) — **Mid-Day** (~3h)
*   **Goal**: De-fragment the Test Suite (68 files → ~20 files).
*   **Why**: The current sprawl makes TDD painful. Strict "One Test File per Component" rule.
*   **Action**:
    *   Execute `T04_TEST_CONSOLIDATION_PLAN.md`.
    *   Targets: `SongRepository`, `MetadataService`, `PlaybackService`, `LibraryWidget`.
*   **Exit Criteria**:
    - [ ] Test file count reduced to target (~20).
    - [ ] All tests pass (`pytest` green).
    - [ ] No orphaned test files in `/tests`.

---

### Phase 3: The "Renamer" (File System) — **DEFERRED** ⏸️
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

