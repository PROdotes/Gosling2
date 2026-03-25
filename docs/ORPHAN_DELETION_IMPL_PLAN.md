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

---

## Two Distinct Features

This plan covers two related but separate features that share repository methods:

### Feature A: Single Entity Delete (Detail Panel)
User selects a specific entity → clicks delete button → system **guards** (is it linked?) → if unlinked, soft-deletes it.

**Flow:** `count_linked_*()` guard → cleanup dangling links (albums only) → `soft_delete()`

### Feature B: Bulk Orphan Cleanup
User clicks "Delete All Unlinked" → system finds all orphans → soft-deletes them all.

**Flow:** `get_unlinked_*()` → `soft_delete()` each in one transaction. No guards needed — they're already proven unlinked by the query.

**Shared repo methods:** `soft_delete()` is used by both features. `count_linked_*()` is only used by Feature A. `get_unlinked_*()` is only used by Feature B.

**Albums special case:** Both paths need `delete_album_links()` before `soft_delete()` — an unlinked album still has dangling `AlbumCredits`/`AlbumPublishers` rows that should be cleaned up.

---

## Step-by-Step Implementation Order

### Step 1: Tag (Simplest — Proves the Pattern)

One junction table (`MediaSourceTags`), no alias trees, no dual-table checks, no dangling links to clean up.

#### 1a. Repository: `TagRepository`

**File:** `src/data/tag_repository.py`

```python
def soft_delete(self, tag_id: int, conn: sqlite3.Connection) -> bool:
    """Set IsDeleted = 1. Returns True if a row was updated."""
    # UPDATE Tags SET IsDeleted = 1 WHERE TagID = ? AND IsDeleted = 0
    # Return cursor.rowcount > 0

def count_linked_songs(self, tag_id: int, conn: sqlite3.Connection) -> int:
    """Count active songs linked to this tag. Used by single delete guard."""
    # SELECT COUNT(*) FROM MediaSourceTags mst
    # JOIN MediaSources ms ON mst.SourceID = ms.SourceID
    # WHERE mst.TagID = ? AND ms.IsDeleted = 0
```

**Key detail:** `count_linked_songs` must JOIN to `MediaSources` and check `ms.IsDeleted = 0` — a tag linked only to soft-deleted songs IS unlinked.

**Conn pattern:** Both take `conn` parameter (caller controls transaction). Neither commits.

#### 1b. Service: `CatalogService`

**File:** `src/services/catalog_service.py`

**Feature A — Single delete:**
```python
def delete_tag(self, tag_id: int) -> bool:
    """Soft-delete a tag if it has zero active song links."""
    # 1. Open connection
    # 2. tag_repo.count_linked_songs(tag_id, conn) → if > 0, return False (403 case)
    # 3. tag_repo.soft_delete(tag_id, conn) → if False, return False (404 case)
    # 4. conn.commit()
    # 5. Return True
```

**Feature B — Orphan discovery + bulk delete:**
```python
def get_unlinked_tags(self) -> List[Tag]:
    """Find all tags with zero active song links."""
    # Single query (see Unlinked Query Reference below)
    # Returns list of Tag domain objects

def bulk_delete_unlinked_tags(self) -> int:
    """Soft-delete all unlinked tags in one transaction. Returns count."""
    # 1. get_unlinked_tags() → list of Tag objects
    # 2. Open connection
    # 3. For each: tag_repo.soft_delete(tag.id, conn)
    # 4. conn.commit()
    # 5. Return len(tags)
```

#### 1c. Tests

**File:** `tests/test_services/test_orphan_deletion.py` (new)

Feature A tests:
- `test_delete_unlinked_tag_succeeds` — tag with 0 songs → IsDeleted = 1
- `test_delete_linked_tag_is_rejected` — tag with 1+ active songs → returns False, tag untouched
- `test_delete_tag_linked_only_to_deleted_songs` — tag's only song is soft-deleted → tag IS unlinked → succeeds
- `test_delete_nonexistent_tag_returns_false`

Feature B tests:
- `test_get_unlinked_tags_returns_only_orphans`
- `test_get_unlinked_tags_excludes_tags_linked_to_active_songs`
- `test_bulk_delete_unlinked_tags` — deletes all orphans, leaves linked ones
- `test_bulk_delete_when_no_orphans_returns_zero`

#### 1d. API Endpoints

**File:** `src/engine/routers/catalog.py`

```python
@router.delete("/tags/{tag_id:int}")
async def delete_tag(tag_id: int):
    """Feature A: Soft-delete a single tag (must be unlinked)."""
    # service.get_tag(tag_id) → 404 if not found
    # service.delete_tag(tag_id) → 403 if linked
    # Return 204

@router.delete("/tags")
async def bulk_delete_tags(unlinked: bool = False):
    """Feature B: Soft-delete all unlinked tags."""
    # if not unlinked: 400 (safety — require explicit ?unlinked=true)
    # count = service.bulk_delete_unlinked_tags()
    # Return {"deleted": count}
```

---

### Step 2: Album

One junction table (`SongAlbums`), but albums have their own metadata links (`AlbumCredits`, `AlbumPublishers`) that become dangling when the album is soft-deleted. Both single delete and bulk delete must clean these up.

#### 2a. Repository: `AlbumRepository`

**File:** `src/data/album_repository.py`

```python
def soft_delete(self, album_id: int, conn: sqlite3.Connection) -> bool:
    """Set IsDeleted = 1. Returns True if updated."""

def count_linked_songs(self, album_id: int, conn: sqlite3.Connection) -> int:
    """Count active songs in this album. Used by single delete guard."""
    # SELECT COUNT(*) FROM SongAlbums sa
    # JOIN MediaSources ms ON sa.SourceID = ms.SourceID
    # WHERE sa.AlbumID = ? AND ms.IsDeleted = 0

def delete_album_links(self, album_id: int, conn: sqlite3.Connection) -> None:
    """Hard-delete AlbumCredits and AlbumPublishers rows for this album.
    Called before soft_delete — same pattern as delete_song_links()."""
    # DELETE FROM AlbumCredits WHERE AlbumID = ?
    # DELETE FROM AlbumPublishers WHERE AlbumID = ?
```

#### 2b. Service: `CatalogService`

**Feature A — Single delete:**
```python
def delete_album(self, album_id: int) -> bool:
    """Soft-delete album if zero active songs are linked."""
    # 1. count_linked_songs → if > 0, return False
    # 2. delete_album_links (purge AlbumCredits + AlbumPublishers)
    # 3. soft_delete album
    # 4. commit, return True
```

**Feature B — Bulk:**
```python
def get_unlinked_albums(self) -> List[Album]:
    """Find all albums with zero active songs."""

def bulk_delete_unlinked_albums(self) -> int:
    """Soft-delete all unlinked albums in one transaction."""
    # 1. get_unlinked_albums() → list
    # 2. Open connection
    # 3. For each: delete_album_links + soft_delete (no guard — already proven unlinked)
    # 4. commit, return count
```

#### 2c. Tests

Feature A tests:
- `test_delete_unlinked_album_succeeds` — album with 0 songs → soft-deleted, AlbumCredits/AlbumPublishers purged
- `test_delete_linked_album_is_rejected` — album with active songs → False
- `test_delete_album_linked_only_to_deleted_songs` — IS unlinked → succeeds
- `test_delete_album_purges_album_credits_and_publishers` — verify rows are gone

Feature B tests:
- `test_get_unlinked_albums_returns_only_orphans`
- `test_bulk_delete_unlinked_albums` — purges album links too

#### 2d. API Endpoints

```
DELETE /api/v1/albums/{album_id:int}
DELETE /api/v1/albums?unlinked=true
```

---

### Step 3: Publisher

**Dual-table check** — publishers can be linked to songs (`RecordingPublishers`) AND albums (`AlbumPublishers`). Must be unlinked from BOTH to be deletable.

#### 3a. Repository: `PublisherRepository`

**File:** `src/data/publisher_repository.py`

```python
def soft_delete(self, publisher_id: int, conn: sqlite3.Connection) -> bool:
    """Set IsDeleted = 1."""

def count_linked_songs(self, publisher_id: int, conn: sqlite3.Connection) -> int:
    """Count active songs linked via RecordingPublishers."""
    # JOIN MediaSources to check IsDeleted = 0

def count_linked_albums(self, publisher_id: int, conn: sqlite3.Connection) -> int:
    """Count active albums linked via AlbumPublishers."""
    # JOIN Albums to check IsDeleted = 0
```

#### 3b. Service: `CatalogService`

**Feature A — Single delete:**
```python
def delete_publisher(self, publisher_id: int) -> bool:
    """Soft-delete publisher if zero active songs AND zero active albums."""
    # 1. count_linked_songs → if > 0, return False
    # 2. count_linked_albums → if > 0, return False
    # 3. soft_delete
    # 4. commit, return True
```

**Feature B — Bulk:**
```python
def get_unlinked_publishers(self) -> List[Publisher]:
    """Find publishers with zero active songs AND zero active albums."""

def bulk_delete_unlinked_publishers(self) -> int:
    """get_unlinked_publishers() → soft-delete each in one transaction."""
```

**Subtlety:** A publisher linked to a soft-deleted album is still "unlinked" — the album is invisible. `count_linked_albums` must check `Albums.IsDeleted = 0`.

#### 3c. Tests

Feature A tests:
- `test_delete_publisher_with_no_links` — succeeds
- `test_delete_publisher_linked_to_active_song` — rejected
- `test_delete_publisher_linked_to_active_album` — rejected
- `test_delete_publisher_linked_to_deleted_song_and_deleted_album` — succeeds

Feature B tests:
- `test_get_unlinked_publishers_dual_check`
- `test_bulk_delete_unlinked_publishers`

#### 3d. API Endpoints

```
DELETE /api/v1/publishers/{publisher_id:int}
DELETE /api/v1/publishers?unlinked=true
```

---

### Step 4: Identity (Most Complex)

**Full identity tree checking**: an Identity has multiple ArtistNames (aliases), and ANY alias could be linked to songs via `SongCredits` or albums via `AlbumCredits`. Deletion is all-or-nothing for the entire tree.

#### 4a. Repository: `IdentityRepository`

**File:** `src/data/identity_repository.py`

```python
def soft_delete(self, identity_id: int, conn: sqlite3.Connection) -> bool:
    """Soft-delete the Identity AND all its ArtistNames rows."""
    # UPDATE Identities SET IsDeleted = 1 WHERE IdentityID = ? AND IsDeleted = 0
    # UPDATE ArtistNames SET IsDeleted = 1 WHERE OwnerIdentityID = ? AND IsDeleted = 0
    # Return True if Identity row was updated

def count_linked_songs(self, identity_id: int, conn: sqlite3.Connection) -> int:
    """Count active songs credited to ANY alias of this identity."""
    # SELECT COUNT(DISTINCT sc.SourceID)
    # FROM SongCredits sc
    # JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
    # JOIN MediaSources ms ON sc.SourceID = ms.SourceID
    # WHERE an.OwnerIdentityID = ? AND ms.IsDeleted = 0

def count_linked_albums(self, identity_id: int, conn: sqlite3.Connection) -> int:
    """Count active albums credited to ANY alias of this identity."""
    # SELECT COUNT(DISTINCT ac.AlbumID)
    # FROM AlbumCredits ac
    # JOIN ArtistNames an ON ac.CreditedNameID = an.NameID
    # JOIN Albums a ON ac.AlbumID = a.AlbumID
    # WHERE an.OwnerIdentityID = ? AND a.IsDeleted = 0
```

**Orphan ArtistNames note:** Some ArtistNames have `OwnerIdentityID = NULL` (created during ingestion, never linked to an Identity). These can't be deleted via Identity deletion. Skipped for MVP — future "identity resolution" pass.

#### 4b. Service: `CatalogService`

**Feature A — Single delete:**
```python
def delete_identity(self, identity_id: int) -> bool:
    """Soft-delete identity + all aliases if zero active songs/albums across ALL aliases."""
    # 1. count_linked_songs(identity_id) → if > 0, return False
    # 2. count_linked_albums(identity_id) → if > 0, return False
    # 3. identity_repo.soft_delete(identity_id, conn) → marks Identity + ArtistNames
    # 4. commit, return True
```

**Feature B — Bulk:**
```python
def get_unlinked_identities(self) -> List[Identity]:
    """Find identities with zero active songs/albums across any alias."""

def bulk_delete_unlinked_identities(self) -> int:
    """get_unlinked_identities() → soft-delete each in one transaction."""
```

#### 4c. Tests

Feature A tests:
- `test_delete_identity_with_no_links` — Identity + ArtistNames all get IsDeleted = 1
- `test_delete_identity_with_active_song_via_primary_alias` — rejected
- `test_delete_identity_with_active_song_via_secondary_alias` — also rejected (any alias blocks)
- `test_delete_identity_with_active_album_credit` — rejected
- `test_delete_identity_linked_only_to_deleted_songs` — succeeds
- `test_delete_identity_soft_deletes_all_aliases` — verify every ArtistNames row gets IsDeleted = 1

Feature B tests:
- `test_get_unlinked_identities_full_tree_check`
- `test_bulk_delete_unlinked_identities`

#### 4d. API Endpoints

```
DELETE /api/v1/identities/{identity_id:int}
DELETE /api/v1/identities?unlinked=true
```

---

### Step 5: API Endpoint Integration Tests

**File:** `tests/test_api/test_orphan_deletion_api.py` (new)

**Note:** Requires httpx (not currently installed). May need to be deferred.

Test each endpoint pair (single + bulk) for each entity type:
- 204 on successful single delete
- 403 on linked entity
- 404 on nonexistent entity
- Bulk returns `{"deleted": N}`
- Bulk requires `?unlinked=true` (400 without it)

---

### Step 6: Frontend

#### 6a. API Client

**File:** `src/static/js/dashboard/api.js`

```javascript
async function deleteEntity(entityType, entityId) { ... }
async function bulkDeleteUnlinked(entityType) { ... }
```

#### 6b. "Show Unlinked" Toggle (Feature B UI)

**Files:** Each renderer (`albums.js`, `artists.js`, `publishers.js`, `tags.js`)

- Add toggle button to view header
- Track toggle state per view
- Client-side filter: entity is "unlinked" if its song/link count is 0
- When ON: filter list to show only unlinked entities
- Show "Delete All Unlinked" button when toggle is ON

#### 6c. "Delete All Unlinked" Button + Modal (Feature B UI)

- Button appears when toggle is ON
- Opens confirmation modal with count + scrollable list
- Calls `bulkDeleteUnlinked()` API
- Refreshes list on success, `alert()` on error

#### 6d. Detail Panel Delete Button (Feature A UI)

- Add delete button to each entity's detail panel
- Disabled with tooltip when entity has linked songs
- Enabled when unlinked
- Calls single `DELETE /api/v1/{entity}/{id}`
- Closes panel + refreshes list on success

---

## Unlinked Query Reference

The `get_unlinked_*()` queries used by Feature B. These go in the service layer (not repos — per Smart Service / Dumb Repo).

### Tags (simplest)
```sql
SELECT t.TagID, t.TagName, t.TagCategory
FROM Tags t
LEFT JOIN MediaSourceTags mst ON t.TagID = mst.TagID
LEFT JOIN MediaSources ms ON mst.SourceID = ms.SourceID AND ms.IsDeleted = 0
WHERE t.IsDeleted = 0
GROUP BY t.TagID
HAVING COUNT(ms.SourceID) = 0
```

### Albums
```sql
SELECT a.AlbumID, a.AlbumTitle, a.ReleaseYear, a.AlbumType
FROM Albums a
LEFT JOIN SongAlbums sa ON a.AlbumID = sa.AlbumID
LEFT JOIN MediaSources ms ON sa.SourceID = ms.SourceID AND ms.IsDeleted = 0
WHERE a.IsDeleted = 0
GROUP BY a.AlbumID
HAVING COUNT(ms.SourceID) = 0
```

### Publishers (dual check)
```sql
SELECT p.PublisherID, p.PublisherName, p.ParentPublisherID
FROM Publishers p
LEFT JOIN RecordingPublishers rp ON p.PublisherID = rp.PublisherID
LEFT JOIN MediaSources ms ON rp.SourceID = ms.SourceID AND ms.IsDeleted = 0
LEFT JOIN AlbumPublishers ap ON p.PublisherID = ap.PublisherID
LEFT JOIN Albums a ON ap.AlbumID = a.AlbumID AND a.IsDeleted = 0
WHERE p.IsDeleted = 0
GROUP BY p.PublisherID
HAVING COUNT(ms.SourceID) = 0 AND COUNT(a.AlbumID) = 0
```

### Identities (full tree)
```sql
SELECT i.IdentityID, i.IdentityType, i.LegalName
FROM Identities i
WHERE i.IsDeleted = 0
AND NOT EXISTS (
    SELECT 1 FROM ArtistNames an
    JOIN SongCredits sc ON an.NameID = sc.CreditedNameID
    JOIN MediaSources ms ON sc.SourceID = ms.SourceID
    WHERE an.OwnerIdentityID = i.IdentityID AND ms.IsDeleted = 0
)
AND NOT EXISTS (
    SELECT 1 FROM ArtistNames an
    JOIN AlbumCredits ac ON an.NameID = ac.CreditedNameID
    JOIN Albums a ON ac.AlbumID = a.AlbumID
    WHERE an.OwnerIdentityID = i.IdentityID AND a.IsDeleted = 0
)
```

---

## File Change Summary

### New Files
| File | Purpose |
|------|---------|
| `tests/test_services/test_orphan_deletion.py` | All service-layer delete tests (Feature A + B) |
| `tests/test_api/test_orphan_deletion_api.py` | API endpoint tests (requires httpx) |

### Modified Files
| File | Changes |
|------|---------|
| `src/data/tag_repository.py` | `soft_delete()`, `count_linked_songs()` |
| `src/data/album_repository.py` | `soft_delete()`, `count_linked_songs()`, `delete_album_links()` |
| `src/data/publisher_repository.py` | `soft_delete()`, `count_linked_songs()`, `count_linked_albums()` |
| `src/data/identity_repository.py` | `soft_delete()`, `count_linked_songs()`, `count_linked_albums()` |
| `src/services/catalog_service.py` | 12 methods: `delete_*` × 4, `get_unlinked_*` × 4, `bulk_delete_unlinked_*` × 4 |
| `src/engine/routers/catalog.py` | 8 DELETE endpoints (single + bulk × 4 types) |
| `src/static/js/dashboard/api.js` | `deleteEntity()`, `bulkDeleteUnlinked()` |
| `src/static/js/dashboard/renderers/*.js` | Toggle, bulk modal, detail delete button (all 4 renderers) |

---

## Implementation Notes

- **Transaction pattern:** All write operations use `conn = repo.get_connection()` → work → `conn.commit()` / `conn.rollback()` → `conn.close()`. Same as `delete_song()`.
- **FK constraints won't fire:** Because soft-delete is `UPDATE`, not `DELETE`. Feature A must always guard with `count_linked_*()` before soft-deleting.
- **Feature B skips guards:** The `get_unlinked_*()` query already proves entities are orphans. No redundant `count_linked_*()` check needed.
- **Bulk operations are all-or-nothing:** Single transaction. If any soft-delete fails, roll back everything.
- **"Linked to deleted" = "unlinked":** A tag whose only songs are soft-deleted IS unlinked. All link-checking queries must join to the parent entity table and verify `IsDeleted = 0`.
