# 📅 Daily Plan: The Cleanup & Refactor

**Date**: December 23, 2025
**Driver**: Voltage
**Focus**: **T-04 Test Consolidation** & **Tech Debt**

---

## 🌅 Morning Startup
- [x] **Context Sync**: Read `tasks.md` and previous `today.md`.
- [x] **Prep**: `T04_TEST_CONSOLIDATION_PLAN.md` created. `LEGACY_LOGIC.md` updated.
- [x] **Big Picture**: Plan defined below.

---

## �️ The Battle Plan: Structure Before Scale

**Theme**: Cleaning the foundation so we can handle the complexity of File System logic later.

### Phase 1: The "Clean Sweep" (T-04) — **Morning**
*   **Goal**: De-fragment the Test Suite (68 files -> ~20 files).
*   **Why**: The current sprawl makes TDD painful. We need strict "Class per Component" rules.
*   **Action**:
    *   Execute `T04_TEST_CONSOLIDATION_PLAN.md`.
    *   Targets: `SongRepository`, `MetadataService`, `PlaybackService`, `LibraryWidget`.

### Phase 2: The "Greatest Hits" Fix — **Mid-Day**
*   **Goal**: STOP Albums from merging incorrectly.
*   **Why**: "Greatest Hits" (Queen) and "Greatest Hits" (ABBA) currently become one album.
*   **Action**:
    *   Schema Update: Add `AlbumArtist` or Compound Constraint to `Albums` table.
    *   Update `AlbumRepository` logic.

### Phase 3: The "Renamer" (File System) — **Afternoon**
*   **Goal**: Implement the Legacy Folder Router.
*   **Why**: We need to prove we can organize files exactly like Gosling 1 (`Z:\Songs\<Genre>\<Year>`).
*   **Action**:
    *   Port routing logic from `LEGACY_LOGIC.md`.
    *   Implement `RenamingService`.

---

## 📅 The Horizon (0.1.0 Alpha)
See [ROADMAP.md](ROADMAP.md) for the full journey to Feature Completion.

---

## � Notes & Findings
*   *Space reserved for today's discoveries.*

