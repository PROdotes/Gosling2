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

## CatalogService
*Location: `src/services/catalog_service.py`*
**Responsibility**: Entry point for song access. Stateless orchestrator that combines data from multiple repositories into complete Domain Models.

### check_ingestion(file_path: str) -> Dict[str, Any]
Performs a multi-tiered collision check for a new file.
1.  **Path check**: Checks `SongRepository.get_by_path`.
2.  **Hash check**: If no path match, checks `MediaSourceRepository.get_by_hash`.
Returns `{"status": "NEW"|"ALREADY_EXISTS"|"MATCHED_HASH"|"ERROR", "song": Song|None, ...}`.

### ingest_file(staged_path: str) -> Dict[str, Any]
Write path for a staged file. Handles collisions and throws specific errors for Reingestion.

### scan_folder(folder_path: str, recursive: bool = True) -> List[str]
Scan a folder for audio files. Pure file discovery - no staging or ingestion.

### ingest_batch(file_paths: List[str], max_workers: int = 10) -> Dict[str, Any]
Atomic batch ingestion entry point using parallel threads.

### delete_song(song_id: int) -> bool
Soft-delete a single song by SourceID. Handles physical cleanup if in staging.

### resolve_conflict(ghost_id: int, staged_path: str) -> Dict[str, Any]
Resolve a ghost conflict by re-activating the soft-deleted record with new file metadata.


### get_song(song_id: int) -> Optional[Song]
Fetch a single song and all its credits by ID.

### get_identity(identity_id: int) -> Optional[Identity]
Fetch a single Identity and all its aliases/members/groups by ID.

### get_all_identities() -> List[Identity]
Fetch a list of all active identities.

### resolve_identity_by_name(display_name: str) -> Optional[int]
Return the IdentityID for an ArtistName (Truth-First resolution).


### publisher_exists(name: str) -> bool
Returns True if a Publisher with this exact name exists in the DB.

### search_identities(query: str) -> List[Identity]
Search for identities by name or alias.

### get_all_publishers() -> List[Publisher]
Fetch the full directory of publishers with resolved hierarchy chains.

### get_all_albums() -> List[Album]
Fetch the full directory of albums with hydrated publishers, credits, and songs.

### search_songs_slim(query: str) -> List[dict]
(-> `SongRepository.search_slim`)

### search_songs_deep_slim(query: str) -> List[dict]
Deep slim search. Base matches + identity/publisher expansion, no hydration.

### search_albums_slim(query: str) -> List[dict]
(-> `AlbumRepository.search_slim`)

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
(-> `TagRepository.get_categories`)

### get_all_roles() -> List[str]
Returns a list of all distinct role names (e.g., Performer, Author, Publisher).

### search_tags(query: str) -> List[Tag]
Search tags by name match.

### get_tag(tag_id: int) -> Optional[Tag]
Fetch a single tag by ID.

### get_songs_by_tag(tag_id: int) -> List[Song]
Fetch the full hydrated song repertoire linked to a specific tag.

### get_songs_by_identity(identity_id: int) -> List[Song]
Reverse Credit lookup starting from a seed identity.

### add_identity_alias(identity_id: int, display_name: str, name_id: Optional[int] = None) -> int
Link a name to an identity.

### remove_identity_alias(name_id: int) -> None
Remove an alias from an identity.

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

### ingest_wav_as_converting(staged_path: str) -> Dict[str, Any]
Ingest a WAV file immediately with processing_status=3 (Converting).

### finalize_wav_conversion(song_id: int, mp3_path: str) -> None
After background WAV→MP3 conversion succeeds, update the DB record to the new MP3 path and status.

### move_song_to_library(song_id: int) -> str
Calculates the target routing, moves the physical file, and updates the database records.

### update_identity_legal_name(identity_id: int, legal_name: Optional[str]) -> None
Update the LegalName on an Identity. Raises LookupError if not found.

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
