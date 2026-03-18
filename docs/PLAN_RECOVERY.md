# [GOSLING2] RECOVERY PLAN: "UNWINDING THE SLOP"

## 1. Executive Summary
The session today has introduced several "Protocol Scars" and architectural regressions. This plan aims to restore the codebase to a 100% "Done and Green" state by fixing N+1 queries, filling instrumentation gaps, and refactoring leaked logic.

---

## 2. Phase 1: Performance & Protocol (The "Low-Hanging Fuckups")

### 2.1 Fix N+1 Publisher Lookup
- **Problem**: `CatalogService._collect_parent_ids` uses a `while` loop that calls `get_by_id` inside.
- **Fix**: Move hierarchy resolution logic to `PublisherRepository`. Use a recursive Common Table Expression (CTE) in SQL to fetch the entire parent chain in **one query**.
- **Target**: `src/data/publisher_repository.py` & `src/services/catalog_service.py`

### 2.2 Standardize Instrumentation
- **Problem**: Missing "Exit" logs for multiple methods in `CatalogService` and `PublisherRepository`.
- **Fix**: Add `logger.info/debug` exit markers with result counts to every method. Ensure "VIOLATION" prefix is used for 404s/Errors.
- **Target**: `src/services/catalog_service.py`, `src/data/publisher_repository.py`.

---

## 3. Phase 2: Refactoring & Architecture

### 3.1 Extract Identity Batching
- **Problem**: `CatalogService` contains raw SQL and deep knowledge of `ArtistNames` and `GroupMemberships`. This is "Service Leakage." 
- **Fix**: Move `_get_aliases_for_identities`, `_get_members_for_identities`, and `_get_groups_for_identities` into `IdentityRepository`.
- **Target**: `src/data/identity_repository.py` and `src/services/catalog_service.py`.

### 3.2 Resolve Model Debt
- **Problem**: Recursive Pydantic models (Identity, Publisher) require `model_rebuild()`.
- **Fix**: Add `Identity.model_rebuild()` and `Publisher.model_rebuild()` at the end of `src/models/domain.py` and `src/models/view_models.py`.
- **Target**: `src/models/domain.py`, `src/models/view_models.py`.

---

## 4. Phase 3: "Done and Green" (The Final Loop)

### 4.1 Lookup Synchronization
- **Fix**: Update `docs/lookup/data.md` and `docs/lookup/services.md` to reflect the exact signatures of the refactored code.

### 4.2 Test Consolidation
- **Fix**: Merge `tests/test_publisher_repository_standalone.py` logic into a properly fixture-backed `tests/test_publisher_repo.py` using `conftest.py`.
- **Validation**: Pass the **entire** suite: `pytest tests/`.

---

## 5. Success Criteria
1. No `while` loops fetching from DB.
2. Every service method has a logged Exit.
3. 0 Raw SQL in `CatalogService`.
4. `pytest` returns 100% Green on all 20+ tests.
