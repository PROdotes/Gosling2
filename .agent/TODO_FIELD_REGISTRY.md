# TODO: Field Registry Pattern Implementation

## Overview
Refactor the "10-Layer Yelling" mechanism from manual distributed tests to a central **Field Registry** (The Single Source of Truth).

## Phase 1: The Manager (Integrity Enforcement) 📋
*Goal: Centralize the "Truth" and automate the "Yelling" without changing application code.*

### 1. Identify & Map Existing Fields
- [ ] Create `src/core/registry.py`.
- [ ] List all current fields: `title`, `performers`, `composers`, `lyricists`, `producers`, `groups`, `bpm`, `recording_year`, `isrc`, `is_done`.
- [ ] Map each field to its DB Column, Song Attribute, and ID3 Frame.

### 2. Implement the "Master Integrity Test" (The Manager)
- [ ] **Forward Check (Registry -> App):** Loop through the registry and verify:
  - [ ] Does the column exist in SQLite?
  - [ ] Does the attribute exist in the `Song` model?
  - [ ] Does the UI Table have the header?
  - [ ] Does `MetadataService.write_tags` handle the mapping?
- [ ] **Reverse Check (App -> Registry):**
  - [ ] Scan SQLite: Is there any column NOT in the registry? (**Silent Drift Protection**)
  - [ ] Scan Song Model: Is there any attribute NOT in the registry?
- [ ] **Cleanup:** Remove the old manual `test_*_schema.py` files once the Manager is fully operational.

---

## Phase 2: The Chef (Logic Automation) 🍳
*Goal: Refactor the services to "look at the book" instead of hardcoding.*

### 1. Metadata Service Refactor
- [ ] Rewrite `extract_from_mp3` to loop through the registry for frame extraction.
- [ ] Rewrite `write_tags` to loop through the registry for frame writing.

### 2. Repository Refactor
- [ ] Update `SongRepository` to build SQL queries dynamically based on registry columns.
- [ ] Automate the mapping from Row -> `Song` object using the registry `model_attr` map.

### 3. UI Refactor
- [ ] Update `LibraryWidget` to generate columns dynamically from the registry.
- [ ] (Future) Generate the Metadata Editor fields automatically from the "is_editable" flag in the registry.

---

## Safety Requirements
1. **Never "Auto-Delete":** If the Manager finds an unknown column in the DB, he should **YELL** (fail test), but never automatically delete data.
2. **Incremental Rollout:** Implement Phase 1 (Tests) first. The application code shouldn't even know the registry exists until the Manager is happy.
3. **9-Layer (now 10) Minimum:** Every check we currently do manually MUST be included in the Manager's checklist.

## Success Criteria
- [ ] `tasks.md` shows Registry Pattern as ✅ COMPLETE.
- [ ] Adding a new field (e.g., `genre`) requires modifying **exactly one file** (`registry.py`).
- [ ] Running `pytest` immediately identifies any layer that isn't updated.
- [ ] Zero hardcoded column names in `MetadataService` or `LibraryWidget`.
