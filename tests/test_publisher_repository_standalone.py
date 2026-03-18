import pytest
import sqlite3
from src.data.publisher_repository import PublisherRepository

@pytest.fixture
def mock_db(tmp_path):
    """Creates a temporary database with publisher data."""
    db_path = str(tmp_path / "test_publishers.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE Publishers (PublisherID INTEGER PRIMARY KEY, PublisherName TEXT, ParentPublisherID INTEGER)")
    conn.execute("CREATE TABLE RecordingPublishers (SourceID INTEGER, PublisherID INTEGER)")
    
    # Hierarchy: UMG (1) -> Island (2) -> Island Def Jam (3)
    conn.execute("INSERT INTO Publishers VALUES (1, 'Universal Music Group', NULL)")
    conn.execute("INSERT INTO Publishers VALUES (2, 'Island Records', 1)")
    conn.execute("INSERT INTO Publishers VALUES (3, 'Island Def Jam', 2)")
    conn.execute("INSERT INTO Publishers VALUES (4, 'Warner Records', NULL)")
    
    # Repertoire
    conn.execute("INSERT INTO RecordingPublishers VALUES (101, 2)") # Song 101 -> Island
    conn.execute("INSERT INTO RecordingPublishers VALUES (102, 2)") # Song 102 -> Island
    
    conn.commit()
    conn.close()
    return db_path

def test_publisher_get_all(mock_db):
    repo = PublisherRepository(mock_db)
    pubs = repo.get_all()
    assert len(pubs) == 4
    # ID顺序可能因主键递增而定，但查询中有 ORDER BY PublisherName
    # ID order: 3 (Island Def Jam), 2 (Island Records), 1 (UMG), 4 (Warner)
    assert pubs[0].name == "Island Def Jam"

def test_publisher_search(mock_db):
    """Verify search finds keywords."""
    repo = PublisherRepository(mock_db)
    # Matching 'Island' finds 'Island Records' (2) and 'Island Def Jam' (3).
    # No hierarchical expansion.
    results = repo.search("Island")
    assert len(results) == 2
    names = {p.name for p in results}
    assert "Island Records" in names
    assert "Island Def Jam" in names
    assert "Universal Music Group" not in names

def test_publisher_get_by_id(mock_db):
    repo = PublisherRepository(mock_db)
    pub = repo.get_by_id(2)
    assert pub is not None
    assert pub.name == "Island Records"
    assert pub.parent_id == 1

def test_publisher_get_by_ids(mock_db):
    repo = PublisherRepository(mock_db)
    pubs = repo.get_by_ids([1, 4])
    assert len(pubs) == 2
    names = {p.name for p in pubs}
    assert "Universal Music Group" in names
    assert "Warner Records" in names

def test_publisher_get_children(mock_db):
    repo = PublisherRepository(mock_db)
    children = repo.get_children(1) # UMG children
    assert len(children) == 1
    assert children[0].name == "Island Records"

def test_publisher_get_repertoire(mock_db):
    repo = PublisherRepository(mock_db)
    song_ids = repo.get_song_ids_by_publisher(2) # Island songs
    assert len(song_ids) == 2
    assert 101 in song_ids
    assert 102 in song_ids

def test_publisher_get_not_found(mock_db):
    repo = PublisherRepository(mock_db)
    assert repo.get_by_id(999) is None
    assert repo.search("Nonexistent") == []
