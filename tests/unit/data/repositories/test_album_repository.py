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


    # ==================== GREATEST HITS FIX TESTS ====================
    # Tests for album artist disambiguation (T-06 / 2025-12-23)

    def test_greatest_hits_different_artists(self):
        """
        THE GREATEST HITS PARADOX: 
        'Greatest Hits' by Queen and 'Greatest Hits' by ABBA must be SEPARATE albums.
        """
        # Create ABBA's Greatest Hits
        abba, created1 = self.repo.get_or_create("Case_Greatest_Hits", album_artist="ABBA", release_year=1992)
        self.assertTrue(created1, "ABBA album should be created")
        
        # Create Queen's Greatest Hits (same title, different artist)
        queen, created2 = self.repo.get_or_create("Case_Greatest_Hits", album_artist="Queen", release_year=1981)
        self.assertTrue(created2, "Queen album should be created (NOT reuse ABBA's)")
        
        # They should have DIFFERENT IDs
        self.assertNotEqual(abba.album_id, queen.album_id, 
            "CRITICAL: Queen and ABBA albums merged! Greatest Hits fix failed.")
        
        # Verify we can retrieve each independently
        found_abba = self.repo.find_by_key("Case_Greatest_Hits", album_artist="ABBA", release_year=1992)
        found_queen = self.repo.find_by_key("Case_Greatest_Hits", album_artist="Queen", release_year=1981)
        
        self.assertIsNotNone(found_abba)
        self.assertIsNotNone(found_queen)
        self.assertEqual(found_abba.album_id, abba.album_id)
        self.assertEqual(found_queen.album_id, queen.album_id)
        
        # Cleanup
        with self.repo.get_connection() as conn:
            conn.execute("DELETE FROM Albums WHERE Title = 'Case_Greatest_Hits'")

    def test_same_artist_different_years(self):
        """
        Same artist, same title, different years = different albums.
        E.g., 'Greatest Hits 1981' vs 'Greatest Hits 2011 Remaster'
        """
        album_1981, created1 = self.repo.get_or_create("Case_Same_Artist", album_artist="Queen", release_year=1981)
        album_2011, created2 = self.repo.get_or_create("Case_Same_Artist", album_artist="Queen", release_year=2011)
        
        self.assertTrue(created1)
        self.assertTrue(created2, "Different year should create new album")
        self.assertNotEqual(album_1981.album_id, album_2011.album_id)
        
        # Cleanup
        with self.repo.get_connection() as conn:
            conn.execute("DELETE FROM Albums WHERE Title = 'Case_Same_Artist'")

    def test_same_artist_same_year_reuses(self):
        """
        Same artist, same title, same year = same album (reuse).
        """
        album1, created1 = self.repo.get_or_create("Case_Reuse_Test", album_artist="Nirvana", release_year=1991)
        album2, created2 = self.repo.get_or_create("Case_Reuse_Test", album_artist="Nirvana", release_year=1991)
        
        self.assertTrue(created1)
        self.assertFalse(created2, "Should reuse existing album")
        self.assertEqual(album1.album_id, album2.album_id)
        
        # Cleanup
        with self.repo.get_connection() as conn:
            conn.execute("DELETE FROM Albums WHERE Title = 'Case_Reuse_Test'")

    def test_null_artist_handling(self):
        """
        Albums with NULL artist should be distinguishable from each other by year.
        Two compilations with no artist but different years = separate.
        """
        comp_2020, created1 = self.repo.get_or_create("Case_Compilation", album_artist=None, release_year=2020)
        comp_2021, created2 = self.repo.get_or_create("Case_Compilation", album_artist=None, release_year=2021)
        
        self.assertTrue(created1)
        self.assertTrue(created2, "Different year compilations should be separate")
        self.assertNotEqual(comp_2020.album_id, comp_2021.album_id)
        
        # Same title, same year, both NULL artist = same album
        comp_2020_again, created3 = self.repo.get_or_create("Case_Compilation", album_artist=None, release_year=2020)
        self.assertFalse(created3, "Should reuse existing NULL artist album")
        self.assertEqual(comp_2020.album_id, comp_2020_again.album_id)
        
        # Cleanup
        with self.repo.get_connection() as conn:
            conn.execute("DELETE FROM Albums WHERE Title = 'Case_Compilation'")

    def test_artist_case_insensitive(self):
        """
        Artist matching should be case-insensitive.
        'queen' should match 'Queen'.
        """
        album1, created1 = self.repo.get_or_create("Case_Artist_Case", album_artist="Queen", release_year=1981)
        album2, created2 = self.repo.get_or_create("Case_Artist_Case", album_artist="queen", release_year=1981)
        
        self.assertTrue(created1)
        self.assertFalse(created2, "Case difference should not create new album")
        self.assertEqual(album1.album_id, album2.album_id)
        
        # Cleanup
        with self.repo.get_connection() as conn:
            conn.execute("DELETE FROM Albums WHERE Title = 'Case_Artist_Case'")

    def test_create_with_album_artist(self):
        """
        Verify create() stores album_artist correctly.
        """
        album = self.repo.create("Case_Create_Artist_Test", album_artist="The Beatles", release_year=1965)
        
        self.assertIsNotNone(album.album_id)
        self.assertEqual(album.album_artist, "The Beatles")
        self.assertEqual(album.release_year, 1965)
        
        # Retrieve and verify
        found = self.repo.get_by_id(album.album_id)
        self.assertEqual(found.album_artist, "The Beatles")
        
        # Cleanup
        with self.repo.get_connection() as conn:
            conn.execute("DELETE FROM Albums WHERE Title = 'Case_Create_Artist_Test'")

    def test_find_by_key_with_all_fields(self):
        """
        Verify find_by_key works with all three disambiguation fields.
        """
        # Create album
        self.repo.create("Case_FindKey_Test", album_artist="Pink Floyd", album_type="Album", release_year=1973)
        
        # Find with all fields
        found = self.repo.find_by_key("Case_FindKey_Test", album_artist="Pink Floyd", release_year=1973)
        self.assertIsNotNone(found)
        self.assertEqual(found.album_artist, "Pink Floyd")
        
        # Wrong artist should not find
        not_found = self.repo.find_by_key("Case_FindKey_Test", album_artist="Led Zeppelin", release_year=1973)
        self.assertIsNone(not_found)
        
        # Cleanup
        with self.repo.get_connection() as conn:
            conn.execute("DELETE FROM Albums WHERE Title = 'Case_FindKey_Test'")

    def test_bobby_tables_album_artist(self):
        """
        Bobby Tables won't burn down the bar.
        SQL injection in album_artist should be safely escaped.
        """
        # Classic Bobby Tables attack via album artist
        malicious_artist = "ABBA'; DROP TABLE Albums;--"
        
        # This should NOT drop any tables
        album, created = self.repo.get_or_create(
            "Case_Bobby_Tables", 
            album_artist=malicious_artist, 
            release_year=2024
        )
        
        self.assertTrue(created, "Album should be created despite malicious input")
        self.assertIsNotNone(album.album_id)
        
        # Verify Albums table still exists
        found = self.repo.get_by_id(album.album_id)
        self.assertIsNotNone(found, "Albums table should still exist")
        self.assertEqual(found.album_artist, malicious_artist, "Malicious string should be stored as-is")
        
        # Cleanup
        with self.repo.get_connection() as conn:
            conn.execute("DELETE FROM Albums WHERE Title = 'Case_Bobby_Tables'")


if __name__ == "__main__":
    unittest.main()


