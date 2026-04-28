# JS Renderers
*Location: `src/static/js/dashboard/renderers/`*

**Responsibility**: HTML construction and UI injection for specific entity types and views.

---

## Shared Entity Rendering
*Location: `src/static/js/dashboard/renderers/entity_renderer.js`*

### renderEntityList(ctx, items, options)
Renders the entity list with common wrapper logic. Handles setState, results summary, list title, actions slot, and empty state.

### renderDetailLoading(ctx, entity, entityType, entityName, subtitle = "")
Renders the skeleton loader/header for an entity detail panel.

### renderDeleteSection(action, entityId, canDelete, reason = "")
Renders a standardized delete button section for the detail panel.

---

## Song Rendering
*Location: `src/static/js/dashboard/renderers/songs.js`*

### renderSongs(songs, selectedId)
Renders the list of song cards. Highlights the selected song.

---

## Song Editor V2
*Location: `src/static/js/dashboard/renderers/song_editor.js`*

High-density metadata editor for single songs or multi-selection.

### renderSongEditorV2(container, song)
Renders the full V2 editor grid for a single song.

### renderSongEditorMultiSelect(container, songs)
Renders a specialized editor view for bulk editing common fields across multiple songs.

### renderSongEditorEmpty(container)
Renders the placeholder view when no song is selected.

### renderActionSidebar(container, song)
Renders the vertical action column (Organization, Cleanup, etc).

### wireScalarInputs(container, song)
Attaches inline-edit triggers to all scalar fields (BPM, Year, ISRC).

### wireAlbumScalarInputs(song, refresh)
Attaches inline-edit triggers to scalar fields on album cards (track number, disc number, etc).

### wireChipInputs(container, song)
Attaches link-modal triggers to all relationship chips (Artists, Albums, Tags).


### wireDriftIndicators(container, song)
Initializes ID3 sync status indicators (LEDs).

---

## Album Rendering
*Location: `src/static/js/dashboard/renderers/albums.js`*

### renderAlbums(albums, selectedId)
Renders the list of album cards.

### renderAlbumDetailComplete(container, album)
Renders the full album profile view including tracks, credits, and links.

### renderAlbumDetailLoading(container)
Renders the skeleton loader for album details.

---

## Artist Rendering
*Location: `src/static/js/dashboard/renderers/artists.js`*

### renderArtists(identities, selectedId)
Renders the artist list cards.

### renderArtistDetailComplete(container, identity)
Renders the artist profile view including aliases, members, and full repertoire.

### renderArtistDetailLoading(container)
Renders the skeleton loader for artist details.

---

## Publisher Rendering
*Location: `src/static/js/dashboard/renderers/publishers.js`*

### renderPublishers(publishers, selectedId)
Renders the list of publisher cards.

### renderPublisherDetailComplete(container, publisher)
Renders the publisher profile view with hierarchy and repertoire listing.

### renderPublisherDetailLoading(container)
Renders the skeleton loader for publisher details.

---

## Tag Rendering
*Location: `src/static/js/dashboard/renderers/tags.js`*

### renderTags(tags, selectedId)
Renders the list of tag cards with category badges.

### renderTagDetailComplete(container, tag)
Renders the detailed tag view with membership listing.

### renderTagDetailLoading(container)
Renders the skeleton loader for tag details.

---

## Ingest Rendering
*Location: `src/static/js/dashboard/renderers/ingestion.js`*

### renderIngestionPanel(container, history)
Renders the file staging workflow (drop-zone, path input, verification results).

### handleIngestDrop(items, allowedExtensions, callbacks)
Orchestrates the drag-and-drop ingestion pipeline.

### collectFilesFromItems(dataTransferItems)
Utility to recursively collect files from a drag-and-drop event.
