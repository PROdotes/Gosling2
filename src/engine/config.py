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

# Media Directory (Permanent storage for ingested files)
MEDIA_DIR = Path("temp/library/media")

# Accepted file extensions for ingestion
ACCEPTED_EXTENSIONS = [".mp3"]

# Tag defaults
TAG_DEFAULT_CATEGORY = os.getenv("GOSLING_TAG_DEFAULT_CATEGORY", "Genre")
TAG_CATEGORY_DELIMITER = os.getenv("GOSLING_TAG_CATEGORY_DELIMITER", ":")
TAG_INPUT_FORMAT = os.getenv("GOSLING_TAG_INPUT_FORMAT", "tag:category")

# Fields whose values should additionally be split on ", " during metadata extraction
COMMA_SPLIT_FIELDS = ["composers"]

# Album defaults
ALBUM_DEFAULT_TYPE = "Single"

# Scalar field validation rules (single source of truth — exposed via /api/v1/validation-rules)
SCALAR_VALIDATION = {
    "year": {"min": 1860, "max_offset": 1},  # max = current_year + max_offset
    "bpm": {"min": 1, "max": 300},
    "isrc": {
        "pattern": r"^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$",
        "strip": "-",
        "uppercase": True,
    },
}

# Song Approval Pipeline
AUTO_MOVE_ON_APPROVE = os.getenv("GOSLING_AUTO_MOVE_ON_APPROVE") == "true"
PROMPT_BEFORE_MOVE = os.getenv("GOSLING_PROMPT_BEFORE_MOVE") == "true"
RENAME_RULES_PATH = Path(
    os.getenv("GOSLING_RENAME_RULES_PATH", "config/rename_rules.json")
)

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
