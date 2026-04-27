# Optimization & Cleanup Audit

**Date:** 2026-04-19
**Scope:** Full codebase (`src/`, `tests/`)

---

## HIGH PRIORITY

- [x] **1.** `[DEBUG]` console.log statements in production — `song_editor.js:141,155,160,183,188`
- [x] **2.** Unused imports in `main.js` — 7 dead imports at lines 22,35,44,47,51,55,61
- [x] **3.** `getState()` ReferenceError — `main.js:299` called without `this.`
- [x] **4.** Duplicate `currentMode` property — `main.js:111` and `129`
- [x] **5.** Redundant `getCatalogSong` after `patchSongScalars` — `song_editor.js:277-280`
- [x] **6.** 18 silent `except Exception:` blocks — `edit_service.py` no logging on rollback
- [x] **7.** Stale TODO comment — `catalog_service.py:1`
- [x] **8.** Unsafe `json.load(open(path))` — `catalog.py:575`

## MEDIUM PRIORITY

- [x] **9.** `escapeHtml` duplicated 3x — `utils.js:19`, `song_editor.js:10`, `chip_input.js:19`
- [x] **10.** Modal lifecycle boilerplate — ~100 lines across 7 modals
- [x] **11.** Autocomplete dropdown logic duplicated — ~200 lines in link_modal.js + edit_modal.js + chip_input.js → extracted to autocomplete.js
- [ ] **12.** Entity renderer boilerplate — ~80 lines across 4 renderers
- [ ] **13.** `import * as api` in 5 files — prevents tree-shaking
- [x] **14.** `processing_status` as bare integers — replaced with `ProcessingStatus(IntEnum)` + JS constants
- [x] **15.** `_SCALAR_ALLOWED` / `_METADATA_ALLOWED` duplicated — moved to `engine/config.py`
- [ ] **16.** 6-8 sequential SQL queries for hydration/deep search — `library_service.py:269-345`
- [ ] **17.** 5 permanent keydown listeners across modals — should register on open, remove on close
- [x] **18.** Private method access across services — `IngestionService` calls `LibraryService._hydrate_songs()`
- [x] **19.** Pydantic models scattered in router files — moved to `view_models.py`
- [x] ~~**20.** Duplicate `_get_service()` factory~~ — SKIPPED, not worth extracting
- [x] ~~**22.** 5 bare `except: pass` blocks~~ — SKIPPED, all legitimate

## LOW PRIORITY

- [ ] **21.** God-files needing splitting — `main.js` (999 lines), `song_actions.js` (954 lines)
- [ ] **22.** 5 bare `except: pass` blocks — `metadata_service.py`, `metadata_parser.py`, `tools.py`
- [ ] **23.** Full innerHTML rebuilds on every update — `songs.js`, `song_editor.js`, `filter_sidebar.js`
- [ ] **24.** Hardcoded color values in JS — `#888`, `#4caf50`, `#f44336`
- [ ] **25.** 8 untested Python services — `edit_service`, `catalog_service`, `identity_service`, `library_service`, `logger`, `metadata_frames_reader`, `filing_service`, `audit_service`
- [ ] **26.** 23 of 27 JS source files have zero tests
- [ ] **27.** Inconsistent test directory structure — `tests/data/` vs `tests/test_data/`
- [ ] **28.** No SQLite connection pooling — `base_repository.py:13-28`
