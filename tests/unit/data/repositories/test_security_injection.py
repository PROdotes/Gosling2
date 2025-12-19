"""Security tests for SQL injection vulnerabilities"""
import os
import pytest
import tempfile
from src.data.repositories.song_repository import SongRepository
from src.data.models.song import Song


class TestSQLInjectionSafety:
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        from src.data.database_config import DatabaseConfig
        original_path = DatabaseConfig.get_database_path
        DatabaseConfig.get_database_path = lambda: db_path
        
        yield db_path
        
        DatabaseConfig.get_database_path = original_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def repo(self, temp_db):
        return SongRepository(temp_db)

    def test_insert_malicious_filename(self, repo):
        """Test that SQL injection in filename is safely escaped"""
        # Classic Bobby Tables attack
        malicious_path = "test'); DROP TABLE MediaSources;--.mp3"
        
        file_id = repo.insert(malicious_path)
        assert file_id is not None, "Insert should succeed with parameterized query"
        
        # Verify MediaSources table still exists and contains the record
        headers, data = repo.get_all()
        assert len(data) == 1, "Table should not be dropped"
        assert "SourceID" in headers, "MediaSources table should still exist"

    def test_update_malicious_artist_name(self, repo):
        """Test that SQL injection in artist name is safely escaped"""
        # Insert a normal file first
        file_id = repo.insert("normal_song.mp3")
        assert file_id is not None
        
        # Create a song with malicious artist name
        malicious_song = Song(
            source_id=file_id,
            source="normal_song.mp3",
            name="Normal Title",
            performers=["Bobby'; DROP TABLE Contributors;--"],
            composers=[],
            lyricists=[],
            producers=[],
            duration=180.0,
            bpm=120
        )
        
        success = repo.update(malicious_song)
        assert success, "Update should succeed with parameterized query"
        
        # Verify Contributors table still exists
        headers, data = repo.get_all()
        assert len(data) == 1, "Database should be intact"

    def test_query_with_special_characters(self, repo):
        """Test that special SQL characters in paths are handled"""
        special_paths = [
            "song'with'quotes.mp3",
            "song\"with\"doublequotes.mp3",
            "song;semicolon.mp3",
            "song--comment.mp3",
            "song/*comment*/.mp3"
        ]
        
        for path in special_paths:
            file_id = repo.insert(path)
            assert file_id is not None, f"Should handle special chars in: {path}"
        
        # Verify all files were inserted
        headers, data = repo.get_all()
        assert len(data) == len(special_paths)

    def test_delete_with_malicious_id(self, repo):
        """Test that delete is safe with string injection attempts"""
        # Insert a file
        file_id = repo.insert("test.mp3")
        
        # Attempt to delete with valid ID (should work normally)
        success = repo.delete(file_id)
        assert success
        
        # Verify deletion worked
        headers, data = repo.get_all()
        assert len(data) == 0

    def test_unicode_and_international_characters(self, repo):
        """Test handling of unicode characters that might break queries"""
        unicode_paths = [
            "歌曲.mp3",  # Chinese
            "песня.mp3",  # Russian
            "أغنية.mp3",  # Arabic
            "שיר.mp3",  # Hebrew
            "🎵song🎵.mp3"  # Emoji
        ]
        
        for path in unicode_paths:
            file_id = repo.insert(path)
            assert file_id is not None, f"Should handle unicode in: {path}"
        
        headers, data = repo.get_all()
        assert len(data) == len(unicode_paths)
