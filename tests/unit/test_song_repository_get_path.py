"""Tests for SongRepository.get_by_path method"""
import pytest
import tempfile
import os
import sqlite3
from src.data.repositories.song_repository import SongRepository
from src.data.database_config import DatabaseConfig
from src.data.models.song import Song

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
        db_path = f.name
    
    # Override database path
    original_path = DatabaseConfig.get_database_path
    DatabaseConfig.get_database_path = lambda: db_path
    
    # Initialize DB (create tables)
    # We can use the connection to run the schema script or rely on existing init logic if any.
    # Since we are testing repository which assumes tables exist, we should init them.
    # For simplicity, let's look at how other tests do it or just run the create statements.
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Files (
                FileID INTEGER PRIMARY KEY AUTOINCREMENT,
                Path TEXT UNIQUE NOT NULL,
                Title TEXT,
                Duration REAL,
                TempoBPM INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Roles (
                RoleID INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT UNIQUE NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Contributors (
                ContributorID INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT UNIQUE NOT NULL,
                SortName TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FileContributorRoles (
                FileID INTEGER,
                ContributorID INTEGER,
                RoleID INTEGER,
                PRIMARY KEY (FileID, ContributorID, RoleID),
                FOREIGN KEY (FileID) REFERENCES Files(FileID),
                FOREIGN KEY (ContributorID) REFERENCES Contributors(ContributorID),
                FOREIGN KEY (RoleID) REFERENCES Roles(RoleID)
            )
        """)
        
        # Seed Roles
        roles = ['Performer', 'Composer', 'Lyricist', 'Producer']
        for role in roles:
             cursor.execute("INSERT INTO Roles (Name) VALUES (?)", (role,))
        
    yield db_path
    
    DatabaseConfig.get_database_path = original_path
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except PermissionError as e:
            print(f"Failed to delete temp DB: {e}")

@pytest.fixture
def repository(temp_db):
    return SongRepository()

def test_get_by_path_found(repository):
    """Test retrieving a song by path returns full object."""
    # 1. Insert a song
    song = Song(
        title="Test Title",
        path="/music/test.mp3",
        duration=180.5,
        bpm=120,
        performers=["Alice", "Bob"],
        composers=["Charlie"]
    )
    
    # We need to insert it properly. Repository.insert only does basic file info.
    # Repository.update does full metadata.
    file_id = repository.insert(song.path)
    assert file_id is not None
    song.file_id = file_id
    repository.update(song)
    
    # 2. Retrieve it
    retrieved_song = repository.get_by_path(song.path)
    
    # 3. Assertions
    assert retrieved_song is not None
    assert retrieved_song.file_id == file_id
    assert retrieved_song.title == "Test Title"
    assert retrieved_song.duration == 180.5
    assert retrieved_song.bpm == 120
    
    # Check lists (order might vary unless sorted, but our update logic preserves insertion order mostly)
    assert "Alice" in retrieved_song.performers
    assert "Bob" in retrieved_song.performers
    assert "Charlie" in retrieved_song.composers
    assert len(retrieved_song.performers) == 2
    assert len(retrieved_song.composers) == 1

def test_get_by_path_not_found(repository):
    """Test retrieving a non-existent path returns None."""
    result = repository.get_by_path("/nonexistent.mp3")
    assert result is None

def test_get_by_path_complex_contributors(repository):
    """Test that all contributor types are retrieved correctly."""
    song = Song(
        path="/music/complex.mp3",
        title="Complex Song",
        performers=["P1"],
        composers=["C1"],
        lyricists=["L1"],
        producers=["Pr1"]
    )
    
    file_id = repository.insert(song.path)
    song.file_id = file_id
    repository.update(song)
    
    retrieved = repository.get_by_path(song.path)
    assert retrieved is not None
    assert retrieved.performers == ["P1"]
    assert retrieved.composers == ["C1"]
    assert retrieved.lyricists == ["L1"]
    assert retrieved.producers == ["Pr1"]
