"""Tests for MetadataService.write_tags()"""
import pytest
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from unittest.mock import MagicMock
import sys

# Mock PyQt6 before importing app code
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['PyQt6.QtMultimedia'] = MagicMock()

from src.business.services.metadata_service import MetadataService
from src.data.models.song import Song
from tests.unit.business.services.test_metadata_fixtures import (
    test_mp3,
    test_mp3_with_album_art,
    test_mp3_with_comments,
    test_mp3_empty
)


class TestWriteTags:
    """Tests for writing ID3 tags to MP3 files"""
    
    def test_write_tags_basic(self, test_mp3):
        """Write all fields to MP3"""
        song = Song(
            source=test_mp3,
            name="New Title",
            performers=["Artist 1", "Artist 2"],
            composers=["Composer 1"],
            lyricists=["Lyricist 1"],
            producers=["Producer 1"],
            groups=["Group 1"],
            bpm=120,
            recording_year=2023,
            isrc="USRC12345678",
            is_done=True
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Verify by reading back
        audio = MP3(test_mp3, ID3=ID3)
        assert str(audio.tags['TIT2']) == "New Title"
        assert "Artist 1" in str(audio.tags['TPE1'])
        assert "Composer 1" in str(audio.tags['TCOM'])
        assert str(audio.tags['TBPM']) == "120"
        assert "2023" in str(audio.tags['TDRC'])
        assert str(audio.tags['TSRC']) == "USRC12345678"
        assert str(audio.tags['TKEY']) == "true"
        assert "1" in str(audio.tags['TXXX:GOSLING_DONE'])
    
    def test_write_tags_preserves_album_art(self, test_mp3_with_album_art):
        """Album art (APIC) is not deleted when writing tags"""
        song = Song(
            source=test_mp3_with_album_art,
            name="Updated Title",
            performers=["New Artist"]
        )
        
        # Verify album art exists before
        audio_before = MP3(test_mp3_with_album_art, ID3=ID3)
        assert 'APIC:Cover' in audio_before.tags
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Verify album art still exists after
        audio_after = MP3(test_mp3_with_album_art, ID3=ID3)
        assert 'APIC:Cover' in audio_after.tags
        assert str(audio_after.tags['TIT2']) == "Updated Title"
    
    def test_write_tags_preserves_comments(self, test_mp3_with_comments):
        """Comments (COMM) are not deleted when writing tags"""
        song = Song(
            source=test_mp3_with_comments,
            name="Updated Title"
        )
        
        # Verify comment exists before
        audio_before = MP3(test_mp3_with_comments, ID3=ID3)
        assert 'COMM::eng' in audio_before.tags
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Verify comment still exists after
        audio_after = MP3(test_mp3_with_comments, ID3=ID3)
        assert 'COMM::eng' in audio_after.tags
        assert "Important comment" in str(audio_after.tags['COMM::eng'])
    
    def test_write_tags_handles_empty_fields(self, test_mp3):
        """None/empty fields don't delete existing data"""
        # First write some data
        song1 = Song(
            source=test_mp3,
            name="Original Title",
            performers=["Original Artist"],
            bpm=100
        )
        MetadataService.write_tags(song1)
        
        # Simulate "Partial Update" by loading existing, changing one field, and saving.
        # Note: We cannot simply instantiate `Song(name='New')` because Song defaults lists to [],
        # which write_tags correctly interprets as "Delete Field".
        # To test preservation, we must ensure the song object has the data.
        
        song2 = MetadataService.extract_from_mp3(test_mp3)
        song2.name = "New Title"
        # Ensure other fields are present (extract should have done this)
        
        # Test Preservation of BPM explicitly by setting it to None?
        # If we set bpm=None, write_tags should skip it, preserving the file's '100'.
        song2.bpm = None 
        
        MetadataService.write_tags(song2)
        
        # Verify title updated 
        audio = MP3(test_mp3, ID3=ID3)
        assert str(audio.tags['TIT2']) == "New Title"
        
        # Verify performers preserved (because extract loaded them, and we didn't touch them)
        assert 'TPE1' in audio.tags
        assert "Original Artist" in str(audio.tags['TPE1'])

        # Verify BPM preserved (because we passed None, triggering sparse update skip)
        assert 'TBPM' in audio.tags
        assert "100" in str(audio.tags['TBPM'])
    
    def test_write_tags_is_done_true(self, test_mp3):
        """is_done=True writes TKEY='true' and TXXX:GOSLING_DONE='1'"""
        song = Song(source=test_mp3, name="Test", is_done=True)
        
        MetadataService.write_tags(song)
        
        audio = MP3(test_mp3, ID3=ID3)
        assert str(audio.tags['TKEY']) == "true"
        assert "1" in str(audio.tags['TXXX:GOSLING_DONE'])
    
    def test_write_tags_is_done_false(self, test_mp3):
        """is_done=False writes TKEY=' ' and TXXX:GOSLING_DONE='0'"""
        song = Song(source=test_mp3, name="Test", is_done=False)
        
        MetadataService.write_tags(song)
        
        audio = MP3(test_mp3, ID3=ID3)
        assert str(audio.tags['TKEY']) == " "
        assert "0" in str(audio.tags['TXXX:GOSLING_DONE'])
    
    def test_write_tags_roundtrip(self, test_mp3):
        """Write then read, data matches"""
        original_song = Song(
            source=test_mp3,
            name="Roundtrip Test",
            performers=["Artist A", "Artist B"],
            composers=["Composer X"],
            bpm=140,
            recording_year=2024,
            isrc="TEST12345678",
            is_done=True
        )
        
        # Write
        result = MetadataService.write_tags(original_song)
        assert result is True
        
        # Read back
        read_song = MetadataService.extract_from_mp3(test_mp3)
        
        # Verify
        assert read_song.title == original_song.title
        assert read_song.performers == original_song.performers
        assert read_song.composers == original_song.composers
        assert read_song.bpm == original_song.bpm
        assert read_song.recording_year == original_song.recording_year
        assert read_song.isrc == original_song.isrc
        assert read_song.is_done == original_song.is_done
    
    def test_write_tags_invalid_file(self, tmp_path):
        """Returns False for non-MP3 file"""
        bad_file = tmp_path / "not_an_mp3.txt"
        bad_file.write_text("This is not an MP3")
        
        song = Song(source=str(bad_file), name="Test")
        result = MetadataService.write_tags(song)
        
        assert result is False
    
    def test_write_tags_no_path(self):
        """Returns False if song has no path"""
        song = Song(name="Test")  # No path
        result = MetadataService.write_tags(song)
        
        assert result is False
    
    def test_write_tags_creates_tags_if_missing(self, test_mp3_empty):
        """Creates ID3v2 tags if file has none"""
        song = Song(
            source=test_mp3_empty,
            name="New Song",
            performers=["New Artist"]
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Verify tags were created
        audio = MP3(test_mp3_empty, ID3=ID3)
        assert audio.tags is not None
        assert 'TIT2' in audio.tags
        assert 'TPE1' in audio.tags
    
    def test_write_tags_handles_multiple_performers(self, test_mp3):
        """Multiple performers are written correctly"""
        song = Song(
            source=test_mp3,
            performers=["Artist 1", "Artist 2", "Artist 3"]
        )
        
        MetadataService.write_tags(song)
        
        audio = MP3(test_mp3, ID3=ID3)
        performers_text = str(audio.tags['TPE1'])
        assert "Artist 1" in performers_text
        assert "Artist 2" in performers_text
        assert "Artist 3" in performers_text
    
    def test_write_tags_producers_dual_mode(self, test_mp3):
        """Producers written to both TIPL and TXXX:PRODUCER"""
        song = Song(
            source=test_mp3,
            producers=["Producer A", "Producer B"]
        )
        
        MetadataService.write_tags(song)
        
        audio = MP3(test_mp3, ID3=ID3)
        # Check TIPL
        assert 'TIPL' in audio.tags
        # Check TXXX:PRODUCER
        assert 'TXXX:PRODUCER' in audio.tags
        assert "Producer A" in str(audio.tags['TXXX:PRODUCER'])
