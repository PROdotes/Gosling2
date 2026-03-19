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

### get_by_title(query: str) -> List[Song]
Finds songs by case-insensitive title match (LIKE '%query%').

### search_surface(query: str) -> List[Song]
Discovery path on titles and albums. Fastest search.

### get_by_identity_ids(identity_ids: List[int]) -> List[Song]
Retrieves songs where any given Identity ID is credited. Forms the base of the "Grohlton Check".

### _row_to_song(row: sqlite3.Row) -> Song

**Internal**: Maps a physical database row to the `Song` domain model, handling NULLs (like `processing_status` and `is_active`) and converting duration to milliseconds.

---

## SongCreditRepository
*Location: `src/data/song_credit_repository.py`*
**Responsibility**: DB reads for the SongCredits table. Bridges Song IDs to Names, Roles, and Identity IDs.

### get_credits_for_songs(song_ids: List[int]) -> List[SongCredit]
Batch-fetches credits for multiple songs in a single query.
- Returns a flat list of `SongCredit` entities.
- Includes `identity_id` by joining `ArtistNames.OwnerIdentityID`.
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

## AlbumRepository
*Location: `src/data/album_repository.py`*
**Responsibility**: Loading first-class Album directory records and album-to-song links.

### get_all() -> List[Album]
Fetch the full album directory ordered by album title.

### search(query: str) -> List[Album]
Search albums by title match.

### get_by_id(album_id: int) -> Optional[Album]
Fetch a single album by its ID.

### get_song_ids_by_album(album_id: int) -> List[int]
Fetch all song IDs linked to a specific album, ordered by disc, track, and source ID.

### get_song_ids_for_albums(album_ids: List[int]) -> Dict[int, List[int]]
Batch fetch song IDs for a set of albums in a single query. Returns a map of AlbumID -> [SourceID].

### _row_to_album(row: sqlite3.Row) -> Album
**Internal**: Maps a physical database row to the strict Pydantic `Album` model.

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

### get_all() -> List[Publisher]
Fetch the full directory of active publishers.

### search(query: str) -> List[Publisher]
Search for publishers by name match.

### get_by_id(publisher_id: int) -> Optional[Publisher]
Fetch a single publisher by its ID.

### get_by_ids(ids: List[int]) -> List[Publisher]
Batch-fetch multiple publishers by ID. Used for parent chain resolution.

### get_hierarchy_batch(publisher_ids: List[int]) -> Dict[int, Publisher]
RESOLVER: Fetches the entire ancestry chain for a list of publishers in a SINGLE query using a recursive CTE.

### get_children(parent_id: int) -> List[Publisher]
Fetch all sub-publishers for a given parent.

### get_song_ids_by_publisher(publisher_id: int) -> List[int]
Find all song IDs explicitly linked to this publisher (Master rights).

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

---

## IdentityRepository
*Location: `src/data/identity_repository.py`*
**Responsibility**: Handles resolution of Artist Identities, Aliases, and Group Memberships.

### get_by_id(identity_id: int) -> Optional[Identity]
Hydrates a basic Identity record without tree expansion.

### get_all_identities() -> List[Identity]
Fetches the directory of all identities.

### get_by_ids(identity_ids: List[int]) -> List[Identity]
Batch-fetch multiple identities by ID.

### search_identities(query: str) -> List[Identity]
Finds identities whose DisplayName, LegalName, or Alias match the query.

### get_group_ids_for_members(member_ids: List[int]) -> List[int]
Batch fetches GroupIdentityIDs for a list of MemberIdentityIDs.

### get_aliases_batch(identity_ids: List[int]) -> Dict[int, List[ArtistName]]
Batch-fetch aliases (ArtistNames) for multiple identities.

### get_members_batch(identity_ids: List[int]) -> Dict[int, List[Identity]]
Batch-fetch member identities for multiple group identities.

### get_groups_batch(identity_ids: List[int]) -> Dict[int, List[Identity]]
Batch-fetch group identities that multiple person identities belong to.

### _row_to_identity(row: sqlite3.Row) -> Identity
**Internal**: Maps a physical database row to the `Identity` domain model.

### _row_to_artist_name(row: sqlite3.Row) -> ArtistName
**Internal**: Maps a physical database row to the `ArtistName` domain model.

---

## AuditRepository
*Location: `src/data/audit_repository.py`*
**Responsibility**: Low-level database access for Audit tables (`ActionLog`, `ChangeLog`, `DeletedRecords`).

### get_actions_for_target(target_id: int, table: str) -> List[AuditAction]
Fetch high-level events (IMPORT, DELETE) for a specific record.

### get_changes_for_record(record_id: int, table: str) -> List[AuditChange]
Fetch field-level modifications for a specific record.

### get_deleted_snapshot(record_id: int, table: str) -> Optional[DeletedRecord]
Fetch the last JSON snapshot of a deleted record.

### _row_to_action(row: sqlite3.Row) -> AuditAction
### _row_to_change(row: sqlite3.Row) -> AuditChange
### _row_to_deleted(row: sqlite3.Row) -> DeletedRecord
**Internal**: Maps physical database rows to the `Audit*` domain models.


