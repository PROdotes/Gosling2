"""Comprehensive tests for MetadataService covering all edge cases"""
import pytest
from unittest.mock import MagicMock, patch
from mutagen.id3 import ID3NoHeaderError
from src.business.services.metadata_service import MetadataService
from src.data.models.song import Song


class TestMetadataServiceComprehensive:
    """Comprehensive tests for metadata extraction"""

    @pytest.fixture
    def mock_mp3(self):
        with patch("src.business.services.metadata_service.MP3") as mock:
            yield mock

    @pytest.fixture
    def mock_id3(self):
        with patch("src.business.services.metadata_service.ID3") as mock:
            yield mock

    # ===== Title Extraction Tests =====
    
    def test_title_with_whitespace(self, mock_mp3, mock_id3):
        """Test that title whitespace is properly stripped"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        mock_frame = MagicMock()
        mock_frame.text = ["  Title With Spaces  "]
        tags_mock.getall.return_value = [mock_frame]
        tags_mock.__contains__.side_effect = lambda key: key == "TIT2"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.title == "Title With Spaces"

    def test_title_empty_string(self, mock_mp3, mock_id3):
        """Test that empty title strings are handled"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        mock_frame = MagicMock()
        mock_frame.text = [""]
        tags_mock.getall.return_value = [mock_frame]
        tags_mock.__contains__.side_effect = lambda key: key == "TIT2"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        # Empty string is filtered out by get_text_list (falsy check)
        # So title_list becomes empty, and title becomes None
        assert song.title is None

    def test_title_multiple_frames(self, mock_mp3, mock_id3):
        """Test that only first title is used when multiple exist"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        mock_frame = MagicMock()
        mock_frame.text = ["First Title", "Second Title"]
        tags_mock.getall.return_value = [mock_frame]
        tags_mock.__contains__.side_effect = lambda key: key == "TIT2"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.title == "First Title"

    # ===== Performer/Artist Tests =====

    def test_performers_deduplication(self, mock_mp3, mock_id3):
        """Test that duplicate performers are removed while preserving order"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TPE1":
                mock_frame = MagicMock()
                mock_frame.text = ["Artist A", "Artist B", "Artist A", "Artist C"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TPE1"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.performers == ["Artist A", "Artist B", "Artist C"]
        assert len(song.performers) == 3  # No duplicates

    def test_performers_with_none_values(self, mock_mp3, mock_id3):
        """Test that None values in performer list are filtered out"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TPE1":
                mock_frame = MagicMock()
                # Simulate frame with None values
                mock_frame.text = ["Artist A", None, "", "Artist B"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TPE1"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        # None and empty strings should be filtered
        assert "Artist A" in song.performers
        assert "Artist B" in song.performers
        assert None not in song.performers

    def test_performers_multiple_frames(self, mock_mp3, mock_id3):
        """Test handling of multiple TPE1 frames"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TPE1":
                frame1 = MagicMock()
                frame1.text = ["Artist 1"]
                frame2 = MagicMock()
                frame2.text = ["Artist 2"]
                return [frame1, frame2]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TPE1"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert "Artist 1" in song.performers
        assert "Artist 2" in song.performers

    # ===== Composer Tests =====

    def test_composers_extraction(self, mock_mp3, mock_id3):
        """Test composer extraction from TCOM"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TCOM":
                mock_frame = MagicMock()
                mock_frame.text = ["Composer A", "Composer B"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TCOM"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.composers == ["Composer A", "Composer B"]

    # ===== Lyricist Tests =====

    def test_lyricists_from_toly(self, mock_mp3, mock_id3):
        """Test lyricist extraction from TOLY"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TOLY":
                mock_frame = MagicMock()
                mock_frame.text = ["Lyricist A"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TOLY"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.lyricists == ["Lyricist A"]

    def test_lyricists_fallback_to_text(self, mock_mp3, mock_id3):
        """Test lyricist fallback from TOLY to TEXT"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TOLY":
                return []  # No TOLY
            if key == "TEXT":
                mock_frame = MagicMock()
                mock_frame.text = ["Lyricist from TEXT"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TEXT"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.lyricists == ["Lyricist from TEXT"]

    # ===== BPM Tests =====

    def test_bpm_valid_integer(self, mock_mp3, mock_id3):
        """Test BPM extraction with valid integer"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TBPM":
                mock_frame = MagicMock()
                mock_frame.text = ["128"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TBPM"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.bpm == 128
        assert isinstance(song.bpm, int)

    def test_bpm_invalid_value(self, mock_mp3, mock_id3):
        """Test BPM with invalid (non-numeric) value"""
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
        
        # Should raise ValueError when trying to convert to int
        with pytest.raises(ValueError):
            MetadataService.extract_from_mp3("test.mp3")

    def test_bpm_empty_list(self, mock_mp3, mock_id3):
        """Test BPM when tag exists but is empty"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        tags_mock.getall.return_value = []
        tags_mock.__contains__.return_value = False
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.bpm is None

    # ===== Producer Tests =====

    def test_producers_from_tipl_only(self, mock_mp3, mock_id3):
        """Test producer extraction from TIPL"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TIPL":
                mock_frame = MagicMock()
                mock_frame.people = [
                    ("producer", "Producer A"),
                    ("engineer", "Engineer B"),
                    ("Producer", "Producer C"),  # Test case insensitivity
                ]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TIPL"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert "Producer A" in song.producers
        assert "Producer C" in song.producers
        assert "Engineer B" not in song.producers  # Should be filtered
        assert len(song.producers) == 2

    def test_producers_from_txxx_only(self, mock_mp3, mock_id3):
        """Test producer extraction from TXXX:PRODUCER"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TXXX:PRODUCER":
                mock_frame = MagicMock()
                mock_frame.text = ["TXXX Producer"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TXXX:PRODUCER"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert "TXXX Producer" in song.producers

    def test_producers_from_both_tipl_and_txxx(self, mock_mp3, mock_id3):
        """Test producer extraction from both TIPL and TXXX"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TIPL":
                mock_frame = MagicMock()
                mock_frame.people = [("producer", "TIPL Producer")]
                return [mock_frame]
            if key == "TXXX:PRODUCER":
                mock_frame = MagicMock()
                mock_frame.text = ["TXXX Producer"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key in ["TIPL", "TXXX:PRODUCER"]
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert "TIPL Producer" in song.producers
        assert "TXXX Producer" in song.producers
        assert len(song.producers) == 2

    def test_producers_deduplication(self, mock_mp3, mock_id3):
        """Test that duplicate producers are removed"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TIPL":
                mock_frame = MagicMock()
                mock_frame.people = [
                    ("producer", "Same Producer"),
                    ("producer", "Same Producer"),
                ]
                return [mock_frame]
            if key == "TXXX:PRODUCER":
                mock_frame = MagicMock()
                mock_frame.text = ["Same Producer"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key in ["TIPL", "TXXX:PRODUCER"]
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.producers == ["Same Producer"]
        assert len(song.producers) == 1  # Deduplicated

    def test_producers_tipl_without_people_attribute(self, mock_mp3, mock_id3):
        """Test TIPL frame without people attribute"""
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
        assert song.producers == []  # Should handle gracefully

    # ===== Groups Tests =====

    def test_groups_extraction(self, mock_mp3, mock_id3):
        """Test group extraction from TIT1"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TIT1":
                mock_frame = MagicMock()
                mock_frame.text = ["Group A", "Group B"]
                return [mock_frame]
            return []
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TIT1"
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.groups == ["Group A", "Group B"]

    # ===== Duration Tests =====

    def test_duration_extraction(self, mock_mp3, mock_id3):
        """Test duration extraction from audio info"""
        audio_mock = MagicMock()
        audio_mock.info.length = 245.67
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        tags_mock.getall.return_value = []
        tags_mock.__contains__.return_value = False
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.duration == 245.67

    def test_duration_missing_info(self, mock_mp3, mock_id3):
        """Test when audio.info is None"""
        audio_mock = MagicMock()
        audio_mock.info = None
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        tags_mock.getall.return_value = []
        tags_mock.__contains__.return_value = False
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.duration is None

    # ===== Edge Cases =====

    def test_frame_without_text_attribute(self, mock_mp3, mock_id3):
        """Test handling of frames without text attribute"""
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
        assert song.performers == []  # Should handle gracefully

    def test_all_fields_populated(self, mock_mp3, mock_id3):
        """Test extraction with all fields populated"""
        audio_mock = MagicMock()
        audio_mock.info.length = 300.0
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            frames = {
                "TIT2": [MagicMock(text=["Full Title"])],
                "TPE1": [MagicMock(text=["Performer"])],
                "TCOM": [MagicMock(text=["Composer"])],
                "TOLY": [MagicMock(text=["Lyricist"])],
                "TIT1": [MagicMock(text=["Group"])],
                "TBPM": [MagicMock(text=["140"])],
                "TIPL": [MagicMock(people=[("producer", "Producer")])],
            }
            return frames.get(key, [])
        
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key in [
            "TIT2", "TPE1", "TCOM", "TOLY", "TIT1", "TBPM", "TIPL"
        ]
        mock_id3.return_value = tags_mock
        
        song = MetadataService.extract_from_mp3("test.mp3", source_id=42)
        
        assert song.source_id == 42
        assert song.title == "Full Title"
        assert song.duration == 300.0
        assert song.bpm == 140
        assert song.performers == ["Performer"]
        assert song.composers == ["Composer"]
        assert song.lyricists == ["Lyricist"]
        assert song.producers == ["Producer"]
        assert song.groups == ["Group"]
