# Orphan Deletion — Implementation Plan

**Purpose:** Step-by-step build plan for the unlinked entity cleanup feature.
**Spec:** [UNLINKED_ENTITIES_SPEC.md](UNLINKED_ENTITIES_SPEC.md)
**Approach:** TDD red-green-refactor per [TDD_TESTING_STANDARD.md](TDD_TESTING_STANDARD.md)

---

## Current State (What's Already Done)

| Layer | Status |
|-------|--------|
| Schema (`IsDeleted` columns on all 6 entity tables) | ✅ Done |
| Repo visibility filtering (`WHERE IsDeleted = 0` on all reads) | ✅ Done |
| Repo reconnection/upsert (wake soft-deleted on re-insert) | ✅ Done |
| Song soft-delete + link severance (`MediaSourceRepository`) | ✅ Done |
| `CatalogService.delete_song()` (links + soft-delete + file cleanup) | ✅ Done |
| Delete integrity tests (`tests/integration/test_delete_integrity.py`) | ✅ Done |
| Soft-delete visibility tests (`tests/test_data/test_soft_delete_visibility.py`) | ✅ Done |
| Reconnection tests (`tests/test_data/test_soft_delete_reconnection.py`) | ✅ Done |
| **Step 1: Tags — full stack** | ✅ Done |

---

## Key Design Decisions (Learned in Step 1)

### Single delete is a special case of bulk delete
There is NO separate `delete_tag(tag_id)` method. Single delete calls `delete_unlinked_tags([tag_id])` and checks the return value:
- Returns `0` → tag is linked (403) or doesn't exist (404, checked first via `get_tag`)
- Returns `1` → deleted (204)

### One service method, one connection
```python
def delete_unlinked_tags(self, tag_ids: List[int]) -> int:
```
- Opens ONE connection for the entire batch
- For each ID: calls `tag_repo.get_song_ids_by_tag(tag_id, conn)` — if empty → `tag_repo.soft_delete(tag_id, conn)`
- One commit at the end, rollback on any error
- Returns count of tags actually deleted

### No `count_linked_*` repo method
The "is this entity linked?" check reuses the existing `get_song_ids_by_tag` (returns empty list = unlinked). No separate count method needed.

### `get_song_ids_by_tag` must JOIN MediaSources
The original query had no `IsDeleted` check. Fixed to:
```sql
SELECT mst.SourceID FROM MediaSourceTags mst
JOIN MediaSources ms ON mst.SourceID = ms.SourceID
WHERE mst.TagID = ? AND ms.IsDeleted = 0
```
Note: In a healthy DB, a tag linked only to soft-deleted songs should be impossible (song deletion hard-deletes `MediaSourceTags` rows). The JOIN is defensive.

### Router: 404 check before delete
```python
if not service.get_tag(tag_id):    # 404
    raise HTTPException(404)
deleted = service.delete_unlinked_tags([tag_id])
if deleted == 0:                   # 403 — exists but linked
    raise HTTPException(403)
```

### Bulk endpoint safety flag
`DELETE /tags?unlinked=true` — requires `?unlinked=true` explicitly (400 without it).
Router fetches all tags, passes all IDs to `delete_unlinked_tags`. Service filters to orphans internally.

### Song count on Tag model
`Tag` domain model and `TagView` both have `song_count: int = 0`.
`TagRepository.get_all()` and `search()` both use a LEFT JOIN + COUNT query so song counts are always included.
Frontend uses `song_count === 0` to show "unlinked" pill and enable/disable delete button.

### Frontend pattern
- Cards show song count pill OR red "unlinked" pill in `.card-meta` (right side), NOT in `.card-subtitle`
  - Example structure: title + category in `.card-subtitle` (left), count pill in `.card-meta` (right)
  - This matches how artists display their type badge — count goes in `.card-meta` for consistency
- "Delete N unlinked" button appears at top of list when orphans exist (`data-action="bulk-delete-unlinked-tags"`)
- Detail panel has delete button, disabled with tooltip when linked (`data-action="delete-tag"`, `data-tag-id`)
- Both actions handled in `NavigationHandler` using `showConfirm` (not `confirm()`)
- `confirm-modal` added to `isModalOpen()` list in `utils.js`
- API calls: `api.deleteTag(id)` → `fetchVoid DELETE /tags/{id}`, `api.bulkDeleteUnlinkedTags()` → `fetchJson DELETE /tags?unlinked=true`

---

## Step 2: Album

One junction table (`SongAlbums`), but albums have their own metadata links (`AlbumCredits`, `AlbumPublishers`) that must be hard-deleted before soft-deleting the album.

### 2a. Repository: `AlbumRepository`

```python
def soft_delete(self, album_id: int, conn: sqlite3.Connection) -> bool:
    """Set IsDeleted = 1. Returns True if updated."""

def get_song_ids_by_album(self, album_id: int, conn: sqlite3.Connection) -> List[int]:
    """Active songs in this album. Already exists — verify it JOINs MediaSources + IsDeleted = 0."""

def delete_album_links(self, album_id: int, conn: sqlite3.Connection) -> None:
    """Hard-delete AlbumCredits and AlbumPublishers rows for this album.
    Called before soft_delete — same pattern as delete_song_links()."""
    # DELETE FROM AlbumCredits WHERE AlbumID = ?
    # DELETE FROM AlbumPublishers WHERE AlbumID = ?
```

**Note:** Check if `get_song_ids_by_album` already exists and whether it correctly filters `IsDeleted = 0` on `MediaSources`.

### 2b. Service: `CatalogService`

```python
def delete_unlinked_albums(self, album_ids: List[int]) -> int:
    """
    Soft-delete albums from the given list that have zero active song links.
    Cleans up AlbumCredits + AlbumPublishers before soft-deleting.
    Single delete: pass [album_id].
    """
    # Open ONE connection
    # For each album_id:
    #   if not album_repo.get_song_ids_by_album(album_id, conn): empty = unlinked
    #     album_repo.delete_album_links(album_id, conn)
    #     album_repo.soft_delete(album_id, conn)
    #     deleted += 1
    # commit, return deleted
```

### 2c. Tests

**File:** `tests/test_services/test_orphan_deletion.py` — add `TestDeleteUnlinkedAlbums`

Feature A (single via list):
- `test_unlinked_album_is_deleted` — album with 0 songs → soft-deleted
- `test_deleted_album_hidden_from_get_album`
- `test_linked_album_is_not_deleted` — album with active songs → returns 0
- `test_linked_album_remains_in_db`
- `test_nonexistent_album_returns_zero`
- `test_album_linked_only_to_deleted_songs_is_deletable`
- `test_delete_album_purges_album_credits` — AlbumCredits rows gone after delete
- `test_delete_album_purges_album_publishers` — AlbumPublishers rows gone after delete

Feature B (bulk):
- `test_bulk_deletes_all_orphan_albums`
- `test_bulk_skips_linked_albums`
- `test_bulk_empty_list_returns_zero`

### 2d. API Endpoints

**File:** `src/engine/routers/catalog.py` — add after album GET endpoints

```python
@router.delete("/albums/{album_id:int}", status_code=204)
async def delete_album(album_id: int) -> None:
    # service.get_album(album_id) → 404
    # service.delete_unlinked_albums([album_id]) → 0 = 403, 1 = 204

@router.delete("/albums", response_model=dict)
async def bulk_delete_unlinked_albums(unlinked: bool = False) -> dict:
    # require ?unlinked=true (400)
    # all_albums = service.get_all_albums() — check if this exists
    # service.delete_unlinked_albums([a.id for a in all_albums])
    # return {"deleted": N}
```

### 2e. Frontend

**File:** `src/static/js/dashboard/renderers/albums.js`
- Add `song_count` to album cards (need to check if `AlbumView`/`AlbumSlimView` already has a song count field)
- Add "unlinked" pill when `song_count === 0`
- Add "Delete N unlinked" button at top of list
- Add delete button to detail panel (disabled if linked)

**File:** `src/static/js/dashboard/api.js`
```js
export function deleteAlbum(albumId) { ... }
export function bulkDeleteUnlinkedAlbums() { ... }
```

**File:** `src/static/js/dashboard/handlers/navigation.js`
- Add `"delete-album"` and `"bulk-delete-unlinked-albums"` to actions set
- Add `handleDeleteAlbum` and `handleBulkDeleteUnlinkedAlbums` methods (same pattern as tags)

---

## Step 3: Publisher

**Dual-table check** — publishers can be linked to songs (`RecordingPublishers`) AND albums (`AlbumPublishers`). Must be unlinked from BOTH.

### 3a. Repository: `PublisherRepository`

```python
def soft_delete(self, publisher_id: int, conn: sqlite3.Connection) -> bool:
    """Set IsDeleted = 1."""

def get_song_ids_by_publisher(self, publisher_id: int, conn: sqlite3.Connection) -> List[int]:
    """Already exists — verify IsDeleted = 0 join."""

def get_album_ids_by_publisher(self, publisher_id: int, conn: sqlite3.Connection) -> List[int]:
    """Active albums linked via AlbumPublishers. May need adding."""
    # SELECT ap.AlbumID FROM AlbumPublishers ap
    # JOIN Albums a ON ap.AlbumID = a.AlbumID
    # WHERE ap.PublisherID = ? AND a.IsDeleted = 0
```

### 3b. Service: `CatalogService`

```python
def delete_unlinked_publishers(self, publisher_ids: List[int]) -> int:
    """
    Soft-delete publishers with zero active songs AND zero active albums.
    Single delete: pass [publisher_id].
    """
    # For each publisher_id:
    #   if not get_song_ids_by_publisher AND not get_album_ids_by_publisher:
    #     soft_delete
```

### 3c. Tests

**File:** `tests/test_services/test_orphan_deletion.py` — add `TestDeleteUnlinkedPublishers`

- `test_publisher_with_no_links_is_deleted`
- `test_publisher_linked_to_active_song_is_rejected`
- `test_publisher_linked_to_active_album_is_rejected`
- `test_publisher_linked_to_deleted_song_and_deleted_album_is_deletable`
- `test_bulk_deletes_orphan_publishers`
- `test_bulk_skips_publishers_with_song_links`
- `test_bulk_skips_publishers_with_album_links`

### 3d. API + Frontend

Same pattern as Albums. Check if `PublisherView` has song/album count fields.

---

## Step 4: Identity (Most Complex)

**Full identity tree checking**: an Identity has multiple ArtistNames (aliases). ANY alias linked to songs (`SongCredits`) or albums (`AlbumCredits`) blocks deletion. Soft-delete is all-or-nothing: marks `Identities` row AND all `ArtistNames` rows.

### 4a. Repository: `IdentityRepository`

```python
def soft_delete(self, identity_id: int, conn: sqlite3.Connection) -> bool:
    """Soft-delete the Identity AND all its ArtistNames rows."""
    # UPDATE Identities SET IsDeleted = 1 WHERE IdentityID = ? AND IsDeleted = 0
    # UPDATE ArtistNames SET IsDeleted = 1 WHERE OwnerIdentityID = ? AND IsDeleted = 0
    # Return True if Identity row was updated

def get_song_ids_by_identity(self, identity_id: int, conn: sqlite3.Connection) -> List[int]:
    """Active songs credited to ANY alias of this identity."""
    # SELECT DISTINCT sc.SourceID FROM SongCredits sc
    # JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
    # JOIN MediaSources ms ON sc.SourceID = ms.SourceID
    # WHERE an.OwnerIdentityID = ? AND ms.IsDeleted = 0

def get_album_ids_by_identity(self, identity_id: int, conn: sqlite3.Connection) -> List[int]:
    """Active albums credited to ANY alias of this identity."""
    # SELECT DISTINCT ac.AlbumID FROM AlbumCredits ac
    # JOIN ArtistNames an ON ac.CreditedNameID = an.NameID
    # JOIN Albums a ON ac.AlbumID = a.AlbumID
    # WHERE an.OwnerIdentityID = ? AND a.IsDeleted = 0
```

**Orphan ArtistNames note:** Some ArtistNames have `OwnerIdentityID = NULL`. These are skipped — out of scope for MVP.

### 4b. Service: `CatalogService`

```python
def delete_unlinked_identities(self, identity_ids: List[int]) -> int:
    """
    Soft-delete identities with zero active songs/albums across ALL aliases.
    Marks Identity + all ArtistNames rows as deleted.
    Single delete: pass [identity_id].
    """
```

### 4c. Tests

**File:** `tests/test_services/test_orphan_deletion.py` — add `TestDeleteUnlinkedIdentities`

- `test_identity_with_no_links_is_deleted`
- `test_identity_with_active_song_via_primary_alias_is_rejected`
- `test_identity_with_active_song_via_secondary_alias_is_rejected`
- `test_identity_with_active_album_credit_is_rejected`
- `test_identity_linked_only_to_deleted_songs_is_deletable`
- `test_delete_identity_soft_deletes_all_aliases`
- `test_bulk_deletes_orphan_identities`
- `test_bulk_skips_linked_identities`

### 4d. API + Frontend

Same pattern. Check if `IdentityView` has song count field.

---

## Step 5: API Integration Tests

**File:** `tests/test_api/test_orphan_deletion_api.py` (new)

For each entity type (tags ✅ already wired, albums, publishers, identities):
- 204 on successful single delete
- 403 on linked entity
- 404 on nonexistent entity
- Bulk returns `{"deleted": N}`
- Bulk requires `?unlinked=true` (400 without it)

---

## Step 6: Frontend Completion

Tags frontend is ✅ done. Repeat for albums, publishers, identities:

### Per-entity checklist
- [ ] Add `song_count` (and `album_count` for publishers/identities) to view model + repo query
- [ ] Update card renderer: song count pill OR red "unlinked" pill
- [ ] Add "Delete N unlinked" button at top of list (`data-action="bulk-delete-unlinked-{type}"`)
- [ ] Add delete button to detail panel (`data-action="delete-{type}"`, disabled if linked)
- [ ] Add `delete{Type}` and `bulkDeleteUnlinked{Type}` to `api.js`
- [ ] Add actions to `NavigationHandler` actions set
- [ ] Add `handle{DeleteType}` and `handleBulkDeleteUnlinked{Type}` methods to `NavigationHandler`

### Shared infrastructure already done (tags)
- `.pill.unlinked` CSS class ✅
- `.btn-danger` CSS class ✅
- `showConfirm` used instead of `confirm()` ✅
- `confirm-modal` in `isModalOpen()` ✅

---

## Implementation Notes

- **Transaction pattern:** `conn = repo.get_connection()` → work → `conn.commit()` / `conn.rollback()` → `conn.close()`. Same as `delete_song()`.
- **FK constraints won't fire:** Soft-delete is `UPDATE`, not `DELETE`. Service layer must check for active links before every soft-delete.
- **"Linked to deleted" = "unlinked":** All link-checking queries must join to the parent entity and verify `IsDeleted = 0`.
- **Single delete = bulk with one ID:** Never write a separate single-delete method. Always `delete_unlinked_*([ id ])`.
- **Router owns 404 vs 403:** Service just returns count. Router calls `get_*(id)` first for 404, then `delete_unlinked_*([id])` → 0 = 403.
- **Bulk skips guards:** Already proven unlinked by the empty-list check inside the service loop.
