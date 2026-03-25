# Phase 2: Frontend Sorting Specification

## Overview
MVP sorting feature to solve immediate pain point of finding "last" ingested songs. Frontend-only implementation with planned backend migration.

---

## Resolution Log

1. **Scope**: Frontend-only sorting for songs list (marked with TODO for backend migration)
2. **Location**: Sort controls render above song cards, below search bar
3. **Sortable Fields**:
   - Title (`media_name`)
   - Artist (`display_artist`)
   - ID (`id`)
4. **UI Layout**:
   ```
   Sort: [Clear]
     ↑  [Title]  [Artist]  [ID]    <- Ascending row
     ↓  [Title]  [Artist]  [ID]    <- Descending row
   ```
5. **Interaction Behavior**:
   - Single selection only (radio button pattern)
   - Click any sort button → apply that sort immediately
   - Click [Clear] → return to default API order
   - Active button receives visual highlight
6. **Default State**: No sort applied (songs render in API return order)
7. **Null Handling**:
   - ASC: nulls sorted to bottom
   - DESC: nulls sorted to top (symmetric behavior)
8. **Implementation Details**:
   - ~60 lines total in `songs.js`
   - Add TODO comment marking for backend migration during Advanced Filters phase
   - No server changes required
   - Sort function signature: `sortSongs(songs, field, direction)`
   - Re-render uses existing `renderSongs()` function

---

## Files Modified
- `src/static/js/dashboard/renderers/songs.js` - Sort logic + button handlers
- `src/static/css/dashboard.css` (or equivalent) - Sort control styling

---

## Future Work
**TODO**: Migrate to backend sorting when implementing Phase 2 Advanced Filters. Backend implementation will require:
- Router: Add `sort_by` and `order` query params to `/songs/search`
- Service: Pass-through to repository
- Repository: SQL `ORDER BY` clause
- Remove frontend sort logic
