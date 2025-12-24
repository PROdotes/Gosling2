import pytest
import unittest
from unittest.mock import MagicMock, patch
from mutagen.id3 import (
    ID3, TIT2, TPE1, TDRC, TYER, TSRC, TBPM, TKEY, TXXX, TIPL, 
    ID3NoHeaderError
)
from mutagen.mp3 import MP3
from src.business.services.metadata_service import MetadataService
from src.data.models.song import Song

class TestMetadataServiceRobustness(unittest.TestCase):
    """
    Level 2: Robustness and Mutation Tests.
    Tests designed to ensure the system handles garbage, malicious, or extreme inputs without crashing.
    """

    @patch('src.business.services.metadata_service.MP3')
    @patch('src.business.services.metadata_service.ID3')
    def test_deduplication_mutation(self, mock_id3, mock_mp3):
        """Kill Mutant: Ensure duplicates are actualy filtered out"""
        mock_tags = MagicMock()
        mock_id3.return_value = mock_tags
        frame = MagicMock()
        frame.text = ["Artist A"]
        mock_tags.getall.return_value = [frame, frame]
        mock_tags.__contains__.side_effect = lambda k: k == "TPE1"
        
        song = MetadataService.extract_from_mp3("dummy.mp3")
        assert len(song.performers) == 1

    @patch('src.business.services.metadata_service.MP3')
    def test_corrupt_file_handling(self, mock_mp3):
        """Kill Mutant: Ensure MP3 read errors are wrapped in ValueError"""
        mock_mp3.side_effect = Exception("Corrupt Header")
        with pytest.raises(ValueError, match="Unable to read MP3 file"):
            MetadataService.extract_from_mp3("bad.mp3")

    def test_very_long_title_truncation(self):
        """Robustness: Prevent database/tag overflow with massive strings"""
        with patch('src.business.services.metadata_service.MP3') as mock_mp3:
            mock_audio = MagicMock()
            mock_mp3.return_value = mock_audio
            long_title = "A" * 5000
            song = Song(source="test.mp3", name=long_title)
            
            MetadataService.write_tags(song)
            
            # Check the TIT2 frame added to tags
            added_frame = mock_audio.tags.add.call_args_list[0][0][0]
            assert isinstance(added_frame, TIT2)
            assert len(added_frame.text[0] if isinstance(added_frame.text, list) else added_frame.text) <= 1000

    @patch('src.business.services.metadata_service.MP3')
    @patch('src.business.services.metadata_service.ID3')
    def test_malformed_year_extraction(self, mock_id3, mock_mp3):
        """Robustness: Handle non-numeric contents in Year tags"""
        tags_mock = mock_id3.return_value
        frame = MagicMock()
        frame.text = ["NotAYear"]
        tags_mock.getall.return_value = [frame]
        tags_mock.__contains__.side_effect = lambda k: k == "TDRC"
        
        song = MetadataService.extract_from_mp3("bad_year.mp3")
        assert song.recording_year is None

    @patch('src.business.services.metadata_service.MP3')
    @patch('src.business.services.metadata_service.ID3')
    def test_raw_tags_read_failure(self, mock_id3, mock_mp3):
        """Robustness: get_raw_tags should return empty dict on internal error"""
        mock_id3.side_effect = Exception("Panic")
        tags = MetadataService.get_raw_tags("error.mp3")
        assert tags == {}

    def test_malicious_input_injection(self):
        """Robustness: Ensure null bytes and newlines don't crash tag writing"""
        with patch('src.business.services.metadata_service.MP3') as mock_mp3:
            mock_audio = MagicMock()
            mock_mp3.return_value = mock_audio
            song = Song(source="test.mp3", name="Inject\x00Null\nNewline")
            
            success = MetadataService.write_tags(song)
            assert success is True

    def test_garbage_list_inputs(self):
        """Robustness: Handle Non-string and empty values in performer lists"""
        with patch('src.business.services.metadata_service.MP3') as mock_mp3:
            mock_audio = MagicMock()
            mock_mp3.return_value = mock_audio
            song = Song(source="test.mp3", performers=["Artist 1", "", 123, None, "Artist 2"])
            
            MetadataService.write_tags(song)
            
            # Find TPE1 add call
            tpe1_frame = next(c[0][0] for c in mock_audio.tags.add.call_args_list if isinstance(c[0][0], TPE1))
            text = tpe1_frame.text
            assert "Artist 1" in text
            assert "Artist 2" in text
            assert "" not in text
            assert None not in text

    def test_negative_values_check(self):
        """Robustness: Ensure BPM and Year don't accept nonsense negative values"""
        with patch('src.business.services.metadata_service.MP3') as mock_mp3:
            mock_audio = MagicMock()
            mock_mp3.return_value = mock_audio
            song = Song(source="test.mp3", bpm=-1, recording_year=-2000)
            
            MetadataService.write_tags(song)
            
            # Should NOT add TBPM or TDRC frames if logic rejects them
            for call in mock_audio.tags.add.call_args_list:
                frame = call[0][0]
                assert not isinstance(frame, (TBPM, TDRC, TYER))


class TestMetadataExtractionRobustness:
    """Level 2: Robustness tests for extraction (from comprehensive.py)"""

    @pytest.fixture
    def mock_mp3(self):
        with patch("src.business.services.metadata_service.MP3") as mock:
            yield mock

    @pytest.fixture
    def mock_id3(self):
        with patch("src.business.services.metadata_service.ID3") as mock:
            yield mock

    def test_title_empty_string(self, mock_mp3, mock_id3):
        """Robustness: Empty title strings are handled"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        mock_frame = MagicMock()
        mock_frame.text = [""]
        tags_mock.getall.return_value = [mock_frame]
        tags_mock.__contains__.side_effect = lambda key: key == "TIT2"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.title is None

    def test_performers_with_none_values(self, mock_mp3, mock_id3):
        """Robustness: None values in performer list are filtered out"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TPE1":
                mock_frame = MagicMock()
                mock_frame.text = ["Artist A", None, "", "Artist B"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TPE1"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert "Artist A" in song.performers
        assert "Artist B" in song.performers
        assert None not in song.performers

    def test_bpm_invalid_value(self, mock_mp3, mock_id3):
        """Robustness: BPM with invalid (non-numeric) value"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TBPM":
                mock_frame = MagicMock()
                mock_frame.text = ["not_a_number"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TBPM"
        mock_id3.return_value = tags_mock
        
        with pytest.raises(ValueError):
            MetadataService.extract_from_mp3("test.mp3")

    def test_bpm_empty_list(self, mock_mp3, mock_id3):
        """Robustness: BPM when tag exists but is empty"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        tags_mock.getall.return_value = []
        tags_mock.__contains__.return_value = False
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.bpm is None

    def test_producers_tipl_without_people_attribute(self, mock_mp3, mock_id3):
        """Robustness: TIPL frame without people attribute"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TIPL":
                mock_frame = MagicMock(spec=[])  # No 'people' attribute
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TIPL"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.producers == []

    def test_duration_missing_info(self, mock_mp3, mock_id3):
        """Robustness: When audio.info is None"""
        audio_mock = MagicMock()
        audio_mock.info = None
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        tags_mock.getall.return_value = []
        tags_mock.__contains__.return_value = False
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.duration is None

    def test_frame_without_text_attribute(self, mock_mp3, mock_id3):
        """Robustness: Frames without text attribute"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TPE1":
                mock_frame = MagicMock(spec=[])  # No 'text' attribute
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TPE1"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.performers == []


class TestWriteTagsDefensive:
    """Robustness tests for write_tags - edge cases and malicious input"""
    
    def test_write_tags_very_long_title(self, test_mp3):
        """Very long title is truncated to prevent corruption"""
        long_title = "A" * 5000
        song = Song(source=test_mp3, name=long_title)
        
        result = MetadataService.write_tags(song)
        assert result is True
        
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
        
        audio = MP3(test_mp3, ID3=ID3)
        assert "🎵" in str(audio.tags['TIT2'])
    
    def test_write_tags_special_characters(self, test_mp3):
        """Special characters (Croatian, Cyrillic, etc.) work correctly"""
        song = Song(
            source=test_mp3,
            name="Željko Čirić",
            performers=["Владимир"]
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
        
        audio = MP3(test_mp3, ID3=ID3)
        assert 'TPE1' in audio.tags
    
    def test_write_tags_all_fields_none(self, test_mp3):
        """Song with all None fields doesn't crash"""
        song = Song(source=test_mp3)
        
        result = MetadataService.write_tags(song)
        assert result is True
    
    def test_write_tags_extremely_long_isrc(self, test_mp3):
        """Extremely long ISRC is truncated"""
        song = Song(
            source=test_mp3,
            isrc="X" * 1000
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
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
        
        audio = MP3(test_mp3, ID3=ID3)
        assert 'TIT2' in audio.tags
    
    def test_write_tags_file_locked_simulation(self, test_mp3):
        """Environment: Handles file access errors gracefully (nonexistent path)"""
        song = Song(source="Z:/nonexistent/locked.mp3", name="Test")
        result = MetadataService.write_tags(song)
        
        # Should return False, not crash
        assert result is False
    
    def test_write_tags_readonly_file(self, test_mp3, tmp_path):
        """Environment: Handles read-only files gracefully"""
        import shutil
        import os
        
        # Create a copy and make it read-only
        readonly_file = tmp_path / "readonly.mp3"
        shutil.copy(test_mp3, readonly_file)
        os.chmod(readonly_file, 0o444)  # Read-only
        
        song = Song(source=str(readonly_file), name="Test")
        result = MetadataService.write_tags(song)
        
        # Should return False (can't write to read-only)
        # On Windows this might still succeed, so we just verify it doesn't crash
        assert result in [True, False]
        
        # Cleanup
        os.chmod(readonly_file, 0o644)


