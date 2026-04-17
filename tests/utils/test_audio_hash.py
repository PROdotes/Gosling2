import hashlib
import os
import pytest
from src.utils.audio_hash import calculate_audio_hash


def get_hash(data: bytes) -> str:
    """Helper to calculate SHA256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()


def create_temp_file(tmp_path, name: str, content: bytes) -> str:
    """Helper to create a temporary file and return its path."""
    filepath = tmp_path / name
    filepath.write_bytes(content)
    return str(filepath)


class TestCalculateAudioHash:
    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            calculate_audio_hash("nonexistent_file.mp3")

    def test_pure_audio_no_tags(self, tmp_path):
        audio_data = b"A" * 200
        filepath = create_temp_file(tmp_path, "pure.mp3", audio_data)

        expected_hash = get_hash(audio_data)
        assert calculate_audio_hash(filepath) == expected_hash, f"Expected {expected_hash}, got {calculate_audio_hash(filepath)}"

    def test_id3v1_only(self, tmp_path):
        audio_data = b"B" * 200
        # ID3v1 is exactly 128 bytes at the end, starting with "TAG"
        id3v1_tag = b"TAG" + b"X" * 125
        filepath = create_temp_file(tmp_path, "id3v1.mp3", audio_data + id3v1_tag)

        expected_hash = get_hash(audio_data)
        assert calculate_audio_hash(filepath) == expected_hash, f"Expected {expected_hash}, got {calculate_audio_hash(filepath)}"

    def test_id3v2_only(self, tmp_path):
        audio_data = b"C" * 200
        # ID3v2 header: "ID3" (3) + version (2) + flags (1) + size (4)
        # Size of 5 -> \x00\x00\x00\x05
        id3v2_header = b"ID3\x03\x00\x00\x00\x00\x00\x05"
        id3v2_body = b"12345"  # 5 bytes to match size
        filepath = create_temp_file(tmp_path, "id3v2.mp3", id3v2_header + id3v2_body + audio_data)

        expected_hash = get_hash(audio_data)
        assert calculate_audio_hash(filepath) == expected_hash, f"Expected {expected_hash}, got {calculate_audio_hash(filepath)}"

    def test_both_id3v1_and_id3v2(self, tmp_path):
        audio_data = b"D" * 200
        id3v2_header = b"ID3\x03\x00\x00\x00\x00\x00\x05"
        id3v2_body = b"12345"
        id3v1_tag = b"TAG" + b"X" * 125
        filepath = create_temp_file(tmp_path, "both.mp3", id3v2_header + id3v2_body + audio_data + id3v1_tag)

        expected_hash = get_hash(audio_data)
        assert calculate_audio_hash(filepath) == expected_hash, f"Expected {expected_hash}, got {calculate_audio_hash(filepath)}"

    def test_fallback_invalid_boundaries(self, tmp_path):
        # Create an ID3v2 tag that claims a large size (100 -> \x64), but file is small.
        # This triggers audio_start >= audio_end
        id3v2_header = b"ID3\x03\x00\x00\x00\x00\x00\x64"
        audio_data = b"E" * 20
        content = id3v2_header + audio_data
        filepath = create_temp_file(tmp_path, "fallback.mp3", content)

        # When boundaries are invalid, the function hashes the entire file
        expected_hash = get_hash(content)
        assert calculate_audio_hash(filepath) == expected_hash, f"Expected {expected_hash}, got {calculate_audio_hash(filepath)}"
