import pytest
from unittest.mock import MagicMock, patch
from src.business.services.metadata_service import MetadataService
from src.data.models.song import Song

class TestMetadataDoneFlag:
    """
    Tests for the 'Done' flag logic (TKEY/TXXX migration).
    
    See ID3_ANALYSIS.md for the "Transition Protocol".
    1. TXXX:GOSLING_DONE takes precedence.
    2. TKEY is checked as fallback (Legacy "true" string).
    """

    @pytest.fixture
    def mock_mp3(self):
        with patch("src.business.services.metadata_service.MP3") as mock:
            yield mock

    @pytest.fixture
    def mock_id3(self):
        with patch("src.business.services.metadata_service.ID3") as mock:
            yield mock

    def test_read_done_flag_primary_txxx_true(self, mock_mp3, mock_id3):
        """Should read True from TXXX:GOSLING_DONE='1'"""
        self._setup_mocks(mock_mp3, mock_id3, txxx_done="1")
        song = MetadataService.extract_from_mp3("test.mp3")
        
        # NOTE: 'is_done' field is not yet on Song model. This test expects it to be added.
        assert getattr(song, "is_done", None) is True

    def test_read_done_flag_primary_txxx_false(self, mock_mp3, mock_id3):
        """Should read False from TXXX:GOSLING_DONE='0' even if TKEY is 'true'"""
        # Scenario: User marked as NOT DONE in new app, but old app still has "true" left over.
        # New tag must win.
        self._setup_mocks(mock_mp3, mock_id3, txxx_done="0", tkey="true")
        song = MetadataService.extract_from_mp3("test.mp3")
        
        assert getattr(song, "is_done", None) is False

    def test_read_done_flag_legacy_tkey_true(self, mock_mp3, mock_id3):
        """Should fallback to True from TKEY='true' if TXXX is missing"""
        self._setup_mocks(mock_mp3, mock_id3, tkey="true")
        song = MetadataService.extract_from_mp3("test.mp3")
        
        assert getattr(song, "is_done", None) is True

    def test_read_done_flag_legacy_tkey_false(self, mock_mp3, mock_id3):
        """Should read False from TKEY=' ' (space) or missing"""
        self._setup_mocks(mock_mp3, mock_id3, tkey=" ")
        song = MetadataService.extract_from_mp3("test.mp3")
        
        # Default should be False/None
        assert not getattr(song, "is_done", False)

    def test_read_done_flag_real_musical_key(self, mock_mp3, mock_id3):
        """Should NOT treat a real musical key (e.g. 'Am') as Done=True"""
        self._setup_mocks(mock_mp3, mock_id3, tkey="Am")
        song = MetadataService.extract_from_mp3("test.mp3")
        
        assert not getattr(song, "is_done", False)

    def _setup_mocks(self, mock_mp3, mock_id3, txxx_done=None, tkey=None):
        """Helper to mock ID3 tags"""
        audio_mock = MagicMock()
        audio_mock.info.length = 120
        mock_mp3.return_value = audio_mock
        
        tags_mock = MagicMock()
        
        def getall_side_effect(key):
            if key == "TXXX:GOSLING_DONE" and txxx_done is not None:
                m = MagicMock()
                m.text = [txxx_done]
                return [m]
            if key == "TKEY" and tkey is not None:
                m = MagicMock()
                m.text = [tkey]
                return [m]
            return []

        def contains_side_effect(key):
            if key == "TXXX:GOSLING_DONE": return txxx_done is not None
            if key == "TKEY": return tkey is not None
            return False

        tags_mock.getall.side_effect = getall_side_effect
        tags_mock.__contains__.side_effect = contains_side_effect
        mock_id3.return_value = tags_mock
