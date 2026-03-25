"""
Execution Checklist - [GOSLING2] Soft Delete Reading Logic
1. [ ] Test & Implement - AlbumRepository.get_all (filter IsDeleted=0)
2. [ ] Test & Implement - AlbumRepository.search (filter IsDeleted=0)
3. [ ] Test & Implement - AlbumRepository.get_by_id (filter IsDeleted=0)
4. [ ] Test & Implement - TagRepository.get_all (filter IsDeleted=0)
5. [ ] Test & Implement - TagRepository.search (filter IsDeleted=0)
6. [ ] Test & Implement - TagRepository.get_by_id (filter IsDeleted=0)
7. [ ] Test & Implement - PublisherRepository.get_all (filter IsDeleted=0)
8. [ ] Test & Implement - PublisherRepository.search (filter IsDeleted=0)
9. [ ] Test & Implement - PublisherRepository.get_by_id (filter IsDeleted=0)
10. [ ] Test & Implement - IdentityRepository (get_by_id, search_identities, etc.)
"""

from src.data.album_repository import AlbumRepository
from src.data.tag_repository import TagRepository
from src.data.publisher_repository import PublisherRepository
from src.data.identity_repository import IdentityRepository
from tests.conftest import _connect

class TestGetAll:
    """AlbumRepository.get_all must filter out soft-deleted records."""

    def test_get_all_excludes_soft_deleted_albums(self, populated_db):
        """
        Record 100 (Nevermind) is active.
        Record 101 (The Colour and the Shape) is active.
        Soft-delete 100, then get_all should only return 101.
        """
        repo = AlbumRepository(populated_db)
        
        # 1. Soft-delete Album 100
        conn = _connect(populated_db)
        conn.execute("UPDATE Albums SET IsDeleted = 1 WHERE AlbumID = 100")
        conn.commit()
        conn.close()

        # 2. Fetch all
        albums = repo.get_all()

        # 3. Assertions (Negative Isolation)
        # In populated_db, there are 2 albums (100, 101).
        # After deleting 100, only 101 should remain.
        assert len(albums) == 1, f"Expected 1 active album, got {len(albums)}"
        assert albums[0].id == 200, f"Expected Album 200, got {albums[0].id}"
        assert albums[0].title == "The Colour and the Shape", f"Expected 'The Colour and the Shape', got '{albums[0].title}'"
        
        album_ids = [a.id for a in albums]
        assert 100 not in album_ids, f"Soft-deleted Album 100 should be excluded, but was found in {album_ids}"

class TestItems:
    """AlbumRepository.search and get_by_id tests."""
    
    def test_search_excludes_soft_deleted_albums(self, populated_db):
        """Search 'Never' should find 100. Soft-delete 100, then search should find none."""
        repo = AlbumRepository(populated_db)
        
        # 1. Verify it's found initially
        assert len(repo.search("Never")) == 1
        
        # 2. Soft-delete
        conn = _connect(populated_db)
        conn.execute("UPDATE Albums SET IsDeleted = 1 WHERE AlbumID = 100")
        conn.commit()
        conn.close()
        
        # 3. Search again
        results = repo.search("Never")
        assert len(results) == 0, f"Expected 0 results for 'Never' after soft-delete, got {len(results)}"

    def test_get_by_id_returns_none_for_soft_deleted(self, populated_db):
        """get_by_id(100) should return None if 100 is soft-deleted."""
        repo = AlbumRepository(populated_db)
        
        # 1. Soft-delete
        conn = _connect(populated_db)
        conn.execute("UPDATE Albums SET IsDeleted = 1 WHERE AlbumID = 100")
        conn.commit()
        conn.close()
        
        # 2. get_by_id
        album = repo.get_by_id(100)
        assert album is None, f"Expected None for soft-deleted album 100, got {album}"

class TestTagVisibility:
    """TagRepository must filter out soft-deleted records."""
    
    def test_get_all_excludes_soft_deleted_tags(self, populated_db):
        """Tag 1 (Grunge) is active. Soft-delete it, then get_all should skip it."""
        repo = TagRepository(populated_db)
        
        # 1. Soft-delete
        conn = _connect(populated_db)
        conn.execute("UPDATE Tags SET IsDeleted = 1 WHERE TagID = 1")
        conn.commit()
        conn.close()
        
        # 2. get_all
        tags = repo.get_all()
        tag_ids = [t.id for t in tags]
        assert 1 not in tag_ids, f"Soft-deleted Tag 1 should be excluded, but was found in {tag_ids}"

    def test_search_excludes_soft_deleted_tags(self, populated_db):
        """Search 'Grunge' should find nothing if it's soft-deleted."""
        repo = TagRepository(populated_db)
        
        # 1. Soft-delete
        conn = _connect(populated_db)
        conn.execute("UPDATE Tags SET IsDeleted = 1 WHERE TagID = 1")
        conn.commit()
        conn.close()
        
        # 2. search
        results = repo.search("Grunge")
        assert len(results) == 0, f"Expected 0 results for 'Grunge' after soft-delete, got {len(results)}"

    def test_get_by_id_returns_none_for_soft_deleted(self, populated_db):
        """get_by_id(1) should return None if 1 is soft-deleted."""
        repo = TagRepository(populated_db)
        
        # 1. Soft-delete
        conn = _connect(populated_db)
        conn.execute("UPDATE Tags SET IsDeleted = 1 WHERE TagID = 1")
        conn.commit()
        conn.close()
        
        # 2. get_by_id
        tag = repo.get_by_id(1)
        assert tag is None, f"Expected None for soft-deleted tag 1, got {tag}"

class TestPublisherVisibility:
    """PublisherRepository must filter out soft-deleted records."""
    
    def test_get_all_excludes_soft_deleted_publishers(self, populated_db):
        """Publisher 10 (DGC Records) is active. Soft-delete it, then get_all should skip it."""
        repo = PublisherRepository(populated_db)
        
        # 1. Soft-delete
        conn = _connect(populated_db)
        conn.execute("UPDATE Publishers SET IsDeleted = 1 WHERE PublisherID = 10")
        conn.commit()
        conn.close()
        
        # 2. get_all
        pubs = repo.get_all()
        pub_ids = [p.id for p in pubs]
        assert 10 not in pub_ids, f"Soft-deleted Publisher 10 should be excluded, but was found in {pub_ids}"

    def test_search_excludes_soft_deleted_publishers(self, populated_db):
        """Search 'DGC' should find nothing if it's soft-deleted."""
        repo = PublisherRepository(populated_db)
        
        # 1. Soft-delete
        conn = _connect(populated_db)
        conn.execute("UPDATE Publishers SET IsDeleted = 1 WHERE PublisherID = 10")
        conn.commit()
        conn.close()
        
        # 2. search
        results = repo.search("DGC")
        assert len(results) == 0, f"Expected 0 results for 'DGC' after soft-delete, got {len(results)}"

    def test_get_by_id_returns_none_for_soft_deleted(self, populated_db):
        """get_by_id(10) should return None if 10 is soft-deleted."""
        repo = PublisherRepository(populated_db)
        
        # 1. Soft-delete
        conn = _connect(populated_db)
        conn.execute("UPDATE Publishers SET IsDeleted = 1 WHERE PublisherID = 10")
        conn.commit()
        conn.close()
        
        # 2. get_by_id
        pub = repo.get_by_id(10)
        assert pub is None, f"Expected None for soft-deleted publisher 10, got {pub}"

class TestIdentityVisibility:
    """IdentityRepository must filter out soft-deleted records."""
    
    def test_get_all_excludes_soft_deleted_identities(self, populated_db):
        """Identity 1 (Dave Grohl) is active. Soft-delete it, then get_all should skip it."""
        repo = IdentityRepository(populated_db)
        
        # 1. Soft-delete
        conn = _connect(populated_db)
        conn.execute("UPDATE Identities SET IsDeleted = 1 WHERE IdentityID = 1")
        conn.commit()
        conn.close()
        
        # 2. get_all
        identities = repo.get_all_identities()
        ids = [i.id for i in identities]
        assert 1 not in ids, f"Soft-deleted Identity 1 should be excluded, but was found in {ids}"

    def test_search_excludes_soft_deleted_identities(self, populated_db):
        """Search 'Grohl' should find nothing if it's soft-deleted."""
        repo = IdentityRepository(populated_db)
        
        # 1. Soft-delete
        conn = _connect(populated_db)
        conn.execute("UPDATE Identities SET IsDeleted = 1 WHERE IdentityID = 1")
        conn.commit()
        conn.close()
        
        # 2. search
        results = repo.search_identities("Grohl")
        assert len(results) == 0, f"Expected 0 results for 'Grohl' after soft-delete, got {len(results)}"

    def test_get_by_id_returns_none_for_soft_deleted(self, populated_db):
        """get_by_id(1) should return None if 1 is soft-deleted."""
        repo = IdentityRepository(populated_db)
        
        # 1. Soft-delete
        conn = _connect(populated_db)
        conn.execute("UPDATE Identities SET IsDeleted = 1 WHERE IdentityID = 1")
        conn.commit()
        conn.close()
        
        # 2. get_by_id
        identity = repo.get_by_id(1)
        assert identity is None, f"Expected None for soft-deleted identity 1, got {identity}"

    def test_get_members_excludes_soft_deleted(self, populated_db):
        """If a member is soft-deleted, it should not appear in get_members_batch."""
        repo = IdentityRepository(populated_db)
        
        # Group 2 (Nirvana) has member 1 (Dave Grohl).
        # Soft-delete Dave.
        conn = _connect(populated_db)
        conn.execute("UPDATE Identities SET IsDeleted = 1 WHERE IdentityID = 1")
        conn.commit()
        conn.close()
        
        # Fetch members for Nirvana
        results = repo.get_members_batch([2])
        members = results.get(2, [])
        assert len(members) == 0, f"Expected 0 members for Nirvana after Dave was soft-deleted, got {len(members)}"

class TestJunctionVisibility:
    """Junction queries must filter out soft-deleted entities."""
    
    def test_get_tags_for_songs_excludes_soft_deleted_tags(self, populated_db):
        """Song 1 has Tag 1 (Grunge). Soft-delete Tag 1, then get_tags_for_songs should skip it."""
        repo = TagRepository(populated_db)
        
        # 1. Soft-delete tag
        conn = _connect(populated_db)
        conn.execute("UPDATE Tags SET IsDeleted = 1 WHERE TagID = 1")
        conn.commit()
        conn.close()
        
        # 2. Fetch tags for song 1
        results = repo.get_tags_for_songs([1])
        # results is List[Tuple[int, Tag]]
        tag_ids = [t.id for sid, t in results]
        assert 1 not in tag_ids, f"Soft-deleted Tag 1 should be excluded from song tags, but was found: {tag_ids}"

    def test_get_credits_for_songs_excludes_soft_deleted_artist_names(self, populated_db):
        """
        Song 1 credited to Nirvana (NameID 20). 
        Soft-delete NameID 20, then get_credits_for_songs should skip it.
        """
        from src.data.song_credit_repository import SongCreditRepository
        repo = SongCreditRepository(populated_db)
        
        # 1. Soft-delete artist name
        conn = _connect(populated_db)
        conn.execute("UPDATE ArtistNames SET IsDeleted = 1 WHERE NameID = 20")
        conn.commit()
        conn.close()
        
        # 2. Fetch credits for song 1
        results = repo.get_credits_for_songs([1])
        name_ids = [c.name_id for c in results]
        assert 20 not in name_ids, f"Soft-deleted ArtistName 20 should be excluded from credits, but was found: {name_ids}"

    def test_get_publishers_for_songs_excludes_soft_deleted_publishers(self, populated_db):
        """
        Song 1 published by DGC Records (ID 10).
        Soft-delete ID 10, then get_publishers_for_songs should skip it.
        """
        repo = PublisherRepository(populated_db)
        
        # 1. Soft-delete publisher
        conn = _connect(populated_db)
        conn.execute("UPDATE Publishers SET IsDeleted = 1 WHERE PublisherID = 10")
        conn.commit()
        conn.close()
        
        # 2. Fetch publishers for song 1
        results = repo.get_publishers_for_songs([1])
        pub_ids = [p.id for sid, p in results]
        assert 10 not in pub_ids, f"Soft-deleted Publisher 10 should be excluded from song publishers, but was found: {pub_ids}"
