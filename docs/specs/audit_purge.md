# [GOSLING2] Audit Purge Plan

## Context
The user has removed all auditing files (`src/services/audit_service.py`, `src/data/audit_repository.py`, etc.).
However, the test suite and some parts of the source code still reference these deleted components, causing `ImportError` and `ModuleNotFoundError`.

## Goal
Purge all "zombie code" related to the Auditing system to restore a green test state.

## Scope of Changes

### 1. `tests/conftest.py`
- [x] Remove `from src.services.audit_service import AuditService`.
- [x] Remove `audit_service` and `audit_service_empty` fixtures.
- [x] Update `_populate_db_data` to stop inserting into `ActionLog`, `ChangeLog`, and `DeletedRecords`.
- [x] Update documentation comments regarding audit data.

### 2. `tests/test_services/test_engine.py`
- [x] Delete `TestAuditHistory` class and all its test methods.

### 3. File Deletion
- [x] Delete `tests/test_services/test_audit.py`.
- [x] Delete `tests/test_data/test_audit_repository.py`.

### 4. `src/static/js/dashboard/api.js`
- [x] Remove `getAuditHistory` function.

### 5. `src/static/js/dashboard/components/utils.js`
- [x] Remove `renderAuditTimeline` function.

### 6. `src/static/js/dashboard/renderers/`
- [x] `song_editor.js`: Remove Audit History details/summary/loading elements.
- [x] `songs.js`: Remove `renderAuditTimeline` import/usage.
- [x] `artists.js`: Remove `renderAuditTimeline` import/usage and `auditHistory` parameter from `renderArtistDetailComplete`.
- [x] `albums.js`: Remove `renderAuditTimeline` import/usage and `auditHistory` parameter from `renderAlbumDetailComplete`.

### 7. Source Code Cleanup
- [x] Check `src/data/base_repository.py` for any remaining audit-related logic.
- [x] Check `src/services/catalog_service.py` for any remaining audit-related logic.

## Verification
1. [x] Run `pytest` and ensure it no longer fails on imports.
2. [x] Run `pytest` to ensure all remaining tests pass.
3. [x] Check for any linting errors related to missing imports.
4. [x] Verify Dashboard UI still works and no longer shows empty "Audit History" sections.
