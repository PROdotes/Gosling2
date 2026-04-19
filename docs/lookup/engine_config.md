# Engine Config
*Location: `src/engine/config.py`*

**Responsibility**: Centralized source of truth for all paths and environment variables.

### DB_PATH
The path to the SQLite library database. Defaults to `sqldb/gosling2.db`.

### get_db_path() -> Path
Returns the DB path, reading `GOSLING_DB_PATH` env var at call time. Use this (not `DB_PATH`) anywhere the path needs to be overridable at runtime (e.g. tests).

### LIBRARY_ROOT
The organized parent folder for all songs. Defaults to `Z:\Songs`.

### get_downloads_folder() -> str
Returns the platform-specific default downloads folder (e.g., `~/Downloads` or `%USERPROFILE%\Downloads`). Used for safe source-file cleanup.


### STAGING_DIR
The Path to the temporary ingestion staging area. Defaults to `temp/library/staging`.

### MEDIA_DIR
The Path to permanent storage for ingested files. Defaults to `temp/library/media`.

### ACCEPTED_EXTENSIONS
List of supported file extensions for ingestion. Currently `[".mp3"]`.

### COMMA_SPLIT_FIELDS
Fields whose values should be split on ", " during metadata extraction (e.g., `["composers"]`).

### SCALAR_VALIDATION
Validation rules for scalar fields exposed via `/api/v1/validation-rules`:
- `year`: min 1860, max = current_year + 1
- `bpm`: min 1, max 300
- `isrc`: pattern `^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$`

### AUTO_MOVE_ON_APPROVE
Auto-move approved songs to library root. Set via `GOSLING_AUTO_MOVE_ON_APPROVE=true`.

### PROMPT_BEFORE_MOVE
Prompt before moving files. Set via `GOSLING_PROMPT_BEFORE_MOVE=true`.

### RENAME_RULES_PATH
Path to rename rules JSON. Defaults to `config/rename_rules.json`.

### TRUSTED_ORIGINS
CORS whitelist of trusted origins (localhost/127.0.0.1 on ports 3000, 5173, 8000).

### ProcessingStatus(IntEnum)
Named constants for `processing_status` values across the stack:
- `REVIEWED = 0` — human review done
- `NEEDS_REVIEW = 1` — auto-check done, awaiting human review
- `PENDING_ENRICHMENT = 2` — MP3 ingested, waiting for MusicBrainz auto-check
- `CONVERTING = 3` — WAV staged, awaiting conversion
