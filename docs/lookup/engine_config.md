# Engine Config
*Location: `src/engine/config.py`*

**Responsibility**: Centralized source of truth for all paths and environment variables.

### get_db_path() -> str
The path to the SQLite library database. Defaults to `sqldb/gosling2.db`. Override via `GOSLING_DB_PATH`.

### get_library_root() -> str
The organized parent folder for all songs. Defaults to `Z:\Songs`. Override via `GOSLING_LIBRARY_ROOT`.

### STAGING_DIR
The Path to the temporary ingestion staging area. Defaults to `temp/library/staging`.

### TRUSTED_ORIGINS
CORS whitelist of trusted origins (localhost/127.0.0.1 on ports 3000, 5173, 8000).
