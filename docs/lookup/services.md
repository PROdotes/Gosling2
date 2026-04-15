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

### search_albums_slim(query: str) -> List[dict]
Slim list-view album search. No tracklist hydration.

### get_album(album_id: int) -> Optional[Album]
Fetch a single album and all its tracks/credits by ID.

### search_publishers(query: str) -> List[Publisher]
Search publishers by name (base layer).

### get_publisher(publisher_id: int) -> Optional[Publisher]
Fetch a single publisher by ID and resolve its full ancestry.

### get_songs_by_publisher(publisher_id: int) -> List[Song]
Fetch the full repertoire associated with a given publisher.

### get_all_tags() -> List[Tag]
Fetch the full directory of tags.

### get_tag_categories() -> List[str]
Fetch all distinct tag categories.

### search_tags(query: str) -> List[Tag]
Search tags by name match.

### get_tag(tag_id: int) -> Optional[Tag]
Fetch a single tag by ID.

### get_songs_by_tag(tag_id: int) -> List[Song]
Fetch the full hydrated song repertoire linked to a specific tag.

### get_songs_by_identity(identity_id: int) -> List[Song]
Reverse Credit lookup starting from a seed identity.

### get_filter_values() -> dict
Returns all distinct filter sidebar values.

### filter_songs_slim(artists, contributors, years, decades, genres, albums, publishers, statuses, tags, live_only, mode) -> List[dict]
Filter songs by sidebar criteria. Returns slim list-view rows.

### search_songs_slim(query: str) -> List[dict]
Slim list-view search. Returns raw dicts for SongSlimView — no hydration.

### search_songs_deep_slim(query: str) -> List[dict]
Deep slim search. Base matches + identity/publisher expansion, no hydration.

---

## EditService
*Location: `src/services/edit_service.py`*

### update_song_scalars(song_id: int, fields: Dict[str, Any]) -> None
Partial update of core song metadata with validation.

### add_song_credit(song_id: int, display_name: str, role_name: str, identity_id: Optional[int] = None) -> SongCredit
Add a credited artist to a song.

### remove_song_credit(song_id: int, credit_id: int) -> None
Remove a credit link from a song.

### update_credit_name(name_id: int, new_name: str) -> None
Globally update an ArtistName.

### add_song_album(song_id: int, album_id: int, track_number: int, disc_number: int) -> SongAlbum
Link a song to an existing album.

### remove_song_album(song_id: int, album_id: int) -> None
Unlink a song from an album.

### update_song_album_link(song_id: int, album_id: int, track_number: int, disc_number: int) -> None
Update track metadata for a song-album association.

### create_and_link_album(song_id: int, album_data: dict, track_number: int, disc_number: int) -> SongAlbum
Atomic: Create and link album.

### update_album(album_id: int, album_data: dict) -> Album
Update album metadata.

### add_album_credit(album_id: int, display_name: str, role_name: str, identity_id: Optional[int] = None) -> int
Add a credit to an album.

### remove_album_credit(album_id: int, name_id: int) -> None
Remove a credit from an album.

### add_album_publisher(album_id: int, publisher_name: str, publisher_id: Optional[int] = None) -> Publisher
Add publisher to an album.

### remove_album_publisher(album_id: int, publisher_id: int) -> None
Remove publisher from an album.

### add_song_tag(song_id: int, tag_name: str, category: str, tag_id: Optional[int] = None) -> Tag
Add a tag to a song.

### remove_song_tag(song_id: int, tag_id: int) -> None
Remove a tag from a song.

### update_tag(tag_id: int, name: str, category: str) -> None
Global tag update.

### set_primary_song_tag(song_id: int, tag_id: int) -> Tag
Promote a specific genre tag to primary status for a song.

### add_song_publisher(song_id: int, publisher_name: str, publisher_id: Optional[int] = None) -> Publisher
Link a master publisher to a song.

### remove_song_publisher(song_id: int, publisher_id: int) -> None
Remove song publisher link.

### update_publisher(publisher_id: int, name: str) -> None
Global publisher update.

### set_publisher_parent(publisher_id: int, parent_id: Optional[int]) -> None
Set or clear the parent of a publisher.

### import_credits_bulk(song_id: int, credits: List[SpotifyCredit], publishers: List[str]) -> None
Atomic import of Spotify credits and publishers.

### format_entity_field(entity_type: str, entity_id: int, field: str, format_type: str) -> Any
Standardizes the casing of an entity's metadata field.

### delete_song(song_id: int) -> bool
Soft-delete a single song. Handles physical cleanup if in staging.

### move_song_to_library(song_id: int) -> str
Calculates the target routing, moves the physical file, and updates the database records.

### delete_unlinked_tags(tag_ids: List[int]) -> int
Soft-delete tags from the given list that have zero active song links.

### delete_unlinked_albums(album_ids: List[int]) -> int
Soft-delete albums from the given list that have zero active song links.

### delete_unlinked_publishers(publisher_ids: List[int]) -> int
Soft-delete publishers from the given list that have zero active songs AND zero active albums.

---

## CatalogService
*Location: `src/services/catalog_service.py`*
**Responsibility**: Entry point for song access. Stateless orchestrator that combines data from multiple repositories into complete Domain Models.

### check_ingestion(file_path: str) -> Dict[str, Any]
(-> `IngestionService.check_ingestion`)


### ingest_file(staged_path: str) -> Dict[str, Any]
(-> `IngestionService.ingest_file`)


### scan_folder(folder_path: str, recursive: bool = True) -> List[str]
(-> `IngestionService.scan_folder`)


### ingest_batch(file_paths: List[str], max_workers: int = 10) -> Dict[str, Any]
(-> `IngestionService.ingest_batch`)


### delete_song(song_id: int) -> bool
Soft-delete a single song by SourceID. Handles physical cleanup if in staging.

### get_filter_values() -> dict
(-> `LibraryService.get_filter_values`)


### filter_songs_slim(artists, contributors, years, decades, genres, albums, publishers, statuses, tags, live_only, mode) -> List[dict]
Filter songs by sidebar criteria. Returns slim list-view rows.
(-> `LibraryService.filter_songs_slim`)


### ingest_wav_as_converting(staged_path: str) -> Dict[str, Any]
(-> `IngestionService.ingest_wav_as_converting`)


### finalize_wav_conversion(song_id: int, mp3_path: str) -> int
(-> `IngestionService.finalize_wav_conversion`)


### resolve_conflict(ghost_id: int, staged_path: str) -> Dict[str, Any]
(-> `IngestionService.resolve_conflict`)



### get_song(song_id: int) -> Optional[Song]
(-> `LibraryService.get_song`)


### get_identity(identity_id: int) -> Optional[Identity]
(-> `IdentityService.get_identity`)

### get_all_identities() -> List[Identity]
(-> `IdentityService.get_all_identities`)

### resolve_identity_by_name(display_name: str) -> Optional[int]
(-> `IdentityService.resolve_identity_by_name`)



### publisher_exists(name: str) -> bool
Returns True if a Publisher with this exact name exists in the DB.

### search_identities(query: str) -> List[Identity]
(-> `IdentityService.search_identities`)


### get_all_publishers() -> List[Publisher]
(-> `LibraryService.get_all_publishers`)


### get_all_albums() -> List[Album]
(-> `LibraryService.get_all_albums`)


### search_songs_slim(query: str) -> List[dict]
(-> `LibraryService.search_songs_slim`)


### search_songs_deep_slim(query: str) -> List[dict]
(-> `LibraryService.search_songs_deep_slim`)


### search_albums_slim(query: str) -> List[dict]
(-> `LibraryService.search_albums_slim`)


### get_album(album_id: int) -> Optional[Album]
(-> `LibraryService.get_album`)


### search_publishers(query: str) -> List[Publisher]
(-> `LibraryService.search_publishers`)


### get_publisher(publisher_id: int) -> Optional[Publisher]
(-> `LibraryService.get_publisher`)


### get_songs_by_publisher(publisher_id: int) -> List[Song]
(-> `LibraryService.get_songs_by_publisher`)


### get_all_tags() -> List[Tag]
(-> `LibraryService.get_all_tags`)


### get_tag_categories() -> List[str]
(-> `LibraryService.get_tag_categories`)


### get_all_roles() -> List[str]
Returns a list of all distinct role names (e.g., Performer, Author, Publisher).

### search_tags(query: str) -> List[Tag]
(-> `LibraryService.search_tags`)


### get_tag(tag_id: int) -> Optional[Tag]
(-> `LibraryService.get_tag`)


### get_songs_by_tag(tag_id: int) -> List[Song]
(-> `LibraryService.get_songs_by_tag`)


### get_songs_by_identity(identity_id: int) -> List[Song]
(-> `LibraryService.get_songs_by_identity`)


### merge_identity_into(source_name_id: int, target_name_id: int) -> None
(-> `IdentityService.merge_identity_into`)


### set_identity_type(identity_id: int, type_: str) -> None
(-> `IdentityService.set_identity_type`)


### add_identity_member(group_id: int, member_id: int) -> None
(-> `IdentityService.add_identity_member`)


### remove_identity_member(group_id: int, member_id: int) -> None
(-> `IdentityService.remove_identity_member`)


### add_identity_alias(identity_id: int, display_name: str, name_id: Optional[int] = None) -> int
(-> `IdentityService.add_identity_alias`)


### remove_identity_alias(name_id: int) -> None
(-> `IdentityService.remove_identity_alias`)


### update_song_scalars(song_id: int, body: Dict[str, Any]) -> None
Partial update of core song metadata.

### add_song_credit(song_id: int, display_name: str, role_name: str, identity_id: Optional[int] = None) -> SongCredit
Add a credited artist to a song.

### remove_song_credit(song_id: int, credit_id: int) -> None
Remove a credit link from a song.

### update_credit_name(name_id: int, new_name: str) -> None
Globally update an ArtistName.

### add_song_album(song_id: int, album_id: int, track_number: int, disc_number: int) -> None
Link a song to an existing album.

### remove_song_album(song_id: int, album_id: int) -> None
Unlink a song from an album.

### update_song_album_link(song_id: int, album_id: int, track_number: int, disc_number: int) -> None
Update track metadata for a song-album association.

### create_and_link_album(song_id: int, title: str, album_type: str, release_year: int, track_number: int, disc_number: int) -> int
Atomic: Create and link album.

### update_album(album_id: int, body: Dict[str, Any]) -> Album
Update album metadata.

### add_album_credit(album_id: int, display_name: str, role_name: str, identity_id: Optional[int] = None) -> int
Add a credit to an album.

### remove_album_credit(album_id: int, name_id: int) -> None
Remove a credit from an album.

### add_album_publisher(album_id: int, publisher_name: str, publisher_id: Optional[int] = None) -> Publisher
Add publisher to an album.

### remove_album_publisher(album_id: int, publisher_id: int) -> None
Remove publisher from an album.

### add_song_tag(song_id: int, tag_name: str, category: str, tag_id: Optional[int] = None) -> Tag
Add a tag to a song. 
- **Auto-Primary**: If category is 'Genre' and the song has no primary genre, the new link is automatically marked as primary.

### remove_song_tag(song_id: int, tag_id: int) -> None
Remove a tag from a song.

### update_tag(tag_id: int, name: str, category: str) -> None
Global tag update.

### delete_unlinked_tags(tag_ids: List[int]) -> int
Soft-delete tags from the given list that have zero active song links. All deletes run in one transaction. Returns count of tags deleted. For single delete pass `[tag_id]` — returns 0 if linked or not found, 1 if deleted.

### delete_unlinked_albums(album_ids: List[int]) -> int
Soft-delete albums from the given list that have zero active song links. Cleans up `AlbumCredits` + `AlbumPublishers` before soft-deleting. Returns count of albums deleted.

### delete_unlinked_publishers(publisher_ids: List[int]) -> int
Soft-delete publishers from the given list that have zero active songs AND zero active albums. Returns count of publishers deleted.

### delete_unlinked_identities(identity_ids: List[int]) -> int
(-> `IdentityService.delete_unlinked_identities`)


### get_publisher_link_counts(publisher_ids: List[int]) -> Dict[int, Dict[str, int]]
Batch fetch link counts (songs and albums) for a list of publishers. Returns `ID -> {"songs": N, "albums": M}`.

### get_identity_song_counts(identity_ids: List[int]) -> Dict[int, int]
(-> `IdentityService.get_identity_song_counts`)


### set_primary_song_tag(song_id: int, tag_id: int) -> Tag
Promote a specific genre tag to primary status for a song. 
- **Strictly for Genres**: Only tags with category 'Genre' (case-insensitive) are allowed.
- **Atomic Reset**: Orchestrates the atomic repository update to ensure only one primary genre exists.

### add_song_publisher(song_id: int, publisher_name: str, publisher_id: Optional[int] = None) -> Publisher
Link a master publisher to a song.

### remove_song_publisher(song_id: int, publisher_id: int) -> None
Remove song publisher link.

### update_publisher(publisher_id: int, name: str) -> None
Global publisher update.

### set_publisher_parent(publisher_id: int, parent_id: Optional[int]) -> None
Set or clear the parent of a publisher.

### import_credits_bulk(song_id: int, credits: List[SpotifyCredit], publishers: List[str]) -> None
Atomic import of Spotify credits and publishers.

### get_id3_frames_config() -> Dict[str, Any]
Returns the consolidated ID3 frame mapping.


### move_song_to_library(song_id: int) -> str
Calculates the target routing, moves the physical file, and updates the database records.

### update_identity_legal_name(identity_id: int, legal_name: Optional[str]) -> None
(-> `IdentityService.update_identity_legal_name`)


### format_entity_field(entity_type: str, entity_id: int, field: str, format_type: str) -> Any
Standardizes the casing of an entity's metadata field (Song/Album) based on "title" or "sentence" format.


---

## CasingService
*Location: `src/services/casing_service.py`*

### to_title_case(text: str) -> str
Converts text to Title Case (Every word capitalized, no exclusions).

### to_sentence_case(text: str) -> str
Converts text to Sentence Case (First letter capitalized, the rest lowercase).

---

## AuditService
*Location: `src/services/audit_service.py`*

### get_history(record_id: int, table: str) -> List[Dict[str, Any]]
Unified timeline of actions and changes for a record.

---

## FilingService
*Location: `src/services/filing_service.py`*

### evaluate_routing(song: Song) -> Path
Calculates the target relative path based on rules.

### copy_to_library(song: Song, library_root: Path) -> Path
Copies physical file to library.

---

## MetadataService
*Location: `src/services/metadata_service.py`*

### extract_metadata(file_path: str) -> Dict[str, List[str]]
Extracts raw tags from audio files via Mutagen.

### compare_songs(db_song: Song, file_song: Song) -> dict
Compares two Song objects field by field.
Returns `{"in_sync": bool, "mismatches": [field_name, ...]}`.
Mismatches are labelled `title`, `year`, `bpm`, `isrc`, `credit:{Role}`, `tag:{Category}`, `publishers`, `album_title`, `track`, `disc`.

### filter_sync_mismatches(db_song: Song, mismatches: list) -> list
Filters raw `compare_songs` mismatches to only those relevant to DB state.
Removes `tag:*` mismatches for categories that exist only in the file (not in the DB).

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
