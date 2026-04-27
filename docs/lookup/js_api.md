# JS API
*Location: `src/static/js/dashboard/api.js`*

**Responsibility**: Centralized data fetching with AbortController support and standardized error handling.

---

## Configuration & Core

### fetchValidationRules()
Fetches server-side validation rules for tags, BPM, and other metadata.

### fetchAppConfig()
Fetches general application configuration.

### abortAllSearches()
Aborts all ongoing search requests (songs, albums, artists, etc).

---

## Entity Search

### searchSongs(query, deep)
Fetches songs matching query. Supports `deep=true` for extensive discovery.

### searchAlbums(query)
Fetches albums matching query.

### searchArtists(query)
Fetches identities matching query.

### searchPublishers(query)
Fetches publishers matching query.

### searchTags(query)
Fetches tags matching query.

---

## Entity Details

### getCatalogSong(id, options)
Fetches basic catalog song data.

### getSongDetail(id, options)
Fetches high-fidelity metadata from InspectService (includes physical file info).

### getSongWebSearch(id, engine)
Triggers a web search for song metadata.

### getAlbumDetail(id, options)
Fetches album details and track list.

### getArtistTree(id, options)
Fetches identity details including aliases and members.

### getArtistSongs(id, options)
Fetches all songs associated with an identity.

### getPublisherDetail(id, options)
Fetches publisher details.

### getPublisherSongs(id, options)
Fetches all songs associated with a publisher.

### getTagDetail(id, options)
Fetches tag details.

### getTagSongs(id, options)
Fetches all songs associated with a tag.

### getTagCategories()
Fetches list of unique tag categories.

### getAuditHistory(table, id, options)
Fetches audit trail for a specific record.

---

## Mutations (Songs)

### patchSongScalars(songId, fields)
Updates scalar fields (BPM, Year, ISRC, etc).

### deleteSong(id)
Soft-deletes a song.

### moveSongToLibrary(id)
Moves song from staging to organized library.

### syncSongId3(id)
Triggers ID3 tag sync from DB to physical file.

### getSongSyncStatus(id)
Checks if DB metadata matches physical file tags.

---

## Mutations (Identities)

### addIdentityAlias(identityId, displayName, nameId)
Adds a new display name to an identity.

### removeIdentityAlias(identityId, nameId)
Removes an alias.

### updateIdentityLegalName(identityId, legalName)
Updates the legal name of an identity.

### setIdentityType(identityId, type)
Sets identity type (person/group).

### addIdentityMember(groupId, memberId)
Adds a member to a group.

### removeIdentityMember(groupId, memberId)
Removes a member from a group.

### mergeIdentity(sourceNameId, targetNameId)
Merges one identity into another.

---

## Mutations (Publishers)

### updatePublisher(publisherId, name)
Renames a publisher.

### setPublisherParent(publisherId, parentId)
Sets/updates the parent publisher (hierarchy).

### deletePublisher(publisherId)
Deletes a publisher.

### bulkDeleteUnlinkedPublishers()
Deletes all publishers with no associated songs or albums.

---

## Mutations (Tags)

### updateTag(tagId, name, category)
Updates tag name or category.

### deleteTag(tagId)
Deletes a tag.

### bulkDeleteUnlinkedTags()
Deletes all tags with no associated songs.

---

## Mutations (Albums)

### updateAlbum(albumId, fields)
Updates album metadata (Title, Year, etc).

### deleteAlbum(albumId)
Deletes an album.

### bulkDeleteUnlinkedAlbums()
Deletes all albums with no associated songs.

### quickCreateAlbum(songId, title = null)
Quick-create an album from a song. Creates album with song's media_name, defaults disc=1, track=1, then syncs metadata atomically.

### syncAlbumFromSong(albumId, songId)
Triggers a metadata sync from a song to its parent album.

---

## Relationship Management (Links)

### addSongPublisher(songId, publisherName, publisherId)
Links a publisher to a song.

### removeSongPublisher(songId, publisherId)
Unlinks a publisher from a song.

### addSongCredit(songId, displayName, roleName, identityId)
Adds a credit (Artist/Role) to a song.

### removeSongCredit(songId, creditId)
Removes a song credit.

### updateCreditName(songId, nameId, displayName)
Updates the display name on a credit.

### addSongTag(songId, tagName, category, tagId)
Links a tag to a song.

### removeSongTag(songId, tagId)
Unlinks a tag from a song.

### setPrimarySongTag(songId, tagId)
Sets a tag as the primary (Main Genre/Language) for a song.

### addSongAlbum(songId, albumId, title, trackNumber, discNumber)
Links a song to an album.

### removeSongAlbum(songId, albumId)
Unlinks a song from an album.

### updateSongAlbumLink(songId, albumId, trackNumber, discNumber)
Updates track/disc position on an album link.

### addAlbumCredit(albumId, displayName, roleName, identityId)
Adds a credit to an album.

### removeAlbumCredit(albumId, nameId)
Removes an album credit.

### addAlbumPublisher(albumId, publisherName, publisherId)
Links a publisher to an album.

### removeAlbumPublisher(albumId, publisherId)
Unlinks a publisher from an album.

---

## Ingest & Tools

### uploadFiles(files)
Uploads multiple files to the staging area.

### checkIngestion(filePath)
Dry-run check for existing files or ghost records.

### getIngestStatus()
Fetches current status of the ingestion/conversion queue.

### resetIngestStatus()
Clears the ingestion status.

### resolveConflict(ghostId, stagedPath)
Resolves a file conflict by re-activating a ghost record.

### scanFolder(folderPath, recursive)
Scans a server-side folder for files to stage.

### getDownloadsFolder()
Fetches the default downloads path from server config.

### getAcceptedFormats()
Fetches list of supported file extensions.

### getPendingConvert()
Fetches list of files waiting for WAV-to-MP3 conversion.

### getStagingOrphans()
Fetches files in staging that are not in the DB.

### deleteStagingOrphan(filePath)
Deletes an orphan file from staging.

### cleanupOriginalFile(filePath)
Deletes the original source file after successful processing.

### formatMetadataCase(entityType, entityId, field, formatType)
Applies title/sentence casing to a metadata field.

### readNdjsonStream(response, onUpdate)
Helper to parse streaming NDJSON responses.

### parseSpotifyCredits(rawText, referenceTitle)
Parses raw Spotify credit text into structured data.

### importSpotifyCredits(songId, credits, publishers)
Imports parsed Spotify credits to a song.

### splitterTokenize(text, separators)
Tokenizes a string (e.g. filename) for the Splitter tool.

### splitterPreview(names, target)
Previews a name split operation.

### splitterConfirm(songId, tokens, target, classification, remove)
Executes a name split operation.

### previewFilenameParsing(filenames, pattern)
Previews metadata extraction from filenames.

### applyFilenameParsing(items, pattern)
Applies metadata extraction from filenames.

---

## Entity Details (Roles & Frames)

### fetchRoles()
Fetches list of available credit roles (Performer, Composer, etc).

### fetchId3Frames()
Fetches list of supported ID3 frames for metadata mapping.

### isAbortError(error)
Helper to check if an error is a fetch AbortError.

---

## Filtering

### getFilterValues()
Fetches all unique values for sidebar filters (Genres, Years, etc).

### filterSongs(filters, mode, liveOnly)
Fetches songs matching multiple filter criteria.

---

## Mutations (Additional)

### deleteIdentity(identityId)
Deletes an identity record.

### bulkDeleteUnlinkedIdentities()
Deletes all identities with no associated songs, albums, or roles.
