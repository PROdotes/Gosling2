import pytest
from unittest.mock import MagicMock, patch
from mutagen.id3 import ID3NoHeaderError
from src.business.services.metadata_service import MetadataService
from src.data.models.song import Song

class TestMetadataService:
    @pytest.fixture
    def mock_mp3(self):
        with patch("src.business.services.metadata_service.MP3") as mock:
            yield mock

    @pytest.fixture
    def mock_id3(self):
        with patch("src.business.services.metadata_service.ID3") as mock:
            yield mock

    def test_extract_from_mp3_success(self, mock_mp3, mock_id3):
        # Setup MP3 mock
        audio_mock = MagicMock()
        audio_mock.info.length = 180.5
        mock_mp3.return_value = audio_mock

        # Setup ID3 mock
        tags_mock = MagicMock()
        
        # Helper to simulate getall behaviour
        def getall_side_effect(key):
            mock_frame = MagicMock()
            if key == "TIT2": # Title
                mock_frame.text = ["Test Title"]
                return [mock_frame]
            elif key == "TPE1": # Performer
                mock_frame.text = ["Artist 1", "Artist 2"]
                return [mock_frame]
            elif key == "TBPM": # BPM
                mock_frame.text = ["120"]
                return [mock_frame]
            elif key == "TIPL": # People list (Producer)
                mock_frame.people = [("Producer", "Prod Name"), ("Engineer", "Eng Name")]
                return [mock_frame]
            return []

        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key in ["TIT2", "TPE1", "TBPM", "TIPL"]
        mock_id3.return_value = tags_mock

        song = MetadataService.extract_from_mp3("dummy.mp3", file_id=1)

        assert isinstance(song, Song)
        assert song.file_id == 1
        assert song.title == "Test Title"
        assert song.duration == 180.5
        assert song.bpm == 120
        assert "Artist 1" in song.performers
        assert "Artist 2" in song.performers
        assert "Prod Name" in song.producers
        assert len(song.producers) == 1 # Engineer should be filtered out

    def test_extract_from_mp3_file_error(self, mock_mp3):
        mock_mp3.side_effect = Exception("File not found")
        
        with pytest.raises(ValueError, match="Unable to read MP3 file"):
            MetadataService.extract_from_mp3("invalid.mp3")

    def test_extract_from_mp3_no_tags(self, mock_mp3, mock_id3):
        audio_mock = MagicMock()
        audio_mock.info.length = 200
        mock_mp3.return_value = audio_mock

        mock_id3.side_effect = ID3NoHeaderError("No tags")

        song = MetadataService.extract_from_mp3("no_tags.mp3")

        assert song.duration == 200
        assert song.title is None
        assert song.bpm is None
        assert song.performers == []
        assert song.producers == []

    def test_extract_from_mp3_minimal_tags(self, mock_mp3, mock_id3):
         # Setup MP3 mock
        audio_mock = MagicMock()
        audio_mock.info.length = 100
        mock_mp3.return_value = audio_mock

        # Setup ID3 mock
        tags_mock = MagicMock()
        tags_mock.getall.return_value = []
        tags_mock.__contains__.return_value = False # No specific tags found
        mock_id3.return_value = tags_mock

        song = MetadataService.extract_from_mp3("minimal.mp3")

        assert song.title is None
        assert song.performers == []
    def test_extract_txxx_producer(self, mock_mp3, mock_id3):
        """Test extraction of producer from TXXX frame"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            mock_frame = MagicMock()
            if key == "TXXX:PRODUCER": # TXXX Producer
                mock_frame.text = ["TXXX Prod"]
                return [mock_frame]
            return []

        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TXXX:PRODUCER"
        mock_id3.return_value = tags_mock

        song = MetadataService.extract_from_mp3("txxx.mp3")

        assert "TXXX Prod" in song.producers

    def test_get_raw_tags_exception(self, mock_id3):
        """Verify get_raw_tags returns empty dict on error"""
        mock_id3.side_effect = Exception("Read Error")
        
        tags = MetadataService.get_raw_tags("error.mp3")
        assert tags == {}
        assert isinstance(tags, dict)

    def test_extract_invalid_year(self, mock_mp3, mock_id3):
        """Test resilience against malformed year tags"""
        audio_mock = MagicMock()
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        def getall_side_effect(key):
            if key == "TDRC":
                mock_frame = MagicMock()
                mock_frame.text = ["NotAYear"]
                return [mock_frame]
            return []
            
        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = lambda key: key == "TDRC"
        mock_id3.return_value = tags_mock

        song = MetadataService.extract_from_mp3("bad_year.mp3")
        assert song.recording_year is None

