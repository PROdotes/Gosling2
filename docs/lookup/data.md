# Data Layer

*Location: `src/data/`_

**Responsibility**: Low-level database access, queries, and repositories.

---

## BaseRepository

*Location: `src/data/base_repository.py`_
**Responsibility**: The connection owner and audit spine for all repositories.

### _get_connection() -> sqlite3.Connection

Single point of truth for all DB connections in `v3core`.

### get_connection() -> sqlite3.Connection

Public connection accessor used by services for atomic transaction control.

---

## MediaSourceRepository

*Location: `src/data/media_source_repository.py`_
**Responsibility**: Universal access for the base `MediaSources` table. Used by specialized repos (Songs, Podcasts) to manage core file metadata.

### insert_source(model: MediaSource, type_name: str, conn: sqlite3.Connection) -> int

Writes the base record into `MediaSources`. Resolves `TypeID` from the given `type_name`. Returns the new `SourceID`.

### get_by_path(path: str, conn: Optional[sqlite3.Connection] = None) -> Optional[MediaSource]

Universal lookup by SourcePath. Returns the base `MediaSource` record (or None) regardless of specialized type (Song, Podcast, etc.). Supports optional shared connection.

### get_by_hash(audio_hash: str, conn: Optional[sqlite3.Connection] = None) -> Optional[MediaSource]

Universal lookup by AudioHash. Returns the base `MediaSource` record (or None). Supports optional shared connection.

### get_source_metadata_by_hash(audio_hash: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]

Truth discovery lookup that ignores the `IsDeleted` filter. Returns basic metadata (`id`, `title`, `duration_s`, `is_deleted`) for re-ingestion conflict resolution. Supports optional shared connection.

### soft_delete(source_id: int, conn: sqlite3.Connection) -> bool

Soft-delete a MediaSource by setting `IsDeleted = 1`. Returns `True` if a record was updated, `False` if not found or already deleted.

### reactivate_source(source_id: int, conn: sqlite3.Connection) -> bool

Restores a previously soft-deleted record by setting `IsDeleted = 0`. Returns `True` if successful.

### hard_delete(source_id: int, conn: sqlite3.Connection) -> None

Hard-delete (destructive) a MediaSource and its specialized child (Song, etc.). Forces DB Cascade to clear all links. Used for discarding failed conversions or merging duplicates. Does NOT commit.

### delete_song_links(source_id: int, conn: sqlite3.Connection) -> None

Hard-delists all junction/link rows for a song (SongCredits, SongAlbums, MediaSourceTags, RecordingPublishers). This must be called before `soft_delete` to ensure links are severed while the anchor record remains for undo/audit purposes.

### _row_to_source(row: sqlite3.Row) -> MediaSource

**Internal**: Maps a physical database row to the base `MediaSource` domain model, preserving the duration in raw seconds (`duration_s`).

---

## SongRepository

*Location: `src/data/song_repository.py`_
**Responsibility**: Specialized access for the `Songs` table. Inherits core file management from `MediaSourceRepository`.

### update_scalars(song_id: int, fields: dict, conn: sqlite3.Connection) -> None

Update editable scalar fields for a song. Partial updates — only send changed fields. Splits between MediaSources (media_name, is_active) and Songs (bpm, year, isrc). Does NOT commit.

### get_by_id(song_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Song]

Fetches the core song record (Title, BPM, Year, Path, etc.) by ID. Supports optional shared connection.
Only returns non-deleted records.

### get_by_ids(ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[Song]

Batch-fetches core song records for multiple IDs. Supports optional shared connection.

### get_by_title(query: str, conn: Optional[sqlite3.Connection] = None) -> List[Song]

Finds songs by case-insensitive title match (LIKE '%query%'). Supports optional shared connection.

### search_slim(query: str, conn: Optional[sqlite3.Connection] = None) -> List[dict]

Fast list-view search. Returns raw dicts with keys: SourceID, MediaName, SourcePath, SourceDuration, RecordingYear, TempoBPM, ISRC, IsActive, DisplayArtist (aggregated), PrimaryGenre (aggregated). Supports optional shared connection.

- Matches: Title, Performer (DisplayName + LegalName), Album, Publisher, Tag, Year, and ISRC via UNION subquery.
- No hydration. Used by the list-view endpoint.

### search_slim_by_ids(ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[dict]

Fetch slim list-view rows for a specific set of SourceIDs. Same column set as `search_slim`. Supports optional shared connection.

### get_by_identity_ids(identity_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[Song]

Retrieves songs where any given Identity ID is credited. Forms the base of the \"Grohlton Check\". Supports optional shared connection.

### get_by_path(file_path: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Song]

Returns a Song record by its exact physical path. Supports optional shared connection.

### get_by_hash(file_hash: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Song]

Fetch a song by its unique audio hash. Supports optional shared connection.

### find_by_metadata(title: str, artists: List[str], year: Optional[int], conn: Optional[sqlite3.Connection] = None) -> List[Song]

Find songs matching Title, exact Performer set, and Recording Year. Supports optional shared connection.

### insert(song: Song, conn: sqlite3.Connection) -> int

Atomic insert into `MediaSources`, `Songs`, and all relationship tables (tags, albums, publishers, credits). Delegates core file record to `MediaSourceRepository.insert_source`, then calls `TagRepository.insert_tags`, `SongAlbumRepository.insert_albums`, `PublisherRepository.insert_song_publishers`, and `SongCreditRepository.insert_credits`. Returns the new `SourceID`. Does NOT commit.

### reactivate_ghost(ghost_id: int, song: Song, conn: sqlite3.Connection) -> bool

Restores a soft-deleted song and updates it with new metadata (Tags, Credits, Albums, Publishers).

- Calls `MediaSourceRepository.reactivate_source`.
- Replaces links via `delete_song_links` + re-insertion.

### _row_to_song(row: sqlite3.Row) -> Song

**Internal**: Maps a physical database row to the `Song` domain model, handling NULLs and preserving the duration in raw seconds (`duration_s`).

---

## SongCreditRepository

*Location: `src/data/song_credit_repository.py`_
**Responsibility**: DB reads and writes for the SongCredits table. Bridges Song IDs to Names, Roles, and Identity IDs.

### insert_credits(source_id: int, credits: List[SongCredit], conn: sqlite3.Connection) -> None

Get-or-create `Roles` rows (exact match on `RoleName`) and `ArtistNames` rows (exact match on `DisplayName`; new names get `NULL` OwnerIdentityID, `IsPrimaryName=0`), then insert `SongCredits` link rows. Uses `INSERT OR IGNORE` for idempotency against the `UNIQUE(SourceID, CreditedNameID, RoleID)` constraint.

### get_credits_for_songs(song_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[SongCredit]

Batch-fetches credits for multiple songs in a single query. Supports optional shared connection for performance.

- Returns a flat list of `SongCredit` entities.
- Includes `identity_id` by joining `ArtistNames.OwnerIdentityID`.
- Performance optimized for list-views (Search/Folders).

### get_all_roles(conn: Optional[sqlite3.Connection] = None) -> List[str]

Returns all role names from the Roles table, ordered alphabetically. Supports optional shared connection.

### get_or_create_role(role_name: str, cursor) -> int

Get-or-create a Role by name. Returns role_id.

### find_by_display_name(display_name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[int]

Exact case-insensitive lookup of an ArtistName by DisplayName. Returns NameID or None. Read-only. Supports optional shared connection.

### get_or_create_credit_name(display_name: str, cursor, identity_id: Optional[int] = None) -> int

Get-or-create an ArtistName by display name, with optional explicit identity linking. Reactivates soft-deleted records. Creates linked Identity if needed. Returns name_id.

### add_credit(source_id: int, display_name: str, role_name: str, conn: sqlite3.Connection, identity_id: Optional[int] = None) -> SongCredit

Add a single credit to a song. Get-or-creates ArtistName and Role. Supports explicit identity_id for Truth-First linking. Returns the SongCredit. Does NOT commit.

### remove_credit(credit_id: int, conn: sqlite3.Connection) -> None

Remove a single SongCredits link by CreditID. Keeps ArtistName record. Does NOT commit.

### update_credit_name(name_id: int, new_name: str, conn: sqlite3.Connection) -> None

Update an ArtistName's DisplayName globally. Affects all songs linked to this name. Does NOT commit.

### _row_to_song_credit(row: sqlite3.Row) -> SongCredit

**Internal**: Maps a physical database row to the `SongCredit` domain model, ensuring that `RoleID` is correctly handled.

---

## SongAlbumRepository

*Location: `src/data/song_album_repository.py`_
**Responsibility**: Batch fetching and writing of album associations for songs (M2M).

### insert_albums(source_id: int, albums: List[SongAlbum], conn: sqlite3.Connection) -> None

Get-or-create `Albums` rows (matched on `AlbumTitle` + `ReleaseYear` + album artist via `AlbumCredits`), then insert `SongAlbums` link rows with track/disc numbers. Also writes `AlbumCredits` for newly created albums. Falls back to Title+Year only when no credits are provided.

### get_albums_for_songs(song_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[SongAlbum]

Fetches album context (Title, Track, Disc, Primary, Publishers) for a set of Song IDs.
Returns `SongAlbum` bridge models ready for publisher hydration by the Service. Supports optional shared connection.

### get_albums_for_songs_reverse(album_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[SongAlbum]

Reverse Batch-fetch: Find all song associations (SongAlbum link models) for a set of Album IDs. Used for efficient tracklist hydration. Supports optional shared connection.

### _find_matching_album(cursor, album: SongAlbum) -> int | None

**Internal**: Finds an existing album matching Title+Year+Artist. Queries candidates by title+year, then compares sorted artist sets from `AlbumCredits`. Falls back to title+year if no incoming credits. Returns `AlbumID` or `None`.

### _insert_album_credits(cursor, album_id: int, album: SongAlbum) -> None

**Internal**: Writes `AlbumCredits` rows for a newly created album. Get-or-creates `Roles` and `ArtistNames` (NULL identity for new names), then inserts `AlbumCredits` links.

### add_album(source_id: int, album_id: int, track_number: int, disc_number: int, conn: sqlite3.Connection) -> None

Link a song to an existing album. Does NOT commit.

### remove_album(source_id: int, album_id: int, conn: sqlite3.Connection) -> None

Remove a song-album link. Keeps Album record. Does NOT commit.

### update_track_info(source_id: int, album_id: int, track_number: int, disc_number: int, conn: sqlite3.Connection) -> None

Update track/disc number for a song-album link. Does NOT commit.

### _row_to_song_album(row: sqlite3.Row) -> SongAlbum

**Internal**: Maps a physical database row to the strict Pydantic `SongAlbum` model.

---

## AlbumRepository

*Location: `src/data/album_repository.py`_
**Responsibility**: Loading first-class Album directory records and album-to-song links.

### get_all(conn: Optional[sqlite3.Connection] = None) -> List[Album]

Fetch the full directory of active (non-deleted) albums, ordered by title. Supports optional shared connection.

### search_slim(query: str, conn: Optional[sqlite3.Connection] = None) -> List[dict]

Fast list-view album search. Returns raw dicts with keys: AlbumID, AlbumTitle, AlbumType, ReleaseYear, DisplayArtist (aggregated), DisplayPublisher (aggregated label string), SongCount. No tracklist hydration. Pass empty string to get all albums. Supports optional shared connection.

### get_by_id(album_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Album]

Fetch a single album by its ID. Supports optional shared connection.

### get_song_ids_by_album(album_id: int, conn: Optional[sqlite3.Connection] = None) -> List[int]

Fetch all song IDs linked to a specific album, ordered by disc, track, and source ID. Supports optional shared connection.

### get_song_ids_for_albums(album_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> Dict[int, List[int]]

Batch fetch song IDs for a set of albums in a single query. Returns a map of AlbumID -> [SourceID]. Supports optional shared connection.

### create_album(title: str, album_type: str, release_year: int, conn: sqlite3.Connection) -> int

Get-or-create an Album by title+year. Reactivates soft-deleted. Returns album_id. Does NOT commit.

### update_album(album_id: int, fields: dict, conn: sqlite3.Connection) -> None

Update editable Album fields (title, album_type, release_year). Partial updates. Does NOT commit.

### _row_to_album(row: sqlite3.Row) -> Album

**Internal**: Maps a physical database row to the strict Pydantic `Album` model.

---

## PublisherRepository

*Location: `src/data/publisher_repository.py`_
**Responsibility**: Loading and writing Publisher metadata for Albums and Tracks.

### insert_song_publishers(source_id: int, publishers: List[Publisher], conn: sqlite3.Connection) -> None

Get-or-create `Publishers` rows (case-insensitive match on `PublisherName`), then insert `RecordingPublishers` link rows.

### get_publishers_for_albums(album_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[Tuple[int, Publisher]]

Batch-fetch publisher objects for a list of Albums (M2M resolution). Supports optional shared connection.

### get_publishers_for_songs(song_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[Tuple[int, Publisher]]

Batch-fetch master record publisher objects for a list of Songs (M2M resolution). Supports optional shared connection.

### get_publishers(publisher_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> Dict[int, Publisher]

Resolve a flat list of ID -> Publisher objects. Supports optional shared connection.

### get_all(conn: Optional[sqlite3.Connection] = None) -> List[Publisher]

Fetch the full directory of active publishers. Supports optional shared connection.

### search(query: str, conn: Optional[sqlite3.Connection] = None) -> List[Publisher]

Surface search for publishers by name match only (no recursive expansion). Supports optional shared connection.

### search_deep(query: str, conn: Optional[sqlite3.Connection] = None) -> List[Publisher]

Deep recursive search for publishers using a CTE. Returns matching publishers AND all their descendants (children, grandchildren). Used by the deep song search expansion leg only. Supports optional shared connection.

### find_by_name(name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[int]

Exact case-insensitive lookup of a Publisher by PublisherName. Returns PublisherID or None. Read-only. Supports optional shared connection.

### get_by_id(publisher_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Publisher]

Fetch a single publisher by its ID. Supports optional shared connection.

### get_by_ids(ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[Publisher]

Batch-fetch multiple publishers by ID. Used for parent chain resolution. Supports optional shared connection.

### get_hierarchy_batch(publisher_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> Dict[int, Publisher]

RESOLVER: Fetches the entire ancestry chain for a list of publishers in a SINGLE query using a recursive CTE. Supports optional shared connection.

### get_children(parent_id: int, conn: Optional[sqlite3.Connection] = None) -> List[Publisher]

Fetch all sub-publishers for a given parent. Supports optional shared connection.

### get_song_ids_by_publisher(publisher_id: int, conn: Optional[sqlite3.Connection] = None) -> List[int]

Find all song IDs explicitly linked to this publisher (Master rights). Supports optional shared connection.

### get_song_ids_by_publisher_batch(publisher_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[int]

Batch fetch song IDs for a set of publishers. Returns a map of PublisherID -> [SourceID]. Supports optional shared connection.

### get_or_create_publisher(name: str, cursor) -> int

Get-or-create a Publisher by name. Reactivates soft-deleted. Returns publisher_id.

### add_song_publisher(source_id: int, name: str, conn: sqlite3.Connection) -> Publisher

Add a publisher link to a song. Get-or-creates the Publisher record. Returns the Publisher. Does NOT commit.

### remove_song_publisher(source_id: int, publisher_id: int, conn: sqlite3.Connection) -> None

Remove a publisher link from a song. Keeps Publisher record. Does NOT commit.

### add_album_publisher(album_id: int, name: str, conn: sqlite3.Connection) -> Publisher

Add a publisher link for an album. Get-or-creates the Publisher record. Returns the Publisher. Does NOT commit.

### remove_album_publisher(album_id: int, publisher_id: int, conn: sqlite3.Connection) -> None

Remove a publisher link from an album. Keeps Publisher record. Does NOT commit.

### update_publisher(publisher_id: int, name: str, conn: sqlite3.Connection) -> None

Update a Publisher's name globally. Affects all songs linked to this publisher. Does NOT commit.

### set_parent(publisher_id: int, parent_id: Optional[int], conn: sqlite3.Connection) -> None

Set or clear the ParentPublisherID for a publisher. Pass `None` to clear. Raises `LookupError` if publisher not found. Does NOT commit.

### _row_to_publisher(row: sqlite3.Row) -> Publisher

**Internal**: Maps a physical database row to the strict Pydantic `Publisher` model.

---

## TagRepository

*Location: `src/data/tag_repository.py`_
**Responsibility**: DB reads and writes for the Tags table.

### get_all(conn: Optional[sqlite3.Connection] = None) -> List[Tag]

Fetch the full directory of active (non-deleted) tags, ordered by name. Supports optional shared connection.

### search(query: str, conn: Optional[sqlite3.Connection] = None) -> List[Tag]

Search active tags by name match. Supports optional shared connection.

### get_categories(conn: Optional[sqlite3.Connection] = None) -> List[str]

Fetch all distinct tag categories currently present in the database. Supports optional shared connection.

### get_by_id(tag_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Tag]

Fetch a single tag by its ID. Supports optional shared connection.

### get_song_ids_by_tag(tag_id: int, conn: Optional[sqlite3.Connection] = None) -> List[int]

Fetch all song IDs linked to a specific tag. Supports optional shared connection.

### insert_tags(source_id: int, tags: List[Tag], conn: sqlite3.Connection) -> None

Get-or-create `Tags` rows (matched on `TagName` + `TagCategory`), then insert `MediaSourceTags` link rows. Preserves the `IsPrimary` flag from the `Tag` model.

### get_tags_for_songs(song_ids: List[int]) -> List[Tuple[int, Tag]]

Batch-fetches tag objects for a list of Songs.

### add_tag(source_id: int, name: str, category: str, conn: sqlite3.Connection, is_primary: int = 0) -> Tag

Add a single tag to a song. Get-or-creates the Tag record.
Returns the Tag. Does NOT commit.

### remove_tag(source_id: int, tag_id: int, conn: sqlite3.Connection) -> None

Remove a tag link from a song. Keeps Tag record. Does NOT commit.

### set_primary_tag(source_id: int, tag_id: int, conn: sqlite3.Connection) -> None

Atomic reset of primary status for all genre tags on a song, then setting the target tag as primary.
Does NOT commit.

### get_or_create_tag(name: str, category: str, cursor) -> int

Get-or-create a Tag by name+category. Reactivates soft-deleted. Returns tag_id.

### update_tag(tag_id: int, name: str, category: str, conn: sqlite3.Connection) -> None

Update a Tag's name/category globally. Does NOT commit.

### soft_delete(tag_id: int, conn: sqlite3.Connection) -> bool

Set `IsDeleted = 1` for a tag. Returns `True` if a record was updated, `False` if not found or already deleted.

### _row_to_tag(row: sqlite3.Row) -> Tag

**Internal**: Maps a physical database row to the strict Pydantic `Tag` model, preserving the `IsPrimary` flag from the link table.marker.

---

## AlbumCreditRepository

*Location: `src/data/album_credit_repository.py`_
**Responsibility**: DB reads for the AlbumCredits table. Bridges Album IDs to Names and Roles.

### get_credits_for_albums(album_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[AlbumCredit]

Batch-fetches credits for multiple albums in a single query. Supports optional shared connection.

- Returns a flat list of `AlbumCredit` entities.
- Joins with `ArtistNames` and `Roles` tables to resolve human-readable names.

### add_credit(album_id: int, display_name: str, role_name: str, conn: sqlite3.Connection, identity_id: Optional[int] = None) -> int

Add a credit to an album. Get-or-creates ArtistName and Role. Returns name_id. Does NOT commit.

### remove_credit(album_id: int, name_id: int, conn: sqlite3.Connection) -> None

Remove a credit from an album. Deletes link only. Does NOT commit.

### _row_to_album_credit(row: sqlite3.Row) -> AlbumCredit

**Internal**: Maps a physical database row to the `AlbumCredit` domain model.

---

## IdentityRepository

*Location: `src/data/identity_repository.py`_
**Responsibility**: Handles resolution of Artist Identities, Aliases, and Group Memberships.

### get_by_id(identity_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Identity]

Hydrates a basic Identity record without tree expansion. Supports optional shared connection.

### get_all_identities(conn: Optional[sqlite3.Connection] = None) -> List[Identity]

Fetches the full directory of active (non-deleted) identities. Supports optional shared connection.

### get_by_ids(identity_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[Identity]

Batch-fetch multiple identities by ID. Supports optional shared connection.

### search_identities(query: str, conn: Optional[sqlite3.Connection] = None) -> List[Identity]

Finds active identities whose DisplayName, LegalName, or Alias match the query. Supports optional shared connection.

### get_group_ids_for_members(member_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[int]

Batch fetches GroupIdentityIDs for a list of MemberIdentityIDs. Supports optional shared connection.

### find_identity_by_name(name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[int]

Return the IdentityID for an exact (case-insensitive) ArtistName match, or None. Supports optional shared connection.

### add_alias(identity_id: int, display_name: str, cursor: sqlite3.Cursor, name_id: Optional[int] = None) -> int

Link a name to an identity. ID-First: If `name_id` is provided, prioritize it. Handles collision checks and potential identity merges. Returns the `NameID`.

### delete_alias(name_id: int, cursor: sqlite3.Cursor) -> None

Soft-delete an alias link. Guard: primary names cannot be deleted.

### update_legal_name(identity_id: int, legal_name: Optional[str], conn: sqlite3.Connection) -> None

Update the LegalName field on an Identity record. Raises LookupError if not found. Does NOT commit.

### get_aliases_batch(identity_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> Dict[int, List[ArtistName]]

Batch-fetch aliases (ArtistNames) for multiple identities. Supports optional shared connection.

### get_members_batch(identity_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> Dict[int, List[Identity]]

Batch-fetch member identities for multiple group identities. Supports optional shared connection.

### get_groups_batch(identity_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> Dict[int, List[Identity]]

Batch-fetch group identities that multiple person identities belong to. Supports optional shared connection.

### set_type(identity_id: int, type_: str, conn: sqlite3.Connection) -> None

Set the `IdentityType` ('person' or 'group') for an identity. Blocks group→person conversion if members exist. Does NOT commit.

### add_member(group_id: int, member_id: int, cursor: sqlite3.Cursor) -> None

Link a person identity as a member of a group. Guarded against self-membership and nesting groups.

### remove_member(group_id: int, member_id: int, cursor: sqlite3.Cursor) -> None

Remove a membership link. No-op if not linked.

### merge_orphan_into(source_name_id: int, target_name_id: int, cursor: sqlite3.Cursor) -> None

Merges a solo (orphan) identity into another by repointing all credits and soft-deleting the source record.

### _row_to_identity(row: sqlite3.Row) -> Identity

**Internal**: Maps a physical database row to the `Identity` domain model.

---

## AuditRepository

*Location: `src/data/audit_repository.py`_
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
