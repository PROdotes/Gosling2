# Services Layer
*Location: `src/services/`*

**Responsibility**: Stateless orchestrators containing the business logic.

---

## CatalogService
*Location: `src/services/catalog_service.py`*
**Responsibility**: Entry point for song access. Stateless orchestrator that combines data from multiple repositories into complete Domain Models.

### get_song(song_id: int) -> Optional[Song]
Fetch a single song and all its credits by ID.
- Accesses `SongRepository` to get the core record.
- Uses `_hydrate_songs` to attach all credits, albums, and publishers.

### search_songs(query: str) -> List[Song]
Search for songs by title, album, and identity expansion (groups/aliases).
- Calls `SongRepository.search_surface` for titles/albums.
- Calls `IdentityRepository.search_identities` and `get_group_ids_for_members` for deep expansion.
- Uses `_hydrate_songs` to attach all metadata.

### get_identity(identity_id: int) -> Optional[Identity]
Fetch a single Identity and all its aliases/members/groups by ID.
- Accesses `IdentityRepository.get_by_id`.
- Uses `_hydrate_identities` for tree expansion.

### get_all_identities() -> List[Identity]
Fetch a list of all active identities.

### search_identities(query: str) -> List[Identity]
Search for identities by name or alias.

### get_songs_by_identity(identity_id: int) -> List[Song]
Reverse Credit lookup: Given a seed identity_id, find all related IDs (its aliases + members/groups) and return all songs where any of those IDs are credited.

### get_all_publishers() -> List[Publisher]
Fetch the full directory of publishers with resolved hierarchy chains.

### get_all_albums() -> List[Album]
Fetch the full directory of albums with hydrated publishers, credits, and songs.

### search_publishers(query: str) -> List[Publisher]
Search for publishers by name match with resolved hierarchy chains.

### search_albums(query: str) -> List[Album]
Search albums by title with hydrated publishers, credits, and songs.

### get_publisher(publisher_id: int) -> Optional[Publisher]
Fetch a single publisher by ID and resolve its full hierarchy and sub-publishers.

### get_album(album_id: int) -> Optional[Album]
Fetch a single album by ID and hydrate its publishers, credits, and songs.

### get_publisher_songs(publisher_id: int) -> List[Song]
Fetch the full song repertoire (Master rights) for a given publisher.

### check_ingestion(file_path: str) -> Dict[str, Any]
Performs a multi-tiered collision check for a new file.
1.  **Path check**: Checks `SongRepository.get_by_path`.
2.  **Hash check**: Calculates and checks `SongRepository.get_by_hash`.
3.  **Metadata check**: Extracts tags and checks `SongRepository.find_by_metadata` (Titles, Artist Set, Year).
Returns status (NEW, ALREADY_EXISTS, ERROR) and match details.


### _hydrate_songs(songs: List[Song], pre_albums: Optional[Dict[int, List[SongAlbum]]] = None) -> List[Song]
**Internal**: Centralized batch hydration for all song metadata.
- Fetches credits from `SongCreditRepository`.
- Fetches album context from `SongAlbumRepository` (unless `pre_albums` is provided).
- Resolves publisher objects via `PublisherRepository`.
- Locally orchestrates/groups the records by SourceID.
- Stitches them back to the Songs creating `SongAlbum` bridge objects with resolved metadata and returns the hydrated list.

### _hydrate_publishers(pubs: List[Publisher]) -> List[Publisher]
**Internal**: Batch-resolves the full parent hierarchy chains for any list of publishers.
1. Performs a single batch fetch for all ancestors using a recursive CTE via `PublisherRepository.get_hierarchy_batch`.
2. Attaches parent names to each entry locally.

### _hydrate_albums(albums: List[Album]) -> List[Album]
**Internal**: Centralized batch hydration for album directory models.
- Fetches album-level publishers from `PublisherRepository`.
- Fetches album credits from `AlbumCreditRepository`.
- Resolves linked songs via `AlbumRepository.get_song_ids_by_album` and `SongRepository.get_by_ids`.
- Reuses `_hydrate_songs` so album track lists carry the same song metadata as the rest of the app.

### _hydrate_identities(identities: List[Identity]) -> List[Identity]
**Internal**: Batch-resolves the "Universal Tree" for a list of identities (Aliases, Members, Groups).
1. Collects all unique owner IDs.
2. Batch fetches aliases and memberships.
3. Hydrates the view model trees.

### _get_credits_by_song(song_ids: List[int]) -> Dict[int, List[SongCredit]]
**Internal**: Fetches and groups credits by song ID.

### _get_publishers_by_song(song_ids: List[int]) -> Dict[int, List[Publisher]]
**Internal**: Fetches and groups master recording publishers by song ID.

### _get_tags_by_song(song_ids: List[int]) -> Dict[int, List[Tag]]
**Internal**: Fetches and groups tags by song ID.

### _get_albums_by_song(song_ids: List[int]) -> Dict[int, List[SongAlbum]]
**Internal**: Fetches album associations, resolves publishers, and groups by song ID.

### _get_publishers_by_album(album_ids: List[int]) -> Dict[int, List[Publisher]]
**Internal**: Batch-fetch and hydrate publishers for albums.

### _get_album_credits_by_album(album_ids: List[int]) -> Dict[int, List[AlbumCredit]]
**Internal**: Batch-fetch album credits grouped by album ID.

### _get_songs_by_album(album_ids: List[int]) -> Dict[int, List[Song]]
**Internal**: RESOLVER: Fetches and hydrates all songs for multiple albums in a single BATCH flow to prevent the N+1 trap.
- Fetches track mappings via `SongAlbumRepository.get_albums_for_songs_reverse`.
- Pre-seeds hydration with album links to avoid redundant SQL queries.
- Batch hydration for ALL songs in the set.
- Re-groups by AlbumID in memory.

### _batch_group_by_id(items: List[Any], id_attr: str) -> Dict[int, List[Any]]
**Internal**: Generic utility to group a list of objects by a specific attribute ID into a dictionary.

### _resolve_publisher_associations(raw_assocs: List[tuple], entity_label: str) -> Dict[int, List[Publisher]]
**Internal**: Shared logic to hydrate and group publisher entities for any source type (Songs or Albums).

---

## Logger
*Location: `src/services/logger.py`*
**Responsibility**: Simple console logging for the application.

### debug(msg: str)
Logs a debug-level message.

### info(msg: str)
Logs an info-level message.

### warning(msg: str)
Logs a warning-level message.

### error(msg: str)
Logs an error-level message.

### critical(msg: str)
Logs a critical-level message.

### _log(level: str, msg: str)
**Internal**: Helper to format and send messages to stdout.

### _get_file(self) -> Optional[TextIO]
**Internal**: Lazy file handle acquisition with stderr fallback on failure.
---

## MetadataService
*Location: `src/services/metadata_service.py`*
**Responsibility**: Extracts high-fidelity metadata (tags) from physical audio files using a dynamic JSON-driven mapping.

### extract_metadata(file_path: str) -> Dict[str, List[str]]
Reads a file and returns a raw dictionary of all found tags, preserving Frame IDs (e.g., `TPE1`, `TXXX:STATUS`).
- **Entry**: Logs `file_path`.
- **Instrumentation**: Skips binary frames (APIC, GEOB, PRIV).
- **Exit**: Logs the count of tags found.

### _read_tags(tags: Any) -> Dict[str, List[str]]
**Internal**: Extracts and cleans tags from mutagen objects. Handles multi-value delimiters (`\u0000`, `|||`, ` / `).
- **Entry**: Logs starting of extraction.
- **Exit**: Logs count of frames extracted.

---

## MetadataParser
*Location: `src/services/metadata_parser.py`*
**Responsibility**: Maps raw dictionaries of ID3 tags into structured `Song` domain models using `json/id3_frames.json`.

### parse(raw_metadata: Dict[str, List[str]], file_path: str) -> Song
Translates raw frame IDs (TPE1, TIT2) into domain fields, credits, and tags.
- **Entry**: Logs `file_path`.
- **Exit**: Logs counts of credits and tags created.
- **Wisdom**: Implements a **Strict Data Contract**. Does not guess missing fields (no Composer->Artist or Mood->Genre fallbacks).
- **Sub-tags**: Resolves frames by exact ID (e.g., TXXX:STATUS). Does not borrow configuration from base frames (TXXX) to prevent mis-mapping.
- **Deduplication**: Handles "Frame Doubling" (e.g. merging TIPL and TPE1 into unique credits).

### _load_config(json_path: str) -> Dict[str, Any]
**Internal**: Loads the frame mapping configuration from JSON. Uses `utf-8-sig` to ignore Windows BOMs.

### _to_int(val: Any) -> Optional[int]
**Internal**: Safely converts string values (e.g. "2024 (Remaster)") into clean integers by stripping non-digit characters.

### _get_role_name(field: str) -> str
**Internal**: Maps internal JSON field names like `artist` or `producers` to clean UI role names like `Performer` or `Producer`.

---

## AuditService
*Location: `src/services/audit_service.py`*
**Responsibility**: Orchestrates audit history logs and snapshots.

### get_history(record_id: int, table: str) -> List[Dict[str, Any]]
Retrieves a unified timeline of actions and changes for a record.
Merges `ActionLog` and `ChangeLog` entries, sorted by timestamp.
Includes `DeletedRecords` lifecycles if available.
Returns a list of dictionaries with `timestamp`, `type`, `label`, `details`, `user`, and `batch`.
