# Unlinked Entity Cleanup Feature

**Status:** Phase 1 complete ✅ | Phase 2 pending
**Deletion Strategy:** Soft delete (see [SOFT_DELETE_PIVOT.md](SOFT_DELETE_PIVOT.md))

## Overview
A maintenance/hygiene feature for cleaning up orphaned metadata entities (Albums, Artists, Publishers, Tags) that are no longer linked to any songs.

Entities are **soft-deleted** (`IsDeleted = 1`) — they remain in the database but are hidden from all normal read operations. Link/junction rows (SongCredits, SongAlbums, MediaSourceTags, AlbumCredits, AlbumPublishers, RecordingPublishers) are still **hard-deleted** as part of normal song removal — when a song is removed, its junction rows are physically deleted, which may leave the connected entities unlinked.

## User Workflow
- **Primary use case:** Periodic cleanup (every few days) to soft-delete garbage/orphaned data from the database
- **Secondary use case:** Spot-check and soft-delete individual typos or duplicates
- Users need both granular control (delete one) and bulk cleanup (delete all unlinked)

## Deletion Model

### What gets soft-deleted (entities)
These tables gain an `IsDeleted BOOLEAN DEFAULT 0` column:
- `Songs` / `MediaSources`
- `Albums`
- `Identities` / `ArtistNames`
- `Publishers`
- `Tags`

Soft-deleting an entity means `UPDATE SET IsDeleted = 1`. The row stays in the database permanently.

### What gets hard-deleted (links)
Junction/link rows are physically removed. These tables have **no** `IsDeleted` column:
- `SongCredits` — artist ↔ song
- `SongAlbums` — song ↔ album
- `MediaSourceTags` — song ↔ tag
- `AlbumCredits` — artist ↔ album
- `AlbumPublishers` — album ↔ publisher
- `RecordingPublishers` — song ↔ publisher

**Example:** Soft-deleting Song 7 sets `IsDeleted = 1` on its MediaSources/Songs rows and hard-deletes the SongCredits, SongAlbums, MediaSourceTags, and RecordingPublishers rows that reference it. Artist 5 and Album 3 remain — they just become unlinked if nothing else points to them.

### Reconnection on re-insert
When inserting an entity that matches a soft-deleted record (e.g. re-ingesting a publisher named "Universal Music"), the system must **upsert**: set `IsDeleted = 0` on the existing row instead of creating a duplicate or failing on UNIQUE constraints.

## UI Components

### 1. Tags View (New) ✅ COMPLETE
Add "Tags" tab to main navigation bar:
```
Songs | Albums | Artists | Publishers | Tags | Ingest
```

Tags view follows the same pattern as other entity views:
- Card-based list view showing: tag name, category badge (genre/other)
- Detail panel on selection showing: tag name, category, linked songs list, ~~delete button (if unlinked)~~, ~~audit history~~

**Implementation Notes:**
- Backend: Added `TagRepository` methods (get_all, search, get_by_id, get_song_ids_by_tag)
- Backend: Added `CatalogService` tag methods and `/api/v1/tags/*` endpoints
- Frontend: Added tags mode to dashboard with [tags.js](../src/static/js/dashboard/renderers/tags.js) renderer
- Category badges styled with `tag-category-badge` class (genre/other)
- Delete button and audit history deferred to Phase 2

### 2. "Show Unlinked" Toggle
- Located at the top of Albums/Artists/Publishers/Tags views
- When ON: filters the current view to show ONLY unlinked entities (client-side filtering)
- When OFF: shows all entities as normal

### 3. "Delete All Unlinked" Button
- Visible when "Show Unlinked" toggle is ON
- Always clickable (no disabled state)
- Opens confirmation modal with:
  - Count: "Delete 47 unlinked artists?" (or "Delete 0 unlinked artists?" if none)
  - Scrollable list of entities to be soft-deleted (format: "Name (#ID)")
  - Confirm/Cancel buttons
- On success: refresh list, close modal
- On error: show alert()
- Note: If count is 0, modal still opens but list is empty (avoids extra conditional UI logic)

### 4. Detail Panel Delete Button
- Appears in detail panel for all 4 entity types (albums, artists, publishers, tags)
- Behavior:
  - **If unlinked:** Button enabled, click soft-deletes entity
  - **If linked:** Button disabled/grayed with tooltip "Cannot delete - X songs attached"
- On successful delete: close detail panel, refresh list
- On error: show alert()

## "Unlinked" Definition

### Artists
- Zero songs/credits referencing ANY of its aliases (full identity tree check)
- Note: Cannot delete individual unused aliases while other aliases exist, as this would require promoting a new carrier/primary (user decision, not automatic)

### Albums
- Zero songs in the album

### Publishers
- Zero songs with this publisher AND zero albums with this publisher

### Tags
- Zero songs with this tag

## Backend Implementation

### Architecture: Smart Service / Dumb Repo

Per the soft delete pivot, the service layer owns all authorization and business logic:

- **Repositories** perform raw SQL only — `UPDATE X SET IsDeleted = 1`, simple `SELECT` with `WHERE IsDeleted = 0`, etc. No dependency-chain calculations in repos.
- **CatalogService** owns the "is this entity linked?" validation before issuing the soft-delete command to the repo.
- **Critical:** Because soft delete is an `UPDATE` (not a `DELETE`), FK constraints like `RESTRICT` **will not fire**. The service layer must explicitly check for active links before soft-deleting.

### Read Operations
Every `get_`, `search_`, and `get_all` repository method must include `WHERE IsDeleted = 0` to exclude soft-deleted entities from normal results.

### New Endpoints

#### Single Delete
```
DELETE /api/albums/:id
DELETE /api/artists/:id
DELETE /api/publishers/:id
DELETE /api/tags/:id
```

**Behavior:** Sets `IsDeleted = 1` on the target entity.

**Response:**
- 204 No Content (success)
- 403 Forbidden (if entity is linked — service layer checks active links first)
- 404 Not Found (if entity doesn't exist or is already soft-deleted)

#### Bulk Delete
```
DELETE /api/albums?unlinked=true
DELETE /api/artists?unlinked=true
DELETE /api/publishers?unlinked=true
DELETE /api/tags?unlinked=true
```

**Response:**
```json
{
  "deleted": 47
}
```

**Behavior:**
- Transaction-based (all-or-nothing)
- Service layer identifies all unlinked entities, then soft-deletes them in a single transaction
- Returns count of soft-deleted entities

### Validation Rules
- All delete operations must verify entity is unlinked via the **service layer** (not FK constraints)
- Return 403 Forbidden if entity has active links
- Use database transactions for bulk operations

## Frontend Implementation

### Filtering Logic
- Client-side filtering when "Show Unlinked" toggle is active
- No new API calls required (filters currently loaded results)
- Soft-deleted entities are already excluded from API responses by the `WHERE IsDeleted = 0` filter, so the frontend never sees them
- Note: May be inaccurate if pagination/limits are in effect, but acceptable for MVP

### State Management
- Track toggle state per view (albums/artists/publishers/tags)
- Refresh list after any delete operation
- Close detail panel after individual delete

### Error Handling
- Use `alert()` for error messages (no toast system implemented)
- Show count in disabled button tooltip for linked entities

## Technical Notes

### Artist Deletion Complexity
Artists require special handling due to alias relationships:
- Always check ALL aliases in the identity tree (regardless of which alias is the carrier/primary)
- Cannot delete individual aliases selectively, as this would require choosing a new carrier/primary
- Soft-deletion is all-or-nothing for the entire identity tree (Identities + all ArtistNames rows)

### Publisher Multi-Relationship Check
Publishers can be linked to both songs (RecordingPublishers) AND albums (AlbumPublishers), requiring checks across both tables. Service layer must query both before allowing soft-delete.

### FK Constraints Will Not Fire
This is the most critical difference from hard delete. Since `UPDATE SET IsDeleted = 1` is not a `DELETE`, the database will happily let you "soft-delete" an ArtistName that has 500 SongCredits pointing at it. The **service layer must enforce** the linked-entity check before every soft-delete.

### Transaction Safety
All bulk soft-delete operations must be wrapped in database transactions to ensure atomicity.

## Future Enhancements (Out of Scope)
- Selection mode with checkboxes for selective bulk delete
- Server-side filtering with `?unlinked=true` query param on list endpoints
- Toast notification system instead of alert()
- Restore/undelete functionality (re-activate soft-deleted entities)
- Pagination support for unlinked entity lists
