import pytest
import os
import json
from unittest.mock import MagicMock, patch
from mutagen.id3 import (
    ID3, TIT2, TPE1, TDRC, TYER, TSRC, TBPM, TKEY, TXXX, TIPL
)
from mutagen.mp3 import MP3
from src.business.services.metadata_service import MetadataService
from src.data.models.song import Song
from src.core import yellberus

class TestMetadataServiceRobustness:
    """
    Level 2: Robustness and Mutation Tests.
    Ensures the system handles garbage, malicious, or extreme inputs without crashing.
    """

    @pytest.fixture
    def mock_mp3(self):
        with patch("src.business.services.metadata_service.MP3") as mock:
            yield mock

    @pytest.fixture
    def mock_id3(self):
        with patch("src.business.services.metadata_service.ID3") as mock:
            yield mock

    def _setup_mock_tags(self, tags_dict, mock_id3, audio_mock=None):
        mock_tags = MagicMock()
        mock_tags.keys.return_value = list(tags_dict.keys())
        mock_tags.__getitem__.side_effect = lambda k: tags_dict.get(k)
        mock_tags.get.side_effect = lambda k, default=None: tags_dict.get(k, default)
        mock_tags.__contains__.side_effect = lambda k: k in tags_dict
        mock_id3.return_value = mock_tags
        if audio_mock:
            audio_mock.tags = mock_tags
        return mock_tags

    # --- EXTRACTION TESTS ---

    def test_deduplication_mutation(self, mock_mp3, mock_id3):
        """Kill Mutant: Ensure duplicates are actually filtered out"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        mock_frame = MagicMock()
        mock_frame.text = ["Artist A", "Artist A"]
        self._setup_mock_tags({"TPE1": mock_frame}, mock_id3, audio_mock)
        
        song = MetadataService.extract_from_mp3("dummy.mp3")
        assert len(song.performers) == 1
        assert song.performers[0] == "Artist A"

    def test_corrupt_file_handling(self, mock_mp3):
        """Kill Mutant: Ensure MP3 read errors are wrapped in ValueError"""
        mock_mp3.side_effect = Exception("Corrupt Header")
        with pytest.raises(ValueError, match="Unable to read MP3 file"):
            MetadataService.extract_from_mp3("bad.mp3")

    def test_malformed_year_extraction(self, mock_mp3, mock_id3):
        """Robustness: Handle non-numeric contents in Year tags"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        mock_frame = MagicMock()
        mock_frame.text = ["NotAYear"]
        self._setup_mock_tags({"TDRC": mock_frame}, mock_id3, audio_mock)
        
        song = MetadataService.extract_from_mp3("bad_year.mp3")
        assert song.recording_year is None

    def test_title_empty_string(self, mock_mp3, mock_id3):
        """Robustness: Empty title strings are handled"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        mock_frame = MagicMock()
        mock_frame.text = [""]
        self._setup_mock_tags({"TIT2": mock_frame}, mock_id3, audio_mock)
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.title is None

    def test_performers_with_none_values(self, mock_mp3, mock_id3):
        """Robustness: None values in performer list are filtered out"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        mock_frame = MagicMock()
        mock_frame.text = ["Artist A", None, "", "Artist B"]
        self._setup_mock_tags({"TPE1": mock_frame}, mock_id3, audio_mock)
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert "Artist A" in song.performers
        assert "Artist B" in song.performers
        assert None not in song.performers
        assert "None" not in song.performers

    def test_bpm_invalid_value(self, mock_mp3, mock_id3):
        """Robustness: BPM with invalid (non-numeric) value should be None (resilient)"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        mock_frame = MagicMock()
        mock_frame.text = ["not_a_number"]
        self._setup_mock_tags({"TBPM": mock_frame}, mock_id3, audio_mock)
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.bpm is None

    def test_bpm_empty_list(self, mock_mp3, mock_id3):
        """Robustness: BPM when tag exists but is empty"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        self._setup_mock_tags({}, mock_id3, audio_mock)
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.bpm is None

    def test_producers_tipl_without_people_attribute(self, mock_mp3, mock_id3):
        """Robustness: TIPL frame without people attribute"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        mock_frame = MagicMock()
        # Ensure it does NOT have 'people'
        del mock_frame.people 
        self._setup_mock_tags({"TIPL": mock_frame}, mock_id3, audio_mock)
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.producers == []

    def test_duration_missing_info(self, mock_mp3, mock_id3):
        """Robustness: When audio.info is None"""
        audio_mock = MagicMock()
        audio_mock.info = None
        mock_mp3.return_value = audio_mock
        self._setup_mock_tags({}, mock_id3, audio_mock)
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.duration is None

    def test_frame_without_text_attribute(self, mock_mp3, mock_id3):
        """Robustness: Frames without text attribute should be ignored"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        # We use a mock that doesn't have .text.
        # It will be skipped because it's a mutagen-like object without text/people.
        mock_frame = MagicMock()
        del mock_frame.text
        del mock_frame.people
        
        self._setup_mock_tags({"TPE1": mock_frame}, mock_id3, audio_mock)
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.performers == []

    # --- WRITING TESTS ---

    def test_very_long_title_truncation(self, mock_mp3):
        """Robustness: Prevent database/tag overflow with massive strings"""
        mock_audio = MagicMock()
        mock_mp3.return_value = mock_audio
        long_title = "A" * 5000
        song = Song(source="test.mp3", name=long_title)
        
        MetadataService.write_tags(song)
        
        # Check the TIT2 frame added to tags
        added_frame = next(c[0][0] for c in mock_audio.tags.add.call_args_list if isinstance(c[0][0], TIT2))
        assert len(added_frame.text[0]) <= 1000

    def test_malicious_input_injection(self, mock_mp3):
        """Robustness: Ensure null bytes and newlines don't crash tag writing"""
        mock_audio = MagicMock()
        mock_mp3.return_value = mock_audio
        song = Song(source="test.mp3", name="Inject\x00Null\nNewline")
        
        success = MetadataService.write_tags(song)
        assert success is True

    def test_garbage_list_inputs(self, mock_mp3):
        """Robustness: Handle Non-string and empty values in performer lists"""
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

    def test_invalid_year_bpm_not_written(self, mock_mp3):
        """Robustness: Invalid numerical values are skipped during write"""
        mock_audio = MagicMock()
        mock_mp3.return_value = mock_audio
        song = Song(source="test.mp3", recording_year=2500, bpm=-10)
        
        MetadataService.write_tags(song)
        
        # Should NOT add TBPM or TDRC frames if logic rejects them
        for call in mock_audio.tags.add.call_args_list:
            frame = call[0][0]
            assert not isinstance(frame, (TBPM, TDRC, TYER))

    def test_write_tags_file_locked_simulation(self, mock_mp3):
        """Environment: Handles file access errors gracefully"""
        mock_mp3.side_effect = Exception("Permission Denied")
        song = Song(source="locked.mp3", name="Test")
        result = MetadataService.write_tags(song)
        assert result is False

    def test_write_tags_readonly_file(self, mock_mp3):
        """Environment: Handles read-only or permission-denied files gracefully during save"""
        # 1. Setup mock audio that raises error ONLY on save
        audio_mock = MagicMock()
        audio_mock.save.side_effect = PermissionError("File is read-only")
        mock_mp3.return_value = audio_mock
        
        # 2. Trigger write
        song = Song(source="test.mp3", name="Test")
        result = MetadataService.write_tags(song)
        
        # 3. Verify graceful failure
        assert result is False
        audio_mock.save.assert_called_once()
