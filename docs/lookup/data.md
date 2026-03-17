# Data Layer
*Location: `src/data/`*

**Responsibility**: Low-level database access, queries, and repositories.

---

## BaseRepository
*Location: `src/data/base_repository.py`*
**Responsibility**: The connection owner and audit spine for all repositories.

### _get_connection() -> sqlite3.Connection
Single point of truth for all DB connections in `v3core`.

### _log_change(cursor, table, record_id, field, old_val, new_val, batch_id)
Writes one audit row to the existing `ChangeLog` table. Silently no-ops if no change.

---

## SongRepository
*Location: `src/data/song_repository.py`*
**Responsibility**: Low-level database access for the Songs and MediaSources tables.

### get_by_id(song_id: int) -> Optional[Song]
Fetches the core song record (Title, BPM, Year, Path, etc.) by ID.

### get_by_ids(ids: List[int]) -> List[Song]
Batch-fetches core song records for multiple IDs.

### get_by_title(query: str, limit: int = 50) -> List[Song]
Finds songs by case-insensitive title match (LIKE '%query%').
Returns full Song models parsed via `_row_to_song`.

### _row_to_song(row: sqlite3.Row) -> Song
**Internal**: Maps a physical database row to the `Song` domain model, handling NULLs (like `processing_status` and `is_active`) and converting duration to milliseconds.

---

## SongCreditRepository
*Location: `src/data/song_credit_repository.py`*
**Responsibility**: DB reads for the SongCredits table. Bridges Song IDs to Names and Roles.

### get_credits_for_songs(song_ids: List[int]) -> List[SongCredit]
Batch-fetches credits for multiple songs in a single query.
- Returns a flat list of `SongCredit` entities.
- Performance optimized for list-views (Search/Folders).

### _row_to_song_credit(row: sqlite3.Row) -> SongCredit
**Internal**: Maps a physical database row to the `SongCredit` domain model, ensuring that `RoleID` is correctly handled.

---

## SongAlbumRepository
*Location: `src/data/song_album_repository.py`*
**Responsibility**: Batch fetching of album associations for songs (M2M).

### get_albums_for_songs(song_ids: List[int]) -> List[SongAlbum]
Fetches album context (Title, Track, Disc, Primary, Publishers) for a set of Song IDs.
Returns `SongAlbum` bridge models ready for publisher hydration by the Service.

### _row_to_song_album(row: sqlite3.Row) -> SongAlbum
**Internal**: Maps a physical database row to the strict Pydantic `SongAlbum` model.

---

## PublisherRepository
*Location: `src/data/publisher_repository.py`*
**Responsibility**: Loading Publisher metadata for Albums and Tracks.

### get_publishers_for_albums(album_ids: List[int]) -> List[Tuple[int, Publisher]]
Batch-fetch publisher objects for a list of Albums (M2M resolution).

### get_publishers_for_songs(song_ids: List[int]) -> List[Tuple[int, Publisher]]
Batch-fetch master record publisher objects for a list of Songs (M2M resolution).

### get_publishers(publisher_ids: List[int]) -> Dict[int, Publisher]
Resolve a flat list of ID -> Publisher objects.

### _row_to_publisher(row: sqlite3.Row) -> Publisher
**Internal**: Maps a physical database row to the strict Pydantic `Publisher` model.

---

## TagRepository
*Location: `src/data/tag_repository.py`*
**Responsibility**: DB reads for the Tags table.

### get_tags_for_songs(song_ids: List[int]) -> List[Tuple[int, Tag]]
Batch-fetches tags for multiple songs (M2M).
- Returns a flat list of `(SongID, Tag)` tuples.
- Hydrates the `is_primary` flag from the `MediaSourceTags` table.

### _row_to_tag(row: sqlite3.Row) -> Tag
**Internal**: Maps a physical database row to the strict Pydantic `Tag` model, including the `IsPrimary` marker.

---

## AlbumCreditRepository
*Location: `src/data/album_credit_repository.py`*
**Responsibility**: DB reads for the AlbumCredits table. Bridges Album IDs to Names and Roles.

### get_credits_for_albums(album_ids: List[int]) -> List[AlbumCredit]
Batch-fetches credits for multiple albums in a single query.
- Returns a flat list of `AlbumCredit` entities.
- Joins with `ArtistNames` and `Roles` tables to resolve human-readable names.

### _row_to_album_credit(row: sqlite3.Row) -> AlbumCredit
**Internal**: Maps a physical database row to the `AlbumCredit` domain model.
