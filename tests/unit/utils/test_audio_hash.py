"""
Unit tests for audio hash calculation.

Tests the calculate_audio_hash() function that generates a hash of MP3 audio frames
only (excluding ID3v2 header and ID3v1 footer) for duplicate detection.

Per TESTING.md:
- Logic tests (this file): Hash calculation, consistency, ID3 exclusion
- Robustness tests (test_audio_hash_mutation.py): Corrupted files, missing ID3
"""

import pytest
import hashlib
from pathlib import Path
from src.utils.audio_hash import calculate_audio_hash


class TestAudioHashLogic:
    """Test audio hash calculation logic."""
    
    def test_same_file_same_hash(self, test_mp3):
        """Same file should produce same hash on multiple calls."""
        hash1 = calculate_audio_hash(test_mp3)
        hash2 = calculate_audio_hash(test_mp3)
        
        assert hash1 == hash2
        assert hash1 is not None
        assert len(hash1) == 64  # SHA256 produces 64 hex characters
    
    def test_different_files_different_hashes(self, test_mp3, test_mp3_banana):
        """Different audio files should produce different hashes."""
        hash1 = calculate_audio_hash(test_mp3)
        hash2 = calculate_audio_hash(test_mp3_banana)
        
        # These are different MP3 files, so hashes should differ
        assert hash1 != hash2
    
    def test_hash_excludes_id3v2_tags(self, test_mp3, test_mp3_with_album_art):
        """
        Hash should be identical for files with same audio but different ID3v2 tags.
        """
        hash1 = calculate_audio_hash(test_mp3)
        hash2 = calculate_audio_hash(test_mp3_with_album_art)
        
        assert hash1 == hash2, "Audio hash differed despite identical audio content (only tags changed)"
    
    def test_hash_excludes_id3v1_tags(self, tmp_path):
        """
        Hash should be identical for files with same audio but different ID3v1 tags.
        
        ID3v1 tags are in the last 128 bytes of the file.
        """
    def test_hash_excludes_id3v1_tags(self, test_mp3, tmp_path):
        """
        Hash should be identical for files with same audio but different ID3v1 tags.
        
        ID3v1 tags are in the last 128 bytes of the file.
        """
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TIT2
        import shutil
        
        # Create a copy
        v1_path = tmp_path / "v1_tags.mp3"
        shutil.copy(test_mp3, v1_path)
        
        # Force ID3v1 tags (v1=2 means V1 only, or both? checking docs... 
        # Actually save(v1=2) usually forces v1 write. 
        # But we just need content to change at the end.
        
        audio = MP3(v1_path)
        if audio.tags is None: audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text='V1 Title'))
        # v1=2 -> Write ID3v1. v2_version=0 -> remove ID3v2? 
        # Let's try writing v1.
        audio.save(v1=2) 
        
        hash1 = calculate_audio_hash(test_mp3)
        hash2 = calculate_audio_hash(str(v1_path))
        
        assert hash1 == hash2, "Audio hash differed when adding ID3v1 tags"
    
    def test_hash_format(self, test_mp3):
        """Hash should be a valid SHA256 hex string."""
        hash_value = calculate_audio_hash(test_mp3)
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64
        # Should be valid hex
        int(hash_value, 16)  # Will raise ValueError if not valid hex
    
    def test_nonexistent_file(self):
        """Nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            calculate_audio_hash("nonexistent.mp3")
    
    def test_empty_file(self, tmp_path):
        """Empty file should raise appropriate error."""
        empty_file = tmp_path / "empty.mp3"
        empty_file.write_bytes(b"")
        
        with pytest.raises(Exception):  # Will be more specific once implemented
            calculate_audio_hash(str(empty_file))


class TestAudioHashConsistency:
    """Test that audio hash is consistent across different scenarios."""
    
    def test_hash_unchanged_after_tag_edit(self, test_mp3, tmp_path):
        """
        Editing ID3 tags should not change the audio hash.
        
        This is the core requirement for duplicate detection - we want to detect
        duplicates even when metadata differs.
        """
        from mutagen.mp3 import MP3
        from mutagen.id3 import TIT2, TPE1
        
        # Calculate hash before tag edit
        hash_before = calculate_audio_hash(test_mp3)
        
        # Edit tags
        audio = MP3(test_mp3)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text='Modified Title'))
        audio.tags.add(TPE1(encoding=3, text='Modified Artist'))
        audio.save(v2_version=4)
        
        # Calculate hash after tag edit
        hash_after = calculate_audio_hash(test_mp3)
        
        # Hash should be unchanged
        assert hash_before == hash_after, "Audio hash changed after tag edit!"
    
    def test_hash_changes_with_audio_modification(self, test_mp3, test_mp3_banana):
        """
        Modifying audio frames should change the hash.
        
        We use two different files (Boop vs Banana) to verify checking works.
        """
        hash1 = calculate_audio_hash(test_mp3)
        hash2 = calculate_audio_hash(test_mp3_banana)
        assert hash1 != hash2
