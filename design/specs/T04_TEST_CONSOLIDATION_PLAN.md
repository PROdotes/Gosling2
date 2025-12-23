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

---

## 📐 The New Standard
To ensure long-term maintainability, we are adopting a **Component-Centric** testing strategy. Future tests must follow these rules:

1.  **One Component = One Test File**:
    If you have `src/.../PlaybackService.py`, you strictly have `tests/.../test_playback_service.py`. Do NOT create `test_playback_bugfix_123.py`.

2.  **Class-Based Organization**:
    Instead of splitting files, use Python `unittest` (or pytest) classes to group related tests within the *same* file.
    *   `class TestPlaybackControls:` -> Basic play/pause
    *   `class TestPlaybackPlaylist:` -> Navigation logic
    *   `class TestPlaybackErrors:` -> Exception handling

3.  **Shared Fixtures**:
    By keeping tests in one file, they can share heavy `setUp` / `teardown` logic (like Mock Database or PyQt App instances) without valid duplicated boilerplate code.

4.  **Exceptions**:
    *   **Integration Tests**: Stay in `tests/integration/`.
    *   **Massive Features**: If a single feature (like Drag & Drop) is >300 lines of test code, it *may* inherit its own file, but try to avoid it.

5.  **Test Requirements (What to Test)**:
    When implementing a new feature, you must cover:
    *   ✅ **Happy Path**: Does it work under normal conditions?
    *   ⚠️ **Edge Cases**: Empty lists, `None` values, bizarre inputs (e.g. Emoji titles).
    *   🛑 **Error Handling**: Does it catch exceptions or crash? (MockDB failures, file locks).
    *   🔍 **Integrity**: If you add a field to a Model, add a test ensuring it is read/written correctly (use `dataclasses.fields()` inspection).

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

**Refined Structure**:
```python
class TestSongRepositoryReads(unittest.TestCase):
    # from test_song_repository.py (get_all, get_by_performer)
    # from test_song_repository_get_path.py
    # from test_song_object_mapping.py

class TestSongRepositoryWrites(unittest.TestCase):
    # from test_song_repository.py (insert, update, delete)
    # from test_song_repository_extra.py

class TestSongRepositorySecurity(unittest.TestCase):
    # from test_security_injection.py (keep separate for clarity)

class TestSongRepositoryEdgeCases(unittest.TestCase):
    # from test_song_repository_exceptions.py
    # from test_song_repository_mutation.py
```

---

### 2. Metadata Service (Business Layer)
**Primary File**: `tests/unit/business/services/test_metadata_service.py`

**Merge These Files Into Primary**:
*   [ ] `test_metadata_service_comprehensive.py` (Main extraction logic)
*   [ ] `test_metadata_service_coverage.py`
*   [ ] `test_metadata_service_mutation.py`
*   [ ] `test_metadata_write.py` (Writing logic)
*   [ ] `test_metadata_write_dynamic.py` (T-38 logic)
*   [ ] `test_metadata_additional.py`
*   [ ] `test_metadata_defensive.py`
*   [ ] `test_metadata_done_flag.py`
*   [ ] `test_metadata_fixtures.py` (Move fixtures to `conftest.py` if possible)

**Refined Structure**:
```python
class TestMetadataExtraction(unittest.TestCase):
    # from test_metadata_service.py
    # from test_metadata_service_comprehensive.py
    # from test_metadata_done_flag.py

class TestMetadataWriting(unittest.TestCase):
    # from test_metadata_write.py
    # from test_metadata_write_dynamic.py
    # from test_metadata_additional.py

class TestMetadataResilience(unittest.TestCase):
    # from test_metadata_defensive.py
    # from test_metadata_service_mutation.py
    # from test_metadata_service_coverage.py
```

---

### 3. Playback Service (Business Layer)
**Primary File**: `tests/unit/business/services/test_playback_service.py`

**Merge These Files Into Primary**:
*   [ ] `test_playback_service_cleanup.py`
*   [ ] `test_playback_service_mutation.py`
*   [ ] `test_playback_crossfade.py`

**Refined Structure**:
```python
class TestPlaybackControls(unittest.TestCase):
    # basic play/pause/stop/seek from primary

class TestPlaybackPlaylist(unittest.TestCase):
    # playlist navigation logic

class TestPlaybackCrossfade(unittest.TestCase):
    # from test_playback_crossfade.py

class TestPlaybackResourceManagement(unittest.TestCase):
    # from test_playback_service_cleanup.py
```

---

### 4. UI Widgets (Presentation Layer)
**Target**: `tests/unit/presentation/widgets/test_library_widget.py`
*   [ ] Merge `test_library_widget_filtering.py`

**Target**: `tests/unit/presentation/widgets/test_playback_control_widget.py`
*   [ ] Merge `test_playback_control_widget_mutation.py`

**Target**: `tests/unit/presentation/widgets/test_playlist_widget.py`
*   [ ] Merge `test_playlist_widget_extra.py`

---

### 5. Cleanup Orphans (Bonus)
**Target**: `tests/unit/business/services/test_library_service.py`
*   [ ] Merge `tests/test_library_service_aliases.py` (Found in root)

**Target**: `tests/unit/data/models/test_song_model.py`
*   [ ] Merge `tests/unit/data/models/test_song_integrity.py`

---

### 6. More Orphans (Presentation Layer)
**Target**: `tests/unit/presentation/widgets/test_filter_widget.py`
*   [ ] Merge `test_filter_widget_integrity.py`

**Target**: `tests/unit/presentation/widgets/test_type_tabs.py`
*   [ ] *Check if needs cleanup* (Currently seems standalone, but verify)

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
*   `tests/unit/data/repositories/test_duplicate_reproduction.py` -> Reproduction scripts should stay separate.
*   `tests/unit/presentation/widgets/test_library_widget_drag_drop.py` -> Too large (400+ lines).
*   `tests/unit/presentation/widgets/test_library_context_menu.py` -> Too complex (200+ lines).
*   `test_contributor_repository.py` -> Standalone is fine.
