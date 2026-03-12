import hashlib
from typing import Optional


def calculate_audio_hash(filepath: str) -> str:
    """
    Calculate SHA256 hash of MP3 audio frames only (excludes ID3 tags).
    
    Ported from Legacy [GOSLING2] math to maintain cross-version consistency.
    """
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except Exception as e:
        raise FileNotFoundError(f"Could not read file {filepath}: {e}")

    # Determine ID3v2 header size (if present)
    id3v2_size = 0
    if data[:3] == b"ID3":
        if len(data) >= 10:
            # Extract size from bytes 6-9 (synchsafe integer)
            size_bytes = data[6:10]
            id3v2_size = (
                (size_bytes[0] << 21)
                | (size_bytes[1] << 14)
                | (size_bytes[2] << 7)
                | size_bytes[3]
            )
            # Add 10 bytes for the header itself
            id3v2_size += 10

    # Determine ID3v1 footer size (if present)
    id3v1_size = 0
    if len(data) >= 128 and data[-128:-125] == b"TAG":
        id3v1_size = 128

    # Extract audio frames only (skip ID3 tags)
    audio_start = id3v2_size
    audio_end = len(data) - id3v1_size

    if audio_start >= audio_end:
        # Fallback for small/weird files or non-MP3: hash everything
        # This prevents breaking on edge cases while trying to be smart
        hash_obj = hashlib.sha256(data)
    else:
        audio_data = data[audio_start:audio_end]
        hash_obj = hashlib.sha256(audio_data)

    return hash_obj.hexdigest()
