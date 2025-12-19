# Testing Strategy & Guide

Gosling2 employs a rigorous, multi-layered testing strategy to ensure reliability, data integrity, and architectural soundness.

## 📊 Test Suite Overview

| Type | Count | Purpose | Location |
|------|-------|---------|----------|
| **Unit Tests** | 260+ | Test individual components in isolation | `tests/unit/` |
| **Integration** | ~10 | Test component interactions (UI/Services) | `tests/integration/` |
| **Schema Integrity** | ~50 | Prevent "Silent Data Loss" & DB drift | `tests/unit/` (various) |
| **Mutation** | ~10 | Verify test quality (kill bugs) | `tests/unit/**/*_mutation.py` |

---

## 🛡️ Layer 1: Schema Integrity (The "Yelling" Safety Net)

We have a specialized, multi-layered suite of tests designed to enforce a **1:1 Strict Mapping** between the Database Schema and every application layer.

**The "9 Layers of Yell" Verification:**
1.  **Repository**: `SongRepository` checks `sqlite_master` to ensure NO unknown tables exist.
2.  **Domain**: `Song` model MUST have a field for every `MediaSources`/`Songs` table column.
3.  **Service**: `LibraryService` MUST expose every DB column as a header.
4.  **UI (Table)**: `LibraryWidget` columns MUST match Service headers.
5.  **UI (Viewer)**: `MetadataViewer` MUST map every ID3 tag to a DB column.
6.  **Search**: Search logic MUST cover all exposed columns.
7.  **Filter**: `FilterWidget` MUST either filter by a column or explicitly ignore it.
8.  **Metadata (Read)**: `MetadataService.extract_from_mp3()` MUST attempt extraction for all DB columns.
9.  **Metadata (Write)**: `MetadataService.write_tags()` MUST handle all Song fields (or explicitly skip).

**Value**: If you add a column to the Database but forget to update ANY layer, **the system yells immediately**. Silent schema drift is impossible.

**Example:** Add `genre` column to DB:
- Layer 2 fails: "Song model missing 'genre' field"
- Layer 3 fails: "LibraryService not exposing 'genre' header"
- Layer 9 fails: "write_tags() doesn't handle 'genre' field"
- All 9 layers must be updated before tests pass ✅

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

## 🧹 2025-12-19: Consolidation Plan (In Progress)

After the major schema migration, the test suite is currently efficient but fragmented (60+ files). We are in the process of:
1.  **Merging Fragments**: Folding `add_..._tests.py` and `append_tests.py` snippets back into their core functional counterparts.
2.  **Shared Fixtures**: Moving repetitive service mocks into a global `conftest.py`.
3.  **Integrity Folder**: Moving all "Strict Coverage" and "Cross-Ref" tests into a dedicated `tests/unit/integrity/` folder to separate "Infrastructure Tests" from "Logic Tests".

