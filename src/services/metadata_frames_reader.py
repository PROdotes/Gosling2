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


def _save_raw(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


@lru_cache(maxsize=1)
def load_id3_frames(path: str = _FRAMES_PATH) -> ID3FrameMapping:
    """
    The single source of truth for ID3 frame mapping.
    Uses @lru_cache to ensure we only read the JSON from disk once.
    """
    try:
        raw_data = _load_raw(path)
        # Strip non-frame keys before validation
        frame_data = {k: v for k, v in raw_data.items() if k != "tag_categories"}
        adapter = TypeAdapter(ID3FrameMapping)
        mapping = adapter.validate_python(frame_data)
        logger.info(
            f"[MetadataFramesReader] Loaded {len(mapping)} frame mapping entries."
        )
        return mapping
    except Exception as e:
        logger.error(
            f"[MetadataFramesReader] Critical error loading frames config: {e}"
        )
        return {}


@lru_cache(maxsize=1)
def load_tag_categories(path: str = _FRAMES_PATH) -> List[str]:
    """Returns the live registry of known tag categories from id3_frames.json."""
    raw_data = _load_raw(path)
    return raw_data.get("tag_categories", [])


def register_tag_category(category: str, path: str = _FRAMES_PATH) -> None:
    """Add a category to the registry if not already present. Clears the cache."""
    raw_data = _load_raw(path)
    categories = raw_data.get("tag_categories", [])
    if category not in categories:
        categories.append(category)
        raw_data["tag_categories"] = sorted(categories)
        _save_raw(path, raw_data)
        load_tag_categories.cache_clear()
        logger.info(f"[MetadataFramesReader] Registered tag category: '{category}'")


def unregister_tag_category(category: str, path: str = _FRAMES_PATH) -> None:
    """Remove a category from the registry. Clears the cache."""
    raw_data = _load_raw(path)
    categories = raw_data.get("tag_categories", [])
    if category in categories:
        categories.remove(category)
        raw_data["tag_categories"] = categories
        _save_raw(path, raw_data)
        load_tag_categories.cache_clear()
        logger.info(f"[MetadataFramesReader] Unregistered tag category: '{category}'")
