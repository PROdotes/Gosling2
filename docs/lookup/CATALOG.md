I will now fix the Catalog Service Lookup by removing the legacy 'Contract' redundancy and aligning it with the Golden Template.

# Catalog Service
*Location: `src/services/catalog_service.py`*
**Responsibility**: Orchestrates data from multiple repositories into complete Domain Models.

---

### get_song(song_id: int) -> Optional[Song]
Fetches a single Song domain model by its unique ID.
- Accesses `SongRepository` to get the core record.
- Accesses `SongCreditRepository` to fetch and attach all credits.
