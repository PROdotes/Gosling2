"""
Robustness tests for AlbumRepository (Level 2: Chaos Monkey).
Per TESTING.md: Tests for malicious input, SQL injection, and edge cases.
"""
import pytest
from src.data.repositories.album_repository import AlbumRepository


class TestAlbumRepositorySecurity:
    """Security and injection tests for AlbumRepository."""
    
    @pytest.fixture
    def repo(self):
        """Fixture providing AlbumRepository instance."""
        return AlbumRepository()
    
    def test_bobby_tables_album_artist(self, repo):
        """
        Bobby Tables won't burn down the bar.
        SQL injection in album_artist should be safely escaped.
        """
        # Classic Bobby Tables attack via album artist
        malicious_artist = "ABBA'; DROP TABLE Albums;--"
        
        # This should NOT drop any tables
        album, created = repo.get_or_create(
            "Mutation_Bobby_Tables", 
            album_artist=malicious_artist, 
            release_year=2024
        )
        
        assert created, "Album should be created despite malicious input"
        assert album.album_id is not None
        
        # Verify Albums table still exists
        found = repo.get_by_id(album.album_id)
        assert found is not None, "Albums table should still exist"
        assert found.album_artist == malicious_artist, "Malicious string should be stored as-is"
        
        # Cleanup
        with repo.get_connection() as conn:
            conn.execute("DELETE FROM Albums WHERE AlbumTitle = 'Mutation_Bobby_Tables'")
