
import pytest
from unittest.mock import MagicMock, patch
from src.data.models.song import Song
from src.business.services.metadata_service import MetadataService
from src.data.repositories.song_repository import SongRepository

class TestISRCImplementation:
    """Test suite for ISRC implementation across the stack"""

    def test_song_model_has_isrc(self):
        """Verify Song model accepts isrc"""
        song = Song(title="Test", isrc="US-S1Z-23-00001")
        assert song.isrc == "US-S1Z-23-00001"
        # Check default is None
        song_empty = Song()
        assert song_empty.isrc is None

    @patch("src.business.services.metadata_service.MP3")
    @patch("src.business.services.metadata_service.ID3")
    def test_metadata_service_extracts_isrc(self, mock_id3, mock_mp3):
        """Verify MetadataService reads TSRC frame"""
        # Setup mock tags
        mock_tags = MagicMock()
        mock_id3.return_value = mock_tags
        
        # Mock the TSRC (ISRC) frame
        # Mutagen access is usually tags["TSRC"] or tags.get("TSRC")
        # MetadataService uses a helper that likely assumes list of strings for text frames
        mock_frame = MagicMock()
        mock_frame.text = ["GB-AYE-65-00001"]
        
        # Setup getall behavior for the service's internal helper
        def side_effect(key):
            if key == "TSRC":
                return [mock_frame]
            return []
            
        mock_tags.getall.side_effect = side_effect
        mock_tags.__contains__.side_effect = lambda k: k == "TSRC"

        # Mock MP3 info for duration
        mock_audio = MagicMock()
        mock_audio.info.length = 120
        mock_mp3.return_value = mock_audio

        song = MetadataService.extract_from_mp3("dummy.mp3")
        assert song.isrc == "GB-AYE-65-00001"

    def test_song_repository_persistence(self, tmp_path):
        """Verify Repository saves and loads ISRC"""
        # Use a temporary DB file
        db_path = tmp_path / "test_isrc.db"
        
        # Initialize repo (should create table with isrc)
        repo = SongRepository(str(db_path))
        
        song = Song(
            path="C:/music/test.mp3",
            title="ISRC Test",
            isrc="US-RC1-76-00123",
            duration=180,
            recording_year=2023,
            performers=["Tester"] 
        )
        
        file_id = repo.insert(song.path)
        # Assuming insert might not take full song object initially based on existing code, 
        # or maybe we need to update it. 
        # Checking existing LibraryService, it calls repo.insert(file_path). 
        # Wait, repo.insert only takes path?
        # Let's check how metadata is saved. 
        # library_service.py: update_song -> repo.update(song)
        
        # So flow is: Insert (Create ID) -> Update (Save Metadata)
        song.file_id = file_id
        repo.update(song)
        
        # Fetch back
        saved_song = repo.get_by_path(song.path)
        assert saved_song.isrc == "US-RC1-76-00123"
