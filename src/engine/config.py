import os
from pathlib import Path
from typing import Optional

# --- GOSLING2 ENGINE CONFIG ---
# Centralized source of truth for all paths and environment variables.


# Database Path
DB_PATH = Path("sqldb/gosling2.db")


def get_db_path() -> Path:
    return Path(os.getenv("GOSLING_DB_PATH", "sqldb/gosling2.db"))

# Library Management (Phase 3.2+)
# GOSLING_LIBRARY_ROOT: The organized parent folder for all songs.
LIBRARY_ROOT = Path("Z:\\Songs")


def get_downloads_folder() -> Optional[str]:
    """NT/POSIX compatible downloads folder path."""
    if os.name == "nt":
        return os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")
    elif os.name == "posix":
        home = os.environ.get("HOME", "")
        return os.path.join(home, "Downloads")
    return None


# Staging Area (Uploaded but un-indexed files)
STAGING_DIR = Path("temp/library/staging")

# Media Directory (Permanent storage for ingested files)
MEDIA_DIR = Path("temp/library/media")

# Accepted file extensions for ingestion
ACCEPTED_EXTENSIONS = [".mp3", ".wav"]

# Tag defaults
TAG_DEFAULT_CATEGORY = "Genre"
TAG_CATEGORY_DELIMITER = ":"
TAG_INPUT_FORMAT = "tag:category"

# Default separators for the Artist Splitter feature
DEFAULT_CREDIT_SEPARATORS = ["&", "feat.", "ft.", " x ", "vs.", ",", ";", "/"]

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

# FFmpeg
FFMPEG_PATH = Path("ffmpeg/ffmpeg.exe")
WAV_AUTO_CONVERT = True

# Song Approval Pipeline
AUTO_MOVE_ON_APPROVE = True
PROMPT_BEFORE_MOVE = True
AUTO_SAVE_ID3 = True
DEFAULT_SEARCH_ENGINE = "spotify"
RENAME_RULES_PATH = Path("json/rules.json")

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
