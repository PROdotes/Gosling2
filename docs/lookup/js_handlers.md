# JS Handlers
*Location: `src/static/js/dashboard/handlers/`*

**Responsibility**: Specialized handlers that offload user interaction logic from the main search orchestrator.

---

## SongActionsHandler
*Location: `src/static/js/dashboard/handlers/song_actions.js`*

Handles mutations, file operations, and metadata formatting for individual songs or selection stacks.

### handle(event)
The primary entry point for action dispatching based on `data-action`.

### syncAlbumWithSong(albumId, songId)
Syncs BPM, Year, Credits, and Publishers from a song to its parent album.

### updateSyncLed(songId)
Checks ID3 sync status and updates the UI indicator.

### handleDeleteSong(actionTarget)
Handles song deletion.

### handleRejectSong(actionTarget, event)
Handles song rejection.

### handleToggleActive(actionTarget, event)
Toggles song active status.

### handleMarkReviewed(actionTarget)
Sets status to `REVIEWED`.

### handleUnreviewSong(actionTarget)
Sets status to `NEEDS_REVIEW`.

### handleMoveToLibrary(actionTarget)
Triggers organization task.

### handleSyncId3(actionTarget)
Triggers ID3 tag write.

### handleStartEditScalar(actionTarget)
Activates inline scalar editing.

### handleSetPrimaryTag(actionTarget)
Sets a tag as primary.

### handleRemoveTag(actionTarget)
Unlinks a tag.

### handleRemovePublisher(actionTarget)
Unlinks a publisher from a song.

### handleRemoveCredit(actionTarget)
Unlinks a credit.

### handleRemoveAlbum(actionTarget)
Unlinks an album.

### handleOpenScrubber(actionTarget)
Opens the audio playback scrubber.

### handleFormatCase(actionTarget)
Applies title/sentence casing.

### handleWebSearch(actionTarget)
Triggers a web search.

### handleWebSearchSetEngine(actionTarget)
Changes preferred search engine.

### handleConvertWav(actionTarget)
Triggers WAV-to-MP3 conversion.

### handleResolveConflict(actionTarget)
Handles ghost record resolution.

### handleCleanupOriginal(actionTarget)
Deletes source file in staging.

### handleOpenSplitterModal(actionTarget)
Opens name/credit splitter.

### handleOpenFilenameParserSingle(actionTarget)
Opens filename extractor.

### handleStartEditAlbumScalar(actionTarget)
Activates inline editing for album fields.

### handleStartEditAlbumLink(actionTarget)
Activates inline editing for track/disc number.

### handleSyncAlbumFromSong(actionTarget)
Explicit action trigger to sync metadata from a sibling song to the album.

### handleRemoveAlbumCredit(actionTarget)
Unlinks a credit from an album.

### handleRemoveAlbumPublisher(actionTarget)
Unlinks a publisher from an album.

### handleChangeAlbumType(actionTarget)
Updates an album's release type (CD, Vinyl, Digital).

### handleOpenSpotifyModal(actionTarget)
Opens the Spotify credit importer.

### handleQuickCreateAlbum(actionTarget)
Quickly creates an album from a song and links it.

### handleCloseEditModal(actionTarget)
Closes the EditModal.

### handleCloseLinkModal(actionTarget)
Closes the LinkModal.

### handleCloseScrubberModal(actionTarget)
Closes the ScrubberModal.

### handleCloseSpotifyModal(actionTarget)
Closes the SpotifyModal.

### handleCloseSplitterModal(actionTarget)
Closes the SplitterModal.

### handleCloseFilenameParserModal(actionTarget)
Closes the FilenameParserModal.

---

## NavigationHandler
*Location: `src/static/js/dashboard/handlers/navigation.js`*

### handle(event, songActions)
Entry point for global navigation actions.

### handleSwitchMode(actionTarget)
Changes active view.

### handleRefreshResults(actionTarget)
Full cache reset and refresh.

### handleSelectResult(actionTarget, event)
Selection tracking.

### handleNavigateSearch(actionTarget)
Deep search navigation.

### handleOpenEditModal(actionTarget)
Opens entity edit modal.

### handleOpenLinkModal(actionTarget)
Opens relationship link modal.

### setupKeyboardHandler(songActions)
Global hotkeys.

### handleDeleteTag(actionTarget)
Tag deletion.

### handleBulkDeleteUnlinkedTags()
Bulk tag cleanup.

### handleDeleteAlbum(actionTarget)
Album deletion.

### handleBulkDeleteUnlinkedAlbums()
Bulk album cleanup.

### handleDeletePublisher(actionTarget)
Publisher deletion.

### handleBulkDeleteUnlinkedPublishers()
Bulk publisher cleanup.

### handleDeleteIdentity(actionTarget)
Identity deletion.

### handleBulkDeleteUnlinkedIdentities()
Bulk identity cleanup.

---

## FilterSidebarHandler
*Location: `src/static/js/dashboard/handlers/filter_sidebar.js`*

### setupListeners()
Attaches UI listeners.

### load()
Fetches counts and values.

### render()
Sidebar injection.

### show()
Expands sidebar.

### hide()
Collapses sidebar.

### toggle()
Toggles sidebar state.

### toggleValue(section, value, checked)
Updates filter selection.

### applyFilters()
Triggers filtered search.

### reapply()
Re-triggers current filters after mode switch.

### clearAll()
Resets filters.

### hasActiveFilters()
Status check.

### setSearchText(text)
Inline sidebar search for values.

### saveFilterState()
Persistence.

### loadSavedFilterState()
Retrieval.

---

## WebSearchHandler
*Location: `src/static/js/dashboard/handlers/web_search.js`*

### setupListeners()
Attaches interaction listeners.

### handleClick(event)
Handles engine selection.

### showOneTimeEnginePicker(target)
Displays engine selector popup.

### handlePointerDown(event)
Tracking for click-outside detection.

### handlePointerUp(event)
Tracking for click-outside detection.
