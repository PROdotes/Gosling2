"""
Logic tests for AlbumRepository (Level 1: Happy Path & Polite Failures).
Per TESTING.md: Tests for expected behavior and documented edge cases.
"""
import pytest
from src.data.repositories.album_repository import AlbumRepository


class TestAlbumRepository:
    """Unit tests for AlbumRepository."""
    
    @pytest.fixture
    def repo(self):
        """Fixture providing AlbumRepository instance with cleanup."""
        repository = AlbumRepository()
        # Cleanup before test
        try:
            with repository.get_connection() as conn:
                conn.execute("DELETE FROM Albums WHERE AlbumTitle LIKE 'Case_%' OR AlbumTitle LIKE 'Pytest_%'")
                conn.execute("DELETE FROM MediaSources WHERE SourcePath IN ('C:\\\\Multi.mp3', 'C:\\\\Remove.mp3', 'C:\\\\Del.mp3')")
        except Exception:
            pass
        
        yield repository
        
        # Cleanup after test
        try:
            with repository.get_connection() as conn:
                conn.execute("DELETE FROM Albums WHERE AlbumTitle LIKE 'Case_%' OR AlbumTitle LIKE 'Pytest_%'")
                conn.execute("DELETE FROM MediaSources WHERE SourcePath IN ('C:\\\\Multi.mp3', 'C:\\\\Remove.mp3', 'C:\\\\Del.mp3')")
        except Exception:
            pass
    
    class TestBasicCRUD:
        """Tests for basic Create, Read, Update operations."""
        
        def test_find_by_title_case_insensitive(self, repo):
            """
            Verify that find_by_title matches regardless of case.
            'Nevermind' should match 'nevermind'.
            """
            test_title = "Case_Sensitivity_Test_Album"
            # 1. Create album with specific casing
            album = repo.create(test_title)
            assert album.album_id is not None
            
            # 2. Search with different casing
            lower_title = test_title.lower()
            found = repo.find_by_title(lower_title)
            
            # 3. Should find the same album
            assert found is not None, f"find_by_title('{lower_title}') returned None. Case sensitivity bug!"
            assert found.album_id == album.album_id
        
        def test_update_album(self, repo):
            """Verify that update() can rename an album."""
            # 1. Create album
            album = repo.create("Case_Sensitivity_Typo")
            original_id = album.album_id
            
            # 2. Rename it
            album.title = "Case_Sensitivity_Fixed"
            success = repo.update(album)
            assert success
            
            # 3. Old name should not exist
            old = repo.find_by_title("Case_Sensitivity_Typo")
            assert old is None
            
            # 4. New name should exist with same ID
            new = repo.find_by_title("Case_Sensitivity_Fixed")
            assert new is not None
            assert new.album_id == original_id
        
        def test_get_or_create(self, repo):
            """Verify get_or_create returns existing album or creates new."""
            # 1. First call creates
            album1, created1 = repo.get_or_create("Case_GetOrCreate_Test")
            assert created1
            assert album1.album_id is not None
            
            # 2. Second call returns existing
            album2, created2 = repo.get_or_create("Case_GetOrCreate_Test")
            assert not created2
            assert album1.album_id == album2.album_id
        
        def test_create_with_album_artist(self, repo):
            """Verify create() stores album_artist correctly."""
            album = repo.create("Case_Create_Artist_Test", album_artist="The Beatles", release_year=1965)
            
            assert album.album_id is not None
            assert album.album_artist == "The Beatles"
            assert album.release_year == 1965
            
            # Retrieve and verify
            found = repo.get_by_id(album.album_id)
            assert found.album_artist == "The Beatles"
        
        def test_delete_album_integrity(self, repo):
            """
            Verify that get_song_count returns correct count and
            delete removes album and unlinks songs (cascade check).
            """
            # 1. Create album + songs
            album = repo.create("Case_Delete_Integrity")
            
            with repo.get_connection() as conn:
                # Create dummy song
                conn.execute("INSERT INTO MediaSources (TypeID, MediaName, SourcePath, IsActive) VALUES (1, 'Del', 'C:\\\\Del.mp3', 1)")
                sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute("INSERT INTO Songs (SourceID) VALUES (?)", (sid,))
            
            # 2. Link
            repo.add_song_to_album(sid, album.album_id)
            
            # 3. Check Count
            count = repo.get_song_count(album.album_id)
            assert count == 1, "Should have 1 song"
            
            # 4. Delete
            success = repo.delete(album.album_id)
            assert success
            
            # 5. Check Album Gone
            found = repo.get_by_id(album.album_id)
            assert found is None
            
            # 6. Check Links Gone (Cascade verification)
            links = repo.get_albums_for_song(sid)
            assert len(links) == 0, "Links should be cascaded"
            
            # Cleanup song
            with repo.get_connection() as conn:
                conn.execute("DELETE FROM MediaSources WHERE SourcePath = 'C:\\\\Del.mp3'")
    
    class TestMultiAlbumSupport:
        """Tests for multi-album (M2M) relationships."""
        
        def test_song_on_multiple_albums(self, repo):
            """
            Verify M2M: A song can be on multiple albums.
            After adding to Album1, adding to Album2 should keep both links.
            """
            # Setup: Create two albums
            album1 = repo.create("Case_Multi_Album1")
            album2 = repo.create("Case_Multi_Album2")
            
            # Create a "song" (we just need a SourceID, so we fake it via raw insert)
            with repo.get_connection() as conn:
                # Insert fake MediaSource
                conn.execute("INSERT INTO MediaSources (TypeID, MediaName, SourcePath, IsActive) VALUES (1, 'Multi Test', 'C:\\\\Multi.mp3', 1)")
                cursor = conn.execute("SELECT last_insert_rowid()")
                source_id = cursor.fetchone()[0]
                # Insert Songs record
                conn.execute("INSERT INTO Songs (SourceID) VALUES (?)", (source_id,))
            
            # Add song to Album1
            repo.add_song_to_album(source_id, album1.album_id)
            
            # Add song to Album2
            repo.add_song_to_album(source_id, album2.album_id)
            
            # Verify: Song should be on BOTH albums
            albums = repo.get_albums_for_song(source_id)
            album_ids = [a.album_id for a in albums]
            
            assert album1.album_id in album_ids, "Song should still be on Album1"
            assert album2.album_id in album_ids, "Song should also be on Album2"
            assert len(albums) == 2, "Song should be on exactly 2 albums"
            
            # Cleanup
            with repo.get_connection() as conn:
                conn.execute("DELETE FROM MediaSources WHERE SourcePath = 'C:\\\\Multi.mp3'")
        
        def test_remove_song_from_album(self, repo):
            """Verify remove_song_from_album unlinks correctly."""
            # Setup
            album = repo.create("Case_Remove_Test")
            
            with repo.get_connection() as conn:
                conn.execute("INSERT INTO MediaSources (TypeID, MediaName, SourcePath, IsActive) VALUES (1, 'Remove Test', 'C:\\\\Remove.mp3', 1)")
                cursor = conn.execute("SELECT last_insert_rowid()")
                source_id = cursor.fetchone()[0]
                conn.execute("INSERT INTO Songs (SourceID) VALUES (?)", (source_id,))
            
            # Add to album
            repo.add_song_to_album(source_id, album.album_id)
            albums = repo.get_albums_for_song(source_id)
            assert len(albums) == 1
            
            # Remove from album
            repo.remove_song_from_album(source_id, album.album_id)
            albums = repo.get_albums_for_song(source_id)
            assert len(albums) == 0
            
            # Cleanup
            with repo.get_connection() as conn:
                conn.execute("DELETE FROM MediaSources WHERE SourcePath = 'C:\\\\Remove.mp3'")
        
        def test_sync_album_replacement(self, repo):
            """
            Verify that SongRepository.update() with song.album replaces existing links,
            supporting the "Snapshot" sync strategy (Fixes the Append bug).
            """
            from src.data.repositories.song_repository import SongRepository
            from src.data.models.song import Song
            import os
            
            # Setup
            song_repo = SongRepository()
            # Ensure path is absolutely identical to how repository stores it
            test_path = os.path.normcase(os.path.abspath("C:\\Music\\Replacement_Test.mp3"))
            
            # Cleanup old
            with song_repo.get_connection() as conn:
                conn.execute("DELETE FROM MediaSources WHERE SourcePath = ?", (test_path,))
                conn.execute("DELETE FROM Albums WHERE AlbumTitle LIKE 'Replacement_Album%'")
            
            # 1. Insert song
            source_id = song_repo.insert(test_path)
            
            # 2. Add to Album1 via update
            song = song_repo.get_by_id(source_id)
            song.album = "Replacement_Album1"
            song.album_artist = "Test Artist"
            song.recording_year = 2024
            song_repo.update(song)
            
            # 3. Add to Album2 via update (should REPLACE Album1 link)
            song = song_repo.get_by_id(source_id)
            song.album = "Replacement_Album2"
            # Keep same artist/year to test title replacement
            song.album_artist = "Test Artist"
            song.recording_year = 2024
            song_repo.update(song)
            
            # 4. Verify: Song should be on Album2 ONLY (Snapshot strategy)
            albums = repo.get_albums_for_song(source_id)
            album_titles = [a.title for a in albums]
            
            assert "Replacement_Album1" not in album_titles, "Album1 should be replaced (Snapshot strategy)"
            assert "Replacement_Album2" in album_titles, "Album2 should be the only album"
            assert len(albums) == 1, "Song should be on 1 album (Snapshot/Replace strategy)"
            
            # Cleanup
            with song_repo.get_connection() as conn:
                conn.execute("DELETE FROM MediaSources WHERE SourcePath = ?", (test_path,))
                conn.execute("DELETE FROM Albums WHERE AlbumTitle LIKE 'Replacement_Album%'")
    
    class TestAlbumDisambiguation:
        """Tests for album artist disambiguation (Greatest Hits Paradox)."""
        
        def test_greatest_hits_different_artists(self, repo):
            """
            THE GREATEST HITS PARADOX: 
            'Greatest Hits' by Queen and 'Greatest Hits' by ABBA must be SEPARATE albums.
            """
            # Create ABBA's Greatest Hits
            abba, created1 = repo.get_or_create("Case_Greatest_Hits", album_artist="ABBA", release_year=1992)
            assert created1, "ABBA album should be created"
            
            # Create Queen's Greatest Hits (same title, different artist)
            queen, created2 = repo.get_or_create("Case_Greatest_Hits", album_artist="Queen", release_year=1981)
            assert created2, "Queen album should be created (NOT reuse ABBA's)"
            
            # They should have DIFFERENT IDs
            assert abba.album_id != queen.album_id, \
                "CRITICAL: Queen and ABBA albums merged! Greatest Hits fix failed."
            
            # Verify we can retrieve each independently
            found_abba = repo.find_by_key("Case_Greatest_Hits", album_artist="ABBA", release_year=1992)
            found_queen = repo.find_by_key("Case_Greatest_Hits", album_artist="Queen", release_year=1981)
            
            assert found_abba is not None
            assert found_queen is not None
            assert found_abba.album_id == abba.album_id
            assert found_queen.album_id == queen.album_id
            
            # Cleanup
            with repo.get_connection() as conn:
                conn.execute("DELETE FROM Albums WHERE AlbumTitle = 'Case_Greatest_Hits'")
        
        def test_same_artist_different_years(self, repo):
            """
            Same artist, same title, different years = different albums.
            E.g., 'Greatest Hits 1981' vs 'Greatest Hits 2011 Remaster'
            """
            album_1981, created1 = repo.get_or_create("Case_Same_Artist", album_artist="Queen", release_year=1981)
            album_2011, created2 = repo.get_or_create("Case_Same_Artist", album_artist="Queen", release_year=2011)
            
            assert created1
            assert created2, "Different year should create new album"
            assert album_1981.album_id != album_2011.album_id
            
            # Cleanup
            with repo.get_connection() as conn:
                conn.execute("DELETE FROM Albums WHERE AlbumTitle = 'Case_Same_Artist'")
        
        def test_same_artist_same_year_reuses(self, repo):
            """Same artist, same title, same year = same album (reuse)."""
            album1, created1 = repo.get_or_create("Case_Reuse_Test", album_artist="Nirvana", release_year=1991)
            album2, created2 = repo.get_or_create("Case_Reuse_Test", album_artist="Nirvana", release_year=1991)
            
            assert created1
            assert not created2, "Should reuse existing album"
            assert album1.album_id == album2.album_id
            
            # Cleanup
            with repo.get_connection() as conn:
                conn.execute("DELETE FROM Albums WHERE AlbumTitle = 'Case_Reuse_Test'")
        
        def test_null_artist_handling(self, repo):
            """
            Albums with NULL artist should be distinguishable from each other by year.
            Two compilations with no artist but different years = separate.
            """
            comp_2020, created1 = repo.get_or_create("Case_Compilation", album_artist=None, release_year=2020)
            comp_2021, created2 = repo.get_or_create("Case_Compilation", album_artist=None, release_year=2021)
            
            assert created1
            assert created2, "Different year compilations should be separate"
            assert comp_2020.album_id != comp_2021.album_id
            
            # Same title, same year, both NULL artist = same album
            comp_2020_again, created3 = repo.get_or_create("Case_Compilation", album_artist=None, release_year=2020)
            assert not created3, "Should reuse existing NULL artist album"
            assert comp_2020.album_id == comp_2020_again.album_id
            
            # Cleanup
            with repo.get_connection() as conn:
                conn.execute("DELETE FROM Albums WHERE AlbumTitle = 'Case_Compilation'")
        
        def test_artist_case_insensitive(self, repo):
            """
            Artist matching should be case-insensitive.
            'queen' should match 'Queen'.
            """
            album1, created1 = repo.get_or_create("Case_Artist_Case", album_artist="Queen", release_year=1981)
            album2, created2 = repo.get_or_create("Case_Artist_Case", album_artist="queen", release_year=1981)
            
            assert created1
            assert not created2, "Case difference should not create new album"
            assert album1.album_id == album2.album_id
            
            # Cleanup
            with repo.get_connection() as conn:
                conn.execute("DELETE FROM Albums WHERE AlbumTitle = 'Case_Artist_Case'")
        
        def test_find_by_key_with_all_fields(self, repo):
            """Verify find_by_key works with all three disambiguation fields."""
            # Create album
            repo.create("Case_FindKey_Test", album_artist="Pink Floyd", album_type="Album", release_year=1973)
            
            # Find with all fields
            found = repo.find_by_key("Case_FindKey_Test", album_artist="Pink Floyd", release_year=1973)
            assert found is not None
            assert found.album_artist == "Pink Floyd"
            
            # Wrong artist should not find
            not_found = repo.find_by_key("Case_FindKey_Test", album_artist="Led Zeppelin", release_year=1973)
            assert not_found is None
            
            # Cleanup
            with repo.get_connection() as conn:
                conn.execute("DELETE FROM Albums WHERE AlbumTitle = 'Case_FindKey_Test'")
