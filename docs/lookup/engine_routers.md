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

### async def get_songs_by_identity(identity_id: int) -> List[SongSlimView]
**HTTP**: `GET /api/v1/identities/{identity_id}/songs`
- Fetches slim song list for this identity or its group/members.
- Raises `HTTPException(404)` if the identity is not found.
- Wraps `CatalogService.get_songs_slim_by_identity`.

### async def get_filter_values() -> dict
**HTTP**: `GET /api/v1/songs/filter-values`
- Returns all distinct values for each filter category (artists, years, decades, genres, albums, publishers, tags, statuses).
- Used to populate the filter sidebar on load.
- Wraps `CatalogService.get_filter_values`.

### async def filter_songs() -> List[SongSlimView]
**HTTP**: `GET /api/v1/songs/filter?artists=...&years=...&genres=...&mode=ALL`
- Filters songs by sidebar criteria. Accepts repeated query params for each category.
- `mode=ALL` (default) = AND logic; `mode=ANY` = OR logic.
- `statuses` accepts: `not_done`, `ready_to_finalize`, `missing_data`, `done`.
- Returns `List[SongSlimView]`.
- Wraps `CatalogService.filter_songs_slim`.

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

### async def get_songs_by_publisher(publisher_id: int) -> List[SongSlimView]
**HTTP**: `GET /api/v1/publishers/{publisher_id}/songs`
- Fetches slim song repertoire for a given publisher.
- Wraps `CatalogService.get_songs_slim_by_publisher`.

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

### async def get_songs_by_tag(tag_id: int) -> List[SongSlimView]
**HTTP**: `GET /api/v1/tags/{tag_id}/songs`
- Fetches slim song list linked to this tag.
- Wraps `CatalogService.get_songs_slim_by_tag`.

### async def delete_tag(tag_id: int) -> None
**HTTP**: `DELETE /api/v1/tags/{tag_id}`
- Soft-delete a single tag. 404 if not found, 403 if linked to active songs.
- Wraps `CatalogService.get_tag` + `CatalogService.delete_unlinked_tags`.

### async def bulk_delete_unlinked_tags(unlinked: bool = False) -> dict
**HTTP**: `DELETE /api/v1/tags?unlinked=true`
- Soft-delete all unlinked tags in one transaction. Requires `?unlinked=true` as a safety flag (400 without it).
- Returns `{"deleted": N}`.
- Wraps `CatalogService.get_all_tags` + `CatalogService.delete_unlinked_tags`.

### async def delete_identity(identity_id: int) -> None
**HTTP**: `DELETE /api/v1/identities/{identity_id}`
- Soft-delete a single identity. 404 if not found, 403 if linked to active songs or albums.
- Wraps `CatalogService.get_identity` + `CatalogService.delete_unlinked_identities`.

### async def bulk_delete_unlinked_identities(unlinked: bool = False) -> dict
**HTTP**: `DELETE /api/v1/identities?unlinked=true`
- Soft-delete all unlinked identities in one transaction. Requires `?unlinked=true` as a safety flag.
- Wraps `CatalogService.get_all_identities` + `CatalogService.delete_unlinked_identities`.

### async def delete_publisher(publisher_id: int) -> None
**HTTP**: `DELETE /api/v1/publishers/{publisher_id}`
- Soft-delete a single publisher. 404 if not found, 403 if linked to active songs or albums.
- Wraps `CatalogService.get_publisher` + `CatalogService.delete_unlinked_publishers`.

### async def bulk_delete_unlinked_publishers(unlinked: bool = False) -> dict
**HTTP**: `DELETE /api/v1/publishers?unlinked=true`
- Soft-delete all unlinked publishers in one transaction. Requires `?unlinked=true` as a safety flag.
- Wraps `CatalogService.get_all_publishers` + `CatalogService.delete_unlinked_publishers`.

### async def delete_album(album_id: int) -> None
**HTTP**: `DELETE /api/v1/albums/{album_id}`
- Soft-delete a single album. 404 if not found, 403 if linked to active songs.
- Wraps `CatalogService.get_album` + `CatalogService.delete_unlinked_albums`.

### async def bulk_delete_unlinked_albums(unlinked: bool = False) -> dict
**HTTP**: `DELETE /api/v1/albums?unlinked=true`
- Soft-delete all unlinked albums in one transaction. Requires `?unlinked=true` as a safety flag.
- Wraps `CatalogService.get_all_albums` + `CatalogService.delete_unlinked_albums`.

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

### AddAliasBody *(see src/models/view_models.py)*
`{ display_name: str, name_id: int|null }`
Used by `add_identity_alias`.

### UpdateLegalNameBody *(see src/models/view_models.py)*
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

### async def get_parser_config() -> dict
**HTTP**: `GET /api/v1/ingest/parser-config`
- Retrieve dynamic tokens and presets for the Filename Parser.

### async def get_downloads_folder_json() -> JSONResponse
**HTTP**: `GET /api/v1/ingest/downloads-folder`
- Returns the platform-specific default downloads folder.

### async def get_accepted_formats() -> JSONResponse
**HTTP**: `GET /api/v1/ingest/formats`
- Returns the list of supported file extensions for ingestion as defined in `ACCEPTED_EXTENSIONS`.

### async def get_ingest_status() -> IngestStatusModel
**HTTP**: `GET /api/v1/ingest/status`
- Returns the session-wide ingestion status: `{pending, success, action}`.
- Used by the frontend to restore badge state on page reload and tab switch.

### async def reset_ingest_status() -> dict
**HTTP**: `POST /api/v1/ingest/reset-status`
- Resets the session-wide success/action counters to zero.
- Returns `{"status": "RESET"}`.

### async def get_pending_convert() -> JSONResponse
**HTTP**: `GET /api/v1/ingest/pending-convert`
- Returns all songs with `processing_status=3` (WAV staged, awaiting conversion).
- Used by the ingest page on mount to restore unconverted WAV cards.
- Returns list of `{status: "PENDING_CONVERT", staged_path, song: SongView}`.

### async def get_staging_orphans() -> JSONResponse
**HTTP**: `GET /api/v1/ingest/staging-orphans`
- List files in the staging folder that have no matching DB record.
- Returns list of objects with `filename`, `path`, and `size_bytes`.

### async def delete_staging_orphan(path: str) -> dict
**HTTP**: `DELETE /api/v1/ingest/staging-orphans`
- Delete a specific file from staging, only if it has no DB record.
- Safety: Path must be within `STAGING_DIR`.
- Returns `{"status": "DELETED", "path": path}`.

### async def upload_files(files: list[UploadFile] = File(...)) -> StreamingResponse
**HTTP**: `POST /api/v1/ingest/upload`
- Batch file ingestion entry point (supports single or multiple files).
- Validates extensions and stages all files to `STAGING_DIR` with UUID filenames.
- Streams results as newline-delimited JSON (`application/x-ndjson`). Each line is the current session status `{pending, success, action}` plus `last_result` for the file just processed.
- WAVs are ingested as `PENDING_CONVERT` via `CatalogService.ingest_wav_as_converting`. Conversion is confirmed separately via `/convert-wav`.
- Non-WAVs are ingested via `IngestionService._ingest_single`.

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
- Converts a staged WAV to MP3 and finalizes the existing status-3 DB record.
- WAV must already be in the DB (ingested via `/upload` as status=3).
- Wraps `convert_to_mp3` then `CatalogService.finalize_wav_conversion`.

### async def get_cleanup_origin(song_id: int) -> dict
**HTTP**: `GET /api/v1/ingest/cleanup-origin/{song_id}`
- Checks if there is a known original file path for this song.
- Returns `{"id": song_id, "origin_path": str|null, "exists": bool}`.

### async def cleanup_original_file(request: CleanupOriginalRequest) -> dict
**HTTP**: `POST /api/v1/ingest/cleanup-original`
- Physically deletes the original source file (e.g. from Downloads).
- Payload: `{"file_path": "... "}`.
- Securely restricts deletions to the Downloads folder.

---

---

## Mutations Router
*Location: `src/engine/routers/mutations.py`*
**Responsibility**: Unified entry point for all database write operations.

### async def mutate(body: MutationRequest) -> dict
**HTTP**: `POST /api/v1/mutate`
- Processes a batch of add, remove, update, and delete operations in a single transaction.
- Returns the updated song views and any warnings (e.g. file move issues).
- Wraps `MutationCoordinator.apply`.

---

## Metabolic Router
*Location: `src/engine/routers/metabolic.py`*
**Responsibility**: File-system inspection and comparison logic.

### async def inspect_file(db_song: SongView) -> dict
**HTTP**: `POST /api/v1/metabolic/inspect-file`
- Accepts the caller's `SongView` as the request body (no DB re-hydration).
- Reads physical file at `db_song.source_path` via `MetadataService`.
- Runs `MetadataService.compare_songs(db_song, file_song)` and returns `{diff, raw_tags}`.

### async def get_id3_frames() -> Dict[str, Any]
**HTTP**: `GET /api/v1/metabolic/id3-frames`
- Returns the full ID3 frame mapping configuration.

---

## Song Updates Router
*Location: `src/engine/routers/song_updates.py`*
**Responsibility**: Roles and ID3 synchronization.

### async def get_all_roles() -> List[str]
**HTTP**: `GET /api/v1/roles`
- Returns all distinct artist credit roles from the database.

### async def sync_id3(song_id: int) -> dict
**HTTP**: `GET /api/v1/songs/{song_id}/sync-id3`
- Writes current DB state to the physical ID3 tags of the song file.

---

## Album Updates Router
*Location: `src/engine/routers/album_updates.py`*
**Responsibility**: Preparing mutation payloads for album operations.

### async def sync_album_from_song_diff(album_id: int, song_id: int) -> dict
**HTTP**: `GET /api/v1/albums/{album_id}/sync-from-song/{song_id}`
- Returns the add/update payload to sync an existing album from a song. Does not write.

### async def prepare_album_from_song(body: PrepareAlbumFromSongBody) -> dict
**HTTP**: `POST /api/v1/albums/prepare-from-song`
- Returns the add/update payload to create and sync an album from a song. Does not write.

### PrepareAlbumFromSongBody
- `song_id: int`
- `album_id: Optional[int]`
- `title: Optional[str]`


---

## Audio Router
*Location: `src/engine/routers/audio.py`*

### async def stream_song_audio(song_id: int)
**HTTP**: `GET /api/v1/songs/{song_id}/audio`
- Streams the audio file content for a song.
- Returns a standard `FileResponse` with guessed mimetype.

### async def get_song_waveform(song_id: int) -> dict
**HTTP**: `GET /api/v1/songs/{song_id}/waveform`
- Returns `{"peaks": [1000 floats]}` — normalized RMS waveform bars (0..1) for the song's working copy.
- Cache-first; on miss, builds via ffmpeg (sync, ~1-3s for a typical song) and caches at `sqldb/waveform_cache/{song_id}.json`.
- Wraps `WaveformService.get_or_build_peaks`.

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

### FormatTextRequest
`{ text: str, type: "title"|"sentence" }`

### format_text(body: FormatTextRequest) -> dict
**HTTP**: `POST /api/v1/tools/format-text`
- Stateless text casing utility. Returns `{ result: str }`.
- `type="title"` → `CasingService.to_title_case`; `type="sentence"` → `CasingService.to_sentence_case`.

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
