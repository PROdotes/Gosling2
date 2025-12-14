
import pytest
from unittest.mock import MagicMock, patch, Mock
from src.business.services.metadata_service import MetadataService
from mutagen.id3 import ID3NoHeaderError

class TestMetadataServiceMutation:
    """
    Mutation tests for MetadataService.
    Designed to fail if specific logic paths (fallbacks, dedupe) are removed.
    """

    @patch('src.business.services.metadata_service.MP3')
    @patch('src.business.services.metadata_service.ID3')
    def test_deduplication_logic(self, mock_id3, mock_mp3):
        """
        Kill Mutant: Removed deduplication logic.
        If deduplicate() is removed, we get ['A', 'A'] instead of ['A'].
        """
        # Setup ID3 tags to return duplicate performers
        mock_tags = MagicMock()
        mock_id3.return_value = mock_tags
        
        # Mock getall to return two idential frames
        frame = MagicMock()
        frame.text = ["Artist A"]
        mock_tags.getall.return_value = [frame, frame] # duplicate frames
        
        # Ensure 'TPE1' (Performers) returns these duplicates
        mock_tags.__contains__.side_effect = lambda k: k == "TPE1"
        
        # Execute
        song = MetadataService.extract_from_mp3("dummy.mp3")
        
        # Verify deduplication happened
        assert len(song.performers) == 1
        assert song.performers == ["Artist A"]

    @patch('src.business.services.metadata_service.MP3')
    @patch('src.business.services.metadata_service.ID3')
    def test_producer_extraction_merging(self, mock_id3, mock_mp3):
        """
        Kill Mutant: Removed TIPL or TXXX parsing.
        If we only parse one source, we miss data.
        """
        mock_tags = MagicMock()
        mock_id3.return_value = mock_tags
        
        # Setup TIPL (Producer A)
        tipl_frame = MagicMock()
        tipl_frame.people = [("Producer", "Producer A")]
        
        # Setup TXXX (Producer B)
        txxx_frame = MagicMock()
        txxx_frame.text = ["Producer B"]
        
        def getall_side_effect(key):
            if key == "TIPL": return [tipl_frame]
            if key == "TXXX:PRODUCER": return [txxx_frame]
            return []
            
        mock_tags.getall.side_effect = getall_side_effect
        
        # Allow checking membership
        mock_tags.__contains__.side_effect = lambda k: k in ["TIPL", "TXXX:PRODUCER"]
        
        song = MetadataService.extract_from_mp3("dummy.mp3")
        
        # Must have BOTH
        assert "Producer A" in song.producers
        assert "Producer B" in song.producers
        assert len(song.producers) == 2

    @patch('src.business.services.metadata_service.MP3')
    def test_mp3_read_error(self, mock_mp3):
        """
        Kill Mutant: Removed try/except block for MP3()
        If removed, exception propagates raw instead of wrapped ValueError
        """
        mock_mp3.side_effect = Exception("Corrupt header")
        
        with pytest.raises(ValueError) as exc:
            MetadataService.extract_from_mp3("bad.mp3")
        
        assert "Unable to read MP3 file" in str(exc.value)

    @patch('src.business.services.metadata_service.MP3')
    @patch('src.business.services.metadata_service.ID3')
    def test_id3_missing_handled_gracefully(self, mock_id3, mock_mp3):
        """
        Kill Mutant: Removed ID3NoHeaderError handling.
        If removed, code crashes on files with no tags.
        """
        mock_id3.side_effect = ID3NoHeaderError("No tags")
        
        # Should NOT raise, just return empty attributes
        song = MetadataService.extract_from_mp3("no_tags.mp3")
        
        assert song.title is None
        assert song.performers == []
