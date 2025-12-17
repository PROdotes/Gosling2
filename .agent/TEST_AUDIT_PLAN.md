# Test Suite Audit Plan

## Overview
Comprehensive audit of the Gosling2 test suite to identify redundancies, improve coverage, and ensure maintainability.

**Current Status:** 302 tests across 56 test files

## Objectives
1. Identify and remove duplicate/redundant tests
2. Consolidate overlapping test files
3. Improve test organization and naming
4. Ensure consistent test patterns
5. Identify coverage gaps
6. Remove obsolete tests

## Test File Inventory

### ✅ Well-Organized (Keep As-Is)
**Metadata Services (13 files):**
- `test_metadata_service.py` - Core extraction tests
- `test_metadata_write.py` - Core write tests (12 tests)
- `test_metadata_defensive.py` - Edge cases (11 tests)
- `test_metadata_additional.py` - Unknown frames, ID3 versions (5 tests)
- `test_metadata_fixtures.py` - Test fixtures
- `test_metadata_done_flag.py` - TKEY read/write
- `test_metadata_service_comprehensive.py` - ?
- `test_metadata_service_coverage.py` - ?
- `test_metadata_service_mutation.py` - ?
- `test_metadata_service_schema.py` - ?

**Action:** Review comprehensive/coverage/mutation/schema files for overlap

### ⚠️ Potential Redundancy
**Repository Tests (11 files):**
- `test_song_repository.py` - Main tests
- `test_song_repository_extra.py` - Extra tests (redundant?)
- `test_song_repository_mutation.py` - Mutation tests
- `test_song_repository_schema.py` - Schema validation
- `test_song_repository_exceptions.py` - Error handling
- `test_song_repository_get_path.py` - Single method tests (should merge?)
- `test_song_object_mapping.py` - Object mapping
- `test_song_persistence_integrity.py` - Integrity checks
- `test_duplicate_reproduction.py` - Bug reproduction (obsolete?)
- `test_contributor_repository.py` - Contributor tests
- `test_contributor_repository_schema.py` - Contributor schema

**Action:** Consolidate into 3-4 files max

**Library Widget Tests (8 files):**
- `test_library_widget.py` - Main tests
- `test_library_widget_constants.py` - Constants (should be in main?)
- `test_library_widget_drag_drop.py` - Drag & drop
- `test_library_widget_filtering.py` - Filtering
- `test_library_context_menu.py` - Context menu
- `test_filter_widget.py` - Filter widget
- `test_filter_widget_integrity.py` - Filter integrity

**Action:** Consolidate into 3-4 files max

**Playback Tests (5 files):**
- `test_playback_service.py` - Main tests
- `test_playback_service_cleanup.py` - Cleanup tests (merge?)
- `test_playback_service_mutation.py` - Mutation tests (merge?)
- `test_playback_crossfade.py` - Crossfade specific
- `test_playback_control_widget.py` - Widget tests

**Action:** Consolidate into 2-3 files

**Main Window Tests (3 files):**
- `test_main_window.py` - Main tests
- `test_main_window_cleanup.py` - Cleanup (merge?)
- `test_mainwindow_edge_cases.py` - Edge cases (merge?)

**Action:** Consolidate into 1 file

## Audit Tasks

### Phase 1: Analysis (1-2 hours)
- [ ] Run coverage report: `pytest --cov=src --cov-report=html`
- [ ] Identify duplicate test names across files
- [ ] Map test files to source files (1:1 correspondence check)
- [ ] Identify orphaned tests (testing deleted code)
- [ ] Check for tests with no assertions
- [ ] Find tests that always pass (mocks returning True)

### Phase 2: Consolidation (2-3 hours)
- [ ] **Repository Tests:** Merge into:
  - `test_song_repository.py` (core CRUD)
  - `test_song_repository_schema.py` (schema validation)
  - `test_contributor_repository.py` (contributor CRUD)
- [ ] **Library Widget Tests:** Merge into:
  - `test_library_widget.py` (core functionality)
  - `test_library_widget_interactions.py` (drag/drop, filtering, context menu)
  - `test_filter_widget.py` (filter widget)
- [ ] **Playback Tests:** Merge into:
  - `test_playback_service.py` (core + crossfade)
  - `test_playback_control_widget.py` (widget)
- [ ] **Main Window Tests:** Merge into:
  - `test_main_window.py` (all tests)
- [ ] **Metadata Tests:** Review and consolidate:
  - Keep: service, write, defensive, additional, fixtures, done_flag
  - Review: comprehensive, coverage, mutation, schema (merge if redundant)

### Phase 3: Cleanup (1 hour)
- [ ] Remove obsolete tests:
  - `test_duplicate_reproduction.py` (if bug is fixed)
  - Any tests for deleted features
- [ ] Standardize test naming:
  - Pattern: `test_<method>_<scenario>_<expected>`
  - Example: `test_write_tags_invalid_year_skips_write`
- [ ] Remove unused fixtures
- [ ] Remove commented-out tests
- [ ] Update docstrings

### Phase 4: Documentation (30 min)
- [ ] Update `tests.md` with:
  - Test file structure
  - Coverage targets
  - How to run specific test suites
  - Naming conventions
- [ ] Add README.md to tests/ directory
- [ ] Document test fixtures and their purposes

## Specific Issues to Investigate

### 1. Metadata Service Tests
**Question:** What's the difference between:
- `test_metadata_service_comprehensive.py`
- `test_metadata_service_coverage.py`
- `test_metadata_service.py`

**Action:** Review and merge if overlapping

### 2. Repository "Extra" Tests
**Question:** Why separate `test_song_repository_extra.py`?

**Action:** Merge into main repository tests

### 3. Cleanup Tests
**Question:** Why separate cleanup tests for playback/main window?

**Action:** Merge into main test files as teardown tests

### 4. Mutation Tests
**Question:** Are mutation tests still relevant?

**Action:** Review mutation testing strategy, keep or remove

## Expected Outcomes

### Before Audit:
- 302 tests
- 56 test files
- Unclear organization
- Potential redundancy

### After Audit:
- ~280-300 tests (remove true duplicates)
- ~30-35 test files (consolidate)
- Clear 1:1 mapping (test file → source file)
- Consistent naming
- Updated documentation

## Success Criteria
- [ ] All tests still passing
- [ ] Coverage maintained or improved
- [ ] Test execution time reduced (fewer file loads)
- [ ] Clear test organization
- [ ] No duplicate test names
- [ ] Documentation updated

## Timeline
- **Phase 1 (Analysis):** 1-2 hours
- **Phase 2 (Consolidation):** 2-3 hours
- **Phase 3 (Cleanup):** 1 hour
- **Phase 4 (Documentation):** 30 min

**Total:** 4.5-6.5 hours

## Risk Mitigation
1. **Backup:** Commit before starting audit
2. **Incremental:** Consolidate one area at a time
3. **Verify:** Run full test suite after each consolidation
4. **Rollback:** Keep git history clean for easy rollback

## 🚨 CRITICAL: Tests That MUST Be Preserved

### 1. Schema Validation Tests (9-Layer Yelling) 🔊
**DO NOT DELETE OR MODIFY:**
- `test_database_schema.py` - Core schema validation
- `test_library_service_schema.py` - Service layer schema checks
- `test_metadata_service_schema.py` - Metadata schema validation
- `test_song_repository_schema.py` - Repository schema validation
- `test_contributor_repository_schema.py` - Contributor schema validation
- `test_schema_model_cross_ref.py` - Cross-reference validation
- Any test with "schema" or "integrity" in the name

**Why:** These enforce the 9-layer validation cascade that prevents database corruption. Removing any of these breaks the "yelling mechanism."

### 2. Security Tests
**DO NOT DELETE:**
- `test_security_injection.py` - SQL injection prevention
- Any test with "security" in the name

**Why:** Critical for preventing data loss and security vulnerabilities.

### 3. Defensive Tests (Recently Added)
**DO NOT DELETE:**
- `test_metadata_defensive.py` - Edge cases, malicious input (11 tests)
- `test_metadata_additional.py` - Unknown frames, ID3 versions (5 tests)
- Any test added in the last commit

**Why:** These protect against ID3 corruption and user mistakes. High value, recently implemented.

### 4. Integration Tests
**DO NOT DELETE:**
- `test_main_window_integration.py` - End-to-end workflows

**Why:** Validates the entire system works together.

### 5. Bug Reproduction Tests
**REVIEW BEFORE DELETING:**
- `test_duplicate_reproduction.py` - May be obsolete if bug is fixed
- Check git history to see if bug is resolved
- If resolved, move test to main suite as regression test

## Detailed Consolidation Rules

### Repository Tests Consolidation
**Target Structure:**
```
test_song_repository.py (Core CRUD)
├── test_create_song
├── test_read_song
├── test_update_song
├── test_delete_song
├── test_get_by_path
├── test_get_all_songs
└── test_error_handling

test_song_repository_schema.py (Schema Validation - KEEP SEPARATE)
├── All schema validation tests
├── Whitelist enforcement
└── 9-layer yelling tests

test_contributor_repository.py (Contributor CRUD)
├── test_create_contributor
├── test_read_contributor
├── test_update_contributor
└── test_delete_contributor
```

**Files to Merge:**
- `test_song_repository_extra.py` → `test_song_repository.py`
- `test_song_repository_exceptions.py` → `test_song_repository.py` (error handling section)
- `test_song_repository_get_path.py` → `test_song_repository.py` (single test)
- `test_song_object_mapping.py` → `test_song_repository.py` (mapping section)
- `test_song_persistence_integrity.py` → Keep separate or merge into schema tests

**Files to Keep Separate:**
- `test_song_repository_schema.py` - Schema validation (9-layer yelling)
- `test_song_repository_mutation.py` - If mutation testing is active strategy

### Library Widget Tests Consolidation
**Target Structure:**
```
test_library_widget.py (Core Functionality)
├── test_initialization
├── test_load_library
├── test_selection
├── test_sorting
└── test_column_visibility

test_library_widget_interactions.py (User Interactions)
├── test_drag_drop (from test_library_widget_drag_drop.py)
├── test_filtering (from test_library_widget_filtering.py)
├── test_context_menu (from test_library_context_menu.py)
└── test_double_click

test_filter_widget.py (Filter Widget - Keep Separate)
├── test_filter_creation
├── test_filter_application
└── test_filter_clearing
```

**Files to Merge:**
- `test_library_widget_constants.py` → `test_library_widget.py` (constants section)
- `test_library_widget_drag_drop.py` → `test_library_widget_interactions.py`
- `test_library_widget_filtering.py` → `test_library_widget_interactions.py`
- `test_library_context_menu.py` → `test_library_widget_interactions.py`

**Files to Keep Separate:**
- `test_filter_widget.py` - Separate widget
- `test_filter_widget_integrity.py` - Schema validation (if applicable)

### Metadata Tests Consolidation
**Current Structure (GOOD - Keep As-Is):**
```
test_metadata_service.py - Core extraction (read)
test_metadata_write.py - Core write (12 tests)
test_metadata_defensive.py - Edge cases (11 tests) ✅ KEEP
test_metadata_additional.py - Unknown frames, ID3 (5 tests) ✅ KEEP
test_metadata_fixtures.py - Test fixtures
test_metadata_done_flag.py - TKEY read/write
```

**Files to Review:**
- `test_metadata_service_comprehensive.py` - Check for overlap with test_metadata_service.py
- `test_metadata_service_coverage.py` - Check for overlap
- `test_metadata_service_mutation.py` - Keep if mutation testing is active
- `test_metadata_service_schema.py` - ✅ KEEP (schema validation)

**Action:** Review comprehensive/coverage files. If they duplicate existing tests, merge into main files.

### Playback Tests Consolidation
**Target Structure:**
```
test_playback_service.py (Core + Crossfade)
├── test_play
├── test_pause
├── test_stop
├── test_seek
├── test_crossfade_enabled
├── test_crossfade_disabled
└── test_cleanup (from test_playback_service_cleanup.py)

test_playback_control_widget.py (Widget - Keep Separate)
├── test_button_clicks
├── test_slider_updates
└── test_volume_control
```

**Files to Merge:**
- `test_playback_service_cleanup.py` → `test_playback_service.py` (cleanup section)
- `test_playback_crossfade.py` → `test_playback_service.py` (crossfade section)
- `test_playback_service_mutation.py` → Keep if mutation testing is active

### Main Window Tests Consolidation
**Target Structure:**
```
test_main_window.py (All Tests)
├── test_initialization
├── test_menu_actions
├── test_window_state
├── test_cleanup (from test_main_window_cleanup.py)
└── test_edge_cases (from test_mainwindow_edge_cases.py)
```

**Files to Merge:**
- `test_main_window_cleanup.py` → `test_main_window.py`
- `test_mainwindow_edge_cases.py` → `test_main_window.py`

## Pre-Consolidation Checklist

Before merging any files, verify:
- [ ] Run full test suite: `pytest -v`
- [ ] Check test count: Should be 302 tests
- [ ] Identify test name conflicts (same test name in different files)
- [ ] Review git history for why files were split
- [ ] Check for shared fixtures between files
- [ ] Verify no circular dependencies

## Post-Consolidation Verification

After each merge:
- [ ] Run full test suite: `pytest -v`
- [ ] Verify test count unchanged (or intentionally reduced)
- [ ] Check coverage: `pytest --cov=src`
- [ ] Verify schema tests still pass (9-layer yelling intact)
- [ ] Commit with descriptive message

## Test Naming Standards

**Pattern:** `test_<component>_<action>_<scenario>_<expected>`

**Examples:**
- ✅ `test_write_tags_invalid_year_skips_write`
- ✅ `test_repository_create_song_duplicate_path_raises_error`
- ✅ `test_library_widget_drag_drop_updates_database`
- ❌ `test_1` (too vague)
- ❌ `test_bug_fix` (not descriptive)

## Coverage Targets

**Maintain or Improve:**
- Overall coverage: >80%
- Critical paths: >95% (repository, metadata service)
- Schema validation: 100% (all 9 layers)

## Notes
- Focus on consolidation, not deletion (preserve test coverage)
- **Maintain all schema validation tests (9-layer yelling)** 🔊
- Keep defensive tests (recently added, high value)
- Prioritize readability over file count
- When in doubt, keep the test (disk space is cheap, bugs are expensive)

## Quick Reference: Files That Are Sacred

**DO NOT TOUCH (Schema Validation):**
- `test_database_schema.py`
- `test_*_schema.py` (any file with "schema" in name)
- `test_schema_model_cross_ref.py`
- `test_*_integrity.py` (integrity tests)
- `test_security_injection.py`

**RECENTLY ADDED (High Value):**
- `test_metadata_defensive.py`
- `test_metadata_additional.py`
- `test_metadata_write.py`

**REVIEW CAREFULLY:**
- `test_duplicate_reproduction.py` (may be obsolete)
- `test_*_mutation.py` (if mutation testing is inactive)
- `test_*_extra.py` (likely redundant)
- `test_*_cleanup.py` (merge into main files)
