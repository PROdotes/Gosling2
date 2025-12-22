# 📅 Daily Plan: The Push for Legacy Sync

**Date**: December 22, 2025
**Driver**: Orion
**Focus**: **T-06 Legacy Sync** (Data Integrity Track)

---

## 🌅 Morning Startup (Completed)
- [x] **Context Sync**: Read `temp.md` and `MORNING_NOTES.md`.
- [x] **09:00 - 11:30**: Field Editor (Defaults, UI) - **Complete**.
- [x] **11:30 - 13:30**: Unified Artist (Groups Fix) - **Complete**.
- [x] **14:30 - 16:00**: Legacy Sync (Phase 1: Albums) - **Complete** (with pins).
    - [x] Schema: `Albums`, `SongAlbums`.
    - [x] Repository: `AlbumRepository`.
    - [x] Integration: `SongRepository` sync logic.
    - [!] **PINNED**: Album Uniqueness (Greatest Hits Paradox).
    - [!] **PINNED**: `_sync_album` implementation review.

---

## 🔨 The Work Plan (For When You Return)

We have prioritized **Features (Legacy Sync)** over Cleanup, but we acknowledge the critical flaws.

### 1. Critical Flaws Check (Immediate) — ETA: 30 min
*Why: Ensure we aren't building on quicksand.*
- [x] **Field Editor Verification**: Open `tools/field_editor.py` and verify it writes `yellberus.py` correctly without "Blue Drift" (Doc/Code mismatch). (✅ Fixed multiple bugs: ID3 popup, DB popup, Defaults drift)
- [x] **Groups Logic**: Confirm the "Zombie" column `S.Groups` is effectively disabled and not leaking into new queries. (✅ Fixed: Deleted leaking `get_all_groups` method; Implemented strict Performer+Alias logic)

### 2. T-06 Legacy Sync (The Main Event) — **COMPLETE**
*Why: Bring Gosling 2 to parity with Gosling 1 metadata standards.*
> **Briefing**: [Read T-06_LEGACY_SYNC_BRIEF.md](design/state/T06_LEGACY_SYNC_BRIEF.md) for architectural constraints.
- [x] **Step A: Schema Expansion**: Implement Relational Tables.
    - [x] `Albums`: Schema, Repository, M2M, Case-Insensitive, Update.
    - [x] `Publishers`: Schema, Repository, M2M, Hierarchy.
    - [x] `Tags` (Genres): Schema, Repository, M2M.
- [x] **Yellberus Integration**:
    - [x] Fields (Album, Publisher, Genre) added to `yellberus.py`.
    - [x] Sync Logic (`_sync_album`, `_sync_publisher`, `_sync_genre`) implemented & hooked.
    - [x] Filter Widget verified dynamic updates.
- [x] **Verification**:
    - [x] Tests: `test_t06_albums.py` (9 pass), `test_t06_publishers.py`, `test_t06_tags.py` (4 pass).
    - [x] Visual: Filters appear and work.

**Step B: Registry Update (The "Sheriff")**
- [x] Use `field_editor.py` to register fields. (Confirmed via UI).

**Step C: Implementation**
- [x] `SongRepository` syncs all fields on update.
- [x] Verified via `inject_fixtures.py`.

### 3. Cleanup & Next Steps
- [ ] **Data Integrity**: Address "Greatest Hits Paradox" (Pinned).
- [ ] **Refactor**: Generic Repository Pattern (Logged in TASKS).
- [ ] **Cleanup**: `test_song_repository_extra.py` merge.
*Why: The test suite is messy (56 files), but it works.*
- [ ] **T-04 Test Consolidation**: Merge `test_song_repository_extra.py` into `test_song_repository.py`.
- [ ] **Consolidate Widgets**: Merge `test_library_widget_*.py` files.

---

---

## � Next Day Plan: The Cleanup & Refactor
**Focus**: T-04 (Test Cleanup) & T-?? (File System Logic).

### 1. The Great Test Consolidation (T-04) — **ETA: 1.5h**
*   Merge `test_song_repository_extra.py` (and friends) into a clean suite.
*   Consolidate `test_library_widget_*.py`.
*   Goal: Reduce 56 test files -> manageable number.

### 2. The Pins (Tech Debt) — **ETA: 1h**
*   **Greatest Hits Paradox**: Solve Album Uniqueness (Schema change: `AlbumArtist` or `Unique Constraint`?).
*   **Repository Duplication**: Discuss/Draft Generic Repository pattern.

### 3. File System Logic (T-19?) — **ETA: 3-4h**
*   **Auto-Renamer**: Implement `LegacyFolderRouter` (Auto-move songs based on Genre/Year).
*   **Duplicate Detection**: Tiered check on import (ISRC -> Hash).
*   *Ref*: `LEGACY_LOGIC.md` Items 3 & 4.

**Britney signing off.** 🎤
---

## 🔖 Meta: Migrate to SEMVER-Based Planning

**Problem**: Current priority system (P0/P1/P2 or "Critical/High/Low") is ambiguous. Features drift between sessions because there's no clear "this ships in version X" contract.

**Solution**: Adopt **Semantic Versioning** for release planning.

### Proposed Structure:
| Version | Scope | Features | ETA |
|---------|-------|----------|-----|
| `0.1.0` | **Alpha** – Today's work | T-06 Legacy Sync, Cleanup | Today |
| `0.2.0` | **Alpha** – Stability | Bug fixes, test consolidation | This week |
| `0.9.0` | **Beta** – Feature-complete | T-16 Advanced Search, polish | TBD |
| `1.0.0` | **Release** – Production-ready | All core features stable | TBD |

**Already Merged** (in current build):
- ✅ T-17 Unified Artist View
- ✅ T-18 Column Persistence
- ✅ T-19 Field Editor Hardening

### Action Items:
- [ ] Create `ROADMAP.md` with version milestones.
- [ ] Tag each task file (T-XX) with its target version.
- [ ] Define "Done" criteria for `1.0.0` release.
