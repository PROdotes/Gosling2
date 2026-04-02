# Services Layer

*Location: `src/services/`_

**Responsibility**: Stateless orchestrators containing the business logic.

---

## FilenameParser
*Location: `src/services/filename_parser.py`*
**Responsibility**: Compiles user-defined patterns into regular expressions to extract metadata from file stems.

### parse_with_pattern(filename: str, pattern: str) -> Dict[str, str]
Parses the filename (stem) using tokens like {Artist}, {Title}, and {Ignore}.
- **Greedy**: The final token captures all remaining text.
- **Sanitized**: Discards {Ignore} segments and strips whitespace from results.
- **Identity Result**: Returns an empty dict if the pattern does not fully explain the stem.

---



## CatalogService

*Location: `src/services/catalog_service.py`_
**Responsibility**: Entry point for song access. Stateless orchestrator that combines data from multiple repositories into complete Domain Models.

### get_song(song_id: int) -> Optional[Song]

Fetch a single song and all its credits by ID.

- Accesses `SongRepository` to get the core record.
- Uses `_hydrate_songs` to attach all credits, albums, and publishers.

### search_songs_slim(query: str) -> List[dict]
(-> `SongRepository.search_slim`)

### search_songs_deep_slim(query: str) -> List[dict]

Deep slim search. Base matches + identity/publisher expansion, no hydration.

- Logic: `SongRepository.search_slim` (base) + identity expansion + publisher expansion.
- Returns List[dict] with same keys as `search_slim`.

### \_expand_identity_songs(query: str) -> List[Song]

Resolves identities matching the query and expands to all songs from any groups they belong to.

- Logic: `IdentityRepository.search_identities` -> `get_group_ids_for_members` -> `SongRepository.get_by_identity_ids`.

### \_expand_publisher_songs(query: str) -> List[Song]

Resolves publishers matching the query and expands to all songs from that publisher or any of its descendants.

- Logic: `PublisherRepository.search_deep` (Recursive) -> `SongRepository.get_by_publisher_ids`.

### \_search_songs_composed(query: str, initial_songs: List[Song]) -> List[Song]

Orchestrator for Deep Discovery. Merges initial seed matches with Identity and Publisher expansion legs and hydrates the final set.

### get_identity(identity_id: int) -> Optional[Identity]

Fetch a single Identity and all its aliases/members/groups by ID.

- Accesses `IdentityRepository.get_by_id`.
- Uses `_hydrate_identities` for tree expansion.

### get_all_identities() -> List[Identity]

Fetch a list of all active identities.

### credit_name_exists(display_name: str) -> bool

Returns True if an ArtistName with this exact display name exists in the DB. Wraps `SongCreditRepository.find_by_display_name`.

### publisher_exists(name: str) -> bool

Returns True if a Publisher with this exact name exists in the DB. Wraps `PublisherRepository.find_by_name`.

### search_identities(query: str) -> List[Identity]

Search for identities by name or alias.

### get_songs_by_identity(identity_id: int) -> List[Song]

Reverse Credit lookup: Given a seed identity_id, find all related IDs (its aliases + members/groups) and return all songs where any of those IDs are credited.

### get_all_publishers() -> List[Publisher]

Fetch the full directory of publishers with resolved hierarchy chains.

### get_all_albums() -> List[Album]

Fetch the full directory of albums with hydrated publishers, credits, and songs.

- Internally calls `search_albums_slim("")` then hydrates via `_hydrate_albums`.

### search_publishers(query: str) -> List[Publisher]

Search for publishers by name match with resolved hierarchy chains.

### search_albums_slim(query: str) -> List[dict]
(-> `AlbumRepository.search_slim`)

### get_publisher(publisher_id: int) -> Optional[Publisher]

Fetch a single publisher by ID and resolve its full hierarchy and sub-publishers.

### get_album(album_id: int) -> Optional[Album]

Fetch a single album by ID and hydrate its publishers, credits, and songs.

### get_songs_by_publisher(publisher_id: int) -> List[Song]

Fetch the full song repertoire (Master rights) for a given publisher.

### get_all_tags() -> List[Tag]
(-> `TagRepository.get_all`)

### search_tags(query: str) -> List[Tag]

Search for tags by name match.

### get_tag_categories() -> List[str]
(-> `TagRepository.get_categories`)

### get_tag(tag_id: int) -> Optional[Tag]

Fetch a single tag by ID.

### get_songs_by_tag(tag_id: int) -> List[Song]

Fetch the full hydrated song repertoire linked to a specific tag.

### check_ingestion(file_path: str) -> Dict[str, Any]

Performs a multi-tiered collision check for a new file.

1.  **Path check**: Checks `SongRepository.get_by_path`.
2.  **Hash check**: Calculates and checks `SongRepository.get_by_hash`.
3.  **Metadata check**: Extracts tags and checks `SongRepository.find_by_metadata` (Titles, Artist Set, Year).
    Returns status (NEW, ALREADY_EXISTS, ERROR) and match details.

### ingest_file(staged_path: str) -> Dict[str, Any]

Full write-path orchestration for a staged file.

- Performs `check_ingestion`.
- If NEW, try insertion.
- **Reactive Conflict**: Catches `sqlite3.IntegrityError`. If the hash matches a soft-deleted record, raises `ReingestionConflictError` (409) with ghost metadata for the Comparison UI.
- Handles transaction lifecycle (commit/rollback).

### \_hydrate_identities(identities: List[Identity]) -> List[Identity]

Bulk hydrates identities with aliases, members, and groups. Recursively expands 1 level to ensure tree discovery.

### resolve_conflict(conflict_id: str, mode: str) -> Dict[str, Any]

Resolves a pending reingestion conflict.

- Modes: `OVERWRITE` (Soft-Deletes current record, swaps in NEW ID3 tags), `CANCEL` (Drops staging file).
- Logic: `MediaSourceRepository.delete_source` -> `ingest_file`.
- Deletes `staged_path` on failure or active duplicate to prevent orphans.
- **Persistence**: Preserves `staged_path` on `ReingestionConflictError` to allow for later restoration.
- Returns `IngestionReportView` data.

### scan_folder(folder_path: str, recursive: bool = True) -> List[str]

Pure file discovery utility that scans a folder for audio files.

- Returns list of absolute paths to audio files.
- If `recursive=True`, walks entire directory tree.
- If `recursive=False`, only scans top-level directory.
- No staging or ingestion - just file system scanning.
- Uses `ACCEPTED_EXTENSIONS` for filtering.

### ingest_batch(file_paths: List[str], max_workers: int = 10) -> Dict[str, Any]

Parallel batch ingestion of multiple already-staged files.

- Each file gets its own transaction (one failure doesn't block others).
- Uses `ThreadPoolExecutor` for concurrent processing (works in web and desktop apps).
- Each thread gets its own DB connection (thread-safe).
- Reuses existing `ingest_file()` method for each file.
- Returns `BatchIngestReport` with aggregate stats (total_files, ingested, duplicates, errors) and per-file results.

### \_ingest_single(file_path: str) -> Dict[str, Any]

**Internal**: Thread-safe wrapper for single file ingestion.

- Called by `ingest_batch()` worker threads.
- Ensures each thread gets its own database connection.
- Catches exceptions and returns error report instead of crashing thread.

### \_enrich_metadata(song_id: int, conn: sqlite3.Connection) -> None

**Internal**: Metadata enrichment sink. Moves status from Virgin (2) -> Enriched (1).

### update_song_scalars(song_id: int, fields: dict) -> Song

Update editable scalar fields (media_name, year, bpm, isrc, is_active). Validates values per spec rules. Returns the fully hydrated Song. Raises ValueError on validation failure, LookupError if not found.

### get_all_roles() -> List[str]
(-> `SongCreditRepository.get_all_roles`)

### add_song_credit(song_id: int, display_name: str, role_name: str, identity_id: Optional[int] = None) -> SongCredit

Add an artist credit to a song. Get-or-create artist name and role. Supports explicit identity_id for Truth-First linking. Returns the created SongCredit.

### remove_song_credit(song_id: int, credit_id: int) -> None

Remove a credit link from a song by credit_id. Keeps the artist name record.

### update_credit_name(name_id: int, new_name: str) -> None

Update an artist's display name globally (affects all songs linked to that artist).

### add_identity_alias(identity_id: int, display_name: str, name_id: Optional[int] = None) -> int

Link a new or existing alias name to an identity (Truth-First mapping).
- **ID-First**: Prioritizes `name_id` for explicit re-linking. Supports `IdentityID` fallback for search results.
- **Hierarchy Guard**: Re-parenting of a Primary Name is only permitted for **Solo Identities** (0 other active aliases). Raises `ValueError` for parent identities.
- **Null-is-New**: If `name_id` is null, the name MUST be truly new. Raises `ValueError` on string collision with another identity.
- **Audit**: Logs 'IDENTITY_ALIAS_ADD' in ActionLog.

### remove_identity_alias(name_id: int) -> None

Remove an alias mapping.
- Guard: Raises ValueError if trying to delete a Primary Name.
- Audit: Logs 'IDENTITY_ALIAS_REMOVE' in ActionLog.

### add_song_album(song_id: int, album_id: int, track_number: Optional[int], disc_number: Optional[int]) -> SongAlbum

Link an existing album to a song. Returns the SongAlbum link object.

### create_and_link_album(song_id: int, album_data: dict, track_number: Optional[int], disc_number: Optional[int]) -> SongAlbum

Create a new album record and link it to a song in a single transaction. Returns the SongAlbum link object.

### remove_song_album(song_id: int, album_id: int) -> None

Unlink a song from an album. Keeps the album record.

### update_song_album_link(song_id: int, album_id: int, track_number: Optional[int], disc_number: Optional[int]) -> None

Update track/disc numbers for an existing song-album link.

### update_album(album_id: int, album_data: dict) -> Album

Update album record fields (title, year, release_type). Returns the fully hydrated Album. Affects all linked songs globally.

### add_album_credit(album_id: int, display_name: str, role_name: str = "Performer", identity_id: Optional[int] = None) -> int

Add a credited artist to an album. Get-or-create artist name. Returns name_id.

### remove_album_credit(album_id: int, artist_name_id: int) -> None

Remove a credited artist from an album.

### add_album_publisher(album_id: int, publisher_name: Optional[str], publisher_id: Optional[int] = None) -> Publisher

Add a publisher link for an album. Links by ID if publisher_id provided, otherwise get-or-creates by name. Returns the hydrated Publisher. Commits transaction.

### remove_album_publisher(album_id: int, publisher_id: int) -> None

Remove a publisher link from an album.

### add_song_tag(song_id: int, tag_name: Optional[str], category: Optional[str], tag_id: Optional[int] = None) -> Tag

Add a tag to a song. Links by ID if tag_id provided, otherwise get-or-creates by name+category. Returns the Tag object.

### remove_song_tag(song_id: int, tag_id: int) -> None

Remove a tag link from a song. Keeps the tag record.

### update_tag(tag_id: int, new_name: str, new_category: str) -> None

Update tag name/category globally (affects all linked songs).

### move_song_to_library(song_id: int) -> str

Move a song from staging to the organized library.

- Verification: Song must be in 'Reviewed' state (Status 0).
- Copy-Commit-Purge: Copies to organized path, updates DB, then unlinks staging source.
- Returns: New relative path within the library.
- Errors: `ValueError` if not reviewed, `LookupError` if not found.

### add_song_publisher(song_id: int, publisher_name: Optional[str], publisher_id: Optional[int] = None) -> Publisher

Add a publisher link to a song. Links by ID if publisher_id provided, otherwise get-or-creates by name. Returns the Publisher object.

### remove_song_publisher(song_id: int, publisher_id: int) -> None

Remove a publisher link from a song. Keeps the publisher record.

### update_publisher(publisher_id: int, new_name: str) -> None

Update publisher name globally (affects all linked songs).

### set_publisher_parent(publisher_id: int, parent_id: Optional[int]) -> None

Set or clear the parent of a publisher. Pass `None` to clear. Raises `LookupError` if publisher not found.

### import_credits_bulk(song_id: int, credits: List[SpotifyCredit], publishers: List[str]) -> None

Atomically imports a batch of credits and publishers for a song.

- Performs a single transaction write; rolls back on any partial failure.
- Resolves identities and roles globally using existing Repository logic.
- Clears existing credits/publishers before applying the new set (Refresh mode).

### get_id3_frames_config() -> Dict[str, Any]

Returns the consolidated ID3 frame mapping (Single Source of Truth) from the cached parser.

### delete_song(song_id: int) -> bool

Atomic hard-delete of a song and its physical file.

- Removes record from DB via `SongRepository`.
- Commits transaction.
- Deletes physical file only if it resides in `STAGING_DIR`.
- Returns `True` if successfully deleted.

### \_hydrate_songs(songs: List[Song], pre_albums: Optional[Dict[int, List[SongAlbum]]] = None) -> List[Song]

**Internal**: Centralized batch hydration for all song metadata.

- Fetches credits from `SongCreditRepository`.
- Fetches album context from `SongAlbumRepository` (unless `pre_albums` is provided).
- Resolves publisher objects via `PublisherRepository`.
- Locally orchestrates/groups the records by SourceID.
- Stitches them back to the Songs creating `SongAlbum` bridge objects with resolved metadata and returns the hydrated list.

### \_hydrate_publishers(pubs: List[Publisher]) -> List[Publisher]

**Internal**: Batch-resolves the full parent hierarchy chains for any list of publishers.

1. Performs a single batch fetch for all ancestors using a recursive CTE via `PublisherRepository.get_hierarchy_batch`.
2. Attaches parent names to each entry locally.

### \_hydrate_albums(albums: List[Album]) -> List[Album]

**Internal**: Centralized batch hydration for album directory models.

- Fetches album-level publishers from `PublisherRepository`.
- Fetches album credits from `AlbumCreditRepository`.
- Resolves linked songs via `AlbumRepository.get_song_ids_by_album` and `SongRepository.get_by_ids`.
- Reuses `_hydrate_songs` so album track lists carry the same song metadata as the rest of the app.

### \_hydrate_identities(identities: List[Identity]) -> List[Identity]

**Internal**: Batch-resolves the "Universal Tree" for a list of identities (Aliases, Members, Groups).

1. Collects all unique owner IDs.
2. Batch fetches aliases and memberships.
3. Hydrates the view model trees.

### \_get_credits_by_song(song_ids: List[int]) -> Dict[int, List[SongCredit]]

**Internal**: Fetches and groups credits by song ID.

### \_get_publishers_by_song(song_ids: List[int]) -> Dict[int, List[Publisher]]

**Internal**: Fetches and groups master recording publishers by song ID.

### \_get_tags_by_songs(song_ids: List[int]) -> Dict[int, List[Tag]]

**Internal**: Fetches and groups tags by song ID.

### \_get_albums_by_song(song_ids: List[int]) -> Dict[int, List[SongAlbum]]

**Internal**: Fetches album associations, resolves publishers, and groups by song ID.

### \_get_publishers_by_album(album_ids: List[int]) -> Dict[int, List[Publisher]]

**Internal**: Batch-fetch and hydrate publishers for albums.

### \_get_album_credits_by_album(album_ids: List[int]) -> Dict[int, List[AlbumCredit]]

**Internal**: Batch-fetch album credits grouped by album ID.

### \_get_songs_by_album(album_ids: List[int]) -> Dict[int, List[Song]]

**Internal**: RESOLVER: Fetches and hydrates all songs for multiple albums in a single BATCH flow to prevent the N+1 trap.

- Fetches track mappings via `SongAlbumRepository.get_albums_for_songs_reverse`.
- Pre-seeds hydration with album links to avoid redundant SQL queries.
- Batch hydration for ALL songs in the set.
- Re-groups by AlbumID in memory.

### \_batch_group_by_id(items: List[Any], id_attr: str) -> Dict[int, List[Any]]

**Internal**: Generic utility to group a list of objects by a specific attribute ID into a dictionary.

### \_resolve_publisher_associations(raw_assocs: List[tuple], entity_label: str) -> Dict[int, List[Publisher]]

**Internal**: Shared logic to hydrate and group publisher entities for any source type (Songs or Albums).

---

## tokenizer

*Location: `src/services/tokenizer.py`*
**Responsibility**: Stateless string utility for splitting raw credit strings into alternating name/separator tokens.

### tokenize_credits(text: str, separators: List[str]) -> List[dict]

Splits a raw credit string into a list of alternating `name` and `sep` tokens.

- Matches separators longest-first to avoid prefix collisions (e.g. ` feat ` vs ` feat. `).
- Space-padded separators (e.g. ` i `) match only as standalone tokens, not substrings.
- Preserves exact text — no stripping.
- Returns `[]` for empty input. Returns a single name token if no separators match.
- Each token: `{"type": "name"|"sep", "text": str}`

### resolve_names(tokens: List[dict]) -> List[str]

Collapses a token list into resolved name strings based on separator toggle state.

- Sep tokens without `ignore` are split points — a new name starts after them.
- Sep tokens with `ignore: True` are folded into the adjacent name text.
- Returns `[]` for empty input.

---

## MetadataFramesReader

*Location: `src/services/metadata_frames_reader.py`_
**Responsibility**: Single utility for loading and caching the ID3 frame configuration.

### load_id3_frames(path: str = "json/id3_frames.json") -> ID3FrameMapping

The single source of truth for ID3 frame mapping. Loads and validates the JSON configuration once and caches it in memory.

---

## Logger

*Location: `src/services/logger.py`_
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

### \_log(level: str, msg: str)

**Internal**: Helper to format and send messages to stdout.

### \_get_file(self) -> Optional[TextIO]

## **Internal**: Lazy file handle acquisition with stderr fallback on failure.

## MetadataService

*Location: `src/services/metadata_service.py`_
**Responsibility**: Extracts high-fidelity metadata (tags) from physical audio files using a dynamic JSON-driven mapping.

### extract_metadata(file_path: str) -> Dict[str, List[str]]

Reads a file and returns a raw dictionary of all found tags, preserving Frame IDs (e.g., `TPE1`, `TXXX:STATUS`).

- **Entry**: Logs `file_path`.
- **Stream Info**: Injects a virtual `TLEN` frame derived from the audio stream (`audio.info.length`) in **raw seconds** to ensure accurate duration across all file types.
- **Instrumentation**: Skips binary frames (APIC, GEOB, PRIV).
- **Exit**: Logs the count of tags found.

### \_read_tags(tags: Any) -> Dict[str, List[str]]

**Internal**: Extracts and cleans tags from mutagen objects. Handles multi-value delimiters (`\u0000`, `|||`, `/`).

- **Entry**: Logs starting of extraction.
- **Exit**: Logs count of frames extracted.

---

## MetadataParser

*Location: `src/services/metadata_parser.py`_
**Responsibility**: Maps raw dictionaries of ID3 tags into structured `Song` domain models using `json/id3_frames.json`.

### parse(raw_metadata: Dict[str, List[str]], file_path: str) -> Song

Translates raw frame IDs (TPE1, TIT2) into domain fields, credits, and tags.

- **Entry**: Logs `file_path`.
- **Exit**: Logs counts of credits and tags created.
- **Wisdom**: Implements a **Strict Data Contract**. Does not guess missing fields (no Composer->Artist or Mood->Genre fallbacks).
- **Sub-tags**: Resolves frames by exact ID (e.g., TXXX:STATUS). Does not borrow configuration from base frames (TXXX) to prevent mis-mapping.
- **Deduplication**: Handles "Frame Doubling" (e.g. merging TIPL and TPE1 into unique credits).

### \_to_int(val: Any) -> Optional[int]

**Internal**: Safely converts string values (e.g. "2024 (Remaster)") into clean integers by stripping non-digit characters.

### \_get_role_name(field: str) -> str

**Internal**: Maps internal JSON field names like `artist` or `producers` to clean UI role names like `Performer` or `Producer`.

---

## AuditService

*Location: `src/services/audit_service.py`_
**Responsibility**: Orchestrates audit history logs and snapshots.

### get_history(record_id: int, table: str) -> List[Dict[str, Any]]

Retrieves a unified timeline of actions and changes for a record.
Merges `ActionLog` and `ChangeLog` entries, sorted by timestamp.

---

## FilingService

*Location: `src/services/filing_service.py`_
**Responsibility**: Physically move and rename songs within the organized library based on metadata and rules.json.

### FilingService(rules_path: Path)

Constructor.

### evaluate_routing(song: Song) -> Path

Calculates the target relative path for a song based on rules.json. Applies ASCII-only sanitization for the physical filename structure.

### copy_to_library(song: Song, library_root: Path) -> Path

Copies the physical file to the organized library root. Stage 1 of a safe filing transaction.

---

## SearchService

*Location: `src/services/search_service.py`_
**Responsibility**: SearchService generates external search URLs (Spotify, Google) for Song domain models.

### SearchService()

Constructor.

### get_search_url(song: Song, engine: str = "spotify") -> str

Builds a search URL for the given song and engine.

---

## SpotifyService

*Location: `src/services/spotify_service.py`_
**Responsibility**: Stateless text parsing for external credit sources.

### parse_credits(raw_text: str, reference_title: str, known_roles: list[str]) -> SpotifyParseResult

Performs stateless regex-based parsing of raw Spotify credits text.

- Extracts "Performed by", "Written by", and "Produced by" blocks.
- Strips role markers and bullets (•).
- Splits publishers from the "Source" block.
- Validates the parsed title against the provided reference title.
