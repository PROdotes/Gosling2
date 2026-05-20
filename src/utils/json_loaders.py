import json
from src.engine.config import TRANSLITERATIONS_PATH
from src.services.logger import logger


def load_transliterations() -> dict[str, str]:
    """Custom character map (e.g. Đ -> Dj, ss -> ss) for chars NFKD cannot decompose."""
    if not TRANSLITERATIONS_PATH.exists():
        logger.warning(
            f"[json_loaders] Transliterations file not found at {TRANSLITERATIONS_PATH}. Using empty map."
        )
        return {}
    try:
        with open(TRANSLITERATIONS_PATH, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[json_loaders] Error loading transliterations: {e}")
        return {}
