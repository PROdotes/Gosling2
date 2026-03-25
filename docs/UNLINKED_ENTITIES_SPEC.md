# Unlinked Entity Cleanup Feature

## Overview
A maintenance/hygiene feature for cleaning up orphaned metadata entities (Albums, Artists, Publishers, Tags) that are no longer linked to any songs.

## User Workflow
- **Primary use case:** Periodic cleanup (every few days) to remove garbage/orphaned data from the database
- **Secondary use case:** Spot-check and delete individual typos or duplicates
- Users need both granular control (delete one) and bulk cleanup (delete all unlinked)

## UI Components

### 1. Tags View (New)
Add "Tags" tab to main navigation bar:
```
Songs | Albums | Artists | Publishers | Tags | Ingest
```

Tags view follows the same pattern as other entity views:
- Card-based list view showing: tag name, category badge (genre/other)
- Detail panel on selection showing: tag name, category, linked songs list, delete button (if unlinked), audit history

### 2. "Show Unlinked" Toggle
- Located at the top of Albums/Artists/Publishers/Tags views
- When ON: filters the current view to show ONLY unlinked entities (client-side filtering)
- When OFF: shows all entities as normal

### 3. "Delete All Unlinked" Button
- Visible when "Show Unlinked" toggle is ON
- Always clickable (no disabled state)
- Opens confirmation modal with:
  - Count: "Delete 47 unlinked artists?" (or "Delete 0 unlinked artists?" if none)
  - Scrollable list of entities to be deleted (format: "Name (#ID)")
  - Confirm/Cancel buttons
- On success: refresh list, close modal
- On error: show alert()
- Note: If count is 0, modal still opens but list is empty (avoids extra conditional UI logic)

### 4. Detail Panel Delete Button
- Appears in detail panel for all 4 entity types (albums, artists, publishers, tags)
- Behavior:
  - **If unlinked:** Button enabled, click deletes entity
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

### New Endpoints

#### Single Delete
```
DELETE /api/albums/:id
DELETE /api/artists/:id
DELETE /api/publishers/:id
DELETE /api/tags/:id
```

**Response:**
- 204 No Content (success)
- 403 Forbidden (if entity is linked)
- 404 Not Found (if entity doesn't exist)

**Authorization:** Check if entity is unlinked before allowing deletion

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
- Only deletes entities that pass the "unlinked" check
- Returns count of successfully deleted entities

### Validation Rules
- All DELETE operations must verify entity is unlinked before deletion
- Return 403 Forbidden if entity has active links
- Use database transactions for bulk operations

## Frontend Implementation

### Filtering Logic
- Client-side filtering when "Show Unlinked" toggle is active
- No new API calls required (filters currently loaded results)
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
- Deletion is all-or-nothing for the entire identity tree

### Publisher Multi-Relationship Check
Publishers can be linked to both songs AND albums, requiring checks across both tables.

### Transaction Safety
All bulk delete operations must be wrapped in database transactions to ensure atomicity.

## Future Enhancements (Out of Scope)
- Selection mode with checkboxes for selective bulk delete
- Server-side filtering with `?unlinked=true` query param on list endpoints
- Toast notification system instead of alert()
- Undo functionality for delete operations
- Pagination support for unlinked entity lists
