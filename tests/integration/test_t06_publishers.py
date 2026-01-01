import unittest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.repositories.song_repository import SongRepository
from src.data.repositories.publisher_repository import PublisherRepository

class TestT06Publishers(unittest.TestCase):
    """
    Integration tests for T-06 Publisher Infrastructure
    """

    def setUp(self):
        # Use a temporary test path
        self.test_path = os.path.normcase(os.path.abspath("C:\\Music\\T06_Publisher_Song.mp3"))
        self.test_publisher = "T06 Universal Validation"
        self.test_album = "T06 Validation Album"
        
        self.song_repo = SongRepository()
        self.pub_repo = PublisherRepository()
        
        # Ensure clean state
        self.cleanup()
        
    def tearDown(self):
        self.cleanup()
        
    def cleanup(self):
        try:
            with self.song_repo.get_connection() as conn:
                conn.execute("DELETE FROM Publishers WHERE PublisherName = ?", (self.test_publisher,))
                conn.execute("DELETE FROM Albums WHERE AlbumTitle = ? OR AlbumTitle = 't06_publisher_song.mp3'", (self.test_album,))
                conn.execute("DELETE FROM MediaSources WHERE SourcePath = ?", (self.test_path,))
        except Exception:
            pass

    def test_publisher_on_single(self):
        """
        Scenario 1: Set Publisher on a Song with NO Album.
        Expectation: 
            - Publisher created
            - 'Single' Album auto-created (Title = Song Name)
            - Link: Song -> Single -> Publisher
        """
        # 1. Create Song
        source_id = self.song_repo.insert(self.test_path)
        self.assertIsNotNone(source_id)
        song = self.song_repo.get_by_path(self.test_path)
        
        # 2. Update Publisher (No Album set)
        song.publisher = self.test_publisher
        success = self.song_repo.update(song)
        self.assertTrue(success)
        
        # 3. Verification Read
        song_fresh = self.song_repo.get_by_path(self.test_path)
        self.assertEqual(song_fresh.publisher, [self.test_publisher])
        
        # 4. DB Verification
        pub = self.pub_repo.find_by_name(self.test_publisher)
        self.assertIsNotNone(pub)
        
        # Check Album was auto-created
        # Album name defaults to file name if Song Name was simple (Insert logic uses BaseName)
        # SongRepo.insert uses os.path.basename(file_path) as Name.
        expected_album_title = "t06_publisher_song.mp3" 
        
        # Use existing album repo or raw sql? pub_repo doesn't fetch albums.
        # Let's inspect via raw SQL or album repo if we imported it. 
        # Actually I can rely on song_fresh.album being set!
        self.assertEqual(song_fresh.album, expected_album_title)
        
    def test_publisher_on_existing_album(self):
        """
        Scenario 2: Set Publisher on a Song WITH an Album.
        Expectation:
            - Publisher created/linked to the Album.
        """
        # 1. Create Song
        source_id = self.song_repo.insert(self.test_path)
        song = self.song_repo.get_by_path(self.test_path)
        
        # 2. Set Album First
        song.album = self.test_album
        self.song_repo.update(song)
        
        # 3. Set Publisher
        song.publisher = self.test_publisher
        self.song_repo.update(song)
        
        # 4. Verification
        song_fresh = self.song_repo.get_by_path(self.test_path)
        self.assertEqual(song_fresh.publisher, [self.test_publisher])
        self.assertEqual(song_fresh.album, self.test_album)
        
        # 5. Check Link Table via Repo (Track Override shouldn't touch AlbumPublishers)
        # We need album ID first
        with self.song_repo.get_connection() as conn:
            cursor = conn.execute("SELECT AlbumID FROM Albums WHERE AlbumTitle=?", (self.test_album,))
            album_id = cursor.fetchone()[0]
            
        pubs = self.pub_repo.get_publishers_for_album(album_id)
        # Should be empty or not contain the track override publisher
        self.assertFalse(any(p.publisher_name == self.test_publisher for p in pubs), "Track Override should NOT add to Album Publishers")

if __name__ == "__main__":
    unittest.main()
