"""Unit tests for SongRepository"""
import pytest
import tempfile
import os
from pathlib import Path
from src.data.repositories.song_repository import SongRepository
from src.data.models.song import Song


class TestSongRepository:
    """Test cases for SongRepository"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def repository(self, temp_db):
        """Create a repository instance with temp database"""
        return SongRepository(db_path=temp_db)

    def test_insert_new_file(self, repository):
        """Test inserting a new file"""
        file_id = repository.insert("/path/to/test.mp3")
        assert file_id is not None
        assert file_id > 0

    def test_insert_duplicate_file(self, repository):
        """Test inserting a duplicate file returns None"""
        path = "/path/to/test.mp3"
        file_id1 = repository.insert(path)
        file_id2 = repository.insert(path)

        assert file_id1 is not None
        assert file_id2 is None

    def test_get_all_empty(self, repository):
        """Test getting all songs from empty database"""
        headers, data = repository.get_all()
        assert len(headers) > 0
        assert len(data) == 0

    def test_get_all_with_data(self, repository):
        """Test getting all songs with data"""
        repository.insert("/path/to/song1.mp3")
        repository.insert("/path/to/song2.mp3")

        headers, data = repository.get_all()
        assert len(data) == 2

    def test_delete_existing_file(self, repository):
        """Test deleting an existing file"""
        file_id = repository.insert("/path/to/test.mp3")
        result = repository.delete(file_id)

        assert result is True

        # Verify it's deleted
        _, data = repository.get_all()
        assert len(data) == 0

    def test_delete_nonexistent_file(self, repository):
        """Test deleting a non-existent file"""
        result = repository.delete(9999)
        assert result is False

    def test_update_song(self, repository):
        """Test updating song metadata"""
        # Insert a file first
        file_id = repository.insert("/path/to/test.mp3")

        # Create song with metadata
        song = Song(
            file_id=file_id,
            title="Test Song",
            duration=180.0,
            bpm=120,
            performers=["Artist 1"],
            composers=["Composer 1"]
        )

        # Update
        result = repository.update(song)
        assert result is True

        # Verify update
        headers, data = repository.get_all()
        assert len(data) == 1
        row = data[0]
        # Check title (index 2)
        assert row[2] == "Test Song"

