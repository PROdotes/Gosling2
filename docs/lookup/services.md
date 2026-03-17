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
Search for songs by title and hydrate with full metadata.
- Calls `SongRepository.get_by_title`.
- Uses `_hydrate_songs` to attach all credits, albums, and publishers.

### _hydrate_songs(songs: List[Song]) -> List[Song]
**Internal**: Centralized batch hydration for all song metadata.
- Fetches credits from `SongCreditRepository`.
- Fetches album context from `SongAlbumRepository`.
- Resolves publisher objects via `PublisherRepository`.
- Locally orchestrates/groups the records by SourceID.
- Stitches them back to the Songs creating `SongAlbum` bridge objects with resolved metadata and returns the hydrated list.

### _get_credits_by_song(song_ids: List[int]) -> Dict[int, List[SongCredit]]
**Internal**: Fetches and groups credits by song ID.

### _get_publishers_by_song(song_ids: List[int]) -> Dict[int, List[Publisher]]
**Internal**: Fetches and groups master recording publishers by song ID.

### _get_tags_by_song(song_ids: List[int]) -> Dict[int, List[Tag]]
**Internal**: Fetches and groups tags by song ID.

### _get_albums_by_song(song_ids: List[int]) -> Dict[int, List[SongAlbum]]
**Internal**: Fetches album associations, resolves publishers, and groups by song ID.

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

### _log(level: str, msg: str)
**Internal**: Helper to format and send messages to stdout.
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
- **Wisdom**: Handles "Frame Doubling" (e.g. merging TIPL and TPE1 into unique credits).

### _load_config(json_path: str) -> Dict[str, Any]
**Internal**: Loads the frame mapping configuration from JSON. Uses `utf-8-sig` to ignore Windows BOMs.

### _to_int(val: Any) -> Optional[int]
**Internal**: Safely converts string values (e.g. "2024 (Remaster)") into clean integers by stripping non-digit characters.

### _get_role_name(field: str) -> str
**Internal**: Maps internal JSON field names like `artist` or `producers` to clean UI role names like `Performer` or `Producer`.
