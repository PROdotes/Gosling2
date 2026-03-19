import os
from pathlib import Path

# --- GOSLING2 ENGINE CONFIG ---
# Centralized source of truth for all paths and environment variables.

# Database Path
DB_PATH = os.getenv("GOSLING_DB_PATH", "sqldb/gosling2.db")

# Library Management (Phase 3.2+)
# GOSLING_LIBRARY_ROOT: The organized parent folder for all songs.
LIBRARY_ROOT = os.getenv("GOSLING_LIBRARY_ROOT", "Z:\\Songs")

# Staging Area (Uploaded but un-indexed files)
STAGING_DIR = Path("temp/library/staging")
