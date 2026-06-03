import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from mutagen.id3 import ID3
from mutagen.mp3 import MP3, BitrateMode

try:
    from mutagen.id3 import ID3NoHeaderError
except ImportError:
    ID3NoHeaderError = Exception

from src.engine.config import FFMPEG_PATH
from src.services.logger import logger

# A real MP3 frame can never exceed 320 kbps. If the audio region is far larger
# than this ceiling implies for the actually-decoded duration, the excess is
# trailing junk (corrupt/truncated source), not audio.
_MAX_MP3_BITRATE = 320_000
_FFMPEG_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")


def _id3v2_size(file_path: str) -> int:
    """Byte length of the leading ID3v2 tag (0 if none), via the synchsafe size."""
    with open(file_path, "rb") as f:
        header = f.read(10)
    if len(header) < 10 or header[:3] != b"ID3":
        return 0
    s = header[6:10]
    return 10 + ((s[0] << 21) | (s[1] << 14) | (s[2] << 7) | s[3])


def _decoded_duration_seconds(file_path: str) -> Optional[float]:
    """True decoded audio length via ffmpeg (authoritative across MPEG versions)."""
    try:
        result = subprocess.run(
            [str(FFMPEG_PATH), "-i", file_path, "-f", "null", "-"],
            capture_output=True,
        )
    except FileNotFoundError:
        return None
    matches = _FFMPEG_TIME_RE.findall(result.stderr.decode(errors="replace"))
    if not matches:
        return None
    h, m, s = matches[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def has_trailing_junk(file_path: str) -> bool:
    """
    True when an MP3's audio region is far larger than its decoded duration can
    physically account for at the 320 kbps ceiling — i.e. it carries trailing
    junk (a truncated/corrupt source padded with garbage). Re-muxing such a file
    folds the junk into the Xing byte_count and produces a header players reject.
    """
    decoded = _decoded_duration_seconds(file_path)
    if not decoded or decoded <= 0:
        return False
    audio_region = os.path.getsize(file_path) - _id3v2_size(file_path)
    max_plausible = decoded * (_MAX_MP3_BITRATE / 8)
    return (
        audio_region > max_plausible * 1.5 and audio_region - max_plausible > 256 * 1024
    )


def needs_xing_repair(file_path: str) -> bool:
    """
    True when an MP3 lacks a valid Xing/Info header.

    Without that header, mutagen (and browsers) estimate duration from the
    first frame's declared bitrate, which is wrong for VBR files. Mutagen
    reports BitrateMode.UNKNOWN in exactly this case.
    """
    if Path(file_path).suffix.lower() != ".mp3":
        return False
    try:
        info = MP3(file_path).info
    except Exception as e:
        logger.warning(
            f"[AudioRepair] needs_xing_repair: cannot read '{file_path}': {e}"
        )
        return False
    return getattr(info, "bitrate_mode", None) == BitrateMode.UNKNOWN


def repair_xing_header(file_path: str) -> float:
    """
    Rewrite an MP3 with a proper Xing header so its duration is reported
    accurately and browser seeking works.

    The audio frames are copied (no re-encode); ffmpeg writes the Xing header.
    ffmpeg mangles multi-value ID3 frames, so its metadata handling is disabled
    (-map_metadata -1) and the original ID3 block is re-applied byte-faithfully
    with mutagen afterward.

    The original is replaced atomically. On any failure the original is left
    untouched and RuntimeError is raised.

    Returns the corrected duration in seconds.
    """
    src = Path(file_path)
    logger.info(f"[AudioRepair] -> repair_xing_header(file='{src}')")

    if not src.exists():
        raise RuntimeError(f"File not found: {src}")

    # Refuse files whose audio region is mostly trailing junk: re-muxing would
    # fold the junk into the Xing byte_count and yield a header players reject.
    # Leave the original untouched for manual review (re-acquire the source).
    if has_trailing_junk(str(src)):
        raise RuntimeError(
            f"refusing repair: '{src.name}' carries trailing junk (truncated or "
            f"corrupt source); re-acquire the file instead"
        )

    # Capture the original tags before ffmpeg strips them.
    try:
        original_tags = ID3(str(src))
    except ID3NoHeaderError:
        original_tags = None

    tmp = src.with_name(src.stem + ".repair_tmp.mp3")
    try:
        result = subprocess.run(
            [
                str(FFMPEG_PATH),
                "-y",
                "-i",
                str(src),
                "-map",
                "0:a",
                "-map_metadata",
                "-1",
                "-c",
                "copy",
                "-write_xing",
                "1",
                str(tmp),
            ],
            capture_output=True,
        )
    except FileNotFoundError:
        logger.error(f"[AudioRepair] ffmpeg not found at '{FFMPEG_PATH}'")
        raise RuntimeError(f"ffmpeg not found at '{FFMPEG_PATH}'")

    try:
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            logger.error(
                f"[AudioRepair] ffmpeg failed (exit {result.returncode}): {stderr}"
            )
            raise RuntimeError(f"ffmpeg failed (exit {result.returncode}): {stderr}")

        if not tmp.exists():
            raise RuntimeError(f"ffmpeg exited 0 but output not created: {tmp}")

        # Restore the original tags, preserving the original ID3v2 minor version.
        if original_tags is not None:
            v2_version = original_tags.version[1] if original_tags.version else 4
            original_tags.save(str(tmp), v2_version=v2_version)

        new_duration = MP3(str(tmp)).info.length

        # Atomic swap (tmp is on the same filesystem as src).
        os.replace(str(tmp), str(src))
    finally:
        if tmp.exists():
            tmp.unlink()

    logger.info(
        f"[AudioRepair] <- repair_xing_header(file='{src}') OK duration={new_duration:.2f}s"
    )
    return new_duration
