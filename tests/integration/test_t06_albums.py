import unittest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.repositories.song_repository import SongRepository
from src.data.models.song import Song
from src.data.repositories.album_repository import AlbumRepository

class TestT06Albums(unittest.TestCase):
    """
    Integration tests for T-06 Album Infrastructure
    TODO: [USER_REVIEW_PENDING] Please review this test logic when time permits.
    """

    def setUp(self):
        # Use a temporary test path
        self.test_path = os.path.normcase(os.path.abspath("C:\\Music\\T06_Test_Song.mp3"))
        self.test_album = "T06 Validation Album"
        
        self.song_repo = SongRepository()
        self.album_repo = AlbumRepository()
        
        # Ensure clean state
        self.cleanup()
        
    def tearDown(self):
        self.cleanup()
        
    def cleanup(self):
        try:
            with self.song_repo.get_connection() as conn:
                conn.execute("DELETE FROM Albums WHERE AlbumTitle = ?", (self.test_album,))
                conn.execute("DELETE FROM MediaSources WHERE SourcePath = ?", (self.test_path,))
        except Exception:
            pass

    def test_full_album_cycle(self):
        """
        Verify that:
        1. We can create a song.
        2. We can update it with an Album string.
        3. This creates the Album entity in DB.
        4. This links Song -> Album.
        5. We can read it back.
        """
        # 1. Create Song
        source_id = self.song_repo.insert(self.test_path)
        self.assertIsNotNone(source_id, "Failed to insert test song")
        
        # 2. Get the song object to update
        song = self.song_repo.get_by_path(self.test_path)
        self.assertIsNotNone(song, "Failed to read back test song")
        self.assertEqual(song.album, [], "New song should have no album")

        # 3. Update with Album
        song.album = self.test_album
        success = self.song_repo.update(song)
        self.assertTrue(success, "SongRepository.update failed")
        
        # 4. Verification Read (Integration)
        song_fresh = self.song_repo.get_by_path(self.test_path)
        self.assertEqual(song_fresh.album, self.test_album, "Song album was not persisted or retrieved correctly")
        
        # 5. Verification DB (Infrastructure)
        found_album = self.album_repo.find_by_title(self.test_album)
        self.assertIsNotNone(found_album, "Album entity was not created in Albums table")
        self.assertEqual(found_album.title, self.test_album)

        print(f"\n[PASS] T-06 Integration Passed: Song '{song.name}' linked to Created Album '{found_album.title}'")

if __name__ == "__main__":
    unittest.main()
