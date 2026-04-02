import subprocess
from pathlib import Path

from src.engine.config import FFMPEG_PATH


def convert_to_mp3(src_path: Path) -> Path:
    """
    Convert a WAV file to MP3 using ffmpeg.

    - Returns the path to the new MP3 file on success.
    - Deletes the source WAV on success.
    - Cleans up partial output and raises RuntimeError on any failure.
    """
    out_path = src_path.with_suffix(".mp3")

    try:
        result = subprocess.run(
            [FFMPEG_PATH, "-i", str(src_path), "-q:a", "2", str(out_path)],
            capture_output=True,
        )
    except FileNotFoundError:
        raise RuntimeError(f"ffmpeg not found at '{FFMPEG_PATH}'")

    if result.returncode != 0:
        if out_path.exists():
            out_path.unlink()
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}): {result.stderr.decode(errors='replace')}"
        )

    if not out_path.exists():
        raise RuntimeError(
            f"ffmpeg exited 0 but output file was not created: {out_path}"
        )

    src_path.unlink()
    return out_path
