import subprocess

import numpy as np

from src.engine.config import FPCALC_PATH
from src.services.logger import logger

# Cap passed to fpcalc. A cap, not a window: tracks shorter than this are
# fingerprinted end to end; only longer tracks lose their tail. 180s is
# AcoustID-compatible (verified 2026-09-10) and covers all radio pop.
FINGERPRINT_LENGTH_CAP = 180


def calculate_fingerprint(filepath: str) -> tuple[np.ndarray, float] | None:
    """
    Chromaprint acoustic fingerprint of an audio file via bundled fpcalc.

    Shells `fpcalc -raw -length 180` and parses its FINGERPRINT and DURATION
    lines. Returns the raw fingerprint as a little-endian uint32 array plus the
    reported duration in seconds. No trimming, no normalisation - alignment is
    handled by the offset window at comparison time.

    Returns None on any failure (fpcalc missing, non-zero exit, unparseable
    output). Callers on the ingest path must treat None as "attempted and
    failed" and continue; a fingerprint that cannot be computed never fails an
    ingest.
    """
    try:
        result = subprocess.run(
            [
                str(FPCALC_PATH),
                "-raw",
                "-length",
                str(FINGERPRINT_LENGTH_CAP),
                filepath,
            ],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0
            ),
        )
    except FileNotFoundError:
        logger.error(f"[AudioFingerprint] fpcalc not found at '{FPCALC_PATH}'")
        return None

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        logger.error(
            f"[AudioFingerprint] fpcalc exited {result.returncode} for "
            f"'{filepath}': {stderr}"
        )
        return None

    stdout = result.stdout.decode(errors="replace")
    fingerprint: np.ndarray | None = None
    duration: float | None = None
    for line in stdout.splitlines():
        if line.startswith("FINGERPRINT="):
            raw = line[len("FINGERPRINT=") :].strip()
            if raw:
                fingerprint = np.array(raw.split(","), dtype="<u4")
        elif line.startswith("DURATION="):
            try:
                duration = float(line[len("DURATION=") :].strip())
            except ValueError:
                duration = None

    if fingerprint is None or fingerprint.size == 0 or duration is None:
        logger.error(
            f"[AudioFingerprint] could not parse fpcalc output for '{filepath}'"
        )
        return None

    return fingerprint, duration
