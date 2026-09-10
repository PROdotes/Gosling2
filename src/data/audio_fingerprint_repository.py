import sqlite3
from typing import Optional

from src.data.base_repository import BaseRepository
from src.services.logger import logger


class AudioFingerprintRepository(BaseRepository):
    """
    Chromaprint acoustic fingerprints, one row per MediaSource once an attempt
    has been made. Machine-derived and recomputable, so writes go direct (not
    through MutationCoordinator) and the table is EXCLUDED_FROM_AUDIT.

    Tri-state without a status column:
      - no row            -> fingerprint never attempted (backfill target)
      - row, Fingerprint NULL -> attempted, fpcalc failed (do not retry blindly)
      - row, Fingerprint set  -> computed
    """

    def set_fingerprint(
        self,
        source_id: int,
        fingerprint: Optional[bytes],
        duration_s: Optional[float],
        length_cap: Optional[int],
        conn: sqlite3.Connection,
    ) -> int:
        """
        Record a fingerprint attempt. Pass fingerprint=None (and the durations
        None) to mark a failed fpcalc run so backfill skips the file next time.
        Replaces any existing row for the source. Returns rowcount; never raises
        on zero.
        """
        logger.debug(
            f"[AudioFingerprintRepository] -> set_fingerprint(id={source_id}, "
            f"computed={fingerprint is not None})"
        )
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO AudioFingerprints
                (SourceID, Fingerprint, DurationS, LengthCap)
            VALUES (?, ?, ?, ?)
            """,
            (source_id, fingerprint, duration_s, length_cap),
        )
        logger.debug(
            f"[AudioFingerprintRepository] <- set_fingerprint(id={source_id}) "
            f"rows={cursor.rowcount}"
        )
        return cursor.rowcount

    def get_fingerprint(
        self, source_id: int, conn: sqlite3.Connection
    ) -> Optional[tuple[Optional[bytes], Optional[float], Optional[int]]]:
        """
        Return (fingerprint_bytes, duration_s, length_cap) for a source, or None
        if no attempt has been recorded. A row with a NULL fingerprint (fpcalc
        failed) returns (None, None, None) - distinct from this method's None.
        """
        row = conn.execute(
            """
            SELECT Fingerprint, DurationS, LengthCap
            FROM AudioFingerprints
            WHERE SourceID = ?
            """,
            (source_id,),
        ).fetchone()
        if row is None:
            return None
        return (row[0], row[1], row[2])
