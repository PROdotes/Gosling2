# Optimization & Cleanup Audit

**Date:** 2026-04-19
**Scope:** Full codebase (`src/`, `tests/`)

---

## HIGH PRIORITY

### 1. `[DEBUG]` console.log statements in production
5 debug logs in `src/static/js/dashboard/renderers/song_editor.js` at lines 141, 155, 160, 183, 188. Retain objects in console preventing GC.

### 2. Unused imports in `main.js`
7 dead imports at lines 22, 35, 44, 47, 51, 55, 61: `getTagCategories`, `setPrimarySongTag`, `activateInlineEdit`, `closeScrubberModal`, `closeSplitterModal`, `closeSpotifyModal`, `formatCountLabel`.

### 3. `getState()` ReferenceError in `updateCachedIngestResult`
`src/static/js/dashboard/main.js:299` — called without `this.`, silently fails at runtime.

### 4. Duplicate `currentMode` property in state object
`src/static/js/dashboard/main.js:111` and `129` — second declaration silently overwrites first.

### 5. Redundant `getCatalogSong` after `patchSongScalars`
`src/static/js/dashboard/renderers/song_editor.js:277-280` — doubles network round-trip per field save.

### 6. 18 silent `except Exception:` blocks with no logging
`src/services/edit_service.py` — all catch blocks do `conn.rollback(); raise` but log nothing, making debugging impossible.

### 7. ~~Stale TODO comment~~ — DONE
Removed stale TODO from `src/services/catalog_service.py:1`.

### 8. ~~Unsafe `json.load(open(path))`~~ — DONE
Fixed with `with open(...)` context manager in `src/engine/routers/catalog.py:575`.

---

## MEDIUM PRIORITY

### 9. `escapeHtml` duplicated 3x
Canonical version in `utils.js:19`, local copies in `song_editor.js:10` and `chip_input.js:19` (named `escHtml`).

### 10. Modal lifecycle boilerplate (7 modals)
All modals repeat: `overlay.style.display` toggling, Escape keydown listener, click-outside-to-close. ~100 lines of duplication across `confirm_modal.js`, `scrubber_modal.js`, `filename_parser_modal.js`, `spotify_modal.js`, `splitter_modal.js`, `link_modal.js`, `edit_modal.js`.

### 11. Autocomplete dropdown logic duplicated
~200 lines of identical debounced search + Arrow key navigation + dropdown rendering in `link_modal.js` (lines 65-278) and `edit_modal.js` (lines 139-267).

### 12. Entity renderer boilerplate (4 renderers)
~80 lines of identical `setState` + `updateResultsSummary` + entity-list-title + bulk-delete + empty-state pattern across `publishers.js`, `tags.js`, `artists.js`, `albums.js`.

### 13. `import * as api` in 5 files
Prevents tree-shaking of 60+ exports. Affected: `orchestrator.js:1`, `navigation.js:6`, `song_actions.js:6`, `web_search.js:6`, `filter_sidebar.js:6`.

### 14. ~~`processing_status` as bare integers across entire stack~~ — DONE
Added `ProcessingStatus(IntEnum)` in `src/engine/config.py` and `PROCESSING_STATUS` frozen object in `src/static/js/dashboard/constants.js`. All bare integers replaced across 10 source files.

### 15. ~~`_SCALAR_ALLOWED` / `_METADATA_ALLOWED` duplicated~~ — DONE
Moved to `src/engine/config.py` as `SCALAR_ALLOWED` / `METADATA_ALLOWED`. Both services now import from config.

### 16. 6-8 sequential SQL queries for hydration/deep search
`src/services/library_service.py:269-345` — song hydration does 4-6 queries; deep search does up to 8. Could combine with JOINs/CTEs.

### 17. 5 permanent keydown listeners across modals
All fire on every keystroke even when closed. Should register on open, remove on close.

### 18. Private method access across services
`IngestionService` calls `LibraryService._hydrate_songs()` — breaks encapsulation.

### 19. ~~Pydantic models scattered in router files~~ — DONE
Moved `AddAliasBody`, `UpdateLegalNameBody`, `SetIdentityTypeBody`, `AddMemberBody` to `src/models/view_models.py`. Removed unused `BaseModel` imports from both routers.

### 20. ~~Duplicate `_get_service()` factory~~ — SKIPPED
3-line factory, not worth extracting. Identical in `catalog.py` and `song_updates.py`.

### 22. ~~5 bare `except: pass` blocks~~ — SKIPPED
All are legitimate: specific exception types in metadata parsing, intentional silent handling.

---

## LOW PRIORITY

### 21. God-files needing splitting
- `main.js` (999 lines): search, mode switching, event delegation, ingestion, detail loading
- `song_actions.js` (954 lines): inline edit flows and modal coordination

### 22. 5 bare `except: pass` blocks
`metadata_service.py:59`, `metadata_parser.py:69,81,98`, `tools.py:149,154` — silently swallow errors.

### 23. Full innerHTML rebuilds on every update
Song list (`songs.js:185`), song editor (`song_editor.js:746`), filter sidebar (`filter_sidebar.js:310-513`) — all destroy and recreate DOM on each change.

### 24. Hardcoded color values in JS
`song_actions.js:14,21,32` — `#888`, `#4caf50`, `#f44336` should be CSS variables.

### 25. 8 untested Python services
`edit_service.py` (834 lines), `catalog_service.py` (525 lines), `identity_service.py` (260 lines), `library_service.py` (537 lines), `logger.py` (79 lines), `metadata_frames_reader.py` (77 lines), `filing_service.py` (185 lines), `audit_service.py` (75 lines).

### 26. 23 of 27 JS source files have zero tests
All renderers, handlers, most components, and core modules (`main.js`, `orchestrator.js`, `api.js`) are untested.

### 27. Inconsistent test directory structure
`tests/data/` vs `tests/test_data/`, `tests/services/` vs `tests/test_services/` — confusing overlap.

### 28. No SQLite connection pooling
`base_repository.py:13-28` — new connection + PRAGMA + collation registration per call.
