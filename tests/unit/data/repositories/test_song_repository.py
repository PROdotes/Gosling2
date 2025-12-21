"""Unit tests for SongRepository"""
import pytest
import tempfile
import os
from unittest.mock import MagicMock, patch
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
            try:
                os.unlink(db_path)
            except PermissionError:
                pass # Can happen if db is still open

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
            source_id=file_id,
            name="Test Song",
            duration=180.0,
            bpm=120,
            performers=["performer 1"],
            composers=["Composer 1"]
        )

        # Update
        result = repository.update(song)
        assert result is True

        # Verify update
        headers, data = repository.get_all()
        assert len(data) == 1
        row = data[0]
        # Check title by looking up the Name column dynamically
        name_idx = headers.index('Name')
        assert row[name_idx] == "Test Song"

    def test_get_by_performer(self, repository):
        """Test getting songs by performer"""
        # Insert a file first
        file_id = repository.insert("/path/to/test.mp3")

        # Update with performer info
        song = Song(
            source_id=file_id,
            name="Test Song",
            performers=["Target performer"]
        )
        repository.update(song)

        # Get by performer
        headers, data = repository.get_by_performer("Target performer")
        assert len(data) == 1
        name_idx = headers.index('Name')
        assert data[0][name_idx] == "Test Song"

        # Get by non-existent performer
        headers, data = repository.get_by_performer("Non-existent")
        assert len(data) == 0

    def test_insert_error(self, repository):
        """Test error handling during insert"""
        with patch.object(repository, 'get_connection') as mock_conn:
            mock_conn.side_effect = Exception("DB Connection Error")
            file_id = repository.insert("path")
            assert file_id is None

    def test_get_all_error(self, repository):
        """Test error handling during get_all"""
        with patch.object(repository, 'get_connection') as mock_conn:
            mock_conn.side_effect = Exception("DB Error")
            headers, data = repository.get_all()
            assert headers == []
            assert data == []

    def test_delete_error(self, repository):
        """Test error handling during delete"""
        with patch.object(repository, 'get_connection') as mock_conn:
            mock_conn.side_effect = Exception("DB Error")
            result = repository.delete(1)
            assert result is False

    def test_update_error(self, repository):
        """Test error handling during update"""
        song = Song(source_id=1, name="Test")
        with patch.object(repository, 'get_connection') as mock_conn:
            mock_conn.side_effect = Exception("DB Error")
            result = repository.update(song)
            assert result is False

    def test_get_by_performer_error(self, repository):
        """Test error handling during get_by_performer"""
        with patch.object(repository, 'get_connection') as mock_conn:
            mock_conn.side_effect = Exception("DB Error")
            headers, data = repository.get_by_performer("performer")
            assert headers == []
            assert data == []

    def test_sync_contributor_roles_branches(self, repository):
        """Test various branches in _sync_contributor_roles"""
        file_id = repository.insert("/path/to/test.mp3")
        
        # 1. Invalid role name (should continue)
        # Note: We can't easily inject invalid role names via Song object because 
        # _sync_contributor_roles uses hardcoded mapping.
        # But we can test empty contributor list "if not contributors: continue"
        
        song_empty = Song(source_id=file_id, name="Empty", performers=[])
        repository.update(song_empty) 
        # Verify no relations created
        with repository.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM MediaSourceContributorRoles WHERE SourceID=?", (file_id,))
            assert cursor.fetchone() is None

        # 2. Empty contributor name "if not contributor_name.strip(): continue"
        song_blank_name = Song(source_id=file_id, name="Blank", performers=["   "])
        repository.update(song_blank_name)
        with repository.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM MediaSourceContributorRoles WHERE SourceID=?", (file_id,))
            assert cursor.fetchone() is None
            
        # 3. Simulate "if not role_row: continue" and "if not contributor_row: continue"
        # Ideally we'd delete a role from DB to test role_row check, 
        # but roles are hardcoded on init. 
        # We can delete "Performer" role from DB temporarily
        with repository.get_connection() as conn:
            conn.execute("DELETE FROM Roles WHERE RoleName='Performer'")
            
        song_missing_role = Song(source_id=file_id, name="Missing Role", performers=["performer"])
        repository.update(song_missing_role)
        # Should not crash, just not add anything

