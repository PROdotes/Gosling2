# GOSLING3 Spec: Artist Browser (Phase 2.6)

## Overview
This specification covers Phase 2.6: The Artist Browser. It outlines the API endpoints required to build the directory of identities and fetch their respective song catalogs ("Reverse Credits"). It also covers the frontend connection points.

---

## 1. Artist Directory API
**Goal**: Provide a paginated list of all Universal Identities for the frontend "Browse Artists" view.

### A. Repository Level (`src/data/identity_repository.py`)
- **New Method**: `get_all_identities(limit: int = 100, offset: int = 0) -> List[Identity]`
- **Query**:
  ```sql
  SELECT IdentityID, IdentityType, DisplayName, LegalName
  FROM Identities
  ORDER BY DisplayName COLLATE NOCASE ASC
  LIMIT ? OFFSET ?
  ```

### B. Service Level (`src/services/catalog_service.py`)
- **New Method**: `get_all_identities(limit: int = 100, offset: int = 0) -> List[Identity]`
- **Logic**: Pass-through to `IdentityRepository.get_all_identities()`.

### C. Router Level (`src/engine/routers/catalog.py`)
- **New Endpoint**: `GET /api/v1/identities`
- **Response**: `List[IdentityView]`

---

## 2. Reverse Credit Endpoint
**Goal**: Given an Identity ID, fetch all songs credited to this identity, including its aliases and group members (Universal Tree resolution).

### A. Repository Level (`src/data/song_repository.py`)
- We will reuse the existing method: `get_by_identity_ids(identity_ids: List[int], limit: int = 100) -> List[Song]`

### B. Service Level (`src/services/catalog_service.py`)
- **New Method**: `get_songs_by_identity(identity_id: int) -> List[Song]`
- **Logic**:
  1. Fetch full `Identity` tree via `_identity_repo.resolve_full(identity_id)`. Returns 404 if missing.
  2. Collect all Identity IDs associated with this universal tree (self, members, groups).
  3. Fetch songs array using `_song_repo.get_by_identity_ids(collected_ids)`.
  4. Return `_hydrate_songs(songs)`.

### C. Router Level (`src/engine/routers/catalog.py`)
- **New Endpoint**: `GET /api/v1/identities/{identity_id}/songs`
- **Response**: `List[SongView]`

---

## 3. UI Plan
- Once the endpoints are ready, the frontend (`src/templates/dashboard.html` or a new `artist_browser.html`) will interface with these endpoints to:
  - Display an Artist Directory grid.
  - Drill down into `/api/v1/identities/{id}` to display the Identity Tree.
  - Drill down into `/api/v1/identities/{id}/songs` to render their complete tracklist.
