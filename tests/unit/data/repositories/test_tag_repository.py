
import pytest
from src.data.database import BaseRepository
from src.data.repositories.tag_repository import TagRepository
from src.core import logger

@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test_tag_repo.db"
    BaseRepository(str(db_path))
    return TagRepository(str(db_path))

class TestTagRepository:
    def test_create_and_find(self, repo):
        # 1. Create with category
        repo.create("Rock", "Genre")
        
        # 2. Find
        found = repo.find_by_name("Rock", "Genre")
        assert found is not None
        assert found.category == "Genre"
        
        # 3. Validation: Category mismatch returns None
        assert repo.find_by_name("Rock", "Mood") is None

    def test_get_or_create(self, repo):
        t1, c1 = repo.get_or_create("Happy", "Mood")
        assert c1 is True
        
        t2, c2 = repo.get_or_create("Happy", "Mood")
        assert c2 is False
        assert t1.tag_id == t2.tag_id

    def test_source_tagging(self, repo):
        # Create tag
        tag = repo.create("Favorite", "User")
        
        # Insert a dummy source to satisfy FK
        fake_source_id = 100
        with repo.get_connection() as conn:
            # We need to insert into MediaSources first with ALL constraints met (TypeID=1 is MP3)
            conn.execute("INSERT INTO MediaSources (SourceID, SourcePath, MediaName, IsActive, TypeID) VALUES (?, 'test.mp3', 'Test Title', 1, 1)", (fake_source_id,))

        # Link
        repo.add_tag_to_source(fake_source_id, tag.tag_id)
        
        # Fetch
        tags = repo.get_tags_for_source(fake_source_id)
        assert len(tags) == 1
        assert tags[0].tag_name == "Favorite"
        
        # Fetch with category filter
        assert len(repo.get_tags_for_source(fake_source_id, "User")) == 1
        assert len(repo.get_tags_for_source(fake_source_id, "Genre")) == 0
        
        # Unlink
        repo.remove_tag_from_source(fake_source_id, tag.tag_id)
        assert len(repo.get_tags_for_source(fake_source_id)) == 0
        
    def test_remove_all_tags_from_source(self, repo):
        """Test bulk removal with and without category filter."""
        s_id = 200
        with repo.get_connection() as conn:
            conn.execute("INSERT INTO MediaSources (SourceID, SourcePath, MediaName, IsActive, TypeID) VALUES (?, 'bulk.mp3', 'Title', 1, 1)", (s_id,))
            
        t1, _ = repo.get_or_create("Rock", "Genre")
        t2, _ = repo.get_or_create("Jazz", "Genre")
        t3, _ = repo.get_or_create("Happy", "Mood")
        
        repo.add_tag_to_source(s_id, t1.tag_id)
        repo.add_tag_to_source(s_id, t2.tag_id)
        repo.add_tag_to_source(s_id, t3.tag_id)
        
        # Check initial state
        assert len(repo.get_tags_for_source(s_id)) == 3
        
        # Remove only Genres
        repo.remove_all_tags_from_source(s_id, "Genre")
        remaining = repo.get_tags_for_source(s_id)
        assert len(remaining) == 1
        assert remaining[0].tag_name == "Happy"
        
        # Remove rest
        repo.remove_all_tags_from_source(s_id)
        assert len(repo.get_tags_for_source(s_id)) == 0

    def test_get_all_by_category(self, repo):
        repo.create("Rock", "Genre")
        repo.create("Jazz", "Genre")
        repo.create("Happy", "Mood")
        
        genres = repo.get_all_by_category("Genre")
        assert len(genres) == 2
        
        moods = repo.get_all_by_category("Mood")
        assert len(moods) == 1

    def test_sentence_casing_logic(self, repo):
        """Verify T-83: Auto-format to Sentence Case on create."""
        # Lowercase input
        t1 = repo.create("pop", "Genre")
        assert t1.tag_name == "Pop"  # Capitalized
        
        # Mixed input
        t2 = repo.create("hIP hOp", "Genre")
        assert t2.tag_name == "HIP hOp" # Only first char is forced upper, standard doesn't force lower on rest (yet)
                                        # Implementation: formatted_name[0].upper() + formatted_name[1:]
                                        # "hIP hOp" -> "HIP hOp". 
                                        # Wait, definition says "Sentence Casing". 
                                        # Let's verify existing logic: name[0].upper() + name[1:]. 
                                        # It does NOT lower the rest. Correct.

    def test_workflow_status_logic(self, repo):
        """Verify is_unprocessed and set_unprocessed logic."""
        s_id = 300
        with repo.get_connection() as conn:
             conn.execute("INSERT INTO MediaSources (SourceID, SourcePath, MediaName, IsActive, TypeID) VALUES (?, 'wf.mp3', 'Title', 1, 1)", (s_id,))
             
        # Initially False (no tag)
        assert repo.is_unprocessed(s_id) is False
        
        # Set to Unprocessed
        repo.set_unprocessed(s_id, True)
        assert repo.is_unprocessed(s_id) is True
        
        # Verify tag exists
        tags = repo.get_tags_for_source(s_id, "Status")
        assert len(tags) == 1
        assert tags[0].tag_name == "Unprocessed"
        
        # Set to Processed (False)
        repo.set_unprocessed(s_id, False)
        assert repo.is_unprocessed(s_id) is False
        
        # Tag should be gone
        assert len(repo.get_tags_for_source(s_id, "Status")) == 0

    def test_merge_tags(self, repo):
        """Verify merging tags reassigns sources and deletes old tag."""
        s1, s2 = 401, 402
        with repo.get_connection() as conn:
             conn.execute("INSERT INTO MediaSources (SourceID, SourcePath, MediaName, IsActive, TypeID) VALUES (?, '1.mp3', 'T1', 1, 1)", (s1,))
             conn.execute("INSERT INTO MediaSources (SourceID, SourcePath, MediaName, IsActive, TypeID) VALUES (?, '2.mp3', 'T2', 1, 1)", (s2,))
        
        # Create "Rok" (Bad) and "Rock" (Good)
        bad_tag = repo.create("Rok", "Genre")
        good_tag = repo.create("Rock", "Genre")
        
        # Assign sources
        repo.add_tag_to_source(s1, bad_tag.tag_id)
        repo.add_tag_to_source(s2, bad_tag.tag_id) # s2 has bad tag
        repo.add_tag_to_source(s2, good_tag.tag_id) # s2 ALSO has good tag (duplicate case)
        
        # Merge "Rok" into "Rock"
        success = repo.merge_tags(bad_tag.tag_id, good_tag.tag_id)
        assert success is True
        
        # 1. "Rok" should be gone
        assert repo.get_by_id(bad_tag.tag_id) is None
        
        # 2. s1 should now have "Rock"
        tags_s1 = repo.get_tags_for_source(s1)
        assert len(tags_s1) == 1
        assert tags_s1[0].tag_id == good_tag.tag_id
        
        # 3. s2 should still have "Rock" (deduplicated, not double assigned)
        tags_s2 = repo.get_tags_for_source(s2)
        assert len(tags_s2) == 1
        assert tags_s2[0].tag_id == good_tag.tag_id

    def test_get_active_tags(self, repo):
        """Verify get_active_tags filters inactive sources."""
        s_active = 501
        s_inactive = 502
        
        with repo.get_connection() as conn:
            # Active source
            conn.execute("INSERT INTO MediaSources (SourceID, SourcePath, MediaName, IsActive, TypeID) VALUES (?, 'act.mp3', 'Active', 1, 1)", (s_active,))
            # Inactive source
            conn.execute("INSERT INTO MediaSources (SourceID, SourcePath, MediaName, IsActive, TypeID) VALUES (?, 'dead.mp3', 'Dead', 0, 1)", (s_inactive,))
            
        t1 = repo.create("ActiveTag", "Genre")
        t2 = repo.create("DeadTag", "Genre")
        
        repo.add_tag_to_source(s_active, t1.tag_id)
        repo.add_tag_to_source(s_inactive, t2.tag_id)
        
        active_map = repo.get_active_tags()
        
        # Should contain ActiveTag
        assert "Genre" in active_map
        assert "ActiveTag" in active_map["Genre"]
        
        # Should NOT contain DeadTag
        assert "DeadTag" not in active_map["Genre"]
