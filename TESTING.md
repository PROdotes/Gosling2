# Testing Strategy & Guide

Gosling2 employs a rigorous, multi-layered testing strategy to ensure reliability, data integrity, and architectural soundness.

## 📊 Test Suite Overview

| Type | Count | Purpose | Location |
|------|-------|---------|----------|
| **Unit Tests** | 260+ | Test individual components in isolation | `tests/unit/` |
| **Integration** | ~10 | Test component interactions (UI/Services) | `tests/integration/` |
| **Schema Awareness** | ✅ Active (10-layer Enforcement) | Prevent "Silent Data Loss" & DB drift | `tests/unit/` (various) |
| **Mutation** | ~10 | Verify test quality (kill bugs) | `tests/unit/**/*_mutation.py` |

---

## 🏗️ Structure & Organization (THE LAW)

**Goal**: Avoid "File Sprawl". We do NOT create new files for every edge case.

### 1. One File Per Component
*   **Rule**: All unit tests for `SongRepository` MUST live in `tests/unit/data/repositories/test_song_repository.py`.
*   **Forbidden**: `test_song_repository_extra.py`, `_exceptions.py`, `_complex.py`.
*   **Solution**: Use **Nested Classes** inside the main file to group tests.
    *   `class TestSongRepoReads(unittest.TestCase): ...`
    *   `class TestSongRepoWrites(unittest.TestCase): ...`

### 2. File Naming
*   **Format**: `test_<component_name_snake_case>.py`
*   **Location**: Mirror the `src/` directory structure.
    *   `src/data/repositories/album_repository.py` -> `tests/unit/data/repositories/test_album_repository.py`

### 3. Integration Tests
*   **Rule**: Only place tests in `tests/integration/` if they require multiple real components (Repository + Service + DB).
*   **Prefix**: `test_integration_<feature>.py` or `test_tXX_<task>.py`.

---

## 🛡️ Layer 1: Schema Integrity (The "Yelling" Safety Net)

We have a specialized, multi-layered suite of tests designed to enforce a **1:1 Strict Mapping** between the Database Schema and every application layer.

**The "10 Layers of Yell" Verification:**
1.  **Repository**: `SongRepository` checks `sqlite_master` to ensure NO unknown tables exist.
2.  **Domain**: `Song` model MUST have a field for every table column.
3.  **Service**: `LibraryService` MUST expose every DB column as a header.
4.  **UI (Table)**: `LibraryWidget` columns MUST match Service headers.
5.  **UI (Viewer)**: `MetadataViewer` MUST map every ID3 tag to a DB column.
6.  **Search**: Search logic MUST cover all exposed columns.
7.  **Filter**: `FilterWidget` MUST use Yellberus strategies for all categories.
8.  **Metadata (Read)**: `MetadataService.extract_from_mp3()` MUST handle all columns.
9.  **Metadata (Write)**: `MetadataService.write_tags()` MUST handle all portable fields.
10. **Persistence**: `SettingsManager` MUST save/load layout based on **Field Identity (Names)**, not indices, to survive registry shifts.

**Value**: If you add a column to the Database but forget to update ANY layer, **the system yells immediately**. Silent schema drift is impossible.

**Example:** Add `genre` column to DB:
- Layer 2 fails: "Song model missing 'genre' field"
- Layer 3 fails: "LibraryService not exposing 'genre' header"
- Layer 9 fails: "write_tags() doesn't handle 'genre' field"
- All 10 layers must be updated before tests pass ✅

## 🧬 Layer 2: Mutation Testing

We use mutation testing (concepts from `mutmut`) to ensure our tests are robust.

*   **How it works**: These tests simulate "mutants" (bugs) in the code—like deleting a fallback line or swapping a variable.
*   **Goal**: The test *must fail* if the bug is introduced.
*   **Coverage**: Currently covers critical logic in:
    *   `MetadataService` (Tag parsing fallbacks)
    *   `SongRepository` (SQL query construction)
    *   `PlaybackService` (State management)

## ⚡ Layer 3: Unit & Logic Tests

Standard pytest coverage for:
*   **Services**: `LibraryService`, `PlaybackService` (Dual-player logic).
*   **Widgets**: `PlaybackControlWidget` (Labels, Buttons), `SeekSlider`.
*   **Utils**: Time formatting, string helpers.

## 🚀 Running Tests

### Standard Run
```bash
pytest
```

### With Coverage Report
```bash
pytest --cov=src tests/
```

### Running Specific Suites
```bash
# Run only Schema Integrity tests
pytest -k "integrity"

# Run only Mutation tests
pytest -k "mutation"
```

## 🐛 Troubleshooting Common Failures

*   **"Unexpected Extra Column"**: You added a column to the DB but didn't update the Test/Model. Update `Song` model and `SongRepository`.
*   **"Property ... not mapped"**: The `Song` model has a field that the `SongRepository` isn't querying.
*   **"Mutant Survived"**: A mutation test passed even though we broke the code? Your logic might be redundant or the test asserts are too weak.

## Future Layers (As Features Grow)

The "Yelling Mechanism" is a living system. As we add features that consume or expose Song data, we must add new validation layers.

**Anticipated Future Layers:**
- **Layer 10: File Renaming** (RenamingService must use all fields in templates)
- **Layer 11: Export** (CSV/JSON export must include all columns)
- **Layer 12: API** (REST endpoints must match schema)
- **Layer 13: Backup** (Backup format must be complete)

**Rule of Thumb:** If a feature **reads or writes** Song data, it needs its own 1:1 schema verification test.

---

## 🏗️ The Field Registry (Yellberus) — LIVE
The "9 Layers of Yell" have been **consolidated** into a centralized **Field Registry (Yellberus)**. This is now the single source of truth for:
*   **Database Columns**: Dynamic mapping via `yellberus.BASE_QUERY`.
*   **UI Headers**: Automatically derived from field definitions.
*   **Validation Rules**: "Requiredness" and min-lengths are defined once.
*   **Metadata Mapping**: Connection between ID3 frames and Song attributes.

## 🧹 2025-12-21: Consolidation Status (COMPLETE)

The "10 Layers of Yell" have been successfully consolidated into the **Yellberus Registry**.
1.  **Shared Fixtures**: Core functional counterparts now use a global `conftest.py` where appropriate.
2.  **Integrity Folder**: Infrastructure tests are now sequestered in `tests/unit/integrity/` or specifically named `_integrity.py`.
3.  **Tool-Assisted Docs**: `FIELD_REGISTRY.md` is now automatically synchronized via `field_editor.py` to prevent "Doc Drift."

---

## 💭 Test Readability: A Philosophical Note

**Observation (2025-12-22):** AI-generated test code tends to be verbose and comment-heavy. This makes tests harder to scan, not easier.

**The Paradox:**
- **Clean code approach**: Extract helpers like `has_txxx()`, `json_with()` → Reads like prose
- **But**: Now you need to trust the helpers, which means... testing them? Turtles all the way down.

**The Counter-Insight:**
Tests are *intentionally* ugly and primitive. You use raw dicts, raw file ops, raw asserts — because those are the bedrock you trust without proof. The ugliness is the point.

**The Rule:**
- Test helpers should be *trivially correct* (e.g., `return f"TXXX:{name}" in data`)
- If a helper needs testing, it's probably production code, not test code
- At some point, you just trust: `assert`, `==`, the language itself

**Future Consideration:**
When refactoring tests, resist the urge to over-abstract. A boring, obvious test that you don't enjoy reading is better than a clever, readable test that hides bugs.

**Related:** AI-generated code in general may need a "human readability pass" — something to consider for the whole codebase, not just tests.
