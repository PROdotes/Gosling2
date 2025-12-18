"""Defensive tests for MetadataService.write_tags() - testing edge cases and malicious input"""
import pytest
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

from src.business.services.metadata_service import MetadataService
from src.data.models.song import Song
from tests.unit.business.services.test_metadata_fixtures import test_mp3


class TestWriteTagsDefensive:
    """Tests for edge cases and potentially malicious input"""
    
    def test_write_tags_very_long_title(self, test_mp3):
        """Very long title is truncated to prevent corruption"""
        long_title = "A" * 5000  # 5000 chars
        song = Song(source=test_mp3, name=long_title)
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Title should be truncated
        audio = MP3(test_mp3, ID3=ID3)
        actual_title = str(audio.tags['TIT2'])
        assert len(actual_title) <= 1000
    
    def test_write_tags_unicode_emoji(self, test_mp3):
        """Unicode and emoji characters are handled correctly"""
        song = Song(
            source=test_mp3,
            name="🎵 Test Song 🎶",
            performers=["Artist 😎"]
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Should be readable
        audio = MP3(test_mp3, ID3=ID3)
        assert "🎵" in str(audio.tags['TIT2'])
    
    def test_write_tags_special_characters(self, test_mp3):
        """Special characters (Croatian, Cyrillic, etc.) work correctly"""
        song = Song(
            source=test_mp3,
            name="Željko Čirić",
            performers=["Владимир"]  # Cyrillic
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        audio = MP3(test_mp3, ID3=ID3)
        assert "Željko" in str(audio.tags['TIT2'])
    
    def test_write_tags_list_with_empty_strings(self, test_mp3):
        """Empty strings in lists are filtered out"""
        song = Song(
            source=test_mp3,
            performers=["Artist 1", "", "  ", "Artist 2", None]
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Should only have valid artists
        audio = MP3(test_mp3, ID3=ID3)
        performers_text = str(audio.tags['TPE1'])
        assert "Artist 1" in performers_text
        assert "Artist 2" in performers_text
    
    def test_write_tags_list_with_non_strings(self, test_mp3):
        """Non-string items in lists are converted/filtered"""
        song = Song(
            source=test_mp3,
            performers=["Artist 1", 123, True, "Artist 2"]
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Should handle conversion
        audio = MP3(test_mp3, ID3=ID3)
        assert 'TPE1' in audio.tags
    
    def test_write_tags_all_fields_none(self, test_mp3):
        """Song with all None fields doesn't crash"""
        song = Song(source=test_mp3)  # All fields None
        
        result = MetadataService.write_tags(song)
        assert result is True  # Should succeed without writing anything
    
    def test_write_tags_extremely_long_isrc(self, test_mp3):
        """Extremely long ISRC is truncated"""
        song = Song(
            source=test_mp3,
            isrc="X" * 1000  # Way too long
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Should be truncated
        audio = MP3(test_mp3, ID3=ID3)
        if 'TSRC' in audio.tags:
            assert len(str(audio.tags['TSRC'])) <= 50
    
    def test_write_tags_negative_year(self, test_mp3):
        """Negative year is rejected"""
        song = Song(
            source=test_mp3,
            recording_year=-100
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Year should not be written
        audio = MP3(test_mp3, ID3=ID3)
        assert 'TDRC' not in audio.tags or '-100' not in str(audio.tags.get('TDRC', ''))
    
    def test_write_tags_zero_bpm(self, test_mp3):
        """Zero BPM is rejected"""
        song = Song(
            source=test_mp3,
            bpm=0
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # BPM should not be written
        audio = MP3(test_mp3, ID3=ID3)
        assert 'TBPM' not in audio.tags or '0' not in str(audio.tags.get('TBPM', ''))
    
    def test_write_tags_newlines_in_title(self, test_mp3):
        """Newlines in title are handled"""
        song = Song(
            source=test_mp3,
            name="Line 1\nLine 2\rLine 3"
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Should write successfully
        audio = MP3(test_mp3, ID3=ID3)
        assert 'TIT2' in audio.tags
    
    def test_write_tags_null_bytes(self, test_mp3):
        """Null bytes in strings are handled"""
        song = Song(
            source=test_mp3,
            name="Test\x00Song"
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Should write successfully
        audio = MP3(test_mp3, ID3=ID3)
        assert 'TIT2' in audio.tags
