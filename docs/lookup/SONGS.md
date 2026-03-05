# Songs Contract Registry

> **LAW**: This file is updated BEFORE the code changes. The signature here is the truth.
> Format: `method_name(param: type, ...) -> ReturnType — plain English description`

---

## SongRepository
*Location: `src/v3core/data/song_repository.py`*

**Responsibility**: DB reads and writes for the Songs and SongCredits tables.

### get_by_id(song_id: int) -> Optional[Song]
Fetches a single Song Domain Model by its primary key.

### get_by_ids(ids: List[int]) -> List[Song]
Batch-fetches multiple Song Domain Models. Optimized for the ID-Skeleton virtual table.

---

## SongService
*Location: `src/v3core/services/song_service.py`*

**Responsibility**: Orchestrates multi-step song queries. The "Jazler-Debounce" and ID-Skeleton logic live here.

*(No methods defined yet — add them here before implementation)*
