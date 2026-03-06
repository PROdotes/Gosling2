# Plan: Phase 1.5 - Discovery Loop

## Objective
Close the loop between data storage and visualization by implementing a search-to-view pipeline.

## 1. Lookup Alignment
Update all lookup files to use consistent naming:
- `CATALOG.md`: `search_songs(query: str)`
- `ENGINE.md`: `async def search_songs(q: str)`

## 2. Implementation
### Data Layer
- Implement `SongRepository.get_by_title(query: str, limit: int = 50)` in `src/data/song_repository.py`.
- Ensure case-insensitive `LIKE` matching.

### Service Layer
- Implement `CatalogService.search_songs(query: str)` in `src/services/catalog_service.py`.
- Hydrate results with credits using `SongCreditRepository`.

### Engine Layer
- Add `GET /api/v1/songs/search` to `src/engine/routers/catalog.py`.
- Mount `StaticFiles` in `src/engine_server.py` to serve the UI via `GET /`.

### UI Layer
- Create `src/templates/dashboard.html` with:
    - Debounced search input.
    - Results list (Song + Year).
    - Detail panel (Credits, BPM, ISRC).

## 3. Testing
- `tests/test_search.py`: Unit tests for repo and service search logic.
- `tests/test_engine_search.py`: Integration tests for the search endpoint.
