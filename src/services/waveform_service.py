import json
import math
import struct
import subprocess
from pathlib import Path
from typing import List

from src.engine.config import FFMPEG_PATH
from src.services.logger import logger

WAVEFORM_CACHE_DIR = Path("sqldb/waveform_cache")
PEAK_COUNT = 1000
SAMPLE_RATE = 8000


def _cache_path(song_id: int) -> Path:
    return WAVEFORM_CACHE_DIR / f"{song_id}.json"


def _build_peaks(audio_path: Path) -> List[float]:
    """Decode audio with ffmpeg to mono s16le PCM and reduce to PEAK_COUNT RMS bars (0-1)."""
    logger.info(f"[Waveform] -> _build_peaks(audio='{audio_path}')")
    try:
        result = subprocess.run(
            [
                str(FFMPEG_PATH),
                "-v", "error",
                "-i", str(audio_path),
                "-f", "s16le",
                "-ac", "1",
                "-ar", str(SAMPLE_RATE),
                "-",
            ],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except FileNotFoundError:
        logger.error(f"[Waveform] ffmpeg not found at '{FFMPEG_PATH}'")
        raise RuntimeError(f"ffmpeg not found at '{FFMPEG_PATH}'")

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        logger.error(f"[Waveform] ffmpeg failed (exit {result.returncode}): {stderr}")
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}): {stderr}")

    pcm = result.stdout
    sample_count = len(pcm) // 2
    if sample_count == 0:
        logger.warning(f"[Waveform] no samples decoded from '{audio_path}'")
        return [0.0] * PEAK_COUNT

    samples = struct.unpack(f"<{sample_count}h", pcm)
    chunk = max(1, sample_count // PEAK_COUNT)

    peaks: List[float] = []
    for i in range(PEAK_COUNT):
        start = i * chunk
        end = start + chunk if i < PEAK_COUNT - 1 else sample_count
        if start >= sample_count:
            peaks.append(0.0)
            continue
        block = samples[start:end]
        sq_sum = sum(s * s for s in block)
        rms = math.sqrt(sq_sum / len(block)) / 32768.0
        # Log scaling: stretches quiet sections (speech, intros) away from the limited-music ceiling.
        # Maps -30dB -> 0, 0dB -> 1.
        if rms <= 0:
            peaks.append(0.0)
        else:
            db = 20 * math.log10(rms)
            peaks.append(max(0.0, min(1.0, 1 + db / 30)))

    peak_max = max(peaks)
    if peak_max > 0:
        peaks = [p / peak_max for p in peaks]

    logger.info(f"[Waveform] <- _build_peaks() generated {len(peaks)} bars")
    return peaks


def delete_cache(song_id: int) -> None:
    """Best-effort removal of the cached waveform for a song. Silent if missing."""
    cache = _cache_path(song_id)
    try:
        cache.unlink(missing_ok=True)
    except OSError as e:
        logger.warning(f"[Waveform] failed to delete cache for {song_id}: {e}")


def get_or_build_peaks(song_id: int, audio_path: Path) -> List[float]:
    """Return cached peaks if present, otherwise build and cache them."""
    cache = _cache_path(song_id)
    if cache.exists():
        try:
            with cache.open("r", encoding="utf-8") as f:
                data = json.load(f)
            peaks = data.get("peaks")
            if isinstance(peaks, list) and len(peaks) == PEAK_COUNT:
                return peaks
            logger.warning(f"[Waveform] cache for {song_id} malformed; rebuilding")
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"[Waveform] cache read failed for {song_id}: {e}; rebuilding")

    peaks = _build_peaks(audio_path)
    WAVEFORM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with cache.open("w", encoding="utf-8") as f:
        json.dump({"peaks": peaks}, f)
    return peaks
