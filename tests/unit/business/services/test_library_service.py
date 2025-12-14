"""Unit tests for LibraryService"""
import pytest
import tempfile
import os
from src.business.services.library_service import LibraryService
from src.data.models.song import Song


class TestLibraryService:
    """Test cases for LibraryService"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            db_path = f.name

        # Set the database path for testing
        from src.data.database_config import DatabaseConfig
        original_path = DatabaseConfig.get_database_path
        DatabaseConfig.get_database_path = lambda: db_path

        yield db_path

        # Restore and cleanup
        DatabaseConfig.get_database_path = original_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def service(self, temp_db):
        """Create a service instance"""
        from src.data.repositories import SongRepository, ContributorRepository
        return LibraryService(SongRepository(), ContributorRepository())

    def test_add_file(self, service):
        """Test adding a file to the library"""
        file_id = service.add_file("/path/to/test.mp3")
        assert file_id is not None

    def test_get_all_songs(self, service):
        """Test getting all songs"""
        service.add_file("/path/to/song1.mp3")
        service.add_file("/path/to/song2.mp3")

        headers, data = service.get_all_songs()
        assert len(data) == 2

    def test_delete_song(self, service):
        """Test deleting a song"""
        file_id = service.add_file("/path/to/test.mp3")
        result = service.delete_song(file_id)

        assert result is True

        # Verify deletion
        _, data = service.get_all_songs()
        assert len(data) == 0

    def test_update_song(self, service):
        """Test updating a song"""
        file_id = service.add_file("/path/to/test.mp3")

        song = Song(
            file_id=file_id,
            title="Updated Title",
            duration=200.0,
            bpm=130
        )

        result = service.update_song(song)
        assert result is True

    def test_get_contributors_by_role(self, service):
        """Test getting contributors by role"""
        # Add a song with contributors
        file_id = service.add_file("/path/to/test.mp3")
        song = Song(
            file_id=file_id,
            title="Test Song",
            performers=["performer 1", "performer 2"]
        )
        service.update_song(song)

        # Get performers
        contributors = service.get_contributors_by_role("Performer")
        assert len(contributors) == 2


    def test_get_songs_by_performer(self, service):
        """Test getting songs by performer"""
        # Add a song with performer
        file_id = service.add_file("/path/to/test.mp3")
        song = Song(
            file_id=file_id,
            title="Test Song",
            performers=["Target performer"]
        )
        service.update_song(song)
        
        # Query by performer
        headers, data = service.get_songs_by_performer("Target performer")
        
        # Verify results
        assert headers is not None
        assert len(data) == 1
        # Data format is row values, verify one of them is the performer
        # The exact implementation of get_by_performer isn't shown, but we know it returns a list of lists/tuples
        # One of the fields should be "Target performer" or the song title
        assert "Test Song" in [str(x) for x in data[0]]
