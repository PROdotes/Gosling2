import json
from pathlib import Path
from functools import lru_cache
from typing import List
from pydantic import TypeAdapter
from src.models.metadata_frames import ID3FrameMapping
from src.services.logger import logger
from src.engine.config import ID3_FRAMES_PATH

_FRAMES_PATH = str(ID3_FRAMES_PATH)


def _load_raw(path: str) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        logger.error(f"[MetadataFramesReader] Config file not found at {config_path}")
        return {}
    with open(config_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_id3_frames(path: str = _FRAMES_PATH) -> ID3FrameMapping:
    """The single source of truth for ID3 frame mapping. Resolves paths to ensure cache hits."""
    return _load_id3_frames_cached(str(Path(path).resolve()))


@lru_cache(maxsize=1)
def _load_id3_frames_cached(path: str) -> ID3FrameMapping:
    try:
        raw_data = _load_raw(path)
        # Strip non-frame keys before validation
        frame_data = {k: v for k, v in raw_data.items() if k != "tag_categories"}
        adapter = TypeAdapter(ID3FrameMapping)
        mapping = adapter.validate_python(frame_data)
        logger.debug(
            f"[MetadataFramesReader] [DISK READ] Loaded {len(mapping)} frame mapping entries from {path}"
        )
        return mapping
    except Exception as e:
        logger.error(
            f"[MetadataFramesReader] Critical error loading frames config: {e}"
        )
        return {}


def load_tag_categories(path: str = _FRAMES_PATH) -> List[str]:
    """Returns the live registry of known tag categories from id3_frames.json."""
    return _load_tag_categories_cached(str(Path(path).resolve()))


@lru_cache(maxsize=1)
def _load_tag_categories_cached(path: str) -> List[str]:
    raw_data = _load_raw(path)
    return raw_data.get("tag_categories", [])


