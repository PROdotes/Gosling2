# Engine Config
*Location: `src/engine/config.py`*

**Responsibility**: Centralized source of truth for all paths and environment variables.

### DB_PATH
The path to the SQLite library database. Defaults to `sqldb/gosling2.db`.

### LIBRARY_ROOT
The organized parent folder for all songs. Defaults to `Z:\Songs`. Override via `GOSLING_LIBRARY_ROOT`.

### STAGING_DIR
The Path to the temporary ingestion staging area. Defaults to `temp/library/staging`.
