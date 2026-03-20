import os
from pathlib import Path

# --- GOSLING2 ENGINE CONFIG ---
# Centralized source of truth for all paths and environment variables.


# Database Path
def get_db_path() -> str:
    return os.getenv("GOSLING_DB_PATH", "sqldb/gosling2.db")


# Library Management (Phase 3.2+)
# GOSLING_LIBRARY_ROOT: The organized parent folder for all songs.
def get_library_root() -> str:
    return os.getenv("GOSLING_LIBRARY_ROOT", "Z:\\Songs")


# Staging Area (Uploaded but un-indexed files)
STAGING_DIR = Path("temp/library/staging")

# CORS Configuration (Audit #4)
# Whitelist of trusted origins for local development and testing.
TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]
