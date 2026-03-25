# Phase 2: Advanced Filters Specification

## Overview
Comprehensive filter sidebar for narrowing song results by metadata, credits, tags, and completeness status. Works in tandem with Deep Search (search bar filters the filter sidebar).

---

## Resolution Log

### Filter Architecture

**Filter Sidebar Behavior:**
- Displays all available filter categories with clickable values
- Multiple filters can be selected simultaneously
- Logic mode controlled by ALL/ANY toggle (see UI Controls)
- Filter selections persist when switching logic modes
- Search bar filters the sidebar itself (shows only matching filter values)

**Filter Building:**
- Built from `SELECT DISTINCT` queries when database changes (ingestion, deletion, metadata edits)
- Rebuilt immediately on every write (MVP - simple and correct, optimize later if needed)
- Complete catalog loaded upfront for instant client-side filtering
- Examples:
  ```sql
  -- Artist filter (Performer role only)
  SELECT DISTINCT an.display_name
  FROM ArtistNames an
  JOIN SongCredits sc ON an.NameID = sc.CreditedNameID
  JOIN Roles r ON sc.RoleID = r.RoleID
  WHERE r.role_name = 'Performer'
  ORDER BY an.display_name

  -- All Contributors (all roles)
  SELECT DISTINCT an.display_name
  FROM ArtistNames an
  JOIN SongCredits sc ON an.NameID = sc.CreditedNameID
  ORDER BY an.display_name

  -- Year
  SELECT DISTINCT year FROM Songs
  WHERE year IS NOT NULL
  ORDER BY year DESC

  -- Decade (computed)
  SELECT DISTINCT (year / 10) * 10 AS decade
  FROM Songs
  WHERE year IS NOT NULL
  ORDER BY decade DESC

  -- Tag categories (dynamic)
  SELECT DISTINCT category FROM Tags
  WHERE category IS NOT NULL
  -- Then for each category:
  SELECT DISTINCT name FROM Tags WHERE category = ?
  ```

### Filter Categories

#### MVP Filters (Must-Have)

**Artist**
- Source: `Credits` table where `role_name = 'Performer'`
- Shows only performers (not composers, producers, etc.)
- Use case: "Show me all songs Taylor Hawkins performed on"
- Flat list, no role grouping

**All Contributors**
- Source: `Credits` table, ALL roles
- Shows everyone (performers, composers, producers, engineers, etc.)
- Use case: "Show me anything Taylor Hawkins touched (any role)"
- Flat list, no grouping by role (removed from old system - was a vestige)

**Year**
- Source: `Songs.year`
- Exact year values (1990, 1991, 1995, etc.)
- Ordered descending (newest first)

**Decade**
- Source: Computed from `Songs.year` (`(year / 10) * 10`)
- Groups: 1960s, 1970s, 1980s, 1990s, 2000s, 2010s, 2020s
- Clicking "1990s" filters to `year >= 1990 AND year < 2000`
- Rationale: In old app, decade was a tag - annoying to maintain. Now computed.

**TOGGLE LIVE**
- Source: `Songs.is_active` (or equivalent field name)
- Toggle button (not a list filter)
- ON = show only active songs (`is_active = true`)
- OFF = show all songs (including inactive)
- Located between Status and Year categories

**Genre (Tag Category)**
- Source: `Tags` table where `category = 'Genre'`
- Dynamic values based on user's tag data
- Examples: Rock, Pop, Jazz, Country, etc.

#### Post-MVP Filters (Nice-to-Have)

**Album**
- Source: `Albums.album_title`
- Flat list of all albums
- Note: Not much more work to add, include in implementation if time permits

**Publisher**
- Source: `Publishers.publisher_name`
- Flat list of all publishers
- Note: Not much more work to add, include in implementation if time permits

**Other Tag Categories (Dynamic)**
- Source: `Tags` table, all categories except Genre
- Examples: Festival, "DJ Favourites: Bob", "Wedding Songs", etc.
- Each category becomes a separate filter section
- Note: System already handles this dynamically, just needs UI space

**Status (Completeness)**
- Values: Not Done, Ready to Finalize, Missing Data, ~~Done~~ (not implemented yet)
- Based on completeness logic (checks required fields)
- Note: "Done" state logic not yet implemented, filter will show but may not work fully

### Filter Interaction Logic

**Logic Mode Toggle:**
- `[ALL]` button = AND logic (intersection)
  - Example: "Taylor Hawkins" + "1991" = Taylor's songs from 1991
- `[ANY]` button = OR logic (union)
  - Example: "Taylor Hawkins" + "Dave Grohl" = songs with Taylor OR Dave
- Default: ALL (AND mode)
- Persists across searches until manually toggled
- Filter selections remain active when switching modes (re-query with new logic)

**Multi-Selection:**
- Within same category (e.g., Artist): Subject to ALL/ANY logic
  - ALL mode: Songs must have ALL selected artists (rare use case)
  - ANY mode: Songs with ANY selected artist (common use case)
- Across categories (e.g., Artist + Year): Subject to ALL/ANY logic
  - ALL mode: Songs must match Artist AND Year (common use case)
  - ANY mode: Songs match Artist OR Year (rare use case)

**Filter Value Display:**
- MVP: Show all filter values regardless of current results
- Future: Could show counts "(234)" or gray out values with 0 results in current context

### UI Controls

**Top Bar Buttons:**
- `[ALL +]` - Expand all filter category trees
- `[ALL -]` - Collapse all filter category trees
- `[ALL]` / `[ANY]` - Logic mode toggle
  - ALL = AND logic (intersection)
  - ANY = OR logic (union)
- `[ALL (count)]` / `[MUS (count)]` - Media type filters
  - Currently both show same count (only songs in DB)
  - Future: Separate counts for podcasts, audiobooks, etc.

**Filter Category Layout:**
```
[ALL +]  [ALL -]      [ALL]      [ALL (392)]  [MUS (392)]

Album
  ○ Ne skidaj mi pismu s usana
  ○ Pravda za Vedrana

Artist
  ○ Ana Srećković
  ○ Ivana Kindl
  ○ Marija Šapina

All Contributors
  ○ Ana Srećković
  ○ Dana
  ○ Dragana Kajtazović

TOGGLE LIVE

Year
  ○ 2026
  ○ 2025
  ○ 2023
  ○ 2021

Decade
  ○ 2020s
  ○ 2010s
  ○ 1990s

Genre
  ○ Country
  ○ Cro
  ○ Dance
  ○ Instrumental
  ○ Klape
  ○ Latin

Status
  ○ Not Done
  ○ Ready to Finalize
  ○ Missing Data
```

### Integration with Deep Search

**Search Bar Filters the Sidebar (Literal Text Match):**
- Type "ana" in search bar → sidebar shows only filters containing "ana" text from complete filter catalog
- Shows: "Ana Srećković", "Ivana Kindl", "Dana", "Pravda za Vedrana" (album)
- Hides: Year section (no year contains "ana" text)
- Does NOT filter based on current song results - always searches all available filters
- Surface/Deep Search toggle changes which songs match in Deep Search queries, NOT sidebar filtering behavior
- Use case: "I have too many results, let me find a specific filter value to narrow down"

**Filter-First Workflow:**
1. User types in search bar → filters sidebar
2. User clicks filter value → songs update
3. User adds more filters → songs narrow (AND) or expand (OR)
4. Search bar can be cleared with X button while keeping filter selections

### Performance Considerations

**Filter Loading:**
- All filter values loaded on app start or data change
- ~80MB for 100k songs (acceptable for modern browsers)
- Client-side filtering of sidebar is instant (JavaScript array filtering)

**Filter Rebuild Strategy:**
- MVP: Rebuild immediately on every DB write (ingestion, edit, delete)
- Expected rebuild time: <500ms for 100k songs
- Simple, correct, no stale data
- Future optimization: Add caching/dirty flags if rebuild becomes a bottleneck

**Filter Application:**
- Song queries are server-side SQL with WHERE clauses
- Multiple filters = multiple WHERE conditions
- Expected performance: <100ms for most filter combinations on 100k songs

---

## Implementation Notes

### Backend (Filter Application Query)

**Example: Artist filter "Taylor Hawkins" + Year filter "1991" in ALL mode:**
```sql
SELECT DISTINCT s.* FROM Songs s
JOIN SongCredits sc ON s.SourceID = sc.SourceID
JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
JOIN Roles r ON sc.RoleID = r.RoleID
WHERE an.display_name = 'Taylor Hawkins'
  AND r.role_name = 'Performer'
  AND s.year = 1991
  AND s.is_active = 1  -- if TOGGLE LIVE is ON
```

**Example: Artist "Taylor" + Artist "Dave" in ANY mode:**
```sql
SELECT DISTINCT s.* FROM Songs s
JOIN SongCredits sc ON s.SourceID = sc.SourceID
JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
JOIN Roles r ON sc.RoleID = r.RoleID
WHERE (an.display_name = 'Taylor Hawkins' OR an.display_name = 'Dave Grohl')
  AND r.role_name = 'Performer'
  AND s.is_active = 1
```

### Frontend

**Filter State Management:**
- Track active filters: `{ artist: ['Taylor Hawkins'], year: [1991], live: true }`
- Track logic mode: `{ mode: 'ALL' }` or `{ mode: 'ANY' }`
- On filter click: Update state, call API with filter params, re-render songs

**Filter Sidebar Rendering:**
- Pre-load all filter values from API on app start
- Client-side filter values based on search bar text
- Highlight active filters (checked circles)
- Collapse/expand categories based on ALL+/ALL- buttons

**API Integration:**
- Endpoint: `GET /api/v1/songs/filter` (new endpoint)
- Params: `?artist=Taylor+Hawkins&year=1991&mode=ALL&live=true`
- Returns: List of matching songs

---

## Files Modified

**Backend:**
- `src/engine/routers/catalog.py` - Add `/songs/filter` endpoint
- `src/services/catalog_service.py` - Add `filter_songs()` method
- `src/data/song_repository.py` - Add `filter()` with dynamic WHERE building

**Frontend:**
- `src/static/js/dashboard/api.js` - Add filter API call
- `src/static/js/dashboard/main.js` - Filter state management + sidebar rendering
- `src/templates/dashboard.html` - Filter sidebar HTML structure
- `src/static/css/dashboard.css` - Filter sidebar styling

---

## Future Enhancements

1. **Filter Result Counts:** Show "(234)" next to each filter value
2. **Smart Filter Hiding:** Gray out or hide filters with 0 results in current context
3. **Filter Presets:** Save common filter combinations ("My 90s Rock")
4. **Exclusion Filters:** "NOT Rock" to exclude genres
5. **Range Filters:** Year slider (1990-1995), BPM range (120-140)
6. **Multi-Level Tag Hierarchy:** Genre → Rock → Hard Rock (sub-genres)
7. **Recently Used Filters:** Quick access to frequently clicked filters
8. **Filter Search Within Category:** Searchable dropdown for long lists (e.g., 1000+ artists)

---

## Open Questions / TODOs

1. **Field name verification:** Confirm `is_active` is the correct field for TOGGLE LIVE
2. **Status "Done" logic:** Implementation pending, may not work in MVP
3. **Post-MVP filters:** Decide if Album/Publisher/Other Tags should be included in initial release (minimal extra work)
