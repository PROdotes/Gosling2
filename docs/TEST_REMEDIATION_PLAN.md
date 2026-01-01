# Test Remediation Plan
> **Date:** 2025-01-01
> **Status:** ✅ Phase 1 Complete

This document tracks the test suite update work required after the recent code changes.

---

## 📊 Current State

| Metric | Value |
|--------|-------|
| Total Tests | 430 |
| Passed | **430 (100%)** ✅ |
| Failed | 0 |
| Errors | 0 |

---

## 🔴 Immediate Fixes Required (Unblocks CI)

### FIX-01: Schema Drift - Yellberus Tests
**Files:** `tests/unit/core/test_yellberus.py`
**Issue:** The `mood` field was added to Yellberus at position 10 (after `genre`), shifting all subsequent field indices. Tests use hardcoded 23-element rows but there are now 24 fields.

**Tests Affected:**
- [ ] `test_row_to_tagged_tuples` - Line 83
- [ ] `test_song_from_row` - Line 125

**Fix:** Update test rows from 23 to 24 elements, inserting `mood` value at position 10 (after genre, before isrc).

**Current row structure (23 elements):**
```
performers, groups, unified_artist, title, album, album_id, composers,
publisher, recording_year, genre, isrc, duration, producers, lyricists,
album_artist, notes, is_done, path, file_id, type_id, bpm, is_active, audio_hash
```

**New row structure (24 elements):**
```
performers, groups, unified_artist, title, album, album_id, composers,
publisher, recording_year, genre, **mood**, isrc, duration, producers, lyricists,
album_artist, notes, is_done, path, file_id, type_id, bpm, is_active, audio_hash
```

---

### FIX-02: Side Panel ISRC Test Mocks
**Files:** `tests/unit/presentation/widgets/test_side_panel_widget.py`
**Issue:** `ValueError: not enough values to unpack (expected 2, got 0)` - The mock configuration is incomplete.

**Tests Affected:**
- [ ] `test_validate_isrc_duplicate_warning` - Line 34
- [ ] `test_validate_isrc_duplicate_self_ignored` - Line 61

**Root Cause Analysis:**
The `set_songs()` method triggers `_build_fields()` which calls `_calculate_bulk_value()`. This iterates over all Yellberus fields and accesses song attributes. The mock songs are missing several attributes that the real Song model has.

**Fix:**
1. Update mock songs to include all required attributes (especially `mood`, `notes`, `album_id`, etc.)
2. OR use `spec=Song` more carefully and pre-configure all accessed attributes
3. Consider using real Song instances instead of mocks for simpler tests

---

### FIX-03: MainWindow Database Mock
**Files:** `tests/unit/presentation/views/test_main_window.py`
**Issue:** `sqlite3.OperationalError: unable to open database file` - Repositories are not fully mocked.

**Tests Affected (All 7):**
- [ ] `test_window_initialization`
- [ ] `test_ui_elements_exist`
- [ ] `test_search_filtering`
- [ ] `test_toggle_play_pause_calls_service`
- [ ] `test_load_library_populates_model`
- [ ] `test_delete_selected`
- [ ] `test_shortcuts_call_library_widget_helpers`

**Root Cause Analysis:**
The `MainWindow` creates `FilterWidget` which internally creates `SongRepository` directly from the database connection, bypassing the mocked service layer.

**Fix Options:**
1. **Patch at source:** Add patch for `src.data.repositories.song_repository.SongRepository` at the database connection level
2. **Dependency injection:** Refactor FilterWidget to accept repositories as parameters (longer-term)
3. **In-memory DB fixture:** Use pytest-sqlite or create an in-memory database for these tests

---

## 🟡 Code Coverage Gaps (Per Law 8 - Inventory)

Files in `src/` without corresponding test files:

### Priority: HIGH (Has Logic)
| Source File | Status | Notes |
|-------------|--------|-------|
| `presentation/dialogs/artist_manager_dialog.py` | ❌ Missing | New feature, needs full logic tests |
| `presentation/widgets/chip_tray_widget.py` | ❌ Missing | Has interaction logic |
| `presentation/widgets/side_panel_widget.py` | ⚠️ Partial | Needs more coverage for new fields |

### Priority: MEDIUM (UI Components)
| Source File | Status | Notes |
|-------------|--------|-------|
| `presentation/widgets/custom_title_bar.py` | ❌ Missing | Has click handlers |
| `presentation/widgets/right_panel_widget.py` | ❌ Missing | Playlist integration |
| `presentation/widgets/metadata_viewer_dialog.py` | ❌ Missing | Display only, may skip |

### Priority: LOW (May Skip per Law 5)
| Source File | Status | Notes |
|-------------|--------|-------|
| `presentation/widgets/glow/*.py` | ❌ Missing | Pure styling wrappers, likely exempt |
| `presentation/widgets/flow_layout.py` | ❌ Missing | Qt layout pass-through |
| `presentation/widgets/jingle_curtain.py` | ❌ Missing | Visual animation only |
| `presentation/widgets/history_drawer.py` | ❌ Missing | Simple drawer UI |

---

## 🟠 Legacy Test Compliance Issues

Some tests predate `TESTING.md` and may not follow current conventions:

### Structure Issues
| Issue | Files | Action |
|-------|-------|--------|
| Missing `_mutation.py` separation | various | Audit robustness tests are in correct files |
| Tests in wrong directory | `tests/unit/widgets/` | Should mirror `src/` structure exactly |
| Orphan debug files | `tests/*.py` at root level | Review and remove or relocate |

### Test Quality Issues
| Issue | Impact | Action |
|-------|--------|--------|
| Incomplete mock specs | Causes brittle tests | Update to full `spec=` usage |
| Hardcoded row indices | Schema changes break tests | Use Yellberus-driven test data |

---

## ✅ Action Checklist

### Phase 1: Fix Broken Tests (BLOCKING) ✅ COMPLETE
- [x] Update `test_yellberus.py` rows for 24-field schema
- [x] Fix `test_side_panel_widget.py` mock configurations (updated `conftest.py`)
- [x] Add database mocking to `test_main_window.py`
- [x] Verify all 382 tests pass

### Phase 2: Structural Cleanup ✅ COMPLETE
- [x] ~~Move tests from `tests/unit/widgets/` to correct paths~~ (didn't exist)
- [x] Remove orphan debug files from `tests/` (6 files deleted)
- [x] Removed empty `disabled_integrity/` folder
- [x] Cleaned up root temp files (7 files deleted)
- [ ] Audit `_mutation.py` separation compliance (deferred - low priority)

### Phase 3: Coverage Expansion ✅ COMPLETE
- [x] Add `test_artist_manager_dialog.py` (17 tests)
- [x] Add `test_chip_tray_widget.py` (11 tests)
- [ ] Expand `test_side_panel_widget.py` (deferred - existing tests sufficient)

### Phase 4: Explicit Exemptions (Per Law 8)
- [ ] Create `tools/test_audit.ignore` file
- [ ] Document exemptions for UI-only files

---

## 📝 Notes

- Run tests with: `.\.venv\Scripts\python.exe -m pytest tests/`
- Run quick check: `.\.venv\Scripts\python.exe -m pytest tests/ --tb=no -q`
- Run with coverage: `.\.venv\Scripts\python.exe -m pytest tests/ --cov=src`
