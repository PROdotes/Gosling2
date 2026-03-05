# Catalog Service Lookup
*Location: `src/v3core/services/catalog_service.py`*

**Responsibility**: Orchestrates data from multiple repositories into complete Domain Models.

---

## CatalogService
### get_song(song_id: int) -> Optional[Song]
Fetches a single Song domain model by its unique ID.
- Accesses `SongRepository` to get the core record.
- Accesses `SongCreditRepository` to fetch and attach all credits (performers/composers) to the Song object.

---

## Catalog Contract
### get_song(song_id: int) -> Optional[Song]
The primary entry point for fetching music data.
- **Returns**: Title, FilePath, Duration, BPM, Year, and ISRC.
