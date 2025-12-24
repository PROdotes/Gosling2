
import pytest
from src.data.database import BaseRepository
from src.data.repositories.tag_repository import TagRepository

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
            # We need to insert into MediaSources first with ALL constraints met
            conn.execute("INSERT INTO MediaSources (SourceID, Source, Name, IsActive, TypeID) VALUES (?, 'test.mp3', 'Test Title', 1, 1)", (fake_source_id,))

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

    def test_get_all_by_category(self, repo):
        repo.create("Rock", "Genre")
        repo.create("Jazz", "Genre")
        repo.create("Happy", "Mood")
        
        genres = repo.get_all_by_category("Genre")
        assert len(genres) == 2
        
        moods = repo.get_all_by_category("Mood")
        assert len(moods) == 1
