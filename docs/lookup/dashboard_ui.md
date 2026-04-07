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

### searchSongs(query, deep)
Fetches songs matching query. Supports `deep=true` for discovery expansion. Returns `List[SongSlimView]`.

### searchAlbums(query)
Fetches albums matching query. Returns `List[AlbumSlimView]`.

### searchArtists(query)
Fetches identities matching query. Returns `List[IdentityView]`.

### searchPublishers(query)
Fetches publishers matching query. Returns `List[PublisherView]`.

### searchTags(query)
Fetches tags matching query. Returns `List[TagView]`.

### getSongDetail(id)
Fetches high-fidelity metadata from `InspectService`. Returns `SongView`.

### patchSongScalars(id, fields)
PATCHs scalar updates (BPM, Year, ISRC, etc.).

### moveSongToLibrary(id)
Trigger orchestrator to move song from staging to organized library. Returns new relative path.

### deleteSong(id)
DELETEs a song by ID. Returns `{"status": "DELETED"}`.

### Ingestion Wrappers
- `uploadFiles(files)`: POSTs multiple files to staging.
- `checkIngestion(filePath)`: Dry-run collision check.
- `resolveConflict(ghostId, stagedPath)`: Reactivate ghost record.
- `scanFolder(path, recursive)`: Server-side staging directory scan.
- `convertAndIngest(stagedPaths)`: WAV to MP3 conversion task.

### Metabolic Wrappers (Link/Unlink)
- `addSongCredit(songId, ...)` / `removeSongCredit`
- `addSongTag(songId, ...)` / `removeSongTag`
- `addSongPublisher(songId, ...)` / `removeSongPublisher`
- `addSongAlbum(songId, ...)` / `removeSongAlbum` / `updateSongAlbumLink`
- `addIdentityAlias(identityId, ...)` / `removeIdentityAlias`
- `updateAlbum(albumId, ...)` / `addAlbumCredit` / `addAlbumPublisher`

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

### tags.js
Renders tag management cards with category badges and song counts.

### ingestion.js
Renders the file verification panel with drag-and-drop support, path input, and result cards.

---

## Components
*Location: `src/static/js/dashboard/components/`*

### utils.js
**Responsibility**: Shared UI components and formatting helpers.
- `renderSongList(songs, emptyMessage)`: Universal stack-list.
- `renderAuditTimeline(history)`: Vertical audit trail.

### edit_modal.js
**Responsibility**: Multi-purpose modal for editing entity names, categories, and hierarchical children (aliases).

### scrubber_modal.js
**Responsibility**: Audio playback modal with waveform scrubbing, volume control, and basic transport (play/pause, seek).

### link_modal.js
**Responsibility**: Universal modal for adding/removing metabolic links. Handles search, result selection, and multi-value submission.

### splitter.js
**Responsibility**: Interactive string tokenizer UI. Used to clean up "Artist, The - Title feat. Guest" mess into structured credits.
