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

### 🧹 Milestone 1: The Cleanup (Pre-Reqs)
*Status: Ready to Start*
*   [ ] **T-04 Test Consolidation** (~3.0 h)
    *   *Why*: Merging 56 files makes future features faster/safer.
    *   *Risk*: Low (Boring work).

### 🚧 Milestone 2: Legacy Sync Core (The Logic)
*Status: Blocked by Cleanup (Recommended)*
*   [ ] **Greatest Hits Fix** (~2.0 h)
    *   *Task*: Schema Change (AlbumArtist) + Logic Update.
    *   *Criticality*: High (Data Corruption).
*   [ ] **Auto-Renamer** (~3.5 h)
    *   *Task*: Port Genre/Year rules + `shutil.move` logic.
    *   *Complexity*: High (File System Risk).
*   [ ] **Duplicate Detection** (~2.5 h)
    *   *Task*: Tiered Import Check (ISRC -> Hash -> Meta).
    *   *Complexity*: Medium.
*   [ ] **Legacy Shortcuts** (~1.0 h)
    *   *Task*: `Ctrl+D` (Done) and `Ctrl+S` (Save).
    *   *Ref*: T-31.

### 🔮 Milestone 3: Safety & Trust (The "0.1.0" Gate)
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
