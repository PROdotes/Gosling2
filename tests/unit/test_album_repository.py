import unittest
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.repositories.album_repository import AlbumRepository


class TestAlbumRepository(unittest.TestCase):
    """Unit tests for AlbumRepository."""

    def setUp(self):
        self.repo = AlbumRepository()
        self.test_title = "Case_Sensitivity_Test_Album"
        self.cleanup()

    def tearDown(self):
        self.cleanup()

    def cleanup(self):
        # Remove test albums
        try:
            with self.repo.get_connection() as conn:
                conn.execute("DELETE FROM Albums WHERE Title LIKE 'Case_%'")
        except Exception:
            pass

    def test_find_by_title_case_insensitive(self):
        """
        Verify that find_by_title matches regardless of case.
        'Nevermind' should match 'nevermind'.
        """
        # 1. Create album with specific casing
        album = self.repo.create(self.test_title)
        self.assertIsNotNone(album.album_id)

        # 2. Search with different casing
        lower_title = self.test_title.lower()
        found = self.repo.find_by_title(lower_title)

        # 3. Should find the same album
        self.assertIsNotNone(found, f"find_by_title('{lower_title}') returned None. Case sensitivity bug!")
        self.assertEqual(found.album_id, album.album_id)

    def test_update_album(self):
        """
        Verify that update() can rename an album.
        """
        # 1. Create album
        album = self.repo.create("Case_Sensitivity_Typo")
        original_id = album.album_id

        # 2. Rename it
        album.title = "Case_Sensitivity_Fixed"
        success = self.repo.update(album)
        self.assertTrue(success)

        # 3. Old name should not exist
        old = self.repo.find_by_title("Case_Sensitivity_Typo")
        self.assertIsNone(old)

        # 4. New name should exist with same ID
        new = self.repo.find_by_title("Case_Sensitivity_Fixed")
        self.assertIsNotNone(new)
        self.assertEqual(new.album_id, original_id)

    def test_song_on_multiple_albums(self):
        """
        Verify M2M: A song can be on multiple albums.
        After adding to Album1, adding to Album2 should keep both links.
        """
        # Setup: Create two albums
        album1 = self.repo.create("Case_Multi_Album1")
        album2 = self.repo.create("Case_Multi_Album2")

        # Create a "song" (we just need a SourceID, so we fake it via raw insert)
        with self.repo.get_connection() as conn:
            # Insert fake MediaSource
            conn.execute("INSERT INTO MediaSources (TypeID, Name, Source, IsActive) VALUES (1, 'Multi Test', 'C:\\\\Multi.mp3', 1)")
            cursor = conn.execute("SELECT last_insert_rowid()")
            source_id = cursor.fetchone()[0]
            # Insert Songs record
            conn.execute("INSERT INTO Songs (SourceID) VALUES (?)", (source_id,))

        # Add song to Album1
        self.repo.add_song_to_album(source_id, album1.album_id)

        # Add song to Album2
        self.repo.add_song_to_album(source_id, album2.album_id)

        # Verify: Song should be on BOTH albums
        albums = self.repo.get_albums_for_song(source_id)
        album_ids = [a.album_id for a in albums]

        self.assertIn(album1.album_id, album_ids, "Song should still be on Album1")
        self.assertIn(album2.album_id, album_ids, "Song should also be on Album2")
        self.assertEqual(len(albums), 2, "Song should be on exactly 2 albums")

        # Cleanup
        with self.repo.get_connection() as conn:
            conn.execute("DELETE FROM MediaSources WHERE Source = 'C:\\\\Multi.mp3'")

    def test_sync_album_additive(self):
        """
        Verify that SongRepository.update() with song.album adds to existing links,
        not replaces them (M2M compliance).
        """
        from src.data.repositories.song_repository import SongRepository
        import os

        # Setup
        song_repo = SongRepository()
        test_path = os.path.normcase(os.path.abspath("C:\\\\Music\\\\Additive_Test.mp3"))

        # Cleanup old
        with song_repo.get_connection() as conn:
            conn.execute("DELETE FROM MediaSources WHERE Source = ?", (test_path,))
            conn.execute("DELETE FROM Albums WHERE Title LIKE 'Additive_Album%'")

        # 1. Insert song
        source_id = song_repo.insert(test_path)

        # 2. Add to Album1 via update
        song = song_repo.get_by_path(test_path)
        song.album = "Additive_Album1"
        song_repo.update(song)

        # 3. Add to Album2 via update (should NOT remove Album1)
        song = song_repo.get_by_path(test_path)
        song.album = "Additive_Album2"
        song_repo.update(song)

        # 4. Verify: Song should be on BOTH albums
        albums = self.repo.get_albums_for_song(source_id)
        album_titles = [a.title for a in albums]

        self.assertIn("Additive_Album1", album_titles, "Song should still be on Album1 after adding Album2")
        self.assertIn("Additive_Album2", album_titles, "Song should be on Album2")

        # Cleanup
        with song_repo.get_connection() as conn:
            conn.execute("DELETE FROM MediaSources WHERE Source = ?", (test_path,))
            conn.execute("DELETE FROM Albums WHERE Title LIKE 'Additive_Album%'")

    def test_get_or_create(self):
        """Verify get_or_create returns existing album or creates new."""
        # 1. First call creates
        album1, created1 = self.repo.get_or_create("Case_GetOrCreate_Test")
        self.assertTrue(created1)
        self.assertIsNotNone(album1.album_id)

        # 2. Second call returns existing
        album2, created2 = self.repo.get_or_create("Case_GetOrCreate_Test")
        self.assertFalse(created2)
        self.assertEqual(album1.album_id, album2.album_id)

    def test_remove_song_from_album(self):
        """Verify remove_song_from_album unlinks correctly."""
        # Setup
        album = self.repo.create("Case_Remove_Test")

        with self.repo.get_connection() as conn:
            conn.execute("INSERT INTO MediaSources (TypeID, Name, Source, IsActive) VALUES (1, 'Remove Test', 'C:\\\\Remove.mp3', 1)")
            cursor = conn.execute("SELECT last_insert_rowid()")
            source_id = cursor.fetchone()[0]
            conn.execute("INSERT INTO Songs (SourceID) VALUES (?)", (source_id,))

        # Add to album
        self.repo.add_song_to_album(source_id, album.album_id)
        albums = self.repo.get_albums_for_song(source_id)
        self.assertEqual(len(albums), 1)

        # Remove from album
        self.repo.remove_song_from_album(source_id, album.album_id)
        albums = self.repo.get_albums_for_song(source_id)
        self.assertEqual(len(albums), 0)

        # Cleanup
        with self.repo.get_connection() as conn:
            conn.execute("DELETE FROM MediaSources WHERE Source = 'C:\\\\Remove.mp3'")



if __name__ == "__main__":
    unittest.main()
