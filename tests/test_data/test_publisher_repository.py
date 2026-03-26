"""
Contract tests for PublisherRepository.
Every assertion verifies EXACT values from the populated_db fixture.
"""

from src.data.publisher_repository import PublisherRepository


class TestGetAll:
    """PublisherRepository.get_all contracts."""

    def test_returns_all_six_publishers_ordered(self, populated_db):
        """Test that get_all returns all publishers ordered by name."""
        repo = PublisherRepository(populated_db)
        pubs = repo.get_all()

        assert len(pubs) == 6, f"Expected 6 publishers, got {len(pubs)}"

        # ORDER BY PublisherName - exhaustive assertions for each
        assert pubs[0].id == 10, f"Expected 10, got {pubs[0].id}"
        assert (
            pubs[0].name == "DGC Records"
        ), f"Expected 'DGC Records', got '{pubs[0].name}'"

        assert pubs[1].id == 3, f"Expected 3, got {pubs[1].id}"
        assert (
            pubs[1].name == "Island Def Jam"
        ), f"Expected 'Island Def Jam', got '{pubs[1].name}'"

        assert pubs[2].id == 2, f"Expected 2, got {pubs[2].id}"
        assert (
            pubs[2].name == "Island Records"
        ), f"Expected 'Island Records', got '{pubs[2].name}'"

        assert pubs[3].id == 4, f"Expected 4, got {pubs[3].id}"
        assert (
            pubs[3].name == "Roswell Records"
        ), f"Expected 'Roswell Records', got '{pubs[3].name}'"

        assert pubs[4].id == 5, f"Expected 5, got {pubs[4].id}"
        assert pubs[4].name == "Sub Pop", f"Expected 'Sub Pop', got '{pubs[4].name}'"

        assert pubs[5].id == 1, f"Expected 1, got {pubs[5].id}"
        assert (
            pubs[5].name == "Universal Music Group"
        ), f"Expected 'Universal Music Group', got '{pubs[5].name}'"

    def test_parent_ids_correct(self, populated_db):
        """Test that parent_id relationships are correct."""
        repo = PublisherRepository(populated_db)
        pubs = repo.get_all()
        parent_map = {p.name: p.parent_id for p in pubs}

        assert (
            parent_map["Universal Music Group"] is None
        ), f"Expected None, got {parent_map['Universal Music Group']}"
        assert (
            parent_map["Island Records"] == 1
        ), f"Expected 1, got {parent_map['Island Records']}"
        assert (
            parent_map["Island Def Jam"] == 2
        ), f"Expected 2, got {parent_map['Island Def Jam']}"
        assert (
            parent_map["DGC Records"] == 1
        ), f"Expected 1, got {parent_map['DGC Records']}"
        assert (
            parent_map["Roswell Records"] is None
        ), f"Expected None, got {parent_map['Roswell Records']}"
        assert (
            parent_map["Sub Pop"] is None
        ), f"Expected None, got {parent_map['Sub Pop']}"

    def test_empty_db_returns_empty(self, empty_db):
        """Test that get_all returns empty on empty DB."""
        repo = PublisherRepository(empty_db)
        pubs = repo.get_all()
        assert pubs == [], f"Expected empty list on empty DB, got {pubs}"


class TestSearch:
    """PublisherRepository.search contracts."""

    def test_exact_match(self, populated_db):
        """Test that exact name match returns publisher."""
        repo = PublisherRepository(populated_db)
        pubs = repo.search("Sub Pop")

        assert len(pubs) == 1, f"Expected 1 publisher, got {len(pubs)}"
        assert pubs[0].id == 5, f"Expected 5, got {pubs[0].id}"
        assert pubs[0].name == "Sub Pop", f"Expected 'Sub Pop', got '{pubs[0].name}'"
        assert (
            pubs[0].parent_id is None
        ), f"Expected None for parent_id, got {pubs[0].parent_id}"

    def test_partial_match(self, populated_db):
        """Test that partial match returns multiple publishers."""
        repo = PublisherRepository(populated_db)
        pubs = repo.search("Island")

        assert len(pubs) == 2, f"Expected 2 publishers, got {len(pubs)}"
        names = {p.name for p in pubs}
        assert names == {
            "Island Records",
            "Island Def Jam",
        }, f"Unexpected names: {names}"

    def test_no_match_returns_empty(self, populated_db):
        """Test that search returns empty list for no matches."""
        repo = PublisherRepository(populated_db)
        pubs = repo.search("ZZZZZ")
        assert pubs == [], f"Expected empty list for no match, got {pubs}"

    def test_universal_match(self, populated_db):
        """'Universal' should match Umbrella (4 publishers)."""
        repo = PublisherRepository(populated_db)
        pubs = repo.search("Universal")

        assert len(pubs) == 4, f"Expected 4 publishers, got {len(pubs)}"
        # Sorted by name: DGC(10), Island Def Jam(3), Island Records(2), Universal(1)
        assert pubs[3].id == 1, f"Expected 1 at index 3, got {pubs[3].id}"
        assert (
            pubs[3].name == "Universal Music Group"
        ), f"Expected 'Universal Music Group', got '{pubs[3].name}'"


class TestGetById:
    """PublisherRepository.get_by_id contracts."""

    def test_valid_id_returns_publisher(self, populated_db):
        """Test that get_by_id returns complete publisher object."""
        repo = PublisherRepository(populated_db)
        pub = repo.get_by_id(1)

        assert pub is not None, f"Expected publisher object, got {pub}"
        assert pub.id == 1, f"Expected 1, got {pub.id}"
        assert (
            pub.name == "Universal Music Group"
        ), f"Expected 'Universal Music Group', got '{pub.name}'"
        assert (
            pub.parent_id is None
        ), f"Expected None for parent_id, got {pub.parent_id}"
        assert (
            pub.parent_name is None
        ), f"Expected None for parent_name, got {pub.parent_name}"
        assert (
            pub.sub_publishers == []
        ), f"Expected empty list for sub_publishers, got {pub.sub_publishers}"

    def test_child_publisher(self, populated_db):
        """Test that child publisher has correct parent_id."""
        repo = PublisherRepository(populated_db)
        pub = repo.get_by_id(10)

        assert pub is not None, f"Expected publisher object, got {pub}"
        assert pub.id == 10, f"Expected 10, got {pub.id}"
        assert pub.name == "DGC Records", f"Expected 'DGC Records', got '{pub.name}'"
        assert pub.parent_id == 1, f"Expected 1, got {pub.parent_id}"

    def test_nonexistent_returns_none(self, populated_db):
        """Test that get_by_id returns None for non-existent ID."""
        repo = PublisherRepository(populated_db)
        pub = repo.get_by_id(999)
        assert pub is None, f"Expected None for nonexistent ID, got {pub}"


class TestGetByIds:
    """PublisherRepository.get_by_ids contracts."""

    def test_batch_fetch_returns_complete_objects(self, populated_db):
        """Test that get_by_ids returns complete publisher objects."""
        repo = PublisherRepository(populated_db)
        pubs = repo.get_by_ids([1, 5, 10])

        assert len(pubs) == 3, f"Expected 3 publishers, got {len(pubs)}"

        # Exhaustive assertions for each
        names = {p.name for p in pubs}
        assert names == {
            "Universal Music Group",
            "Sub Pop",
            "DGC Records",
        }, f"Unexpected names: {names}"

    def test_empty_list_returns_empty(self, populated_db):
        """Test that get_by_ids returns empty list for empty input."""
        repo = PublisherRepository(populated_db)
        pubs = repo.get_by_ids([])
        assert pubs == [], f"Expected empty list, got {pubs}"


class TestGetPublishers:
    """PublisherRepository.get_publishers (dict return) contracts."""

    def test_returns_dict_keyed_by_id(self, populated_db):
        """Test that get_publishers returns dict keyed by ID."""
        repo = PublisherRepository(populated_db)
        pubs = repo.get_publishers([1, 2])

        assert len(pubs) == 2, f"Expected 2 publishers, got {len(pubs)}"
        assert 1 in pubs, f"Expected key 1 in dict, got keys: {pubs.keys()}"
        assert 2 in pubs, f"Expected key 2 in dict, got keys: {pubs.keys()}"
        assert pubs[1].id == 1, f"Expected 1, got {pubs[1].id}"
        assert (
            pubs[1].name == "Universal Music Group"
        ), f"Expected 'Universal Music Group', got '{pubs[1].name}'"
        assert pubs[2].id == 2, f"Expected 2, got {pubs[2].id}"
        assert (
            pubs[2].name == "Island Records"
        ), f"Expected 'Island Records', got '{pubs[2].name}'"

    def test_empty_input_returns_empty_dict(self, populated_db):
        """Test that empty input returns empty dict."""
        repo = PublisherRepository(populated_db)
        pubs = repo.get_publishers([])
        assert pubs == {}, f"Expected empty dict, got {pubs}"


class TestGetHierarchyBatch:
    """PublisherRepository.get_hierarchy_batch (recursive CTE) contracts."""

    def test_island_def_jam_chain(self, populated_db):
        """Island Def Jam (3) -> Island Records (2) -> UMG (1). CTE should return all three."""
        repo = PublisherRepository(populated_db)
        hierarchy = repo.get_hierarchy_batch([3])

        assert (
            3 in hierarchy
        ), f"Expected key 3 in hierarchy, got keys: {hierarchy.keys()}"
        assert (
            2 in hierarchy
        ), f"Expected key 2 in hierarchy, got keys: {hierarchy.keys()}"
        assert (
            1 in hierarchy
        ), f"Expected key 1 in hierarchy, got keys: {hierarchy.keys()}"

        assert hierarchy[3].id == 3, f"Expected 3, got {hierarchy[3].id}"
        assert (
            hierarchy[3].name == "Island Def Jam"
        ), f"Expected 'Island Def Jam', got '{hierarchy[3].name}'"
        assert hierarchy[2].id == 2, f"Expected 2, got {hierarchy[2].id}"
        assert (
            hierarchy[2].name == "Island Records"
        ), f"Expected 'Island Records', got '{hierarchy[2].name}'"
        assert hierarchy[1].id == 1, f"Expected 1, got {hierarchy[1].id}"
        assert (
            hierarchy[1].name == "Universal Music Group"
        ), f"Expected 'Universal Music Group', got '{hierarchy[1].name}'"

    def test_root_publisher(self, populated_db):
        """UMG (1) has no parent. CTE should return only itself."""
        repo = PublisherRepository(populated_db)
        hierarchy = repo.get_hierarchy_batch([1])

        assert len(hierarchy) == 1, f"Expected 1 publisher, got {len(hierarchy)}"
        assert (
            1 in hierarchy
        ), f"Expected key 1 in hierarchy, got keys: {hierarchy.keys()}"
        assert hierarchy[1].id == 1, f"Expected 1, got {hierarchy[1].id}"
        assert (
            hierarchy[1].name == "Universal Music Group"
        ), f"Expected 'Universal Music Group', got '{hierarchy[1].name}'"

    def test_dgc_chain(self, populated_db):
        """DGC Records (10) -> UMG (1)."""
        repo = PublisherRepository(populated_db)
        hierarchy = repo.get_hierarchy_batch([10])

        assert (
            10 in hierarchy
        ), f"Expected key 10 in hierarchy, got keys: {hierarchy.keys()}"
        assert (
            1 in hierarchy
        ), f"Expected key 1 in hierarchy, got keys: {hierarchy.keys()}"
        assert hierarchy[10].id == 10, f"Expected 10, got {hierarchy[10].id}"
        assert (
            hierarchy[10].name == "DGC Records"
        ), f"Expected 'DGC Records', got '{hierarchy[10].name}'"
        assert hierarchy[1].id == 1, f"Expected 1, got {hierarchy[1].id}"
        assert (
            hierarchy[1].name == "Universal Music Group"
        ), f"Expected 'Universal Music Group', got '{hierarchy[1].name}'"

    def test_empty_input_returns_empty_dict(self, populated_db):
        """Test that empty input returns empty dict."""
        repo = PublisherRepository(populated_db)
        hierarchy = repo.get_hierarchy_batch([])
        assert hierarchy == {}, f"Expected empty dict, got {hierarchy}"


class TestGetChildren:
    """PublisherRepository.get_children contracts."""

    def test_umg_children(self, populated_db):
        """UMG (1) has children: Island Records (2) and DGC Records (10)."""
        repo = PublisherRepository(populated_db)
        children = repo.get_children(1)

        assert len(children) == 2, f"Expected 2 children, got {len(children)}"
        names = {c.name for c in children}
        assert names == {"Island Records", "DGC Records"}, f"Unexpected names: {names}"

    def test_island_children(self, populated_db):
        """Island Records (2) has one child: Island Def Jam (3)."""
        repo = PublisherRepository(populated_db)
        children = repo.get_children(2)

        assert len(children) == 1, f"Expected 1 child, got {len(children)}"
        assert children[0].id == 3, f"Expected 3, got {children[0].id}"
        assert (
            children[0].name == "Island Def Jam"
        ), f"Expected 'Island Def Jam', got '{children[0].name}'"

    def test_leaf_has_no_children(self, populated_db):
        """Sub Pop (5) has no children."""
        repo = PublisherRepository(populated_db)
        children = repo.get_children(5)
        assert children == [], f"Expected empty list for leaf publisher, got {children}"


class TestGetSongIdsByPublisher:
    """PublisherRepository.get_song_ids_by_publisher contracts."""

    def test_dgc_has_song_1(self, populated_db):
        """DGC Records (10) has Song 1 via RecordingPublishers."""
        repo = PublisherRepository(populated_db)
        song_ids = repo.get_song_ids_by_publisher(10)
        assert song_ids == [1], f"Expected [1], got {song_ids}"

    def test_publisher_with_no_songs(self, populated_db):
        """Sub Pop (5) has no RecordingPublisher entries."""
        repo = PublisherRepository(populated_db)
        song_ids = repo.get_song_ids_by_publisher(5)
        assert (
            song_ids == []
        ), f"Expected empty list for publisher with no songs, got {song_ids}"


class TestGetPublishersForAlbums:
    """PublisherRepository.get_publishers_for_albums contracts."""

    def test_nevermind_publishers(self, populated_db):
        """Nevermind (100) has DGC Records (10) and Sub Pop (5)."""
        repo = PublisherRepository(populated_db)
        results = repo.get_publishers_for_albums([100])

        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        pub_names = {pub.name for album_id, pub in results}
        assert pub_names == {"DGC Records", "Sub Pop"}, f"Unexpected names: {pub_names}"
        # All should be album 100
        assert all(
            aid == 100 for aid, _ in results
        ), f"Expected all album_id=100, got {[aid for aid, _ in results]}"

    def test_tcats_publisher(self, populated_db):
        """The Colour and the Shape (200) has Roswell Records (4)."""
        repo = PublisherRepository(populated_db)
        results = repo.get_publishers_for_albums([200])

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0][0] == 200, f"Expected 200, got {results[0][0]}"
        assert results[0][1].id == 4, f"Expected 4, got {results[0][1].id}"
        assert (
            results[0][1].name == "Roswell Records"
        ), f"Expected 'Roswell Records', got '{results[0][1].name}'"

    def test_empty_input_returns_empty(self, populated_db):
        """Test that empty input returns empty list."""
        repo = PublisherRepository(populated_db)
        results = repo.get_publishers_for_albums([])
        assert results == [], f"Expected empty list, got {results}"


class TestGetPublishersForSongs:
    """PublisherRepository.get_publishers_for_songs contracts."""

    def test_song_1_publisher(self, populated_db):
        """Song 1 has DGC Records (10) via RecordingPublishers."""
        repo = PublisherRepository(populated_db)
        results = repo.get_publishers_for_songs([1])

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0][0] == 1, f"Expected 1, got {results[0][0]}"
        assert results[0][1].id == 10, f"Expected 10, got {results[0][1].id}"
        assert (
            results[0][1].name == "DGC Records"
        ), f"Expected 'DGC Records', got '{results[0][1].name}'"

    def test_song_without_publisher(self, populated_db):
        """Song 2 has no RecordingPublisher entry."""
        repo = PublisherRepository(populated_db)
        results = repo.get_publishers_for_songs([2])
        assert (
            results == []
        ), f"Expected empty list for song without publisher, got {results}"

    def test_empty_input_returns_empty(self, populated_db):
        """Test that empty input returns empty list."""
        repo = PublisherRepository(populated_db)
        results = repo.get_publishers_for_songs([])
        assert results == [], f"Expected empty list, got {results}"


# ===================================================================
# Mapper Tests: _row_to_publisher
# ===================================================================
class TestRowToPublisher:
    def test_all_fields_present(self, mock_db_path):
        mock_row = {
            "PublisherID": 1,
            "PublisherName": "Universal Music Group",
            "ParentPublisherID": None,
        }
        repo = PublisherRepository(mock_db_path)
        result = repo._row_to_publisher(mock_row)
        assert result.id == 1
        assert result.name == "Universal Music Group"
        assert result.parent_id is None

    def test_null_fields(self, mock_db_path):
        mock_row = {
            "PublisherID": 1,
            "PublisherName": "Universal Music Group",
            "ParentPublisherID": None,
        }
        repo = PublisherRepository(mock_db_path)
        result = repo._row_to_publisher(mock_row)
        assert result.id == 1
        assert result.name == "Universal Music Group"
        assert result.parent_id is None
