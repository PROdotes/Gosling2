# Services Layer
*Location: `src/services/`*

**Responsibility**: Stateless orchestrators containing the business logic.

---

## CatalogService
*Location: `src/services/catalog_service.py`*
**Responsibility**: Entry point for song access. Stateless orchestrator that combines data from multiple repositories into complete Domain Models.

### get_song(self, song_id: int) -> Optional[Song]
Fetch a single song and all its credits by ID.
- Accesses `SongRepository` to get the core record.
- Uses `_hydrate_songs` to attach all credits.

### search_songs(self, query: str) -> List[Song]
Search for songs by title and hydrate with full metadata.
- Calls `SongRepository.get_by_title`.
- Uses `_hydrate_songs` to attach all credits.

### _hydrate_songs(self, songs: List[Song]) -> List[Song]
**Internal**: Centralized batch hydration for song credits.
- Fetches a flat list of credits using `SongCreditRepository.get_credits_for_songs`.
- Locally orchestrates/groups the credits by SourceID for O(1) attribute access.
- Stitches them back to the Songs and returns the hydrated list.
