
import unittest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.repositories.song_repository import SongRepository
from src.data.repositories.tag_repository import TagRepository

class TestT06Tags(unittest.TestCase):
    """
    Integration tests for T-06 Tags/Genre Infrastructure
    """

    def setUp(self):
        self.test_path = os.path.normcase(os.path.abspath("C:\\Music\\T06_Genre_Song.mp3"))
        self.song_repo = SongRepository()
        self.tag_repo = TagRepository()
        self.cleanup()

    def tearDown(self):
        self.cleanup()
        
    def cleanup(self):
        try:
            with self.song_repo.get_connection() as conn:
                conn.execute("DELETE FROM Tags WHERE TagName LIKE 'T06_%'")
                conn.execute("DELETE FROM MediaSources WHERE SourcePath = ?", (self.test_path,))
        except Exception:
            pass

    def test_basic_tag_crud(self):
        """Test basic TagRepository operations independent of Songs."""
        # 1. Create
        tag = self.tag_repo.create("T06_Test_Genre", "Genre")
        self.assertIsNotNone(tag.tag_id)
        
        # 2. Find
        found = self.tag_repo.find_by_name("T06_Test_Genre", "Genre")
        self.assertIsNotNone(found)
        self.assertEqual(found.tag_id, tag.tag_id)
        
        # 3. Get or Create (Existing)
        tag2, created = self.tag_repo.get_or_create("T06_Test_Genre", "Genre")
        self.assertFalse(created)
        self.assertEqual(tag2.tag_id, tag.tag_id)
        
        # 4. Get or Create (New)
        tag3, created = self.tag_repo.get_or_create("T06_New_Genre", "Genre")
        self.assertTrue(created)
        self.assertNotEqual(tag3.tag_id, tag.tag_id)

    def test_sync_genre_creation(self):
        """Test that updating a Song creates and links Tags."""
        # 1. Insert Song
        source_id = self.song_repo.insert(self.test_path)
        song = self.song_repo.get_by_path(self.test_path)
        
        # 2. Set Genre via unified tags
        song.tags = ["Genre:T06_Rock", "Genre:T06_Pop"]
        self.song_repo.update(song)
        
        # 3. Verify Tags Created
        rock = self.tag_repo.find_by_name("T06_Rock", "Genre")
        pop = self.tag_repo.find_by_name("T06_Pop", "Genre")
        self.assertIsNotNone(rock)
        self.assertIsNotNone(pop)
        
        # 4. Verify Links
        tags = self.tag_repo.get_tags_for_source(source_id, "Genre")
        tag_names = [t.tag_name for t in tags]
        self.assertIn("T06_Rock", tag_names)
        self.assertIn("T06_Pop", tag_names)
        self.assertEqual(len(tags), 2)

    def test_sync_genre_replacement(self):
        """Test that changing genre replaces old genre tags."""
        # 1. Setup with initial genre
        source_id = self.song_repo.insert(self.test_path)
        song = self.song_repo.get_by_path(self.test_path)
        song.tags = ["Genre:T06_Old"]
        self.song_repo.update(song)
        
        # Verify initial
        tags = self.tag_repo.get_tags_for_source(source_id, "Genre")
        self.assertEqual(tags[0].tag_name, "T06_Old")
        
        # 2. Update to new genre
        song.tags = ["Genre:T06_New"]
        self.song_repo.update(song)
        
        # 3. Verify Replacement
        tags = self.tag_repo.get_tags_for_source(source_id, "Genre")
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].tag_name, "T06_New")
        
        # Ensure 'T06_Old' link is gone
        links = self.tag_repo.get_tags_for_source(source_id)
        old_links = [t for t in links if t.tag_name == "T06_Old"]
        self.assertEqual(len(old_links), 0)

    def test_case_sensitivity(self):
        """Test that 'Rock' and 'rock' map to same tag."""
        # 1. Create 'T06_Case'
        self.tag_repo.create("T06_Case", "Genre")
        
        # 2. Update song with lowercase 't06_case'
        source_id = self.song_repo.insert(self.test_path)
        song = self.song_repo.get_by_path(self.test_path)
        song.tags = ["Genre:t06_case"]
        self.song_repo.update(song)
        
        # 3. Verify it used the existing tag
        tags = self.tag_repo.get_tags_for_source(source_id, "Genre")
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].tag_name, "T06_Case") # Should preserve DB casing
        
        # 4. Ensure no duplicate tag created
        with self.tag_repo.get_connection() as conn:
            cursor = conn.execute("SELECT Count(*) FROM Tags WHERE TagName LIKE 'T06_Case'")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)

if __name__ == "__main__":
    unittest.main()
