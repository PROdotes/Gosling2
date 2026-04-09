# Engine Routers
*Location: `src/engine/routers/`*

**Responsibility**: HTTP interface and input validation for the API.

---

## Catalog Router
*Location: `src/engine/routers/catalog.py`*
**Responsibility**: HTTP interface for song and artist metadata.

### async def get_song(song_id: int) -> SongView
**HTTP**: `GET /api/v1/songs/{song_id}`
Fetches a single Song domain model by its unique ID with full hydration.
- Raises `HTTPException(404)` if the song does not exist.
- Wraps `CatalogService.get_song`.

### async def search_songs(q: Optional[str] = None, query: Optional[str] = None, deep: bool = False) -> List[SongSlimView]
**HTTP**: `GET /api/v1/songs/search?q={query}&query={alt_query}&deep={true|false}`
- Surface slim search by default (`deep=false`). Full resolution when `deep=true`.
- Accepts both `q` and `query` params (q takes precedence).
- Wraps `CatalogService.search_songs_slim` or `search_songs_deep_slim`.
- Returns a JSON list of `SongSlimView` models.
- **Instrumentation**: Traces query and result count.

### async def get_identity(identity_id: int) -> IdentityView
**HTTP**: `GET /api/v1/identities/{identity_id}`
- Fetches a full identity tree by ID.
- Raises `HTTPException(404)` if not found.
- Wraps `CatalogService.get_identity`.
- Maps to `IdentityView` for recursive tree serialization.

### async def get_all_identities() -> List[IdentityView]
**HTTP**: `GET /api/v1/identities`
- Fetches the directory of active identities.
- Wraps `CatalogService.get_all_identities`.

### async def search_identities(q: str) -> List[IdentityView]
**HTTP**: `GET /api/v1/identities/search?q={query}`
- Searches identities by name or alias.
- Wraps `CatalogService.search_identities`.

### async def get_songs_by_identity(identity_id: int) -> List[SongView]
**HTTP**: `GET /api/v1/identities/{identity_id}/songs`
- Fetches all songs credited to this identity or its group/members.
- Raises `HTTPException(404)` if the identity is not found.
- Wraps `CatalogService.get_songs_by_identity`.

### async def get_all_publishers() -> List[Publisher]
**HTTP**: `GET /api/v1/publishers`
- Fetches the directory of all active music publishers.
- Wraps `CatalogService.get_all_publishers`.
- Returns `List[PublisherView]`.

### async def get_all_albums() -> List[AlbumSlimView]
**HTTP**: `GET /api/v1/albums`
- Fetches the directory of all albums.
- Wraps `CatalogService.get_all_albums`.
- Maps to `AlbumSlimView` for dashboard rendering.

### async def search_publishers(q: str) -> List[Publisher]
**HTTP**: `GET /api/v1/publishers/search?q={query}`
- Searches publishers by name.
- Wraps `CatalogService.search_publishers`.

### async def search_albums(q: str) -> List[AlbumSlimView]
**HTTP**: `GET /api/v1/albums/search?q={query}`
- Searches albums by title.
- Wraps `CatalogService.search_albums_slim`.
- Returns `AlbumSlimView` for dashboard rendering.

### async def get_publisher(publisher_id: int) -> Publisher
**HTTP**: `GET /api/v1/publishers/{publisher_id}`
- Fetches a single publisher by ID.
- Raises `HTTPException(404)` if not found.
- Wraps `CatalogService.get_publisher`.

### async def get_album(album_id: int) -> AlbumView
**HTTP**: `GET /api/v1/albums/{album_id}`
- Fetches a single album by ID.
- Raises `HTTPException(404)` if not found.
- Wraps `CatalogService.get_album`.
- Maps to `AlbumView` for dashboard rendering.

### async def get_songs_by_publisher(publisher_id: int) -> List[SongView]
**HTTP**: `GET /api/v1/publishers/{publisher_id}/songs`
- Fetches the full repertoire (Master rights) for a given publisher.
- Wraps `CatalogService.get_songs_by_publisher`.

### async def get_all_tags() -> List[Tag]
**HTTP**: `GET /api/v1/tags`
- Directory of all active metadata markers.
- Wraps `CatalogService.get_all_tags`.

### async def search_tags(q: str) -> List[Tag]
**HTTP**: `GET /api/v1/tags/search?q={query}`
- Searches tags by name match.
- Wraps `CatalogService.search_tags`.

### async def get_tag(tag_id: int) -> Tag
**HTTP**: `GET /api/v1/tags/{tag_id}`
- Fetches a single tag by ID.
- Wraps `CatalogService.get_tag`.

### async def get_songs_by_tag(tag_id: int) -> List[SongView]
**HTTP**: `GET /api/v1/tags/{tag_id}/songs`
- Fetches the full hydrated song repertoire linked to this tag.
- Wraps `CatalogService.get_songs_by_tag`.
- Returns `List[SongView]`.

### async def get_song_web_search(song_id: int, engine: Optional[str] = None, service: CatalogService = Depends(_get_service)) -> dict
**HTTP**: `GET /api/v1/songs/{song_id}/web-search`
- Generates an external search URL for a song.
- Returns `{"url": "... "}`.
- Wraps `SearchService.get_search_url`.

### async def add_identity_alias(identity_id: int, body: AddAliasBody) -> dict
**HTTP**: `POST /api/v1/identities/{identity_id}/aliases`
- Add or re-link an alias name to an identity.
- Wraps `CatalogService.add_identity_alias`.

### async def remove_identity_alias(identity_id: int, name_id: int) -> None
**HTTP**: `DELETE /api/v1/identities/{identity_id}/aliases/{name_id}`
- Remove an alias from an identity.
- Wraps `CatalogService.remove_identity_alias`.

### async def get_tag_categories() -> List[str]
**HTTP**: `GET /api/v1/tags/categories`
- Returns all distinct tag categories from the database.
- Wraps `CatalogService.get_tag_categories`.

### async def check_ingestion(request: IngestionCheckRequest) -> IngestionReportView
**HTTP**: `POST /api/v1/catalog/ingest/check`
- Performs a dry-run ingestion collision check.
- Returns status (NEW, ALREADY_EXISTS, ERROR) and match details.
- Wraps `CatalogService.check_ingestion`.

### AddAliasBody
`{ display_name: str, name_id: int|null }`
Used by `add_identity_alias`.

### UpdateLegalNameBody
`{ legal_name: str|null }`
Used by `update_identity_legal_name`.

### async def update_identity_legal_name(identity_id: int, body: UpdateLegalNameBody) -> None
**HTTP**: `PATCH /api/v1/identities/{identity_id}/legal-name`
- Update the LegalName on an Identity globally.
- Wraps `CatalogService.update_identity_legal_name`.

### def get_validation_rules() -> Dict[str, Any]
**HTTP**: `GET /api/v1/validation-rules`
- Returns scalar field validation rules and global metadata defaults (e.g., tag categories/delimiters) for frontend use.

### def get_config() -> Dict[str, Any]
**HTTP**: `GET /api/v1/config`
- Returns application configuration settings.
- Returns `search_engines` dictionary and `default_search_engine`.

---


## Ingest Router
*Location: `src/engine/routers/ingest.py`*
**Responsibility**: Dedicated endpoints for binary file handling and session state.

### def _get_service() -> CatalogService
**Internal**: Service factory for the ingestion router.

### async def get_downloads_folder_json() -> JSONResponse
**HTTP**: `GET /api/v1/ingest/downloads-folder`
- Returns the platform-specific default downloads folder.

### async def get_accepted_formats() -> JSONResponse
**HTTP**: `GET /api/v1/ingest/formats`
- Returns the list of supported file extensions for ingestion as defined in `ACCEPTED_EXTENSIONS`.

### async def get_staging_orphans() -> JSONResponse
**HTTP**: `GET /api/v1/ingest/staging-orphans`
- List files in the staging folder that have no matching DB record.
- Returns list of objects with `filename`, `path`, and `size_bytes`.

### async def delete_staging_orphan(path: str) -> dict
**HTTP**: `DELETE /api/v1/ingest/staging-orphans`
- Delete a specific file from staging, only if it has no DB record.
- Safety: Path must be within `STAGING_DIR`.
- Returns `{"status": "DELETED", "path": path}`.

### async def upload_files(files: list[UploadFile] = File(...)) -> BatchIngestReport
**HTTP**: `POST /api/v1/ingest/upload`
- Batch file ingestion entry point (supports single or multiple files).
- Browser automatically flattens folder drag-and-drop into file list.
- Validates extensions and stages all files to `STAGING_DIR` with UUID filenames.
- Orchestrates batch ingestion via `CatalogService.ingest_batch()`.
- Returns `BatchIngestReport` with aggregate stats and per-file results.

### async def scan_folder(request: FolderScanRequest) -> BatchIngestReport
**HTTP**: `POST /api/v1/ingest/scan-folder`
- Server-side folder scanning and ingestion.
- Scans local filesystem path for audio files (recursive or flat).
- Copies files to staging and ingests via `CatalogService.ingest_batch()`.
- Returns `BatchIngestReport` with aggregate stats and per-file results.
- Example payload: `{"folder_path": "Z:\\Songs\\NewAlbum", "recursive": true}`

### async def delete_song(song_id: int) -> Dict[str, Any]
**HTTP**: `DELETE /api/v1/ingest/songs/{song_id}`
- Atomic hard-delete of a song by ID.
- Triggers DB cascade and physical cleanup if in staging.
- Returns `{"status": "DELETED", "id": song_id}`.

### async def resolve_conflict(ghost_id: int, staged_path: str) -> IngestionReportView
**HTTP**: `POST /api/v1/ingest/resolve-conflict?ghost_id={id}&staged_path={path}`
- Resolves a ghost record conflict by reactivating a soft-deleted record with new metadata from a staged file.
- Wraps `CatalogService.resolve_conflict`.

### async def convert_wav(staged_path: str) -> dict
**HTTP**: `POST /api/v1/ingest/convert-wav?staged_path={path}`
- Converts a staged WAV to MP3 and ingests.
- Wraps `CatalogService.ingest_file` after conversion.

### async def cleanup_original_file(request: CleanupOriginalRequest) -> dict
**HTTP**: `POST /api/v1/ingest/cleanup-original`
- Physically deletes the original source file (e.g. from Downloads).
- Payload: `{"file_path": "... "}`.
- Securely restricts deletions to the Downloads folder.

---

## Metabolic Router
*Location: `src/engine/routers/metabolic.py`*
**Responsibility**: File-system inspection and comparison logic.

### def _get_catalog_service() -> CatalogService
**Internal**: Factory for the router.

### async def inspect_file(song_id: int) -> SongView
**HTTP**: `GET /api/v1/metabolic/inspect-file/{song_id}`
- Reads physical file metadata via `MetadataService`.
- Parses into domain model via `MetadataParser`.
- Returns a `SongView` for UI comparison.

### async def get_id3_frames() -> Dict[str, Any]
**HTTP**: `GET /api/v1/metabolic/id3-frames`
- Returns the full ID3 frame mapping configuration.
- Unified source of truth for icons and categories.

---

## Audit Router
*Location: `src/engine/routers/audit.py`*
**Responsibility**: HTTP interface for unified history logs.

### def _get_service() -> AuditService
**Internal**: Centralized service factory for the router.

### async def get_history(table: str, record_id: int) -> List[Dict[str, Any]]
**HTTP**: `GET /api/v1/audit/history/{table}/{record_id}`
- Fetches the complete unified audit timeline for a record.
- Matches `ActionLog`, `ChangeLog`, and `DeletedRecords` snapshots.

---


## Song Updates Router
*Location: `src/engine/routers/song_updates.py`*
**Responsibility**: HTTP interface for partial metadata updates and relationship management.

### async def update_song_scalars(song_id: int, body: SongScalarUpdate, service: CatalogService = Depends(_get_service))
**HTTP**: `PATCH /api/v1/songs/{song_id}`
- Partially updates core metadata (media_name, year, bpm, isrc, notes).
- Raises `HTTPException(404)` if the song does not exist.
- Wraps `CatalogService.update_song_scalars`.

### async def get_all_roles(service: CatalogService = Depends(_get_service)) -> List[str]
**HTTP**: `GET /api/v1/roles`
- Returns all distinct artist credit roles from the database.
- Wraps `CatalogService.get_all_roles`.

### async def add_song_credit(song_id: int, body: AddCreditBody, service: CatalogService = Depends(_get_service)) -> SongCredit
**HTTP**: `POST /api/v1/songs/{song_id}/credits`
- Adds a credited artist with a specific role.
- Get-or-creates `ArtistNames` and `Roles` globally.
- Wraps `CatalogService.add_song_credit`.

### async def remove_song_credit(song_id: int, credit_id: int, service: CatalogService = Depends(_get_service))
**HTTP**: `DELETE /api/v1/songs/{song_id}/credits/{credit_id}`
- Removes the specific `SongCredits` link.
- Wraps `CatalogService.remove_song_credit`.

### async def update_credit_name(song_id: int, name_id: int, body: UpdateCreditNameBody, service: CatalogService = Depends(_get_service))
**HTTP**: `PATCH /api/v1/songs/{song_id}/credits/{name_id}`
- Updates an `ArtistNames` record display name globally across all songs.
- Wraps `CatalogService.update_credit_name`.

### async def add_song_album(song_id: int, body: AddAlbumBody, service: CatalogService = Depends(_get_service)) -> SongAlbum
**HTTP**: `POST /api/v1/songs/{song_id}/albums`
- Links a song to an existing album or creates a new album record and links it.
- Resolves `album_id` vs `title` logic.
- Wraps `CatalogService.add_song_album` and `CatalogService.create_and_link_album`.

### async def remove_song_album(song_id: int, album_id: int, service: CatalogService = Depends(_get_service))
**HTTP**: `DELETE /api/v1/songs/{song_id}/albums/{album_id}`
- Unlinks a song from an album.
- Wraps `CatalogService.remove_song_album`.

### async def update_song_album_link(song_id: int, album_id: int, body: UpdateAlbumLinkBody, service: CatalogService = Depends(_get_service))
**HTTP**: `PATCH /api/v1/songs/{song_id}/albums/{album_id}`
- Updates the track/disc metadata for a specific song-album link.
- Wraps `CatalogService.update_song_album_link`.

### async def update_album(album_id: int, body: UpdateAlbumBody, service: CatalogService = Depends(_get_service)) -> Album
**HTTP**: `PATCH /api/v1/albums/{album_id}`
- Updates an `Albums` record metadata globally.
- Wraps `CatalogService.update_album`.

### async def add_album_credit(album_id: int, body: AddAlbumCreditBody, service: CatalogService = Depends(_get_service))
**HTTP**: `POST /api/v1/albums/{album_id}/credits`
- Adds a credited artist to an album.
- Wraps `CatalogService.add_album_credit`.

### async def remove_album_credit(album_id: int, name_id: int, service: CatalogService = Depends(_get_service))
**HTTP**: `DELETE /api/v1/albums/{album_id}/credits/{name_id}`
- Removes a credited artist from an album.
- Wraps `CatalogService.remove_album_credit`.

### async def add_album_publisher(album_id: int, body: AddAlbumPublisherBody, service: CatalogService = Depends(_get_service))
**HTTP**: `POST /api/v1/albums/{album_id}/publishers`
- Adds a publisher to an album record. Get-or-creates by name or links by ID.
- Wraps `CatalogService.add_album_publisher`.

### async def remove_album_publisher(album_id: int, publisher_id: int, service: CatalogService = Depends(_get_service))
**HTTP**: `DELETE /api/v1/albums/{album_id}/publishers/{publisher_id}`
- Removes a publisher from an album.
- Wraps `CatalogService.remove_album_publisher`.

### async def add_song_tag(song_id: int, body: AddTagBody, service: CatalogService = Depends(_get_service)) -> Tag
**HTTP**: `POST /api/v1/songs/{song_id}/tags`
- Adds a tag to a song. Get-or-creates the tag record.
- Wraps `CatalogService.add_song_tag`.

### async def remove_song_tag(song_id: int, tag_id: int, service: CatalogService = Depends(_get_service))
**HTTP**: `DELETE /api/v1/songs/{song_id}/tags/{tag_id}`
- Removes a tag-song link.
- Wraps `CatalogService.remove_song_tag`.

### async def update_tag(tag_id: int, body: UpdateTagBody, service: CatalogService = Depends(_get_service))
**HTTP**: `PATCH /api/v1/tags/{tag_id}`
- Updates a tag name and category globally.
- Wraps `CatalogService.update_tag`.

### async def set_primary_song_tag(song_id: int, tag_id: int, service: CatalogService = Depends(_get_service)) -> Tag
**HTTP**: `PATCH /api/v1/songs/{song_id}/tags/{tag_id}/primary`
- Promote a specific genre tag to primary status for a song. 
- Atomic reset of all other genre links.
- Wraps `CatalogService.set_primary_song_tag`.

### async def add_song_publisher(song_id: int, body: AddPublisherBody, service: CatalogService = Depends(_get_service)) -> Publisher
**HTTP**: `POST /api/v1/songs/{song_id}/publishers`
- Links a publisher to a song. Get-or-creates the publisher record.
- Wraps `CatalogService.add_song_publisher`.

### async def remove_song_publisher(song_id: int, publisher_id: int, service: CatalogService = Depends(_get_service))
**HTTP**: `DELETE /api/v1/songs/{song_id}/publishers/{publisher_id}`
- Removes a publisher-song link.
- Wraps `CatalogService.remove_song_publisher`.

### async def update_publisher(publisher_id: int, body: UpdatePublisherBody, service: CatalogService = Depends(_get_service))
**HTTP**: `PATCH /api/v1/publishers/{publisher_id}`
- Updates a publisher name globally across all songs.
- Wraps `CatalogService.update_publisher`.

### async def set_publisher_parent(publisher_id: int, body: SetPublisherParentBody, service: CatalogService = Depends(_get_service))
**HTTP**: `PATCH /api/v1/publishers/{publisher_id}/parent`
- Sets or clears the parent of a publisher. Pass `{"parent_id": null}` to clear.
- Returns 404 if publisher or parent not found.
- Wraps `CatalogService.set_publisher_parent`.

### async def get_sync_status(song_id: int, service: CatalogService = Depends(_get_service))
**HTTP**: `GET /api/v1/songs/{song_id}/sync-status`
- Compares DB state against physical ID3 tags.
- Returns `{"in_sync": bool, "mismatches": [field_name, ...]}`.
- Returns `{"in_sync": false, "mismatches": ["file_not_found"]}` if file is missing.
- Wraps `MetadataService.compare_songs` and `MetadataService.filter_sync_mismatches`.

### async def sync_id3(song_id: int, service: CatalogService = Depends(_get_service))
**HTTP**: `GET /api/v1/songs/{song_id}/sync-id3`
- Writes current DB state to the physical ID3 tags of the song file.
- Returns `{"status": "ok", "song_id": song_id}` on success.
- Raises `HTTPException(400)` if file not found, `HTTPException(500)` on write failure.
- Wraps `CatalogService._metadata_writer.write_metadata`.

### async def move_song_to_library(song_id: int, service: CatalogService = Depends(_get_service)) -> str
**HTTP**: `POST /api/v1/songs/{song_id}/move`
- Moves a 'Reviewed' song from staging to the organized library.
- Wraps `CatalogService.move_song_to_library`.

### async def format_metadata_case(entity_type: str, entity_id: int, field: str, format_type: str, service: CatalogService = Depends(_get_service)) -> Any
**HTTP**: `PATCH /api/v1/formatting/case?entity_type={type}&entity_id={id}&field={field}&format_type={type}`
- Action endpoint to manually fix casing of a song or album field.
- Returns the updated hydrated entity (SongView or AlbumView).
- Wraps `CatalogService.format_entity_field`.

---

## Audio Router
*Location: `src/engine/routers/audio.py`*

### async def stream_song_audio(song_id: int)
**HTTP**: `GET /api/v1/songs/{song_id}/audio`
- Streams the audio file content for a song.
- Returns a standard `FileResponse` with guessed mimetype.

---

## Tools Router
*Location: `src/engine/routers/tools.py`*
**Responsibility**: Consolidated stateless utility endpoints (Parsing, Splitting, Tokenization).

### FilenamePreviewRequest
`{ filenames: List[str], pattern: str }`

### FilenameApplyItem
`{ song_id: int, filename: str }`

### FilenameApplyRequest
`{ items: List[FilenameApplyItem], pattern: str }`

### TokenizeRequest
`{ text: str, separators: List[str] }`

### PreviewRequest
`{ names: List[str], target: "credits"|"publishers" }`

### RemoveRef
`{ type: "credit"|"publisher", id: int }`

### ConfirmRequest
`{ song_id: int, tokens: List[dict], target: "credits"|"publishers", classification: str|null, remove: RemoveRef }`

### filename_parser_preview(body: FilenamePreviewRequest) -> dict
**HTTP**: `POST /api/v1/tools/filename-parser/preview`
- Takes a list of filenames and a pattern.
- Returns a list of parsed metadata results for as-you-type previews.
- Wraps `src/services/filename_parser.py`.

### filename_parser_apply(body: FilenameApplyRequest) -> dict
**HTTP**: `POST /api/v1/tools/filename-parser/apply`
- Parses each filename and applies extracted metadata to the DB.
- Handles: Title, Year, BPM, ISRC (scalars), Artist (Performer credit), Genre (tag), Publisher.

### tokenize(body: TokenizeRequest) -> List[dict]
**HTTP**: `POST /api/v1/tools/splitter/tokenize`
- Splits a raw credit string into alternating name/sep tokens.
- Wraps `tokenize_credits` from `src/services/tokenizer.py`.

### preview(body: PreviewRequest) -> List[dict]
**HTTP**: `POST /api/v1/tools/splitter/preview`
- For each name, checks whether it already exists in the DB (exact match).
- `target="credits"` checks ArtistNames; `target="publishers"` checks Publishers.
- Returns `[{ name, exists: bool }, ...]` in input order.
- Wraps `CatalogService.resolve_identity_by_name` / `CatalogService.publisher_exists`.

### confirm(body: ConfirmRequest) -> dict
**HTTP**: `POST /api/v1/tools/splitter/confirm`
- Resolves token list into names via `resolve_names`, then adds each as a credit or publisher and removes the original.
- Wraps `CatalogService.add_song_credit` / `add_song_publisher` / `remove_song_credit` / `remove_song_publisher`.

---

## Spotify Router
*Location: `src/engine/routers/spotify.py`*
**Responsibility**: Stateless text parsing and atomic bulk credits ingestion.

### async def parse_credits(request: SpotifyParseRequest) -> SpotifyParseResult
**HTTP**: `POST /api/v1/spotify/parse`
- Performs stateless regex-based parsing of raw Spotify credits text.
- Validates the parsed title against the provided reference title.
- Wraps `SpotifyService.parse_credits`.

### async def import_credits(request: SpotifyImportRequest) -> None
**HTTP**: `POST /api/v1/spotify/import`
- Atomically imports a batch of credits and publishers for a song.
- Performs a single transaction write; rolls back on any partial failure.
- Wraps `CatalogService.import_credits_bulk`.
