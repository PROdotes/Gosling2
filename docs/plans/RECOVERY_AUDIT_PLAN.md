# Implementation Plan: Protocol Recovery & Test Consolidation

## Overview
This plan completes the "Cleanup" phase by consolidating orphan tests into the project-standard suite and ensuring 100% test coverage for the core services. This prevents "AI Ghost" code and ensures a "Done and Green" state before starting Phase 2.2 (Ingestion).

## Proposed Changes

### Data Layer & Fixtures
- [MODIFY] **[tests/conftest.py](file:///c:/Users/glazb/PycharmProjects/gosling2/tests/conftest.py)**:
    - Update `populated_db` to include a 3-tier publisher hierarchy: `Universal Music Group (1) -> Island Records (2) -> Island Def Jam (3)`.
    - Link `Nevermind` to `Island Records` to test inherited labels.
    - Integrate publisher hierarchy tests from `test_publisher_repository_standalone.py`.
    - Use the `populated_db` fixture to verify recursive parent-chain resolution (CTE performance check).
    - Add edge-case tests for identities with cycles or missing members (if not covered).
- [DELETE] **[tests/test_publisher_repository_standalone.py](file:///c:/Users/glazb/PycharmProjects/gosling2/tests/test_publisher_repository_standalone.py)**: To be purged once integrated.
- [DELETE] **[tests/test_publisher_repo_service.py](file:///c:/Users/glazb/PycharmProjects/gosling2/tests/test_publisher_repo_service.py)**: To be purged once integrated.

### Instrumentation Cleanup
- [MODIFY] **[src/services/catalog_service.py](file:///c:/Users/glazb/PycharmProjects/gosling2/src/services/catalog_service.py)**:
    - Ensure all "VIOLATION" logs for 404s are present as per the Recovery Plan.

---

## Verification Plan

### Automated Tests
- **`pytest --cov=src/services/catalog_service.py tests/test_catalog.py`**:
    - Aim for 100% coverage.
- **`pytest tests/`**:
    - Full suite regression test.

### Linting
- **`black .`**
- **`ruff check . --fix`**
