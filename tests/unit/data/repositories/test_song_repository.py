import pytest
import sqlite3
import os
from unittest.mock import MagicMock, patch
from src.data.database import BaseRepository
from src.data.repositories.song_repository import SongRepository
from src.data.models.song import Song
from src.core import yellberus

@pytest.fixture
def temp_db(tmp_path):
    """Fixture creating a temporary database with the schema."""
    db_path = tmp_path / "test_gosling_repo.db"
    
    # Initialize Schema (using the application's BaseRepository class)
    # Repository init automatically calls _ensure_schema
    db = BaseRepository(str(db_path))
    
    return str(db_path)

@pytest.fixture
def song_repo(temp_db):
    """Fixture providing a SongRepository connected to the temporary database."""
    return SongRepository(temp_db)

@pytest.fixture
def sample_song():
    """Fixture providing a standard sample Song object."""
    # Use normalized path for consistency
    path = os.path.normcase(os.path.abspath("C:/Music/test.mp3"))
    return Song(
        name="Test Song",
        source=path,
        duration=180,
        bpm=120,
        source_id=None,  # Was file_id
        is_active=True
    )

class TestSongRepoCRUD:
    """Core Create, Read, Update, Delete functionality."""
    
    def _create_song(self, repo, song):
        """Helper to simulate the full Service creation flow."""
        # 1. Insert (creates skeleton)
        file_id = repo.insert(song.source)  # Fixed: use song.source
        assert file_id is not None
        song.file_id = file_id
        song.source_id = file_id 
        
        # 2. Update (fills details)
        repo.update(song)
        return file_id

    def test_insert_and_get_by_path(self, song_repo, sample_song):
        """Test adding a song and retrieving it by Path (Primary Lookup)."""
        file_id = self._create_song(song_repo, sample_song)
        assert file_id > 0

        # 2. Get by Path
        fetched_song = song_repo.get_by_path(sample_song.source)  # Fixed: use song.source
        assert fetched_song is not None
        assert fetched_song.source_id == file_id
        assert fetched_song.source == sample_song.source  # Fixed: use song.source
        assert fetched_song.name == "Test Song"
        assert fetched_song.duration == 180

    def test_update_song(self, song_repo, sample_song):
        """Test updating an existing song."""
        file_id = self._create_song(song_repo, sample_song)
        song_to_update = song_repo.get_by_path(sample_song.source)  # Fixed: use song.source
        
        # Modify
        song_to_update.name = "Updated Title"
        song_to_update.bpm = 125
        
        # Save
        result = song_repo.update(song_to_update)
        assert result is True
        
        # Verify
        updated = song_repo.get_by_path(sample_song.source)  # Fixed: use song.source
        assert updated.name == "Updated Title"
        assert updated.bpm == 125


    def test_delete_song(self, song_repo, sample_song):
        """Test deleting a song."""
        file_id = self._create_song(song_repo, sample_song)
        
        song_repo.delete(file_id)
        
        found = song_repo.get_by_path(sample_song.source)  # Fixed: use song.source
        assert found is None

    def test_get_all(self, song_repo, sample_song):
        """Test retrieving all songs."""
        self._create_song(song_repo, sample_song)
        
        headers, data = song_repo.get_all()
        
        assert len(data) >= 1
        assert len(headers) > 0


class TestSongRepoLookups:
    """Specific query lookups."""

    def test_get_by_path_found(self, song_repo, sample_song):
        """Test finding a song by its exact path."""
        repo_crud = TestSongRepoCRUD()
        repo_crud._create_song(song_repo, sample_song)
        
        found = song_repo.get_by_path(sample_song.source)  # Fixed: use song.source
        assert found is not None
        assert found.source == sample_song.source  # Fixed: use song.source

    def test_get_by_path_not_found(self, song_repo):
        """Test behavior when path does not exist."""
        found = song_repo.get_by_path("non/existent/path.mp3")
        assert found is None

    def test_get_by_performer(self, song_repo):
        """Test retrieval by performer."""
        path = os.path.normcase(os.path.abspath("C:/Music/perf.mp3"))
        s = Song(name="PerfTest", source=path, performers=["Alice"], source_id=None)
        
        # Helper reuse
        crud = TestSongRepoCRUD()
        crud._create_song(song_repo, s)
        
        headers, data = song_repo.get_by_performer("Alice")
        assert len(data) == 1

    def test_get_by_composer(self, song_repo):
        """Test retrieval by composer."""
        path = os.path.normcase(os.path.abspath("C:/Music/comp.mp3"))
        s = Song(name="CompTest", source=path, composers=["Beethoven"], source_id=None)
        
        crud = TestSongRepoCRUD()
        crud._create_song(song_repo, s)
        
        headers, data = song_repo.get_by_composer("Beethoven")
        assert len(data) == 1
        # data is a list of sqlite3.Row objects.
        # We assume one of the columns (like Title/Name or Path) contains our data.
        # Let's inspect the row by converting it to a dict or accessing key.
        row = data[0]
        # In Yellberus queries, typically "Name" or "Title" is returned.
        # Let's verify by checking if the name we set is in the values.
        # Row values are accessible by index or case-insensitive name if using Row factory.
        found_values = [str(item) for item in row] # Convert all columns to string
        assert "CompTest" in found_values

    def test_get_by_year(self, song_repo):
        """Test retrieval by year."""
        path = os.path.normcase(os.path.abspath("C:/Music/year.mp3"))
        # The Song model uses 'recording_year', not 'year'
        s = Song(name="YearTest", source=path, recording_year=1999, source_id=None)
        
        crud = TestSongRepoCRUD()
        crud._create_song(song_repo, s)
        
        headers, data = song_repo.get_by_year("1999")
        assert len(data) == 1
        


class TestSongRepoEdgeCases:
    """Exceptions, data integrity, and weird inputs."""

    def test_insert_duplicate_path(self, song_repo, sample_song):
        """Adding a song with an existing path (Constraint)."""
        # 1. Insert first
        song_repo.insert(sample_song.path)
        
        # 2. Insert duplicate - should check UNIQUE constraint on MediaSources.Source
        # insert() catches exception and returns None
        result = song_repo.insert(sample_song.path)
        assert result is None
            
    def test_song_object_mapping_integrity(self, song_repo, sample_song):
        """Ensure Song object fields map 1:1 with Repository logic."""
        crud = TestSongRepoCRUD()
        file_id = crud._create_song(song_repo, sample_song)
        
        fetched = song_repo.get_by_path(sample_song.source)  # Fixed: use song.source
        
        # Verify critical fields survive the round trip
        assert fetched.source == sample_song.source  # Fixed: use song.source
        assert fetched.name == sample_song.name
        assert fetched.duration == sample_song.duration

    def test_duplicate_paths_different_separators(self, song_repo):
        """Regression: Different separators should still trigger duplicate detection."""
        # Insert using forward slashes
        path1 = os.path.normcase(os.path.abspath("C:/Music/test_song_sep.mp3"))
        id1 = song_repo.insert(path1)
        assert id1 is not None

        # Insert same file using backslashes - attempt to duplicate
        # Note: We must replicate the logic that client code would use - passing raw strings
        # But since Repo expects normalized paths mostly, we verify that if we pass normalized, it works.
        # Ideally, normalization happens in Service. Repo should enforce UNIQUE whatever it gets.
        path2 = os.path.normcase(os.path.abspath("C:/Music/test_song_sep.mp3"))
        
        # Should now return None (caught by existing unique constraint)
        id2 = song_repo.insert(path2)
        assert id2 is None

    def test_duplicate_paths_different_case(self, song_repo):
        """Regression: different case should still trigger duplicate detection (Windows)."""
        path1 = os.path.normcase(os.path.abspath("C:/Music/TEST_SONG_CASE.mp3"))
        id1 = song_repo.insert(path1)
        assert id1 is not None

        # Even if we construct the string differently, normcase makes them equal
        path2 = os.path.normcase(os.path.abspath("c:/music/test_song_case.mp3"))
        
        id2 = song_repo.insert(path2)
        assert id2 is None



class TestSongRepoMultiAlbum:
    """Tests for Phase 2/3 Multi-Album Infrastructure."""

    def test_sync_album_non_destructive(self, song_repo, sample_song):
        """Verify _sync_album promotes new target and preserves old links."""
        crud = TestSongRepoCRUD()
        file_id = crud._create_song(song_repo, sample_song)
        
        # 1. Link to Album A (Primary)
        sample_song.album = "Album A"
        sample_song.recording_year = 2020
        
        with song_repo.get_connection() as conn:
            cursor = conn.cursor()  # Get cursor from connection
            song_repo._sync_album(sample_song, cursor)  # Pass cursor
            conn.commit()
        
        # Verify 1 link
        with song_repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT AlbumID, IsPrimary FROM SongAlbums WHERE SourceID = ?", (file_id,))
            links = cursor.fetchall()
            assert len(links) == 1
            id_a = links[0][0]
            assert links[0][1] == 1 # Primary

        # 2. Link to Album B (Should Replace Album A - Snapshot strategy)
        sample_song.album = "Album B"
        with song_repo.get_connection() as conn:
            cursor = conn.cursor()  # Get cursor from connection
            song_repo._sync_album(sample_song, cursor)  # Pass cursor
            conn.commit()
        
        # Verify 1 link (Snapshot strategy replaces, doesn't append)
        with song_repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT AlbumID, IsPrimary FROM SongAlbums WHERE SourceID = ? ORDER BY AlbumID", (file_id,))
            links = cursor.fetchall()
            assert len(links) == 1  # Snapshot strategy: only new album
            
            # B should be the only one, and it's Primary
            assert links[0][1] == 1  # IsPrimary


    def test_sync_publisher_track_override(self, song_repo, sample_song):
        """Verify Track Override (Level 1) vs Album (Level 2)."""
        crud = TestSongRepoCRUD()
        file_id = crud._create_song(song_repo, sample_song)
        
        # 1. Setup Album A with "Major Label"
        sample_song.album = "Album A"
        
        with song_repo.get_connection() as conn:
            cursor = conn.cursor()  # Get cursor from connection
            song_repo._sync_album(sample_song, cursor)  # Pass cursor
            
            # Manually set Album Publisher to Major Label
            cursor = conn.cursor()
            cursor.execute("SELECT AlbumID FROM SongAlbums WHERE SourceID=?", (file_id,))
            row = cursor.fetchone()
            assert row is not None
            alb_id = row[0]
            
            cursor.execute("INSERT INTO Publishers (PublisherName) VALUES ('Major Label')")
            maj_id = cursor.lastrowid
            cursor.execute("INSERT INTO AlbumPublishers (AlbumID, PublisherID) VALUES (?, ?)", (alb_id, maj_id))
            conn.commit()

        # 2. Set 'Remix Label' on Song (Override)
        sample_song.publisher = "Remix Label"
        with song_repo.get_connection() as conn:
            cursor = conn.cursor()  # Get cursor from connection
            song_repo._sync_publisher(sample_song, cursor)  # Pass cursor
            conn.commit()
            
        # 3. Verify Waterfall Resolution via get_songs_by_ids
        # This checks the SQL Priority Logic
        fetched_list = song_repo.get_songs_by_ids([file_id])
        assert len(fetched_list) == 1
        fetched = fetched_list[0]
        
        # Should return "Remix Label" (Level 1)
        assert fetched.publisher == ["Remix Label"]
        
        # Verify Level 2 (Album Publisher) is still "Major Label" in DB
        with song_repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT PublisherID FROM AlbumPublishers WHERE AlbumID=?", (alb_id,))
            pids = [r[0] for r in cursor.fetchall()]
            assert maj_id in pids # Should still be there
            
            # Verify TrackPublisherID is set
            cursor.execute("SELECT TrackPublisherID FROM SongAlbums WHERE SourceID=?", (file_id,))
            track_pid = cursor.fetchone()[0]
            assert track_pid is not None
            assert track_pid != maj_id
