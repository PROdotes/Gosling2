# Cleanup Audit: 2026-03-27

## 1. Systematic Scan Results

### 1.1 Structural Duplication in Repositories (`src/data/`)
| Location | Issue | Proposed DRY Abstraction |
| :--- | :--- | :--- |
| `SongRepository.get_by_path` / `get_by_hash` | Identical logic: calls `super()` then `get_by_id`. | Create a generic `_get_hydrated(field, value)` helper in `SongRepository` or move hydration trigger to a shared decorator/wrapper. |
| `MediaSourceRepository.delete_song_links` | Business logic for "Songs" inside a universal "MediaSource" base repository. | Move to `SongRepository` or rename to `_hard_delete_associated_links` and accept a table list. |
| `SongRepository.insert` / `reactivate_ghost` | Repeated instantiation of 4 specialized repositories (`Tag`, `Album`, `Publisher`, `Credit`). | Use a Repository Factory or inject dependencies to avoid 4x instantiation per call. |
| `IdentityRepository` / `AlbumRepository` | `get_by_id` boilerplate calling `get_by_ids`. | Move `get_by_id` logic to `BaseRepository` as a generic template using `get_by_ids`. |

### 1.2 Redundant Logic in Services (`src/services/`)
| Location | Issue | Proposed DRY Abstraction |
| :--- | :--- | :--- |
| `CatalogService.search_songs` / `search_songs_deep` | Parallel methods with shared seed search but different expansions. | Merge into `search_songs(query, deep=False)`. |
| `CatalogService._get_tags_by_song` / `_get_credits_by_song` | Boilerplate "fetch then group by ID" logic. | Ensure all use `_batch_group_by_id` and potentially generalize the fetch call. |
| `CatalogService.delete_song` | Orchestrating two separate repo calls (links + soft-delete). | Move atomic soft-delete orchestration (links + row) into `SongRepository.soft_delete_song`. |
| `src/static/js/dashboard/` | "Slop" in `main.js`, `songs.js`, and `ingestion.js` (all >18KB). | UI event handlers duplicate logic. Refactor into shared components or utils. |

### 1.3 Automated Tool Scans (jscpd & fallow)
| Tool | Result | Context |
| :--- | :--- | :--- |
| `jscpd` | 4 Clones Found | Detailed below. |
| `fallow` | 6 Issues / 2 Clone Groups | Maintainability Index 84.3. Complexity hotspots flagged in `CatalogService` and config duplication in `purgecss.config.cjs`. |

#### jscpd Clone Details:
1. **Python (15 lines)**: `src/data/song_album_repository.py` (165-180) ↔ `src/data/song_credit_repository.py` (49-65). *Shared Role/ArtistName creation logic.*
2. **Python (5 lines)**: `src/data/publisher_repository.py` (193-198) ↔ (79-84). *Internal insertion logic duplication.*
3. **Python (5 lines)**: `src/data/identity_repository.py` (196-201) ↔ (166-171). *Nearly identical Membership/Group grouping logic.*
4. **JavaScript (9 lines)**: `src/static/js/dashboard/renderers/ingestion.js` (277-286) ↔ (175-184).

### 1.4 Audit of `docs/lookup/` Discrepancies
- `services.md`: Duplicate entries for `_hydrate_songs` (lines 102/146) and `_hydrate_identities` (lines 106/166).
- `data.md`: Method signatures in `SongAlbumRepository` and `SongCreditRepository` are slightly out of date compared to actual code (e.g., parameter names).

## 2. Redundancy Identification (Deduplication Pass)

### 2.1 The "Lookup-to-Hydration" Pattern
Every specialized repository (Song, Album, Identity) follows a pattern:
1. Fetch core record(s).
2. Hydrate relations in the Service layer.

However, `SongRepository` currently re-fetches itself via `get_by_id` after finding a path/hash match in the base table. 
**Optimization**: `SongRepository` can override `get_by_path` to perform a single JOIN query that returns the Song record directly, rather than two round-trips.

### 2.2 The "Delete Orchestration" Smells
`CatalogService` shouldn't need to know that songs require link deletion before soft-deletion. This is a data-integrity rule that belongs in the Repository Layer.

---
**Status**: Phase 1 Audit Complete.
