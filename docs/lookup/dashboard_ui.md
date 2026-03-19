# Dashboard UI
*Location: `src/static/js/dashboard/`*

**Responsibility**: Frontend logic for the single-page discovery dashboard.

---

## main.js
*Location: `src/static/js/dashboard/main.js`*
**Responsibility**: Entry point, global state management, mode switching, and keyboard navigation.

### init()
Bootstraps the dashboard, sets up event listeners, and triggers the initial search.

### switchMode(mode)
Changes the active entity mode (songs, albums, artists, publishers) and resets UI state.

---

## api.js
*Location: `src/static/js/dashboard/api.js`*
**Responsibility**: Centralized data fetching with AbortController support to prevent race conditions.

### searchSongs(query)
Fetches songs matching query. Returns `List[SongView]`.

### searchAlbums(query)
Fetches albums matching query. Returns `List[AlbumView]`.

---

## Renderers
*Location: `src/static/js/dashboard/renderers/`*
**Responsibility**: HTML construction for specific entities.

### songs.js
Renders song list entries and the detailed comparison view (DB vs physical file).

### albums.js
Renders album cards and collection track lists.

### artists.js
Renders artist profiles, aliases, and group memberships.

### publishers.js
Renders publisher details and repertoire listings.
