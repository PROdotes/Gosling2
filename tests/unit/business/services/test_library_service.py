"""Unit tests for LibraryService"""
import pytest
import tempfile
import os
from src.business.services.library_service import LibraryService
from src.data.models.song import Song


class TestLibraryService:
    """Test cases for LibraryService"""

    @pytest.fixture
    def temp_db(self, monkeypatch):
        """Create a temporary database for testing"""
        # Create a temporary file
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        # Patch the database path
        from src.data.database_config import DatabaseConfig
        monkeypatch.setattr(DatabaseConfig, "get_database_path", lambda: db_path)

        yield db_path

        # Cleanup
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass

    @pytest.fixture
    def service(self, temp_db):
        """Create a service instance with a clean DB"""
        from src.data.repositories import SongRepository, AlbumRepository, PublisherRepository, TagRepository
        from src.business.services import SongService, ContributorService, AlbumService, PublisherService, TagService
        from unittest.mock import MagicMock
        
        song_repo = SongRepository(temp_db)
        alb_repo = AlbumRepository(temp_db)
        pub_repo = PublisherRepository(temp_db)
        tag_repo = TagRepository(temp_db)
        
        song_service = SongService(song_repo)
        cont_service = ContributorService(db_path=temp_db)
        alb_service = AlbumService(alb_repo)
        pub_service = PublisherService(pub_repo)
        tag_service = TagService(tag_repo)
        search_service = MagicMock()
        
        return LibraryService(song_service, cont_service, alb_service, pub_service, tag_service, search_service)

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

        # Fetch the song object to ensure it has the mandatory 'path' field for normalization
        song = service.get_song_by_id(file_id)
        song.name = "Updated Title"
        song.duration = 200.0
        song.bpm = 130

        result = service.update_song(song)
        assert result is True

    def test_get_contributors_by_role(self, service):
        """Test getting contributors by role"""
        # Add a song with contributors
        file_id = service.add_file("/path/to/test.mp3")
        song = service.get_song_by_id(file_id)
        song.performers = ["performer 1", "performer 2"]
        service.update_song(song)

        # Get performers
        contributors = service.get_contributors_by_role("Performer")
        assert len(contributors) == 2


    def test_get_songs_by_performer(self, service):
        """Test getting songs by performer"""
        # Add a song with performer
        file_id = service.add_file("/path/to/test.mp3")
        song = service.get_song_by_id(file_id)
        song.performers = ["Target performer"]
        service.update_song(song)
        
        # Query by performer
        headers, data = service.get_songs_by_performer("Target performer")
        
        # Verify results
        assert headers is not None
        assert len(data) == 1
        # Data format is row values, verify one of them is the performer
        # The exact implementation of get_by_performer isn't shown, but we know it returns a list of lists/tuples
        # One of the fields should be "Target performer" or the song title
        assert "Test Song" in [str(x) for x in data[0]] or "test.mp3" in [str(x) for x in data[0]]

    def test_get_artist_genre_stats(self, service):
        """
        T-108: Verify artist genre statistics calculation.
        Should return a dict of {Genre: count}.
        """
        # Setup: Create songs for "Queen" with specific genres
        # Song 1: Rock
        s1 = Song(source="path/1.mp3", name="Bohemian Rhapsody")
        s1.performers = ["Queen"]
        s1.tags = ["Genre: Rock", "Mood: Epic"]
        service.add_song(s1)
        
        # Song 2: Rock
        s2 = Song(source="path/2.mp3", name="We Will Rock You")
        s2.performers = ["Queen"]
        s2.tags = ["Genre: Rock"]
        service.add_song(s2)
        
        # Song 3: Pop
        s3 = Song(source="path/3.mp3", name="Radio Ga Ga")
        s3.performers = ["Queen"]
        s3.tags = ["Genre: Pop"]
        service.add_song(s3)
        
        # Song 4: Opera (Different Artist check)
        s4 = Song(source="path/4.mp3", name="Nessun Dorma")
        s4.performers = ["Pavarotti"]
        s4.tags = ["Genre: Opera"]
        service.add_song(s4)
        
        # Action
        stats = service.get_artist_genre_stats("Queen")
        
        # Assert
        assert stats == {"Rock": 2, "Pop": 1}
        assert "Opera" not in stats
