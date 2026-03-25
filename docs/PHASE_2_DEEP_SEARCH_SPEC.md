# Phase 2: Deep Search Specification

## Overview
Universal search across all song fields. Complements Surface Search (title/artist only) with comprehensive field coverage for power users.

---

## Resolution Log

### Search Modes

**Surface Search (Default):**
- Searches: Title (`media_name`) + Artist (`display_artist`) fields only
- Fast, simple queries
- For quick "I know the song/artist name" lookups

**Deep Search (Toggle ON):**
- Searches: ALL song fields (title, artist, year, BPM, ISRC, credits, albums, tags, publishers)
- Slower, comprehensive queries
- For "I remember something about this song" scenarios
- Example: Search "1991" finds songs from that year, not just titles containing "1991"

### Search Behavior

**Critical: Search bar filters the filter sidebar, NOT songs directly**

1. User types query in search bar
2. Filter sidebar updates to show only filter values containing the query text
3. User clicks a filter → songs update to show filtered results
4. Search bar remains populated (add X clear button for UX)

**Example Flow:**
- Type "ana" → Sidebar shows "Ana Srećković", "Ivana Kindl", "Dana", "Pravda za Vedrana" (album) from complete filter catalog
- Click "Ana Srećković" → Song list shows only her songs
- Type "2021" in search → Sidebar shows "2021" year filter (and any other filters containing "2021" text)
- Click "2021" → Song list narrows to Ana's 2021 songs (if AND mode) OR shows all 2021 songs (if ANY mode)

### Filter Sidebar Architecture

**Filter Categories (Dynamic):**
- Album
- Artist (only Performer role - separate from All Contributors for quick access)
- Publisher
- Year
- Decade (computed from year)
- All Contributors (any credited person, any role)
- TOGGLE LIVE (show only active songs via `is_active` field)
- Tag categories (dynamic based on `Tags.category` values in DB)
  - Genre, Festival, and any user-created categories
  - Examples: "DJ Favourites: Bob", "Wedding Songs", etc.
- Status (completeness: Not Done, Ready to Finalize, Missing Data, ~~Done~~ not implemented yet)

**Filter Building:**
- Filters built via `SELECT DISTINCT` queries when database changes (ingestion, deletion, metadata edits)
- Rebuilt immediately on every write (MVP - optimize later if needed)
- Complete catalog loaded upfront (~80MB for 100k songs - acceptable)
- Examples:
  ```sql
  SELECT DISTINCT year FROM Songs WHERE year IS NOT NULL ORDER BY year DESC
  SELECT DISTINCT an.display_name FROM ArtistNames an
    JOIN SongCredits sc ON an.NameID = sc.CreditedNameID
    ORDER BY an.display_name
  SELECT DISTINCT category FROM Tags WHERE category IS NOT NULL
  ```

**Filter Interaction:**
- Multiple filters can be selected
- Logic mode controlled by ALL/ANY toggle:
  - ALL = AND logic (intersection)
  - ANY = OR logic (union)
  - Default: ALL (AND)
  - Persists until manually toggled
  - Filter selections persist when switching modes (re-query with new logic)

**Filter Sidebar Search (Critical - Non-Standard Behavior):**
- Search bar performs **literal text search on filter values** (independent of Surface/Deep mode)
- Does NOT filter songs directly
- Does NOT filter based on current song results - always searches the complete filter catalog
- Example: Search "ana" shows ALL filters containing "ana" text: "Ana Srećković", "Ivana Kindl", "Dana", "Pravda za Vedrana" (album)
- Example: Search "1991" shows Year filter "1991", plus any artists/albums/tags containing "1991" in their name
- Use case: "Too many songs, let me find a specific filter to narrow down" - not "show me facets of current results"

### UI Controls

**Top Bar Buttons:**
- `[ALL +]` - Expand all filter category trees
- `[ALL -]` - Collapse all filter category trees
- `[ALL]` or `[ANY]` - Logic mode toggle (ALL=AND, ANY=OR)
- Media type filters: `[ALL (count)]`, `[MUS (count)]` - Filter by MediaSource type (future: podcasts, audiobooks)

**Search Bar:**
- Text input for filtering sidebar
- `[X]` clear button (new addition)
- `[☐ Deep Search]` toggle checkbox

**Result Counts:**
- Nice-to-have but not MVP
- Example: "Rock (234)" vs just "Rock"

**Unavailable Filters:**
- MVP: Show all filters regardless of current results
- Future: Could gray out or hide filters with 0 results in current context

### Deep Search Query Coverage

**Fields Searched:**

**Song Core:**
- Title (`media_name`)
- Year (`year`)
- BPM (`bpm`)
- ISRC (`isrc`)
- Duration (`duration_s` / `formatted_duration`)

**Relationships (via joins):**
- All Credits: `display_name` + `role_name` (SongCredits → ArtistNames + Roles)
- Albums: `album_title` (SongAlbums → Albums)
- Publishers: `publisher_name` (RecordingPublishers → Publishers)
- Tags: `tag_name` (MediaSourceTags → Tags)

**Derived Fields:**
- Decade (computed from year)
- Primary Genre (specific tag category)

**Not Searched (MVP):**
- Audio hash (too technical)
- Source path (file system detail)

### Query Behavior

**No Token Splitting (MVP):**
- Query "bob marley 1981" searches for exact phrase "bob marley 1981" in each field
- Will return 0 results (no single field contains that full phrase)
- Simplifies implementation, avoids complex parsing logic

**Future Enhancement:**
- Field prefix syntax: `artist:Grohl year:1991`
- Token splitting with relevance ranking
- FTS5 full-text search index

### Performance Considerations

**Current Approach:**
- Load all filter values upfront (~80MB for 100k songs)
- Filter sidebar search is client-side JavaScript (instant)
- Song queries are server-side SQL with `LIKE '%term%'` across multiple fields
- Expected performance for Deep Search:
  - < 1,000 songs: ~50ms
  - 1,000-10,000 songs: ~200-500ms
  - 10,000-100,000 songs: ~2-5 seconds

**Acceptable for MVP** - Can optimize with FTS5 index later if needed.

**Filter Rebuild Strategy (MVP: Rebuild on Every Write):**
- On DB write (ingestion, edit, delete): Immediately rebuild filter cache
- Simple, correct, no stale data
- Expected rebuild time for 100k songs: <500ms (acceptable for MVP)
- Frontend fetches fresh filters on next `/filters` API call
- Future optimization: Add dirty flag + lazy rebuild if rebuild becomes a bottleneck

---

## Implementation Notes

### Backend (SQL Query)

**Surface Search Query:**
```sql
SELECT DISTINCT s.* FROM Songs s
LEFT JOIN SongCredits sc ON s.SourceID = sc.SourceID
LEFT JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
WHERE s.media_name LIKE '%query%'
   OR an.display_name LIKE '%query%'
```

**Deep Search Query:**
```sql
SELECT DISTINCT s.* FROM Songs s
LEFT JOIN SongCredits sc ON s.SourceID = sc.SourceID
LEFT JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
LEFT JOIN Roles r ON sc.RoleID = r.RoleID
LEFT JOIN SongAlbums sa ON s.SourceID = sa.SourceID
LEFT JOIN Albums a ON sa.AlbumID = a.AlbumID
LEFT JOIN RecordingPublishers rp ON s.SourceID = rp.SourceID
LEFT JOIN Publishers p ON rp.PublisherID = p.PublisherID
LEFT JOIN MediaSourceTags mst ON s.SourceID = mst.SourceID
LEFT JOIN Tags t ON mst.TagID = t.TagID
WHERE s.media_name LIKE '%query%'
   OR an.display_name LIKE '%query%'
   OR r.role_name LIKE '%query%'
   OR a.album_title LIKE '%query%'
   OR p.publisher_name LIKE '%query%'
   OR t.tag_name LIKE '%query%'
   OR CAST(s.year AS TEXT) LIKE '%query%'
   OR CAST(s.bpm AS TEXT) LIKE '%query%'
   OR s.isrc LIKE '%query%'
```

### Frontend

**Filter Sidebar Search (existing behavior):**
- JavaScript filters pre-loaded filter values by text match
- Independent of Surface/Deep toggle

**Deep Search Toggle:**
- Checkbox that changes API endpoint or passes `deep=true` param
- Triggers different SQL query on backend

---

## Files Modified

**Backend:**
- `src/engine/routers/catalog.py` - Add `deep` parameter to `/songs/search` endpoint
- `src/services/catalog_service.py` - Add `search_songs_deep()` method
- `src/data/song_repository.py` - Add `search_deep()` with multi-join query

**Frontend:**
- `src/static/js/dashboard/api.js` - Add `deep` parameter to search API call
- `src/static/js/dashboard/main.js` - Add Deep Search toggle UI + handler
- `src/templates/dashboard.html` - Add toggle checkbox
- `src/static/css/dashboard.css` - Style toggle

---

## Future Enhancements

1. **Field-Prefix Syntax:** `artist:Grohl year:1991`
2. **Range Queries:** `year:1990-1995`, `bpm:120-140`
3. **FTS5 Index:** For sub-100ms searches on 100k+ songs
4. **Token Splitting:** "bob marley 1981" → ["bob", "marley", "1981"] with relevance ranking
5. **Filter Result Counts:** Show "(234)" next to filter values
6. **Smart Filter Hiding:** Gray out or hide filters with 0 results in current context
7. **Search History:** Remember recent searches
8. **Saved Searches:** Bookmark complex filter combinations
