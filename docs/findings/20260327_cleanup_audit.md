# Cleanup Audit: Repository Boilerplate Consolidation
**Date**: 2026-03-27
**Status**: DRAFT

## 1. Objective
Identify structural redundancies in the `src/data/` repository layer, specifically focusing on the inconsistent implementation of `get_by_id` and `get_by_ids` methods across entities.

## 2. Redundancy Matrix

| Repository | `get_by_id` | `get_by_ids` | Consolidated? | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `SongRepository` | Yes | Yes | **YES** | Calls `get_by_ids([id])`. |
| `IdentityRepository` | Yes | Yes | **YES** | Calls `get_by_ids([id])`. |
| `PublisherRepository` | Yes | Yes | **YES** | Calls `get_by_ids([id])`. |
| `AlbumRepository` | Yes | **NO** | NO | Has independent SELECT query. |
| `TagRepository` | Yes | **NO** | NO | Has independent SELECT query. |
| `MediaSourceRepository` | Yes | **NO** | NO | Has independent SELECT query. |
| `SongCreditRepository` | No | No | N/A | Primarily link-based. |

## 3. Structural Patterns
- **Query Duplication**: `AlbumRepository.get_all` and `get_by_id` use the same column list and JOIN logic but separate SQL strings.
- **Row Mapping**: Every repo implements its own `_row_to_entity` mapping logic.
- **Batching Gaps**: `AlbumRepository` and `TagRepository` lack batch-fetch capabilities for domain objects, forcing N+1 patterns if the service layer ever needs them (though `CatalogService` currently uses custom joining logic).

## 4. Proposed Refactors
1. **Consolidate `get_by_id`**: For all repositories, `get_by_id` should call `get_by_ids`.
2. **Implement `get_by_ids`**: Add batch-fetching to `AlbumRepository` and `TagRepository`.
3. **Standardize `get_all`**: Use `get_by_ids` internally or share the column/join definitions.

## 5. Risk Assessment
- **Breaking Changes**: Minimal, as method signatures remain identical.
- **Performance**: Consolidating to `IN (?)` for single items has negligible overhead on SQLite compared to `=` (often optimized similarly by the engine).
