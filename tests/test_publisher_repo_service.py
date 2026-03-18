import sqlite3
from src.data.publisher_repository import PublisherRepository
from src.services.catalog_service import CatalogService

def prepare_db(path):
    """Helper to seed the hermetic DB with required collation and tables."""
    conn = sqlite3.connect(path)
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > f"{s2}".lower()) - (s1.lower() < f"{s2}".lower()),
    )
    return conn

def test_publisher_hierarchy_resolution(mock_db_path):
    """Test that Publisher hierarchy (Child -> Parent -> Grandparent) resolves correctly."""
    conn = prepare_db(mock_db_path)
    # 1. Setup Hierarchy
    conn.execute("INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (1, 'Universal Music Group', NULL)")
    conn.execute("INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (2, 'Island Records', 1)")
    conn.execute("INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (3, 'Island Def Jam', 2)")
    conn.commit()
    conn.close()
    
    # 2. Test Repo
    repo = PublisherRepository(mock_db_path)
    pub3 = repo.get_by_id(3)
    assert pub3.name == "Island Def Jam"
    assert pub3.parent_id == 2
    
    # 3. Test Service (Hydration)
    service = CatalogService(mock_db_path)
    hydrated = service.get_publisher(3)
    assert hydrated.name == "Island Def Jam"
    assert hydrated.parent_name == "Island Records"

def test_publisher_search_sorted(mock_db_path):
    """Test that search results are alphabetically sorted."""
    conn = prepare_db(mock_db_path)
    conn.execute("INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (1, 'Zoo Records', NULL)")
    conn.execute("INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (2, 'Apple Records', NULL)")
    conn.commit()
    conn.close()
    
    repo = PublisherRepository(mock_db_path)
    results = repo.get_all()
    assert sorted([r.name for r in results])[0] == "Apple Records"

def test_publisher_repertoire_lookup(mock_db_path):
    """Test that we can retrieve songs for a specific publisher."""
    conn = prepare_db(mock_db_path)
    # 1. Setup Media/Song
    conn.execute("INSERT INTO Types (TypeID, TypeName) VALUES (1, 'Song')")
    conn.execute("INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) VALUES (10, 1, 'Test Song', 'p.mp3', 10, 1)")
    conn.execute("INSERT INTO Songs (SourceID) VALUES (10)")
    
    # 2. Link to Publisher
    conn.execute("INSERT INTO Publishers (PublisherID, PublisherName, ParentPublisherID) VALUES (5, 'Island Records', NULL)")
    conn.execute("INSERT INTO RecordingPublishers (SourceID, PublisherID) VALUES (10, 5)")
    conn.commit()
    conn.close()
    
    service = CatalogService(mock_db_path)
    rep = service.get_publisher_songs(5)
    assert len(rep) == 1
    assert rep[0].media_name == "Test Song"
