import hashlib
import os


def calculate_audio_hash(filepath: str, chunk_size: int = 65536) -> str:
    """
    Calculate SHA256 hash of MP3 audio frames only (excludes ID3 tags).
    Streams file in chunks to avoid high memory usage (Audit #2).
    Matches Step 631 logic for cross-version consistency.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    # 1. Determine boundaries (ID3v2 header and ID3v1 footer)
    id3v2_size = 0
    with open(filepath, "rb") as f:
        header = f.read(10)
        if len(header) == 10 and header[:3] == b"ID3":
            # Extract size from bytes 6-9 (synchsafe integer - 7 bits per byte)
            size_bytes = header[6:10]
            id3v2_size = (
                (size_bytes[0] << 21)
                | (size_bytes[1] << 14)
                | (size_bytes[2] << 7)
                | size_bytes[3]
            )
            # Add 10 bytes for the header itself
            id3v2_size += 10

    id3v1_size = 0
    file_size = os.path.getsize(filepath)
    if file_size >= 128:
        with open(filepath, "rb") as f:
            f.seek(-128, os.SEEK_END)
            footer_header = f.read(3)
            if footer_header == b"TAG":
                id3v1_size = 128

    audio_start = id3v2_size
    audio_end = file_size - id3v1_size

    if audio_start >= audio_end:
        # Fallback for weird files (same as Step 631 spirit but chunked)
        hash_obj = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    # 2. Hash only the MPEG frames (the 'Slab') in chunks
    hash_obj = hashlib.sha256()
    bytes_to_read = audio_end - audio_start
    with open(filepath, "rb") as f:
        f.seek(audio_start)
        while bytes_to_read > 0:
            chunk = f.read(min(chunk_size, bytes_to_read))
            if not chunk:
                break
            hash_obj.update(chunk)
            bytes_to_read -= len(chunk)

    return hash_obj.hexdigest()
