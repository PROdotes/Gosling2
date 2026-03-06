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
- Validates query (at least 2 chars).
- Calls `CatalogService.search_songs(q)`.
- Returns a JSON list of `Song` models.
