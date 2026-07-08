# Engine Config
*Location: `src/engine/config.py`*

**Responsibility**: Immutable code facts — paths, enums, and validation rules. Editable runtime settings (library root, auto-move, search engine, etc.) live on the `Settings` model in `src/services/config_service.py`, not here.

### DB_PATH
The path to the SQLite library database. Defaults to `sqldb/gosling2.db`.

### get_db_path() -> Path
Returns the DB path, reading `GOSLING_DB_PATH` env var at call time. Use this (not `DB_PATH`) anywhere the path needs to be overridable at runtime (e.g. tests).

### get_downloads_folder() -> Optional[str]
Returns the platform-specific default downloads folder (e.g., `~/Downloads` or `%USERPROFILE%\Downloads`). Used for safe source-file cleanup.

### STAGING_DIR
The Path to the temporary ingestion staging area: `temp/library/staging`.

### MEDIA_DIR
The Path to permanent storage for ingested files: `temp/library/media`.

### ACCEPTED_EXTENSIONS
Supported ingestion extensions: `[".mp3", ".wav"]` (WAVs stage as status-3 and convert to MP3).

### TAG_DEFAULT_CATEGORY
`"Genre"`. Related: `TAG_CATEGORY_DELIMITER = "::"`, `TAG_INPUT_FORMAT = "tag:category"`.

### DEFAULT_CREDIT_SEPARATORS
Separators for the Artist Splitter: `["&", "feat.", "ft.", " x ", "vs.", ",", ";", "/"]`.

### COMMA_SPLIT_FIELDS
Fields whose values are additionally split on ", " during metadata extraction: `["composers"]`.

### ALBUM_DEFAULT_TYPE
`"Single"`. Related: `SONG_DEFAULT_YEAR = 2026`.

### YEAR_VALIDATION
Bundles `YEAR_MIN = 1860` and `YEAR_MAX = current_year + 1` for `SCALAR_VALIDATION`.

### SCALAR_VALIDATION
Single source of truth for scalar validation, exposed via `/api/v1/validation-rules`:
- `year` and `release_year`: `YEAR_VALIDATION` (min 1860, max current_year + 1)
- `bpm`: min 1, max 300
- `isrc`: pattern `^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$`, strip `-`, uppercase
- `track_number`: min 1, max 999
- `disc_number`: min 1, max 99

### FFMPEG_PATH
Bundled ffmpeg binary: `ffmpeg/ffmpeg.exe`.

### RENAME_RULES_PATH
`json/rules.json`. Sibling JSON config paths: `PARSER_PRESETS_PATH` = `json/parser_presets.json`, `ID3_FRAMES_PATH` = `json/id3_frames.json`, `TRANSLITERATIONS_PATH` = `json/transliterations.json`, `SETTINGS_PATH` = `json/settings.json` (source of truth for the `Settings` model).

### SCALAR_ALLOWED
Field allowlist for song scalar updates: `{media_name, year, bpm, isrc, is_active, processing_status, mood, energy, notes}`. `METADATA_ALLOWED` adds `{credits, albums, tags, publishers}`.

### TRUSTED_ORIGINS
CORS whitelist of trusted origins (localhost/127.0.0.1 on ports 3000, 5173, 8000).

### ProcessingStatus(IntEnum)
Named constants for `processing_status` values across the stack:
- `REVIEWED = 0` — human review done
- `NEEDS_REVIEW = 1` — auto-check done, awaiting human review
- `PENDING_ENRICHMENT = 2` — MP3 ingested, waiting for MusicBrainz auto-check
- `CONVERTING = 3` — WAV staged, awaiting conversion
