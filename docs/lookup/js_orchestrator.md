# JS Orchestrator
*Location: `src/static/js/dashboard/orchestrator.js`*

**Responsibility**: Centralized logic for all modal-based entity interactions. Coordinates between the API, UI state, and specialized modals.

---

## Player Orchestration

### orchestrateScrubber(ctx, songId, songTitle)
Opens the Scrubber modal and handles tag editing callbacks during playback.

---

## Relationship Orchestration (Link Modals)

### manageSongTags(ctx, songId, songTitle, currentTags)
Opens LinkModal for song tag management. Handles search/add/remove with category parsing logic.

### manageSongCredits(ctx, songId, role, currentCredits)
Opens LinkModal for song credits (e.g. Composers, Producers).

### manageSongAlbums(ctx, songId, songTitle, currentAlbums)
Opens LinkModal for linking songs to albums.

### manageSongPublishers(ctx, songId, currentPublishers)
Opens LinkModal for song publisher management.

### manageAlbumPublishers(ctx, albumId, songId, currentChips)
Opens LinkModal for album publisher management.

### manageAlbumCredits(ctx, albumId, songId, currentChips)
Opens LinkModal for album credit management.

---

## Entity Orchestration (Edit Modals)

### manageArtist(ctx, artistId, artistName)
Opens EditModal for Identity management (Roles, Aliases, Members). Handles merging logic on rename.

### managePublisher(ctx, publisherId, publisherName)
Opens EditModal for Publisher management (Hierarchy/Sub-publishers).

### manageTag(ctx, tagId)
Opens EditModal for Tag management (Name/Category).
