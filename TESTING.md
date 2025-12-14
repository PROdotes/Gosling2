# Testing Strategy & Guide

Gosling2 employs a rigorous, multi-layered testing strategy to ensure reliability, data integrity, and architectural soundness.

## 📊 Test Suite Overview

| Type | Count | Purpose | Location |
|------|-------|---------|----------|
| **Unit Tests** | 200+ | Test individual components in isolation | `tests/unit/` |
| **Integration** | ~10 | Test component interactions (UI/Services) | `tests/integration/` |
| **Schema Integrity** | ~15 | Prevent "Silent Data Loss" & DB drift | `tests/unit/` (various) |
| **Mutation** | ~10 | Verify test quality (kill bugs) | `tests/unit/**/*_mutation.py` |

---

## 🛡️ Layer 1: Schema Integrity (The Safety Net)

We have a specialized suite of tests designed solely to prevent **Silent Data Loss** and ensuring the codebase stays in sync with the Database Schema.

*   **Database Schema**: Checks `sqlite_master` to ensure strict table/column existence.
*   **Repo vs DB**: Ensures `SongRepository` fetches exactly the columns defined in the table.
*   **Model vs DB**: Ensures `Song` dataclass attributes match Database columns.
*   **Persistence**: Ensures `insert()` and `update()` methods write ALL columns.
*   **Metadata**: Ensures `MetadataService` extracts ALL fields supported by the specific model.

**Value**: If you add a column to the Database but forget to update the Repository, Model, or UI, **these tests will fail immediately**.

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
