"""
Contract tests for PublisherRepository.
Every assertion verifies EXACT values from the populated_db fixture.
"""
from src.data.publisher_repository import PublisherRepository


class TestGetAll:
    """PublisherRepository.get_all contracts."""

    def test_returns_all_six_publishers(self, populated_db):
        repo = PublisherRepository(populated_db)
        pubs = repo.get_all()

        assert len(pubs) == 6
        names = [p.name for p in pubs]
        # ORDER BY PublisherName
        assert names == [
            "DGC Records",
            "Island Def Jam",
            "Island Records",
            "Roswell Records",
            "Sub Pop",
            "Universal Music Group",
        ]

    def test_parent_ids_correct(self, populated_db):
        repo = PublisherRepository(populated_db)
        pubs = repo.get_all()
        parent_map = {p.name: p.parent_id for p in pubs}

        assert parent_map["Universal Music Group"] is None
        assert parent_map["Island Records"] == 1   # parent = UMG
        assert parent_map["Island Def Jam"] == 2    # parent = Island Records
        assert parent_map["DGC Records"] == 1       # parent = UMG
        assert parent_map["Roswell Records"] is None
        assert parent_map["Sub Pop"] is None

    def test_empty_db(self, empty_db):
        repo = PublisherRepository(empty_db)
        assert repo.get_all() == []


class TestSearch:
    """PublisherRepository.search contracts."""

    def test_exact_match(self, populated_db):
        repo = PublisherRepository(populated_db)
        pubs = repo.search("Sub Pop")
        assert len(pubs) == 1
        assert pubs[0].id == 5
        assert pubs[0].name == "Sub Pop"

    def test_partial_match(self, populated_db):
        repo = PublisherRepository(populated_db)
        pubs = repo.search("Island")
        assert len(pubs) == 2
        names = {p.name for p in pubs}
        assert names == {"Island Records", "Island Def Jam"}

    def test_no_match(self, populated_db):
        repo = PublisherRepository(populated_db)
        assert repo.search("ZZZZZ") == []

    def test_universal_match(self, populated_db):
        """'Universal' should match only 'Universal Music Group'."""
        repo = PublisherRepository(populated_db)
        pubs = repo.search("Universal")
        assert len(pubs) == 1
        assert pubs[0].name == "Universal Music Group"


class TestGetById:
    """PublisherRepository.get_by_id contracts."""

    def test_valid_id(self, populated_db):
        repo = PublisherRepository(populated_db)
        pub = repo.get_by_id(1)
        assert pub is not None
        assert pub.name == "Universal Music Group"
        assert pub.parent_id is None

    def test_child_publisher(self, populated_db):
        repo = PublisherRepository(populated_db)
        pub = repo.get_by_id(10)
        assert pub is not None
        assert pub.name == "DGC Records"
        assert pub.parent_id == 1

    def test_nonexistent(self, populated_db):
        repo = PublisherRepository(populated_db)
        assert repo.get_by_id(999) is None


class TestGetByIds:
    """PublisherRepository.get_by_ids contracts."""

    def test_batch_fetch(self, populated_db):
        repo = PublisherRepository(populated_db)
        pubs = repo.get_by_ids([1, 5, 10])
        assert len(pubs) == 3
        names = {p.name for p in pubs}
        assert names == {"Universal Music Group", "Sub Pop", "DGC Records"}

    def test_empty_input(self, populated_db):
        repo = PublisherRepository(populated_db)
        assert repo.get_by_ids([]) == []


class TestGetPublishers:
    """PublisherRepository.get_publishers (dict return) contracts."""

    def test_returns_dict_keyed_by_id(self, populated_db):
        repo = PublisherRepository(populated_db)
        pubs = repo.get_publishers([1, 2])

        assert len(pubs) == 2
        assert pubs[1].name == "Universal Music Group"
        assert pubs[2].name == "Island Records"

    def test_empty_input(self, populated_db):
        repo = PublisherRepository(populated_db)
        assert repo.get_publishers([]) == {}


class TestGetHierarchyBatch:
    """PublisherRepository.get_hierarchy_batch (recursive CTE) contracts."""

    def test_island_def_jam_chain(self, populated_db):
        """Island Def Jam (3) -> Island Records (2) -> UMG (1). CTE should return all three."""
        repo = PublisherRepository(populated_db)
        hierarchy = repo.get_hierarchy_batch([3])

        assert 3 in hierarchy  # seed
        assert 2 in hierarchy  # parent
        assert 1 in hierarchy  # grandparent

        assert hierarchy[3].name == "Island Def Jam"
        assert hierarchy[2].name == "Island Records"
        assert hierarchy[1].name == "Universal Music Group"

    def test_root_publisher(self, populated_db):
        """UMG (1) has no parent. CTE should return only itself."""
        repo = PublisherRepository(populated_db)
        hierarchy = repo.get_hierarchy_batch([1])
        assert len(hierarchy) == 1
        assert hierarchy[1].name == "Universal Music Group"

    def test_dgc_chain(self, populated_db):
        """DGC Records (10) -> UMG (1)."""
        repo = PublisherRepository(populated_db)
        hierarchy = repo.get_hierarchy_batch([10])
        assert 10 in hierarchy
        assert 1 in hierarchy
        assert hierarchy[10].name == "DGC Records"
        assert hierarchy[1].name == "Universal Music Group"

    def test_empty_input(self, populated_db):
        repo = PublisherRepository(populated_db)
        assert repo.get_hierarchy_batch([]) == {}


class TestGetChildren:
    """PublisherRepository.get_children contracts."""

    def test_umg_children(self, populated_db):
        """UMG (1) has children: Island Records (2) and DGC Records (10)."""
        repo = PublisherRepository(populated_db)
        children = repo.get_children(1)
        names = {c.name for c in children}
        assert names == {"Island Records", "DGC Records"}

    def test_island_children(self, populated_db):
        """Island Records (2) has one child: Island Def Jam (3)."""
        repo = PublisherRepository(populated_db)
        children = repo.get_children(2)
        assert len(children) == 1
        assert children[0].name == "Island Def Jam"

    def test_leaf_has_no_children(self, populated_db):
        """Sub Pop (5) has no children."""
        repo = PublisherRepository(populated_db)
        children = repo.get_children(5)
        assert children == []


class TestGetSongIdsByPublisher:
    """PublisherRepository.get_song_ids_by_publisher contracts."""

    def test_dgc_has_song_1(self, populated_db):
        """DGC Records (10) has Song 1 via RecordingPublishers."""
        repo = PublisherRepository(populated_db)
        song_ids = repo.get_song_ids_by_publisher(10)
        assert song_ids == [1]

    def test_publisher_with_no_songs(self, populated_db):
        """Sub Pop (5) has no RecordingPublisher entries."""
        repo = PublisherRepository(populated_db)
        song_ids = repo.get_song_ids_by_publisher(5)
        assert song_ids == []


class TestGetPublishersForAlbums:
    """PublisherRepository.get_publishers_for_albums contracts."""

    def test_nevermind_publishers(self, populated_db):
        """Nevermind (100) has DGC Records (10) and Sub Pop (5)."""
        repo = PublisherRepository(populated_db)
        results = repo.get_publishers_for_albums([100])
        pub_names = {pub.name for album_id, pub in results}
        assert pub_names == {"DGC Records", "Sub Pop"}
        # All should be album 100
        assert all(aid == 100 for aid, _ in results)

    def test_tcats_publisher(self, populated_db):
        """The Colour and the Shape (200) has Roswell Records (4)."""
        repo = PublisherRepository(populated_db)
        results = repo.get_publishers_for_albums([200])
        assert len(results) == 1
        assert results[0][0] == 200
        assert results[0][1].name == "Roswell Records"

    def test_empty_input(self, populated_db):
        repo = PublisherRepository(populated_db)
        assert repo.get_publishers_for_albums([]) == []


class TestGetPublishersForSongs:
    """PublisherRepository.get_publishers_for_songs contracts."""

    def test_song_1_publisher(self, populated_db):
        """Song 1 has DGC Records (10) via RecordingPublishers."""
        repo = PublisherRepository(populated_db)
        results = repo.get_publishers_for_songs([1])
        assert len(results) == 1
        assert results[0][0] == 1
        assert results[0][1].name == "DGC Records"

    def test_song_without_publisher(self, populated_db):
        """Song 2 has no RecordingPublisher entry."""
        repo = PublisherRepository(populated_db)
        results = repo.get_publishers_for_songs([2])
        assert results == []

    def test_empty_input(self, populated_db):
        repo = PublisherRepository(populated_db)
        assert repo.get_publishers_for_songs([]) == []
