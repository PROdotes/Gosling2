---
tags:
  - plan/refactor
  - type/runbook
  - status/active
---

# T-04: The Great Test Consolidation Runbook

**Objective**: Reduce the fragmented test suite (~68 files) to a clean, component-based structure (~35 files), separating Logic, Robustness, and Integrity.
**Driver**: Next Available Agent
**Estimated Time**: ~4 Hours (increased for safety)

---

## 📜 The Constitution of Testing

All future tests must adhere to these **Four Laws**:

### 1. The Law of Mirroring
The test directory **MUST** mirror the source directory structure exactly.
*   `src/data/repositories/song_repository.py` -> `tests/unit/data/repositories/test_song_repository.py`.

### 2. The Law of Containment
All functional logic tests for a component must live in its mirrored file.
*   **Forbidden**: `test_song_repository_extra.py`, `test_metadata_done_flag.py`.
*   **Solution**: Proper use of **Nested Classes** to organize large files (e.g., `class TestSongRepoReads(unittest.TestCase)`).

### 3. The Law of Separation
Tests are categorized by their **Intent**:
*   **Logic (Level 1)**: `test_component.py`. Fast, deterministic, checks feature correctness.
*   **Robustness (Level 2)**: `test_component_mutation.py`. Slower, fuzzing, bad inputs, "making it crash". **Do NOT merge these into Logic files.**
*   **Integrity (Level 3)**: `tests/unit/integrity/test_schema_integrity.py`. Checks if the Codebase matches the Database/Docs.

### 4. The Law of Unity
Fixtures must be unified. Do not copy-paste 20 versions of `setUp`.
*   **Global**: Use `conftest.py` for app-wide mocks (DB, Qt App).
*   **Local**: Use `setUp` methods within the specific Test Class.

---

## 🎯 The Kill List (Consolidation Targets)

Execute these merges in order.

### 0. Prerequisites
*   Ensure virtual environment is active.
*   `pip install -r requirements.txt`

### 1. Song Repository (Data Layer)
**Target**: `tests/unit/data/repositories/test_song_repository.py`
**Action**: MERGE & DELETE content from:
*   [ ] `test_song_repository_exceptions.py` (Move to `class TestSongRepoEdgeCases`)
*   [ ] `test_song_repository_extra.py`
*   [ ] `test_song_repository_get_path.py` (Move to `class TestSongRepoReads`)
*   [ ] `test_song_object_mapping.py`
*   [ ] `test_security_injection.py` (Move to `class TestSongRepoSecurity`)

**Keep Separate**: `test_song_repository_mutation.py` (Renamed if needed to match `_mutation.py` suffix).

### 2. Metadata Service (Business Layer)
**Target**: `tests/unit/business/services/test_metadata_service.py`
**Action**: MERGE & DELETE content from:
*   [ ] `test_metadata_service_comprehensive.py`
*   [ ] `test_metadata_service_coverage.py`
*   [ ] `test_metadata_write.py` (Move to `class TestMetadataWrites`)
*   [ ] `test_metadata_write_dynamic.py`
*   [ ] `test_metadata_additional.py`
*   [ ] `test_metadata_defensive.py` (Move to `class TestMetadataResilience`)
*   [ ] `test_metadata_done_flag.py`
*   [ ] `test_metadata_fixtures.py` (Refactor into `conftest.py` or local `setUp`)

**Keep Separate**: `test_metadata_service_mutation.py`.

### 3. Playback Service (Business Layer)
**Target**: `tests/unit/business/services/test_playback_service.py`
**Action**: MERGE & DELETE content from:
*   [ ] `test_playback_service_cleanup.py`
*   [ ] `test_playback_crossfade.py`

**Keep Separate**: `test_playback_service_mutation.py`.

### 4. UI Widgets (Presentation Layer)
**Target**: `tests/unit/presentation/widgets/test_library_widget.py`
**Merge**: `test_library_widget_filtering.py`

**Target**: `tests/unit/presentation/widgets/test_playback_control_widget.py`
**Keep Separate**: `test_playback_control_widget_mutation.py`.

**Target**: `tests/unit/presentation/widgets/test_playlist_widget.py`
**Merge**: `test_playlist_widget_extra.py`

### 5. Integrity & Orphans (The Cleanup)
**Action**: Create/Ensure `tests/unit/integrity/` exists.
1.  **Move** `test_song_integrity.py` -> `tests/unit/integrity/test_song_model_integrity.py`.
2.  **Move** `test_column_name_alignment.py` -> `tests/unit/integrity/test_column_alignment.py`.
3.  **Merge** `test_library_service_aliases.py` (root) -> `tests/unit/business/services/test_library_service.py`.
4.  **Delete** `tests/disabled_integrity/` (Investigate contents first, but default to DELETE if duplicated).

---

## 🔨 Execution Protocol (The "How-To")

For each Target Group:

1.  **Safety Check**: Run the group.
    ```bash
    pytest tests/unit/data/repositories/test_song_repository*.py
    ```
2.  **Refactor**:
    *   Open `Target File`.
    *   Create `class TestCategory(unittest.TestCase):` blocks.
    *   Move methods from source files into these blocks.
3.  **Verify**:
    ```bash
    pytest tests/unit/data/repositories/test_song_repository.py
    ```
4.  **Purge**:
    *   Delete source files.
5.  **Commit**: `git commit -am "refactor: consolidated [Component] tests"`

---

## 🚫 Exclusions
*   `tests/integration/` -> Keep separate.
*   `test_duplicate_reproduction.py` -> Keep separate (Specialized script).
*   `test_library_widget_drag_drop.py` -> Keep separate (Too large).
