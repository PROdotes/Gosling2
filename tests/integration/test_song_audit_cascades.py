
import pytest
import sqlite3
import os
from src.data.repositories.song_repository import SongRepository
from src.data.repositories.audit_repository import AuditRepository
from src.data.repositories.contributor_repository import ContributorRepository
from src.data.repositories.album_repository import AlbumRepository
from src.data.repositories.publisher_repository import PublisherRepository
from src.data.models.song import Song

@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test_song_audit.db"
    return str(path)

@pytest.fixture
def repos(db_path):
    # Initialize all repos on same DB
    s_repo = SongRepository(db_path=db_path)
    c_repo = ContributorRepository(db_path=db_path)
    a_repo = AlbumRepository(db_path=db_path)
    p_repo = PublisherRepository(db_path=db_path)
    audit_repo = AuditRepository(db_path=db_path)
    
    # Ensure tables exist
    s_repo._ensure_schema()
    
    return {
        "song": s_repo,
        "contributor": c_repo,
        "album": a_repo,
        "publisher": p_repo,
        "audit": audit_repo
    }

def test_song_delete_cascades_audited(repos):
    """Scenario: Song has Artist, Album, and Publisher. Delete song. Verify all unlinks are audited."""
    s_repo = repos["song"]
    c_repo = repos["contributor"]
    a_repo = repos["album"]
    p_repo = repos["publisher"]
    audit_repo = repos["audit"]
    
    # 1. Setup Data
    artist = c_repo.create("The Beatles")
    album = a_repo.create("Abbey Road")
    publisher = p_repo.create("Apple Records")
    
    song = Song(
        source_id=None,
        source="C:/m.mp3",
        name="Something",
        performers=["The Beatles"],
        album="Abbey Road",
        publisher="Apple Records"
    )
    source_id = s_repo.insert(song)
    
    # Clear history before delete to isolate cleanup
    # (Actually GenericRepository.insert also logs)
    
    # 2. Delete Song
    s_repo.delete(source_id)
    
    # 3. Verify Audit
    history = audit_repo.get_unified_log(limit=50)
    
    # We expect:
    # - MediaSourceContributorRoles delete
    # - SongAlbums delete
    # - RecordingPublishers delete
    # - MediaSources delete
    
    tables_deleted = [h['TableName'] for h in history if h['EntryType'] == 'CHANGE' and h['NewValue'] is None]
    
    assert "SongCredits" in tables_deleted
    assert "SongAlbums" in tables_deleted
    assert "RecordingPublishers" in tables_deleted
    assert "Songs" in tables_deleted
    
    # Check for BatchID consistency in the delete operation
    delete_entry = next(h for h in history if h['TableName'] == 'Songs' and h['NewValue'] is None)
    batch_id = delete_entry['BatchID']
    assert batch_id is not None
    
    related_junctions = [h for h in history if h['BatchID'] == batch_id and h['TableName'] in ["SongAlbums", "RecordingPublishers"]]
    assert len(related_junctions) >= 2, f"Expected junctions to be in same batch {batch_id}"

def test_song_update_batching(repos):
    """Scenario: Change song artists and album. Verify one BatchID covers all changes."""
    s_repo = repos["song"]
    c_repo = repos["contributor"]
    audit_repo = repos["audit"]
    
    # 1. Setup
    song = Song(source_id=None, source="C:/x.mp3", name="X", performers=["Artist A"])
    source_id = s_repo.insert(song)
    
    # 2. Update
    song.source_id = source_id
    song.performers = ["Artist B"]
    song.album = "New Album"
    s_repo.update(song)
    
    # 3. Verify
    history = audit_repo.get_unified_log(limit=50)
    
    # Find the UPDATE for Songs/MediaSources
    main_update = next(h for h in history if h['TableName'] == 'Songs' and h['EntryType'] == 'CHANGE' and h['NewValue'] is not None)
    batch_id = main_update['BatchID']
    
    # Check related junction changes
    junction_changes = [h for h in history if h['BatchID'] == batch_id and h['TableName'] in ["SongCredits", "SongAlbums"]]
    assert len(junction_changes) > 0, "Junction changes should share BatchID with main update"
