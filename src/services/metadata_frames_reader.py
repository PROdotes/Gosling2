import json
from pathlib import Path
from functools import lru_cache
from pydantic import TypeAdapter
from src.models.metadata_frames import ID3FrameMapping
from src.services.logger import logger


@lru_cache(maxsize=1)
def load_id3_frames(path: str = "json/id3_frames.json") -> ID3FrameMapping:
    """
    The single source of truth for ID3 frame mapping.
    Uses @lru_cache to ensure we only read the JSON from disk once.
    """
    config_path = Path(path)
    if not config_path.exists():
        logger.error(f"[MetadataFramesReader] Config file not found at {config_path}")
        return {}

    try:
        # Data Fidelity: Handle UTF-8 with BOM (utf-8-sig) found in the frames JSON.
        with open(config_path, "r", encoding="utf-8-sig") as f:
            raw_data = json.load(f)

        # Validate the data against our formal Model.
        adapter = TypeAdapter(ID3FrameMapping)
        mapping = adapter.validate_python(raw_data)

        logger.info(
            f"[MetadataFramesReader] Loaded {len(mapping)} frame mapping entries."
        )
        return mapping
    except Exception as e:
        logger.error(
            f"[MetadataFramesReader] Critical error loading frames config: {e}"
        )
        return {}
