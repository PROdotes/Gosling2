# Engine Service
*Location: `src/engine_server.py`*
**Responsibility**: Entry point and router aggregator for the V3CORE background service.

---

# Catalog Router
*Location: `src/engine/routers/catalog.py`*
**Responsibility**: HTTP interface for song and artist metadata.

### async def get_song(song_id: int) -> Song
Fetches a single Song domain model by its unique ID.
- Raises `HTTPException(404)` if the song does not exist.
- Wraps `CatalogService.get_song`.
