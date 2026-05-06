# Services Layer

*Location: `src/services/`*

**Responsibility**: Stateless orchestrators containing the business logic.

---

## FilenameParser
*Location: `src/services/filename_parser.py`*

### parse_with_pattern(filename: str, pattern: str) -> Dict[str, str]
Parses the filename (stem) using tokens like {Artist}, {Title}, and {Ignore}.
- **Greedy**: The final token captures all remaining text.
- **Sanitized**: Discards {Ignore} segments and strips whitespace from results.
- **Identity Result**: Returns an empty dict if the pattern does not fully explain the stem.

---

## IdentityService
*Location: `src/services/identity_service.py`*

### get_identity(identity_id: int) -> Optional[Identity]
Fetch a single Identity and all its aliases/members/groups by ID.

### get_all_identities() -> List[Identity]
Fetch a list of all active identities.

### resolve_identity_by_name(display_name: str) -> Optional[int]
Return the IdentityID for an ArtistName (Truth-First resolution).

### add_identity_alias(identity_id: int, display_name: str, name_id: Optional[int] = None) -> int
Link a new or existing alias name to an identity (Truth-First mapping).

### remove_identity_alias(name_id: int) -> None
Remove an alias from an identity. Raises ValueError if it is the primary name.

### update_identity_legal_name(identity_id: int, legal_name: Optional[str]) -> None
Update the LegalName on an Identity.

### search_identities(query: str) -> List[Identity]
Search for identities by name or alias.

### get_identity_song_counts(identity_ids: List[int]) -> dict
Batch active song counts for identities (across all aliases). Returns {id: N}.

### merge_identity_into(source_name_id: int, target_name_id: int) -> None
Merges a solo identity into an existing one.

### set_identity_type(identity_id: int, type_: str) -> None
Convert an identity between person and group.

### add_identity_member(group_id: int, member_id: int) -> None
Add a person identity as a member of a group.

### remove_identity_member(group_id: int, member_id: int) -> None
Remove a member from a group. Noop if not linked.

### delete_unlinked_identities(identity_ids: List[int]) -> int
Soft-delete identities that have zero active songs/albums across ALL aliases.

## IngestionService
*Location: `src/services/ingestion_service.py`*

### get_session_status() -> Dict[str, int]
Returns the current session-wide ingestion counters: `{pending, success, action}`. Derived from class-level `_active_tasks`, `_session_success`, `_session_action`.

### register_task(task_id: str, total: int) -> None
Register a new ingestion batch task in `_active_tasks`. Call before streaming begins.

### reset_session_status() -> None  *(classmethod)*
Reset `_session_success` and `_session_action` to zero. Does not clear active tasks.

### check_ingestion(file_path: str) -> Dict[str, Any]
Performs a multi-tiered collision check for a new file (Path, Hash, Metadata).

### ingest_file(staged_path: str) -> Dict[str, Any]
Primary write path for staged files. Atomic record insertion with duplication safety.

### ingest_wav_as_converting(staged_path: str) -> Dict[str, Any]
Ingest a WAV file immediately with `processing_status=3` (Converting).

### finalize_wav_conversion(song_id: int, mp3_path: str) -> int
Update a status-3 record with the final MP3 path and hash post-conversion. Handles ghost reactivation.

### resolve_conflict(ghost_id: int, staged_path: str) -> Dict[str, Any]
Resolve a 409 conflict by reactivating a soft-deleted record with new file data.

### ingest_batch(file_paths: List[str], max_workers: int = 10) -> Dict[str, Any]
Parallel ingestion of multiple staged files. Each file has its own transaction.

### ingest_single(file_path: str, original_path: Optional[str] = None) -> Dict[str, Any]
Thread-safe single-file ingestion wrapper around `ingest_file`. Catches `ReingestionConflictError` and returns it as a `CONFLICT` dict instead of raising.

### enrich_metadata(song_id: int, conn: sqlite3.Connection) -> None
Internal post-insert metadata enrichment hook (currently simulated).

### scan_folder(folder_path: str, recursive: bool = True) -> List[str]
Scan a directory for supported audio formats. Pure discovery path.

---

## LibraryService
*Location: `src/services/library_service.py`*

### get_song(song_id: int) -> Optional[Song]
Fetch a single song and all its credits by ID.

### get_all_publishers() -> List[Publisher]
Fetch the full directory of publishers with resolved hierarchy chains.

### get_all_albums() -> List[Album]
Fetch the full directory of albums with hydrated publishers, credits, and songs.

### hydrate_songs(songs: List[Song], pre_albums: Optional[Dict[int, List[SongAlbum]]] = None) -> List[Song]
Centralized batch hydration for songs and their relations (Credits, Albums, Publishers, Tags, Staging Origins). Handles Desired State Sync (physical organization).

### search_albums_slim(query: str) -> List[dict]
Slim list-view album search. No tracklist hydration.

### get_album(album_id: int) -> Optional[Album]
Fetch a single album and all its tracks/credits by ID.

### search_publishers(query: str) -> List[Publisher]
Search publishers by name (base layer).

### get_publisher(publisher_id: int) -> Optional[Publisher]
Fetch a single publisher by ID and resolve its full ancestry.


### get_songs_slim_by_publisher(publisher_id: int) -> List[dict]
Fetch slim list-view rows for all songs linked to a publisher.

### get_all_tags() -> List[Tag]
Fetch the full directory of tags.

### get_tag_categories() -> List[str]
Fetch all distinct tag categories.

### search_tags(query: str) -> List[Tag]
Search tags by name match.

### get_tag(tag_id: int) -> Optional[Tag]
Fetch a single tag by ID.


### get_songs_slim_by_tag(tag_id: int) -> List[dict]
Fetch slim list-view rows for all songs linked to a tag.


### get_songs_slim_by_identity(identity_id: int) -> List[dict]
Slim reverse credit lookup — resolves aliases/members/groups, returns slim rows.

### get_filter_values() -> dict
Returns all distinct filter sidebar values.

### filter_songs_slim(artists, contributors, years, decades, genres, albums, publishers, statuses, tags, live_only, mode) -> List[dict]
Filter songs by sidebar criteria. Returns slim list-view rows.

### search_songs_slim(query: str) -> List[dict]
Slim list-view search. Returns raw dicts for SongSlimView — no hydration.

### search_songs_deep_slim(query: str) -> List[dict]
Deep slim search. Base matches + identity/publisher expansion, no hydration.

---

## CatalogService
*Location: `src/services/catalog_service.py`*
**Responsibility**: The primary facade for all read operations and legacy/specialized write paths.

### get_song(song_id: int) -> Optional[Song]
### get_album(album_id: int) -> Optional[Album]
### get_publisher(publisher_id: int) -> Optional[Publisher]
### get_tag(tag_id: int) -> Optional[Tag]
### get_identity(identity_id: int) -> Optional[Identity]

### search_songs_slim(query: str) -> List[dict]
### search_songs_deep_slim(query: str) -> List[dict]
### search_albums_slim(query: str) -> List[dict]
### search_publishers(query: str) -> List[Publisher]
### search_tags(query: str) -> List[Tag]
### search_identities(query: str) -> List[Identity]

### get_all_publishers() -> List[Publisher]
### get_all_albums() -> List[Album]
### get_all_tags() -> List[Tag]
### get_all_identities() -> List[Identity]
### get_all_roles() -> List[str]

### filter_songs_slim(...) -> List[dict]
### get_filter_values() -> dict
### get_tag_categories() -> List[str]
### get_id3_frames_config() -> Dict[str, Any]

### ingest_file(staged_path: str) -> Dict[str, Any]
### ingest_batch(file_paths: List[str]) -> Dict[str, Any]
### ingest_single(file_path: str) -> Dict[str, Any]
### scan_folder(folder_path: str, recursive: bool) -> List[str]
### check_ingestion(file_path: str) -> Dict[str, Any]
### ingest_wav_as_converting(...) -> Dict[str, Any]
### finalize_wav_conversion(...) -> int
### resolve_conflict(...) -> Dict[str, Any]

### sync_id3_if_enabled(song_id: int) -> None
### move_song_to_library(song_id: int) -> str
### delete_song(song_id: int) -> bool
### delete_original_source(song_id: int) -> bool
### get_staging_origin(song_id: int) -> Optional[str]

### update_song_scalars(song_id: int, fields: dict)
### add_song_credit(song_id: int, display_name: str, role_name: str)
### remove_song_credit(song_id: int, credit_id: int)
### update_credit_name(name_id: int, new_name: str)
### add_song_album(song_id: int, album_id: int)
### remove_song_album(song_id: int, album_id: int)
### update_song_album_link(song_id: int, album_id: int, ...)
### update_album(album_id: int, album_data: dict)
### add_song_tag(song_id: int, tag_name: str)
### remove_song_tag(song_id: int, tag_id: int)
### update_tag(tag_id: int, new_name: str, new_category: str)
### set_primary_song_tag(song_id: int, tag_id: int)
### add_song_publisher(song_id: int, publisher_name: str)
### remove_song_publisher(song_id: int, publisher_id: int)
### update_publisher(publisher_id: int, new_name: str)
### set_publisher_parent(publisher_id: int, parent_id: int)
### add_album_credit(album_id: int, display_name: str)
### remove_album_credit(album_id: int, artist_name_id: int)
### add_album_publisher(album_id: int, publisher_name: str)
### remove_album_publisher(album_id: int, publisher_id: int)
### merge_identity_into(source_name_id: int, target_name_id: int)
### set_identity_type(identity_id: int, type_: str)
### add_identity_member(group_id: int, member_id: int)
### remove_identity_member(group_id: int, member_id: int)
### delete_unlinked_albums(album_ids: list)
### delete_unlinked_publishers(publisher_ids: list)
### delete_unlinked_identities(identity_ids: list)
### delete_unlinked_tags(tag_ids: list)
### import_credits_bulk(song_id: int, credits: list, publishers: list)
### quick_create_album_for_song(song_id: int, title: str)
### format_entity_field(field: str, value: str, format_type: str)
### enrich_metadata(song_id: int, conn: sqlite3.Connection)
### publisher_exists(name: str) -> bool
### resolve_identity_by_name(name: str) -> Optional[int]
### get_publisher_link_counts(publisher_ids: List[int]) -> dict
### get_identity_song_counts(identity_ids: List[int]) -> dict
### get_songs_slim_by_publisher(publisher_id: int) -> List[dict]
### get_songs_slim_by_tag(tag_id: int) -> List[dict]
### get_songs_slim_by_identity(identity_id: int) -> List[dict]
### add_identity_alias(identity_id: int, display_name: str, name_id: Optional[int]) -> int
### update_identity_legal_name(identity_id: int, legal_name: Optional[str])
### remove_identity_alias(name_id: int)
### create_and_link_album(song_id: int, album_data: dict)

---

## EditService
*Location: `src/services/edit_service.py`*
**Responsibility**: Specialized orchestrator for metadata modifications. Legacy layer being replaced by `MutationCoordinator`.

### update_song_scalars(song_id: int, fields: dict)
### add_song_credit(song_id: int, display_name: str, role_name: str)
### remove_song_credit(song_id: int, credit_id: int)
### update_credit_name(name_id: int, new_name: str)
### add_song_album(song_id: int, album_id: int)
### create_and_link_album(song_id: int, album_data: dict)
### remove_song_album(song_id: int, album_id: int)
### update_song_album_link(song_id: int, album_id: int, ...)
### update_album(album_id: int, album_data: dict)
### add_album_credit(album_id: int, display_name: str)
### remove_album_credit(album_id: int, artist_name_id: int)
### add_album_publisher(album_id: int, publisher_name: str)
### remove_album_publisher(album_id: int, publisher_id: int)
### sync_album_with_song(album_id: int, song_id: int)
### quick_create_album_for_song(song_id: int, title: str)
### add_song_tag(song_id: int, tag_name: str)
### remove_song_tag(song_id: int, tag_id: int)
### update_tag(tag_id: int, new_name: str, new_category: str)
### set_primary_song_tag(song_id: int, tag_id: int)
### add_song_publisher(song_id: int, publisher_name: str)
### remove_song_publisher(song_id: int, publisher_id: int)
### update_publisher(publisher_id: int, new_name: str)
### set_publisher_parent(publisher_id: int, parent_id: int)
### import_credits_bulk(song_id: int, credits: list, publishers: list)
### format_entity_field(field: str, value: str, format_type: str)
### delete_song(song_id: int)
### move_song_to_library(song_id: int)
### delete_unlinked_albums(album_ids: list)
### delete_unlinked_publishers(publisher_ids: list)
### delete_unlinked_tags(tag_ids: list)
### sync_id3_if_enabled(song_id: int)
### delete_original_source(song_id: int)

---

## MutationCoordinator
*Location: `src/services/mutation_coordinator.py`*

**Responsibility**: The high-level orchestrator for all database write operations. It coordinates multiple mutators and ensures atomicity across DB writes and physical file operations.

### apply(body: MutationRequest) -> dict
The single entry point for all mutations (Add, Remove, Update, Delete).
- Coordinates `SongMutator`, `CreditMutator`, `TagMutator`, `PublisherMutator`, `AlbumMutator`, and `DeleteMutator`.
- Ensures atomic transactions: if any mutation fails, the entire batch is rolled back.
- Triggers physical file move/renaming via `FilingService` and ID3 writing via `MetadataWriter` for any touched songs.
- Returns the updated song views and a list of warnings.

---

## SongMutator
*Location: `src/services/mutators/song_mutator.py`*
**Responsibility**: Handles scalar updates for the `Songs` and `MediaSources` tables.

### apply_within(action: str, item: UpdateSongItem, conn: sqlite3.Connection) -> None
Performs the low-level SQL update within an existing transaction.

---

## CreditMutator
*Location: `src/services/mutators/credit_mutator.py`*
**Responsibility**: Handles adding and removing artist credits.

### apply_within(action: str, item: MutationItem, conn: sqlite3.Connection) -> None
Performs the low-level SQL operations for credit links.

---

## TagMutator
*Location: `src/services/mutators/tag_mutator.py`*
**Responsibility**: Handles adding, removing, and updating metadata tags.

### apply_within(action: str, item: MutationItem, conn: sqlite3.Connection) -> None
Performs the low-level SQL operations for tag links and tag records.

---

## PublisherMutator
*Location: `src/services/mutators/publisher_mutator.py`*
**Responsibility**: Handles adding, removing, and updating publisher links.

### apply_within(action: str, item: MutationItem, conn: sqlite3.Connection) -> None
Performs the low-level SQL operations for publisher links and publisher records.

---

## AlbumMutator
*Location: `src/services/mutators/album_mutator.py`*
**Responsibility**: Handles adding, removing, and updating album links.

### apply_within(action: str, item: MutationItem, conn: sqlite3.Connection) -> None
Performs the low-level SQL operations for album links and album records.

---

## DeleteMutator
*Location: `src/services/mutators/delete_mutator.py`*
**Responsibility**: Handles soft-deletion of songs, albums, identities, and tags.

### apply_within(action: str, item: MutationItem, conn: sqlite3.Connection) -> None
Performs the low-level SQL soft-delete operations.


---

## CasingService
*Location: `src/services/casing_service.py`*

### to_title_case(text: str) -> str
Converts text to Title Case (Every word capitalized, no exclusions).

### to_sentence_case(text: str) -> str
Converts text to Sentence Case (First letter capitalized, the rest lowercase).

---

---

---

## FilingService
*Location: `src/services/filing_service.py`*

### evaluate_routing(song: Song) -> Path
Calculates the target relative path based on rules.

### copy_to_library(song: Song, library_root: Path) -> Path
Copies physical file to library. Handles same-file bypass logic.

### write_id3_if_needed(song: Song, writer: MetadataWriter) -> List[str]
Writes current DB state to the physical ID3 tags if they differ. Returns a list of warnings.

### delete_staging_file(file_path: str) -> bool
Physically deletes a file from the staging area.

### delete_physical_file(file_path: str) -> bool
Physically deletes a file from the library.

### copy_if_needed(src: Path, dst: Path) -> None
Copies file if destination doesn't exist or is different.

---

## MetadataService
*Location: `src/services/metadata_service.py`*

### extract_metadata(file_path: str) -> Dict[str, List[str]]
Extracts raw tags from audio files via Mutagen.

### compare_songs(db_song: Song, file_song: Song) -> dict
Compares two Song objects field by field.
Returns a diff dict: `{key: {"db": db_val, "file": file_val}, ...}`.
Empty dict means in sync. Keys align with frontend chip/scalar identifiers (media_name, year, bpm, isrc, notes, credit:{Role}, tag:{Cat}, publisher, album).

---

## MetadataWriter
*Location: `src/services/metadata_writer.py`*

**Responsibility**: Stateless service that writes a Song domain object back to physical ID3 tags. DB is always source of truth; ID3 is a "backup save".

### write_metadata(song: Song) -> None
Writes current Song state to the file at `song.source_path`.
- Skips non-.mp3 files silently. Raises `FileNotFoundError` if the file is missing.
- Opens existing ID3 or creates a new container — **preserves non-owned frames** (APIC, TXXX from other tools, etc.).
- Scalar fields (`media_name`, `year`, `bpm`, `isrc`) written via `field_to_tag` config map.
- Credits written by role via `role_to_tag` map (Performer→TPE1, Composer→TCOM, etc.); unmapped roles fall back to `TXXX:RoleName`.
- Tags written by category via `category_to_tag` map (Genre→TCON, Mood→TMOO, etc.); unmapped categories fall back to `TXXX:CategoryName`.
- Only first album is written (TALB, TRCK, TPOS, TPE2).
- Duplicate names within a role/category are deduplicated before writing.
- Saves as ID3v2.4 (`v2_version=4`), converting any v2.3 aliases via `update_to_v24()`.

---

## MetadataParser
*Location: `src/services/metadata_parser.py`*

### parse(raw_metadata: Dict[str, List[str]], file_path: str) -> Song
Translates raw tags into a Song object using the frame map.

---

## SearchService
*Location: `src/services/search_service.py`*

### get_search_url(song: Song, engine: str = "spotify") -> str
Builds a search URL.

---

## SpotifyService
*Location: `src/services/spotify_service.py`*

### parse_credits(raw_text: str, reference_title: str, known_roles: list[str]) -> SpotifyParseResult
Heuristic parser for Spotify credit blocks.
- **Role Expansion**: Automatically expands "Writer" into ["Composer", "Lyricist"].
- **Deduplication**: Ensures unique (Name, Role) pairs in the result.

---

## Tokenizer
*Location: `src/services/tokenizer.py`*

### tokenize_credits(text: str, separators: List[str]) -> List[dict]
Splits a raw credit string into alternating name/separator tokens.

### resolve_names(tokens: List[dict]) -> List[str]
Collapses tokens into resolved name strings.

---

## MetadataFramesReader
*Location: `src/services/metadata_frames_reader.py`*

### load_id3_frames(path: str = "json/id3_frames.json") -> ID3FrameMapping
The single source of truth for ID3 frame mapping.

### load_tag_categories(path: str = "json/id3_frames.json") -> List[str]
Returns the live registry of known user-defined tag categories from `id3_frames.json`.

### register_tag_category(category: str, path: str = "json/id3_frames.json") -> None
Adds a category to the registry if not already present. Clears the lru_cache.

### unregister_tag_category(category: str, path: str = "json/id3_frames.json") -> None
Removes a category from the registry. Clears the lru_cache.

---

## Logger
*Location: `src/services/logger.py`*

### debug(msg: str)
### info(msg: str)
### warning(msg: str)
### error(msg: str)
### critical(msg: str)

---

## Converter
*Location: `src/services/converter.py`*

### convert_to_mp3(src_path: Path) -> Path
Converts a WAV file to MP3 using FFmpeg.
