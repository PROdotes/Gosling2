# Engine Routers
*Location: `src/engine/routers/`*

**Responsibility**: HTTP interface and input validation for the API.

---

## Catalog Router
*Location: `src/engine/routers/catalog.py`*
**Responsibility**: HTTP interface for song and artist metadata.

### def _get_service() -> CatalogService
**Internal**: Centralized service factory for the router that injects `GOSLING_DB_PATH`.

### async def get_song(song_id: int) -> SongView
**HTTP**: `GET /api/v1/songs/{song_id}`
Fetches a single Song domain model by its unique ID.
- Raises `HTTPException(404)` if the song does not exist.
- Wraps `CatalogService.get_song`.

### async def search_songs(q: str) -> List[SongView]
**HTTP**: `GET /api/v1/songs/search?q={query}`
- Validates query (at least 1 char now per user request).
- Calls `CatalogService.search_songs(q)`.
- Returns a JSON list of `Song` models.
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

### async def get_all_albums() -> List[AlbumView]
**HTTP**: `GET /api/v1/albums`
- Fetches the directory of all albums.
- Wraps `CatalogService.get_all_albums`.
- Maps to `AlbumView` for dashboard rendering.

### async def search_publishers(q: str) -> List[Publisher]
**HTTP**: `GET /api/v1/publishers/search?q={query}`
- Searches publishers by name.
- Wraps `CatalogService.search_publishers`.

### async def search_albums(q: str) -> List[AlbumView]
**HTTP**: `GET /api/v1/albums/search?q={query}`
- Searches albums by title.
- Wraps `CatalogService.search_albums`.
- Maps to `AlbumView` for dashboard rendering.

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

### async def get_publisher_songs(publisher_id: int) -> List[SongView]
**HTTP**: `GET /api/v1/publishers/{publisher_id}/songs`
- Fetches the full repertoire (Master rights) for a given publisher.
- Wraps `CatalogService.get_publisher_songs`.

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

### async def get_tag_songs(tag_id: int) -> List[SongView]
**HTTP**: `GET /api/v1/tags/{tag_id}/songs`
- Fetches the full hydrated song repertoire linked to this tag.
- Wraps `CatalogService.get_tag_songs`.

### async def check_ingestion(request: IngestionCheckRequest) -> IngestionReportView
**HTTP**: `POST /api/v1/catalog/ingest/check`
- Performs a dry-run ingestion collision check.
- Returns status (NEW, ALREADY_EXISTS, ERROR) and match details.
- Wraps `CatalogService.check_ingestion`.

---


## Ingest Router
*Location: `src/engine/routers/ingest.py`*
**Responsibility**: Dedicated endpoints for binary file handling and session state.

### def _get_service() -> CatalogService
**Internal**: Service factory for the ingestion router.

### def _get_downloads_folder() -> Optional[str]
**Internal**: NT/POSIX compatible downloads folder path.

### async def get_downloads_folder() -> JSONResponse
**HTTP**: `GET /api/v1/ingest/downloads-folder`
- Returns the platform-specific default downloads folder.

### async def get_accepted_formats() -> JSONResponse
**HTTP**: `GET /api/v1/ingest/formats`
- Returns the list of supported file extensions for ingestion as defined in `ACCEPTED_EXTENSIONS`.

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
- Wraps `AuditService.get_history`.
