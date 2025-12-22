# 📅 Daily Plan: The Push for Legacy Sync

**Date**: December 22, 2025
**Driver**: Orion
**Focus**: **T-06 Legacy Sync** (Data Integrity Track)

---

## 🌅 Morning Startup (Completed)
- [x] **Context Sync**: Read `temp.md` and `MORNING_NOTES.md`.
- [x] **Sanity Check**: Full test suite PASSED (358 tests).
- [x] **Test Audit**: Confirmed `test_database_schema.py` is ACTIVE (will yell on schema changes).

---

## 🔨 The Work Plan (For When You Return)

We have prioritized **Features (Legacy Sync)** over Cleanup, but we acknowledge the critical flaws.

### 1. Critical Flaws Check (Immediate)
*Why: Ensure we aren't building on quicksand.*
- [ ] **Field Editor Verification**: Open `tools/field_editor.py` and verify it writes `yellberus.py` correctly without "Blue Drift" (Doc/Code mismatch).
- [ ] **Groups Logic**: Confirm the "Zombie" column `S.Groups` is effectively disabled and not leaking into new queries.

### 2. T-06 Legacy Sync (The Main Event)
*Why: Bring Gosling 2 to parity with Gosling 1 metadata standards.*

**Step A: Schema Expansion**
- [ ] Update `DATABASE.md` to include:
    - `Album` (Text? Registry?) -> likely Text for now to match G1.
    - `Genre` (Text/Registry).
    - `Publisher` (Text).
- [ ] **Expectation**: `test_database_schema.py` will FAIL here. We will fix it immediately.

**Step B: Registry Update (The "Sheriff")**
- [ ] Use `field_editor.py` (or manual edit if safer) to register these fields in `yellberus.py`.
- [ ] Ensure `id3_frames.json` mappings exist (TALB, TCON, TPUB).

**Step C: Implementation**
- [ ] Update `SongRepository` to read/write these new fields.
- [ ] Verify they appear in the UI (Library Widget).

### 3. Cleanup (If Time Allows)
*Why: The test suite is messy (56 files), but it works.*
- [ ] **T-04 Test Consolidation**: Merge `test_song_repository_extra.py` into `test_song_repository.py`.
- [ ] **Consolidate Widgets**: Merge `test_library_widget_*.py` files.

---

## 📝 Closing the Day
- [ ] Update `TASKS.md` with T-06 progress.
- [ ] Log any "yelling" incidents in `temp.md` for the next sibling.
