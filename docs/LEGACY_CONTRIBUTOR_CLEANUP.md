# Legacy Contributor System Cleanup

**Author:** AI Assistant  
**Date:** 2026-01-16  
**Status:** IN PROGRESS  

## Overview

The codebase has TWO contributor systems running in parallel:
1. **Legacy System** - `Contributors`, `ContributorAliases`, `GroupMembers`, `MediaSourceContributorRoles`
2. **New Identity System** - `Identities`, `ArtistNames`, `GroupMemberships`, `SongCredits`, `AlbumCredits`

This cleanup removes the legacy system entirely. Since the app supports 2-way save (metadata in ID3 tags), we can delete the DB and re-import.

---

## Pre-Requisites

- [x] Type change bug fixed (cleanup of GroupMemberships on Person↔Group switch)
- [ ] Backup current database (optional - data is in ID3 tags anyway)
- [ ] Delete database file before testing (fresh start)

---

## Phase 1: Database Schema Cleanup

### File: `src/data/database.py`

**REMOVE these table definitions:**

| Line Range | Table | Reason |
|------------|-------|--------|
| 183-191 | `Contributors` | Replaced by `Identities` + `ArtistNames` |
| 208-221 | `MediaSourceContributorRoles` | Replaced by `SongCredits` |
| 223-234 | `GroupMembers` | Replaced by `GroupMemberships` |
| 237-244 | `ContributorAliases` | Replaced by non-primary `ArtistNames` |
| 258-269 | `AlbumContributors` | Replaced by `AlbumCredits` |

**REMOVE these migrations:**
| Line Range | Migration |
|------------|-----------|
| 401-405 | `MediaSourceContributorRoles.CreditedAliasID` column |
| 407-411 | `GroupMembers.MemberAliasID` column |

**REMOVE these indexes:**
| Line | Index |
|------|-------|
| 420 | `idx_mscr_contributorid` |
| 421 | `idx_mscr_roleid` |
| 422 | `idx_albumcontributor_albumid` |

---

## Phase 2: Repository Cleanup

### File: `src/data/repositories/contributor_repository.py`

**Current Status:** 851 lines  
**Target Status:** DELETE ENTIRE FILE or reduce to ~50 lines (facade)

**Methods that use LEGACY tables (to remove):**

| Method | Line | Uses Legacy Table |
|--------|------|------------------|
| `get_by_id` | 17-28 | `Contributors` |
| `get_by_name` | 30-52 | `Contributors`, `ContributorAliases` |
| `_get_by_id_logic` | 54-65 | `Contributors` |
| `get_by_role` | 67-86 | `MediaSourceContributorRoles` |
| `get_usage_count` | 88-98 | `MediaSourceContributorRoles` |
| `swap_song_contributor` | 100-137 | `MediaSourceContributorRoles` |
| `get_all_aliases` | 141-151 | `ContributorAliases` |
| `get_all_names` | 153-163 | `Contributors` |
| `_insert_db` | 165-171 | `Contributors` |
| `_update_db` | 173-202 | `Contributors`, `GroupMembers` |
| `_delete_db` | 204-215 | `GroupMembers`, `Contributors` |
| `create` | 217-245 | `Contributors` |
| `search` | 251-284 | `Contributors`, `ContributorAliases` |
| `get_all` | 286-296 | `Contributors` |
| `get_all_by_type` | 298-327 | `Contributors`, `ContributorAliases` |
| `search_identities` | 329-369 | `Contributors`, `ContributorAliases` |
| `get_types_for_names` | 371-411 | Uses NEW tables ✅ (KEEP) |
| `get_or_create` | 413-446 | `Contributors`, `ContributorAliases` |
| `validate_identity` | 448-488 | `Contributors`, `ContributorAliases` |
| `get_member_count` | 492-510 | `GroupMembers` (deprecated) |
| `get_members` | 512-540 | `GroupMembers` (deprecated) |
| `get_groups` | 542-563 | `GroupMembers` (deprecated) |
| `add_member` | 565-588 | `GroupMembers` (deprecated) |
| `remove_member` | 590-616 | `GroupMembers` (deprecated) |
| `get_aliases` | 618-627 | `ContributorAliases` |
| `add_alias` | 629-646 | `ContributorAliases` |
| `update_alias` | 648-668 | `ContributorAliases` |
| `delete_alias` | 673-700 | `ContributorAliases`, `MediaSourceContributorRoles` |
| `_generate_sort_name` | 702-707 | Pure logic ✅ (MOVE to service) |
| `resolve_identity_graph` | 709-765 | `Contributors`, `ContributorAliases`, `GroupMembers` |
| `add_song_role` | 767-800+ | `MediaSourceContributorRoles` |
| `remove_song_role` | | `MediaSourceContributorRoles` |

**DECISION:** Delete entire file. All functionality exists in `ContributorService` using new tables.

---

## Phase 3: Service Layer Refactoring

### File: `src/business/services/contributor_service.py`

**Current Status:** 648 lines  
**Target Status:** ~400 lines (remove legacy, keep new)

**Remove these lines:**

```python
# Line 15-18: Remove legacy repo import/init
self._repo = contributor_repository or ContributorRepository(db_path=db_path)
```

**Methods using new tables (KEEP as-is):**
- `get_all()` - Uses `ArtistNames` + `Identities` ✅
- `get_by_id()` - Uses `ArtistNames` + `Identities` ✅
- `get_by_name()` - Uses `ArtistNames` + `Identities` ✅
- `create()` - Uses `IdentityService` + `ArtistNameService` ✅
- `get_or_create()` - Uses service layer ✅
- `merge()` - Uses `IdentityService` ✅
- `update()` - Uses new tables ✅
- `get_by_role()` - Uses `SongCredits` ✅
- `get_all_by_type()` - Uses `Identities` + `ArtistNames` ✅
- `search()` - Uses `ArtistNames` + `Identities` ✅
- `resolve_identity_graph()` - Uses `ArtistNames`, `GroupMemberships` ✅
- Group/Member methods - All use `GroupMemberships` ✅
- Alias methods - All use `ArtistNames` ✅

**Update required:**
- `get_usage_count()` - Change from `MediaSourceContributorRoles` to `SongCredits`
- `add_song_role()` - Change to `SongCredits`
- `remove_song_role()` - Change to `SongCredits`

---

## Phase 4: Credit Repository Updates

### File: `src/data/repositories/credit_repository.py`

**Check:** Ensure all methods use `SongCredits` and `AlbumCredits` tables.

Methods to verify:
- `add_song_credit(source_id, name_id, role_id)`
- `remove_song_credit(source_id, name_id, role_id)`
- `get_credits_for_song(source_id)`
- `get_credits_for_album(album_id)`

---

## Phase 5: Presentation Layer Updates

### Files to check for legacy usage:

1. **`src/presentation/widgets/side_panel_widget.py`**
   - Search for `contributor_repository` references
   - Should use `contributor_service` instead

2. **`src/presentation/dialogs/artist_manager_dialog.py`**
   - Already uses `ContributorService` ✅

3. **`src/presentation/widgets/library_widget.py`**
   - Uses `contributor_service.resolve_identity_graph()` ✅

4. **`src/core/context_adapters.py`**
   - Check for legacy usage in `_legacy_link_staged` methods

---

## Phase 6: Song Sync Service

### File: `src/business/services/song_sync_service.py`

**Check line 66:** `_resolve_identity_legacy()` 
- If this uses old tables, update to use `IdentityService` / `ArtistNameService`

---

## Phase 7: Testing

### Run these test files after changes:

```bash
# Core identity tests
pytest tests/integration/test_artist_type_change.py -v
pytest tests/integration/test_unified_artist_logic.py -v
pytest tests/unit/business/services/test_identity_service.py -v

# Filter/Search tests
pytest tests/unit/presentation/widgets/test_filter_widget.py -v

# Full regression
pytest tests/unit tests/integration --ignore=tests/unit/business/services/test_duplicate_scanner.py -x
```

---

## Implementation Order

1. [ ] **Create backup of `contributor_repository.py`** (in case we need to reference)
2. [ ] **Update `contributor_service.py`:**
   - [ ] Remove `self._repo` usage
   - [ ] Update `get_usage_count()` to use `SongCredits`
   - [ ] Update any `add_song_role()` / `remove_song_role()` to use `SongCredits`
3. [ ] **Update `database.py`:**
   - [ ] Remove legacy table definitions
   - [ ] Remove legacy migrations
   - [ ] Remove legacy indexes
4. [ ] **Update `song_sync_service.py`:**
   - [ ] Update `_resolve_identity_legacy()` if needed
5. [ ] **Check presentation layer:**
   - [ ] `side_panel_widget.py`
   - [ ] `context_adapters.py`
6. [ ] **Delete `contributor_repository.py`**
7. [ ] **Delete database file:** `gosling2.db`
8. [ ] **Run tests**
9. [ ] **Manual test with app**

---

## Rollback Plan

If things go wrong:
1. Revert git changes
2. Restore database backup (or re-import from MP3 files)

---

## Notes

- The `Contributor` data model (`src/data/models/contributor.py`) can remain as a DTO
- `ContributorService` becomes the ONLY way to access contributor data
- All queries should go through `IdentityService`, `ArtistNameService`, or `CreditRepository`

---

## Progress Tracker

| Step | Status | Notes |
|------|--------|-------|
| Phase 1: Database Schema | ⬜ Not Started | Legacy tables still exist (no harm) |
| Phase 2: Repository Cleanup | ⬜ Deferred | ContributorRepository still exists but no longer imported in main code |
| Phase 3: Service Refactoring | ✅ DONE | ContributorService no longer uses ContributorRepository |
| Phase 4: Credit Repository | ✅ DONE | Already using SongCredits |
| Phase 5: Presentation Layer | ✅ DONE | main_window.py updated |
| Phase 6: Song Sync | ✅ DONE | Removed V1 legacy sync from song_sync_service.py |
| Phase 7: Testing | ✅ DONE | All 9 identity/artist tests pass |

## Files Modified

- `src/business/services/contributor_service.py` - Removed ContributorRepository dependency
- `src/business/services/song_sync_service.py` - Removed V1 legacy sync (MediaSourceContributorRoles)
- `src/data/repositories/song_repository.py` - Removed ContributorRepository, updated get_contributors_for_song
- `src/data/repositories/__init__.py` - Removed ContributorRepository export
- `src/presentation/views/main_window.py` - Removed ContributorRepository usage
