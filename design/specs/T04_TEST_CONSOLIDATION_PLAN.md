---
tags:
  - plan/refactor
  - type/spec
  - status/draft
---

# T-04: The Great Test Consolidation Plan

**Objective**: Reduce the 68 scattered test files in `tests/` to a manageable, logical structure (~20 files).
**Driver**: Any
**Safety**: High (Test only)

---

## 🏗️ The Problem
The current test suite suffers from "Scenario Fragmentation". Instead of organizing by **Component**, we organized by **Ad-Hoc Scenario** (e.g., `test_song_repository_extra.py`).

**Current Count**: ~68 Files
**Target Count**: ~20-25 Files

---

## 🗺️ The New Map

### Rule #1: One Test File Per Component
If you are testing `SongRepository`, all tests go in `test_song_repository.py`. 
Use **Classes** to separate concerns within the file.

### Kill List & Targets

#### 1. Song Repository (The Big One)
**Target**: `tests/unit/data/repositories/test_song_repository.py`
**Merge Source(s)**:
- `test_song_repository_extra.py`
- `test_song_repository_get_path.py`
- `test_song_repository_exceptions.py`
- `test_song_repository_mutation.py`
- `test_song_integrity.py` (Move logic here if it's repo-centric)
- `test_song_object_mapping.py`
- `test_security_injection.py`

**Internal Structure**:
```python
class TestSongRepository(unittest.TestCase):
    # Setup/Teardown
    ...

class TestSongReads(TestSongRepository):
    # get_by_path, get_all, etc.

class TestSongWrites(TestSongRepository):
    # insert, update, etc.

class TestSongEdgeCases(TestSongRepository):
    # injection, long paths, etc.
```

#### 2. Metadata Service
**Target**: `tests/unit/business/services/test_metadata_service.py`
**Merge Source(s)**:
- `test_metadata_service_comprehensive.py`
- `test_metadata_service_coverage.py`
- `test_metadata_service_mutation.py`
- `test_metadata_additional.py`
- `test_metadata_defensive.py`
- `test_metadata_done_flag.py`
- `test_metadata_fixtures.py`
- `test_metadata_write.py`

#### 3. Playback Service
**Target**: `tests/unit/business/services/test_playback_service.py`
**Merge Source(s)**:
- `test_playback_service_cleanup.py`
- `test_playback_service_mutation.py`
- `test_playback_crossfade.py`

#### 4. Library Widget (UI)
**Target**: `tests/unit/presentation/widgets/test_library_widget.py`
**Merge Source(s)**:
- `test_library_widget_filtering.py`
- `test_library_widget_selection.py`
- `test_library_widget_signals.py`
- `test_library_widget_sorting.py`

---

## 🔨 Execution Protocol

1.  **Backup**: Ensure git is clean.
2.  **Create Wrapper**: Rename `test_song_repository.py` -> `test_song_repository_OLD.py`.
3.  **Scaffold**: Create new empty `test_song_repository.py` with standard imports.
4.  **Migrate Chunk**:
    *   Copy ONE source file's tests into the new file.
    *   **Run Pytest**: `pytest tests/unit/data/repositories/test_song_repository.py`.
    *   **Pass?**: Delete the source file.
5.  **Repeat**: Until all source files are consumed.

---

## 🚫 What NOT to Merge
*   **Disabled Integrity Tests**: Leave `tests/disabled_integrity/` alone. They are disabled for a reason.
*   **Integration Tests**: Leave `tests/integration/` alone.
*   **One-off Repos**: `test_contributor_repository.py` is fine as is (unless there are 5 of them).

---

## ✅ Definition of Done
1.  file count in `tests/unit` reduced by > 50%.
2.  `pytest` runs green on the merged files.
3.  No loss of coverage (all test methods migrated).
