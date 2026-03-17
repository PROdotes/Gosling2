# Engine Routers
*Location: `src/engine/routers/`*

**Responsibility**: HTTP interface and input validation for the API.

---

## Catalog Router
*Location: `src/engine/routers/catalog.py`*
**Responsibility**: HTTP interface for song and artist metadata.

### def _get_service() -> CatalogService
**Internal**: Centralized service factory for the router that injects `GOSLING_DB_PATH`.

### async def get_song(song_id: int) -> Song
**HTTP**: `GET /api/v1/songs/{song_id}`
Fetches a single Song domain model by its unique ID.
- Raises `HTTPException(404)` if the song does not exist.
- Wraps `CatalogService.get_song`.

### async def search_songs(q: str) -> List[Song]
**HTTP**: `GET /api/v1/songs/search?q={query}`
- Validates query (at least 1 char now per user request).
- Calls `CatalogService.search_songs(q)`.
- Returns a JSON list of `Song` models.
- **Instrumentation**: Traces query and result count.

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
