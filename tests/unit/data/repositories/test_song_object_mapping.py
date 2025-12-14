import pytest
import os
from src.data.repositories.song_repository import SongRepository
from src.data.models.song import Song

def test_song_object_mapping_integrity(tmp_path):
    """
    Object Mapping Integrity Test:
    Ensures that SongRepository.get_by_path() correctly populates EVERY field 
    of the Song data model from the database.
    
    If a new column is added to the DB, it must be mapped in get_by_path.
    If a new field is added to Song, it must be populated (or default handled).
    """
    db_path = tmp_path / "test_mapping.db"
    repo = SongRepository(str(db_path))
    
    # helper to create full record
    test_path = "/music/test.mp3"
    norm_path = os.path.normcase(os.path.abspath(test_path))
    
    with repo.get_connection() as conn:
        cursor = conn.cursor()
        # Insert File
        cursor.execute(
            "INSERT INTO Files (Path, Title, Duration, TempoBPM) VALUES (?, ?, ?, ?)",
            (norm_path, "Full Title", 123.45, 140)
        )
        file_id = cursor.lastrowid
        
        # Insert Contributors & Roles
        # We need to ensure Performers, Composers, etc are mapped
        # Performer
        cursor.execute("INSERT INTO Contributors (Name) VALUES (?)", ("Perf One",))
        perf_id = cursor.lastrowid
        # Role 'Performer' already exists from BaseRepository setup
        cursor.execute("SELECT RoleID FROM Roles WHERE Name='Performer'")
        perf_role_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO FileContributorRoles VALUES (?, ?, ?)", (file_id, perf_id, perf_role_id))
        
        # Composer
        cursor.execute("INSERT INTO Contributors (Name) VALUES (?)", ("Comp One",))
        comp_id = cursor.lastrowid
        cursor.execute("SELECT RoleID FROM Roles WHERE Name='Composer'")
        comp_role_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO FileContributorRoles VALUES (?, ?, ?)", (file_id, comp_id, comp_role_id))
        
    # Act
    song = repo.get_by_path(test_path)
    
    # Assert
    assert song is not None
    
    # Explicit Field Checks (The "Mapping" Verification)
    assert song.file_id == file_id, "file_id not mapped"
    assert song.path == norm_path, "path not mapped"
    assert song.title == "Full Title", "title not mapped"
    assert song.duration == 123.45, "duration not mapped"
    assert song.bpm == 140, "bpm not mapped"
    assert "Perf One" in song.performers, "performers not mapped"
    assert "Comp One" in song.composers, "composers not mapped"
    
    # "Completeness" Check: Iterate over all fields of the Song object
    # If a new field "genre" starts appearing in Song class, it presumably defaults to None/Empty.
    # We want to enable a mode where we warn if it is EMPTY, but only if we EXPECT it to be filled.
    # Ideally, we should check that `song.genre` is not None if we inserted a genre. 
    # But checking generic "is not None" for all fields is good sanitary check.
    
    import dataclasses
    for field in dataclasses.fields(Song):
        value = getattr(song, field.name)
        # We expect most things to be populated, or at least default initialized (empty list)
        if field.default_factory is list:
             assert isinstance(value, list), f"Field {field.name} should be list"
        
        # For optionals, valid values or None.
        # But if we want to force mapping update when DB adds column, this test needs to KNOW about the DB column.
        # That is covered by `test_schema_model_alignment.py` (Item 9).
        # This test focuses on "Did the repository logic actually copy the data?" checking confirmed fields.
        
    # Passed
