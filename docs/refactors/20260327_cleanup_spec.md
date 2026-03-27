# Refactor Spec: Repository Boilerplate Consolidation
**Date**: 2026-03-27
**Target**: `src/data/`
**Complexity**: LOW

## 1. Goal
DRY the repository layer by ensuring all "Fetch by ID" operations use a single, batched execution path. This reduces SQL maintenance surface area and prepares the codebase for future batch optimizations.

## 2. Architectural Rules
- `get_by_id(id)` MUST be a wrapper for `get_by_ids([id])`.
- Repository columns and JOINs MUST be defined as class constants to ensure `get_by_ids` and `get_all` stay in sync.
- Return types and logging levels MUST remain consistent with current implementations.

## 3. Implementation Plan

### Phase A: AlbumRepository
1. Implement `get_by_ids(album_ids: List[int]) -> List[Album]`.
2. Refactor `get_by_id(album_id: int)` to use `get_by_ids`.
3. Refactor `get_all()` to use shared constants.

### Phase B: TagRepository
1. Implement `get_by_ids(tag_ids: List[int]) -> List[Tag]`.
2. Refactor `get_by_id(tag_id: int)` to use `get_by_ids`.
3. Refactor `get_all()` to use shared constants.

## 4. Verification Protocol
- All existing tests for `AlbumRepository` and `TagRepository` must pass.
- 100% test coverage for new `get_by_ids` methods.
- No regression in `CatalogService` hydration (which depends on these repos).
