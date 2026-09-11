from typing import Optional

import numpy as np

from src.data.audio_fingerprint_repository import AudioFingerprintRepository
from src.data.song_repository import SongRepository
from src.engine.config import DUPLICATE_DETECTION_DEFAULT_THRESHOLD, get_db_path
from src.services.logger import logger
from src.utils.audio_fingerprint_match import find_matches


class DuplicateDetectionService:
    """
    Part 2A test harness - read-only. Runs the acoustic comparison in
    src/utils/audio_fingerprint_match.py against stored fingerprints and
    returns candidate duplicates for a human to review. No DB writes, no
    MutationCoordinator involvement (nothing here changes state).

    Temporary: this is the tuning harness for Part 2, not the shipped
    feature. See docs/todo/duplicate_detection.md, "Temporary 'check dupes'
    button" - expected to be removed or absorbed into Part 3.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(get_db_path())
        self._fp_repo = AudioFingerprintRepository(db_path)
        self._song_repo = SongRepository(db_path)

    def find_duplicates(
        self, song_id: int, threshold: float = DUPLICATE_DETECTION_DEFAULT_THRESHOLD
    ) -> Optional[dict]:
        """
        Returns None if the song does not exist. Otherwise a dict:
          {"comparable": bool, "matches": [{"song_id", "score", "title",
           "artist", "path"}, ...]}
        `comparable=False` means the song has no computed fingerprint yet
        (never attempted, or fpcalc failed) - distinct from "comparable but
        zero matches", per the "not comparable is a third state" pin.
        """
        conn = self._fp_repo.get_connection()
        try:
            if self._song_repo.get_by_id(song_id, conn) is None:
                return None

            row = self._fp_repo.get_fingerprint(song_id, conn)
            if row is None or row[0] is None:
                logger.debug(
                    f"[DuplicateDetectionService] song {song_id} has no "
                    f"computed fingerprint - not comparable"
                )
                return {"comparable": False, "matches": []}
            fingerprint_bytes, duration_s, _ = row
            assert fingerprint_bytes is not None and duration_s is not None
            fp = np.frombuffer(fingerprint_bytes, dtype="<u4")

            candidates = [
                (source_id, np.frombuffer(blob, dtype="<u4"), cand_duration)
                for source_id, blob, cand_duration in self._fp_repo.get_all_computed(
                    conn
                )
                if source_id != song_id
            ]

            matches = find_matches(fp, duration_s, candidates, threshold)
            match_ids = [matched_id for matched_id, _ in matches]
            slim_by_id = {
                row["SourceID"]: row
                for row in self._song_repo.search_slim_by_ids(match_ids, conn)
            }

            results = []
            for matched_id, matched_score in matches:
                info = slim_by_id.get(matched_id)
                results.append(
                    {
                        "song_id": matched_id,
                        "score": round(matched_score, 4),
                        "title": info["MediaName"] if info else None,
                        "artist": info["DisplayArtist"] if info else None,
                        "path": info["SourcePath"] if info else None,
                    }
                )

            logger.debug(
                f"[DuplicateDetectionService] find_duplicates(song_id={song_id}, "
                f"threshold={threshold}) -> {len(results)} match(es)"
            )
            return {"comparable": True, "matches": results}
        finally:
            conn.close()
