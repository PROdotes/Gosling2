# Refactor Spec: 2026-03-27 Cleanup

## 1. Goal
Deduplicate repository boilerplate, consolidate service search paths, and sync documentation with implementation.

## 2. Before vs. After (Critical Example)

### Example: Song Deletion Orchestration
**Before (`CatalogService.delete_song`):**
```python
def delete_song(self, song_id: int) -> bool:
    # 1. Fetch info
    song = self._song_repo.get_by_id(song_id)
    # 2. Delete links
    self._song_repo.delete_song_links(song_id, conn)
    # 3. Soft delete
    self._song_repo.soft_delete(song_id, conn)
    # 4. Physical cleanup...
```

**After:**
```python
# SongRepository.py
def soft_delete_song(self, song_id: int, conn: sqlite3.Connection) -> bool:
    self.delete_song_links(song_id, conn)
    return super().soft_delete(song_id, conn)

# CatalogService.py
def delete_song(self, song_id: int) -> bool:
    # ... metadata lookup ...
    with self._song_repo.get_connection() as conn:
        success = self._song_repo.soft_delete_song(song_id, conn)
        # ... commit + physical cleanup ...
```

## 3. Implementation Plan

### Item 1: Repository Layer DRYing
- **Action**: Move `get_by_id` boilerplate to `BaseRepository` if possible, or use a shared mixin.
- **Action**: Refactor `SongRepository.get_by_path` and `get_by_hash` to use a single JOIN query instead of two round-trips via `super()`.
- **Action**: Move `delete_song_links` and soft-delete orchestration into `SongRepository`.

### Item 2: Service Layer Consolidation
- **Action**: Merge `CatalogService.search_songs` and `search_songs_deep` into `search_songs(query, deep=False)`.
- **Action**: Refactor `_get_tags_by_song` and others to use `_batch_group_by_id`.

### Item 3: Automated Tool Cleanups
- **Action**: Resolve the 4 high-priority `jscpd` clones by extracting the "Get-or-Create Role/Name" logic as defined in Item 1.
- **Action**: Address `fallow` maintainability index (MI) by splitting high-complexity methods in `CatalogService` into smaller, atomic private methods.
- **Action**: Review `purgecss.config.cjs` for redundant configuration or unused patterns.

### Item 4: Documentation Sync
- **Action**: Remove duplicate entries in `docs/lookup/services.md`.
- **Action**: Audit and fix signatures in `docs/lookup/data.md`.

## 4. Verification Plan
1. `pytest tests/integration/` to ensure ingestion, search, and deletion logic remains sound.
2. `ruff check .` for any new linting issues.
3. `pyright` for type integrity.
