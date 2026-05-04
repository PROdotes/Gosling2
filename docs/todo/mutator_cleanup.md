# Mutator Cleanup

Audit of commits `7feebd4..fead054` (song, album, credit, delete, publisher, tag mutators).

## Conventions

- Repositories return data (rowcounts, bools, rows). They do NOT raise business errors.
- Mutators/services check return values and raise `LookupError` (not found) or `ValueError` (bad input / business rule).
- All repo methods returning `cursor.rowcount` are annotated `-> int`, not `-> None`.

---

## Phase 1: Repository Layer Fixes

### 1.1 tag_repository.py

| Line | Method | Current | Fix |
|------|--------|---------|-----|
| ~256-268 | `remove_tag()` | Returns `None` | Return `cursor.rowcount` (`-> int`) |
| ~286-288 | `update_tag()` | Raises `LookupError` on rowcount==0 | Return `cursor.rowcount` (`-> int`), remove raise |
| ~320-326 | `set_primary_tag()` | Raises `LookupError` on rowcount==0 | Return `cursor.rowcount` (`-> int`), remove raise |

### 1.2 publisher_repository.py

| Line | Method | Current | Fix |
|------|--------|---------|-----|
| ~504-518 | `remove_song_publisher()` | Returns `None` | Return `cursor.rowcount` (`-> int`) |
| ~556-570 | `remove_album_publisher()` | Returns `None` | Return `cursor.rowcount` (`-> int`) |
| ~587-591 | `update_publisher()` | Raises `LookupError` on rowcount==0 | Return `cursor.rowcount` (`-> int`), remove raise |
| ~606-607 | `set_parent()` | Raises `LookupError` on rowcount==0 | Return `cursor.rowcount` (`-> int`), remove raise |

### 1.3 song_album_repository.py

| Line | Method | Current | Fix |
|------|--------|---------|-----|
| ~278-284 | `set_primary()` | Returns `None` | Return `cursor.rowcount` (`-> int`) |
| ~286-291 | `clear_primary()` | Returns `None` | Return `cursor.rowcount` (`-> int`) |

### 1.4 Fix `-> None` annotations that actually return rowcount

| File | Method | Current | Fix |
|------|--------|---------|-----|
| song_credit_repository.py ~220 | `remove_credit()` | `-> None` | `-> int` |
| song_credit_repository.py ~233 | `update_credit_name()` | `-> None` | `-> int` |
| album_credit_repository.py ~90 | `remove_credit()` | `-> None` | `-> int` |
| album_repository.py ~179 | `update_album()` | `-> None` | `-> int` |
| song_album_repository.py ~236 | `update_track_info()` | `-> None` | `-> int` |

---

## Phase 2: Mutator Error Handling

After repos are fixed, add consistent error checks to mutators that are missing them.

### 2.1 publisher_mutator.py

| Method | Current | Fix |
|--------|---------|-----|
| `_remove()` ~32-36 | No check on remove | Check rowcount from `remove_song_publisher`/`remove_album_publisher`, raise `LookupError` if 0 |
| `_update()` ~38-42 | Relies on repo raising | Check rowcount from `update_publisher`/`set_parent`, raise `LookupError` if 0 |
| `apply_within()` | Untyped `item` | Add `item: Union[AddPublisherItem, RemovePublisherItem, UpdatePublisherEntityItem]` type annotation |

### 2.2 tag_mutator.py

| Method | Current | Fix |
|--------|---------|-----|
| `_remove()` ~47-55 | No check on `remove_tag` | Check rowcount from `remove_tag`, raise `LookupError` if 0 |
| `_update()` ~57-67 | For `UpdateTagEntityItem`: does `get_by_id` check then calls `update_tag` which also raises. For `UpdateSongTagItem`: `set_primary_tag` raises in repo. | Remove duplicate check: rely on `update_tag` rowcount. For `set_primary_tag`: check rowcount, raise in mutator. |
| `apply_within()` | Untyped `item` | Add union type annotation |

### 2.3 album_mutator.py

| Method | Current | Fix |
|--------|---------|-----|
| `_update_song_album()` ~74-78 | No check on `set_primary`/`clear_primary` | Check rowcount, raise `LookupError` if 0 |
| `apply_within()` | Untyped `item` | Add union type annotation |

### 2.4 credit_mutator.py

| Method | Current | Fix |
|--------|---------|-----|
| `apply_within()` | Untyped `item` | Add union type annotation |

### 2.5 delete_mutator.py

| Method | Current | Fix |
|--------|---------|-----|
| `apply_within()` | Untyped `item` | Add union type annotation |

### 2.6 Silent else branches (should raise, not no-op)

| File | Method | Current | Fix |
|------|--------|---------|-----|
| album_mutator.py `_update()` | `else` after isinstance checks | Silent no-op | Raise `ValueError` |
| tag_mutator.py `_update()` | `else` after isinstance checks | Silent no-op | Raise `ValueError` |

---

## Phase 3: Model Consistency

### 3.1 Validator naming

In `mutation_models.py`:
- `Add*Item` validators are named `non_empty`
- `Update*Item` validators are named `not_empty`
- Pick one: **`not_empty`** everywhere. Rename all `non_empty` to `not_empty`.

### 3.2 `is_primary` optionality

- `UpdateSongTagItem.is_primary` is `bool` (required)
- `UpdateSongAlbumItem.is_primary` is `Optional[bool]` (optional)
- Decide: should both be `Optional[bool]`? (you might want to update track number without touching primary status)

### 3.3 Missing validation: `DeleteItem(id=None, unlinked=False)`

Add a Pydantic model validator to reject this invalid state. Neither a specific delete nor a bulk operation.

### 3.4 Missing validation: `AddAlbumItem` / `AddPublisherItem` with `id` that doesn't exist

Currently trusts the provided `id`. Need existence check in the mutator (like `TagMutator._add` does with `get_by_id`).

---

## Phase 4: Code Smells

### 4.1 Ellipsis sentinel in album_mutator.py

Lines ~67-69 use `...` as sentinel for "field not set". Replace with proper `exclude_unset` pattern matching other mutators, or use a dedicated sentinel `_UNSET = object()`.

### 4.2 `model_fields_set` hack in publisher_mutator.py

Line ~41 manually inspects `item.model_fields_set`. Use `item.model_dump(exclude_unset=True)` like everywhere else.

### 4.3 `batch_id` parameter unused everywhere

All mutators accept `batch_id: UUID` and never use it. Remove from mutator signatures and from coordinator's call sites. Re-add when audit logging is implemented.

### 4.4 `warnings` always empty

`mutation_coordinator.py:66` always returns `warnings: []`. Remove the field from the response model until file system side effects are implemented and can actually produce warnings.

### 4.5 `MutationCoordinator._get_connection` duplicates `BaseRepository.get_connection`

Extract connection creation (with `UTF8_NOCASE` collation and FK pragma) into a shared factory. Both coordinator and repos should use it.

### 4.6 `_make_conn` duplicated across 4 test files

Extract into `tests/conftest.py` as a fixture. Fix: `test_song_mutator.py` is missing `UTF8_NOCASE` collation registration.

---

## Phase 5: Critical Bugs

### 5.1 DeleteMutator misses album links for publishers

`_delete_publisher` only checks `get_song_ids_by_publisher()`. Must also check album links before allowing delete or soft-deleting unlinked publishers.

### 5.2 No `touched_song_ids` from delete operations

`mutation_coordinator.py` collects `touched_song_ids` from add/update/remove but not delete. Deleting an entity affects linked songs. The coordinator should collect and return affected song IDs from delete operations too.

### 5.3 N+1 queries in bulk delete

`DeleteMutator._delete_*` with `unlinked=True` iterates all entities and issues per-entity link checks. Replace with bulk queries like:
```sql
SELECT TagID FROM Tags WHERE TagID NOT IN (SELECT DISTINCT TagID FROM MediaSourceTags)
```

---

## Phase 6: Test Gaps

### 6.1 No tests for `unlinked=True` bulk delete

Most complex code path in delete_mutator, zero coverage. Add tests for each entity type.

### 6.2 No test for publisher delete missing album link check

Related to 5.1: test that a publisher linked only to albums is properly blocked.

### 6.3 `test_song_mutator.py` missing `UTF8_NOCASE` collation

Fix `_make_conn` to register collation like other test files.

### 6.4 Auto-move tests deleted without replacement

5 tests from `test_catalog_update.py` covering file-move-on-scalar-save were removed. When file system side effects are implemented, these need to be recreated.

---

## Phase 7: Frontend/Backend Mismatches (deferred)

These types in `api.js` have no backend handler and will 422:
- `"identity_alias"`, `"identity"`, `"identity_member"` (identity mutator not yet built)
- `"ingest_status"`, `"ingest_conflict"` (separate system)
- `"original_file"` (separate system)

`deleteSong` sends `delete_file` field not in model. Expected: file system not implemented yet.

These are intentional gaps, not bugs. Note here for awareness.
