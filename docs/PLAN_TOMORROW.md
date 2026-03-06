# Plan: Phase 1.5 - Closing the Discovery Loop

## Objective
We have data (SQLite) and we have an edge (FastAPI), but we have no way to **Find** or **See** the data. This phase moves from "JSON Pipelines" to a functional "Browse & View" experience.

---

## 1. Discovery (The Search API)
- **Data**: Implement `SongRepository.search(query: str, limit: int = 50) -> List[Song]`.
- **Service**: `CatalogService.search_songs(query: str)` to orchestrate name-based lookup.
- **Engine**: Endpoint `GET /api/v1/search?q=...` returning a list of `Song` metadata.

---

## 2. Visualization (The Web Dashboard)
- **Engine**: Serve a single-page HTML/JS dashboard at `GET /`.
- **Features**:
  - **Search Bar**: Real-time (debounced) search hitting the `/api/v1/search` endpoint.
  - **Results List**: Clickable list of song titles + years.
  - **Song Detail View**: Clicking a song name calls `GET /api/v1/songs/{id}` and displays the **Full Metadata** (ISRC, BPM, Credits, Path) in a clean, legible side panel.

---

## 3. Verification
- **Full Suite Rule**: Every new method must have a corresponding test in `tests/test_catalog.py` or `tests/test_engine.py`.
- **UI Smoke Test**: Prove that searching for "Everlong" in the browser results in a clickable entry that displays "Foo Fighters" in the credits.

---

## ⚖️ Next Steps (Agreement)
1. **Approval**: Wait for USER approval of this "Loop Closing" plan.
2. **Lookup**: Update `ENGINE.md` and `CATALOG.md` with the new Search signatures.
3. **Execution**: Build the Search -> View pipeline in one contiguous phase.
