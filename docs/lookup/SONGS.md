# Songs & Media Data Lookup
*Location: `src/data/song_repository.py`*

**Responsibility**: Low-level database access for the Songs and MediaSources tables.

---

## SongRepository
### get_by_id(song_id: int) -> Optional[Song]
Fetches the core song record (Title, BPM, Year, Path, etc.) by ID.

### get_by_ids(ids: List[int]) -> List[Song]
Batch-fetches core song records for multiple IDs.

### _row_to_song(row: sqlite3.Row) -> Song
**Internal**: Maps a physical database row to the strict Pydantic `Song` model, handling NULLs (like `processing_status` and `is_active`) and converting duration to milliseconds.

---

## BaseRepository
*Location: `src/data/base_repository.py`*

**Responsibility**: The connection owner and audit spine for all repositories.

### _get_connection() -> sqlite3.Connection
Single point of truth for all DB connections in `v3core`.

### _log_change(cursor, table, record_id, field, old_val, new_val, batch_id)
Writes one audit row to the existing `ChangeLog` table. Silently no-ops if no change.

---

## SongCreditRepository
*Location: `src/data/song_credit_repository.py`*

**Responsibility**: DB reads for the SongCredits table. Bridges Song IDs to Names and Roles.

### get_credits_for_song(song_id: int) -> List[SongCredit]
Fetches all credits for a given song, joining `ArtistNames` to include the human-readable `display_name`.

### _row_to_song_credit(row: sqlite3.Row) -> SongCredit
**Internal**: Maps a physical database row to the strict Pydantic `SongCredit` model, enforcing strict validation that `RoleID` cannot be NULL.
