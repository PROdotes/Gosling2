---
tags:
  - plan/refactor
  - type/runbook
  - status/approved
---

# T-04: The Great Test Consolidation Runbook

**Objective**: Reduce the fragmented test suite (~68 files) to a clean, component-based structure (~25 files).
**Driver**: Next Available Agent
**Estimated Time**: ~3 Hours

---

## 🏗️ The Problem
The test suite suffers from "Scenario Fragmentation". Tests were added as new files for every edge case (e.g., `test_playback_service_mutation.py`) rather than extending the component's main test file. This increases maintenance overhead and slows down TDD.

**Rule of Law**: 
> **One Test File Per Component.** 
> Use `class TestComponentFeature(unittest.TestCase):` to separate concerns within the file.

---

## 🎯 The Kill List (Consolidation Targets)

Execute these merges in order.

### 0. Prerequisites (CRITICAL)
Before running any tests, ensure dependencies are installed. The Service Layer imports `PyQt6`.
```bash
pip install -r requirements.txt
```
*Note: If `pytest` fails with `ModuleNotFoundError: No module named 'PyQt6'`, this is why.*

### 1. Song Repository (Data Layer)
**Primary File**: `tests/unit/data/repositories/test_song_repository.py`

**Merge These Files Into Primary**:
*   [ ] `test_song_repository_exceptions.py`
*   [ ] `test_song_repository_extra.py`
*   [ ] `test_song_repository_get_path.py`
*   [ ] `test_song_repository_mutation.py`
*   [ ] `test_song_object_mapping.py`
*   [ ] `test_security_injection.py`

**Desired Structure**:
```python
class TestSongRepositoryBase(unittest.TestCase): ...

class TestSongReads(TestSongRepositoryBase):
    # test_get_all, test_get_by_path...

class TestSongWrites(TestSongRepositoryBase):
    # test_insert, test_update...

class TestSongEdgeCases(TestSongRepositoryBase):
    # test_injection, test_long_paths, test_exceptions...
```

---

### 2. Metadata Service (Business Layer)
**Primary File**: `tests/unit/business/services/test_metadata_service.py`

**Merge These Files Into Primary**:
*   [ ] `test_metadata_service_comprehensive.py`
*   [ ] `test_metadata_service_coverage.py`
*   [ ] `test_metadata_service_mutation.py`
*   [ ] `test_metadata_write.py`
*   [ ] `test_metadata_write_dynamic.py` (Contains T-38 logic)
*   [ ] `test_metadata_additional.py`
*   [ ] `test_metadata_defensive.py`
*   [ ] `test_metadata_done_flag.py`
*   [ ] `test_metadata_fixtures.py`

**Note**: This is the largest merge. Be careful with `setUp` methods. Ensure `MetadataService` is mocked/initialized consistently.

---

### 3. Playback Service (Business Layer)
**Primary File**: `tests/unit/business/services/test_playback_service.py`

**Merge These Files Into Primary**:
*   [ ] `test_playback_service_cleanup.py`
*   [ ] `test_playback_service_mutation.py`
*   [ ] `test_playback_crossfade.py`

---

### 4. UI Widgets (Presentation Layer)
**Small cleanups to reduce noise.**

**Target**: `tests/unit/presentation/widgets/test_library_widget.py`
*   [ ] Merge `test_library_widget_filtering.py`
*   *Keep `drag_drop` and `context_menu` separate for now if they are large (>200 lines).*

**Target**: `tests/unit/presentation/widgets/test_playback_control_widget.py`
*   [ ] Merge `test_playback_control_widget_mutation.py`

**Target**: `tests/unit/presentation/widgets/test_playlist_widget.py`
*   [ ] Merge `test_playlist_widget_extra.py`

---

## 🔨 Execution Protocol (The "How-To")

For each Target Group above:

1.  **Safety Check**: Run the specific group first to ensure green state.
    ```bash
    pytest tests/unit/data/repositories/test_song_repository*.py
    ```
2.  **Backup**: specific file backup.
    ```bash
    cp tests/unit/data/repositories/test_song_repository.py tests/unit/data/repositories/test_song_repository.BAK
    ```
3.  **Merge**:
    *   Open `Primary File`.
    *   Open `Source File` (e.g., `test_song_repository_exceptions.py`).
    *   Copy the `test_...` methods (or whole class) from Source to Primary.
    *   Wrap them in a logical class if needed (e.g., `class TestExceptions:`).
4.  **Verify**:
    ```bash
    # Run ONLY the Primary File
    pytest tests/unit/data/repositories/test_song_repository.py
    ```
5.  **Delete**:
    *   If Green, delete the `Source File`.
6.  **Commit**: `git commit -am "refactor: merged [Source] into [Primary]"`

---

## 🚫 Exclusions (Do Not Merge)
*   `tests/disabled_integrity/` -> Leave them rotting.
*   `tests/integration/` -> Keep separate.
*   `test_contributor_repository.py` -> Standalone is fine.
