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
*Status: After Schema Fix*
*   [ ] **T-04 Test Consolidation** (~3.0 h)
    *   *Why*: Merging 56 files makes future features faster/safer.
    *   *Risk*: Low (Boring work).

### �️ Milestone 3: Usable UI (Backlog Enabler)
*Status: Required for processing 400-song backlog*
*   [ ] **Side Panel Alpha** (~3.0 h)
    *   *Task*: Basic metadata editor panel (Genre, Artist, Album, Done).
    *   *Why*: Can't efficiently edit songs without it.
*   [ ] **Auto-Renamer** (~3.5 h)
    *   *Task*: Port Genre/Year rules + `shutil.move` logic.
    *   *Complexity*: High (File System Risk). Rules documented in `LEGACY_LOGIC.md`.
*   [ ] **Legacy Shortcuts** (~1.0 h)
    *   *Task*: `Ctrl+D` (Done) and `Ctrl+S` (Save).
    *   *Ref*: T-31.
*   [ ] **UX Polish** (~2.0 h)
    *   *Task*: Dark theme, consistent button styling.
    *   *Note*: Keep default PyQt6 components. Custom tag picker DEFERRED to 1.0.

### 🚧 Milestone 4: Data Integrity
*Status: Queue*
*   [ ] **Duplicate Detection** (~2.5 h)
    *   *Task*: Tiered Import Check (ISRC -> Hash -> Meta).
    *   *Complexity*: Medium.

### 🔮 Milestone 5: Safety & Trust (The "0.1.0" Gate)
*Status: Queue*
*   [ ] **Audit Log (History)** (~1.0 h)
    *   *Task*: Record INSERT/UPDATE events.
*   [ ] **Settings UI** (~1.5 h)
    *   *Task*: UI for Root Directory & Rules.
*   [ ] **Tag Verification** (~1.0 h)
    *   *Task*: Verify `TXXX:GOSLING_DONE` and ID3 writes.

---

## 📉 Technician's Corner (Tech Debt)
*Non-blocking, but beneficial.*

*   [ ] **Generic Repository** (~2.0 h): Refactor repetitive CRUD code.
*   [ ] **ID3 Logic Extraction** (~1.0 h): Deduplicate JSON lookup.

---

## 🏁 Release Criteria (0.1.0)
1.  Can Import 1,000 songs without crashing.
2.  Detects duplicates accurately.
3.  Renames files to correct folder structure on Save.
4.  Writes all ID3 tags (including custom ones) verified.
5.  Persists all changes to DB with History log.
