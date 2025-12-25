"""
Audio hash calculation for duplicate detection.

This module provides utilities to calculate a hash of MP3 audio frames only,
excluding ID3v2 headers and ID3v1 footers. This allows detection of duplicate
audio files even when metadata differs.

Per PROPOSAL_DUPLICATE_DETECTION.md Phase 2.
"""

import hashlib
from pathlib import Path
from typing import Optional


def calculate_audio_hash(filepath: str) -> str:
    """
    Calculate SHA256 hash of MP3 audio frames only (excludes ID3 tags).
    
    This function:
    1. Skips ID3v2 header (if present) at the start of the file
    2. Skips ID3v1 footer (if present) at the end of the file
    3. Hashes only the MPEG audio frames in between
    
    This ensures that two files with identical audio but different metadata
    (tags, album art, etc.) will produce the same hash.
    
    Args:
        filepath: Path to the MP3 file
        
    Returns:
        SHA256 hash as a 64-character hex string
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file is empty or not a valid MP3
        
    Examples:
        >>> hash1 = calculate_audio_hash("song.mp3")
        >>> hash2 = calculate_audio_hash("song_retagged.mp3")
        >>> hash1 == hash2  # True if same audio, different tags
    """
    file_path = Path(filepath)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    file_size = file_path.stat().st_size
    
    if file_size == 0:
        raise ValueError(f"File is empty: {filepath}")
    
    # Read the entire file into memory
    # For large files, we could use chunked reading, but MP3s are typically small
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # Determine ID3v2 header size (if present)
    id3v2_size = 0
    if data[:3] == b'ID3':
        # ID3v2 header format:
        # - Bytes 0-2: "ID3"
        # - Bytes 3-4: Version (e.g., 0x04 0x00 for ID3v2.4)
        # - Byte 5: Flags
        # - Bytes 6-9: Size (synchsafe integer - 7 bits per byte)
        
        if len(data) >= 10:
            # Extract size from bytes 6-9 (synchsafe integer)
            # Each byte uses only 7 bits, MSB is always 0
            size_bytes = data[6:10]
            id3v2_size = (
                (size_bytes[0] << 21) |
                (size_bytes[1] << 14) |
                (size_bytes[2] << 7) |
                size_bytes[3]
            )
            # Add 10 bytes for the header itself
            id3v2_size += 10
    
    # Determine ID3v1 footer size (if present)
    id3v1_size = 0
    if len(data) >= 128 and data[-128:-125] == b'TAG':
        # ID3v1 tag is exactly 128 bytes at the end
        id3v1_size = 128
    
    # Extract audio frames only (skip ID3 tags)
    audio_start = id3v2_size
    audio_end = len(data) - id3v1_size
    
    if audio_start >= audio_end:
        raise ValueError(f"No audio frames found in file: {filepath}")
    
    audio_data = data[audio_start:audio_end]
    
    # Calculate SHA256 hash of audio frames
    hash_obj = hashlib.sha256(audio_data)
    return hash_obj.hexdigest()
