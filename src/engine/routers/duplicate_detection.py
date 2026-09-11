from fastapi import APIRouter, Depends, HTTPException

from src.engine.config import DUPLICATE_DETECTION_DEFAULT_THRESHOLD
from src.services.duplicate_detection_service import DuplicateDetectionService
from src.services.logger import logger

router = APIRouter(prefix="/api/v1", tags=["Duplicate Detection"])


def _get_service() -> DuplicateDetectionService:
    return DuplicateDetectionService()


@router.post("/songs/{song_id}/find-duplicates")
def find_duplicates(
    song_id: int,
    threshold: float = DUPLICATE_DETECTION_DEFAULT_THRESHOLD,
    service: DuplicateDetectionService = Depends(_get_service),
) -> dict:
    """
    Read-only acoustic duplicate scan - Part 2A test harness. Runs the song's
    stored fingerprint against every other computed fingerprint in the
    library via src/utils/audio_fingerprint_match.py and returns matches at
    or above `threshold`. Writes nothing.

    Temporary: this is the tuning harness for Part 2, not the shipped
    feature - see docs/todo/duplicate_detection.md. `threshold` is a query
    param specifically so it can be tuned against live data without a
    redeploy.
    """
    logger.debug(
        f"[DuplicateDetectionRouter] find_duplicates(song_id={song_id}, "
        f"threshold={threshold})"
    )
    result = service.find_duplicates(song_id, threshold)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Song ID {song_id} not found")
    return result
