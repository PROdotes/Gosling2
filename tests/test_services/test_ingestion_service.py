"""
Integration tests for ingestion metadata collision detection.
Tests find_by_metadata, get_by_path, get_by_hash against real SQLite.
NO MOCKING. All assertions hit real data.

Populated DB reference (from conftest):
    Song 1:  "Smells Like Teen Spirit"  Performers: [Nirvana]                      Year: 1991
    Song 2:  "Everlong"                 Performers: [Foo Fighters]                  Year: 1997
    Song 3:  "Range Rover Bitch"        Performers: [Taylor Hawkins]                Year: 2016
    Song 4:  "Grohlton Theme"           Performers: [Grohlton]                      Year: None
    Song 5:  "Pocketwatch Demo"         Performers: [Late!]                         Year: 1992
    Song 6:  "Dual Credit Track"        Performers: [Dave Grohl], Composer: [Taylor] Year: None
    Song 7:  "Hollow Song"              Performers: []                              Year: None
    Song 8:  "Joint Venture"            Performers: [Dave Grohl, Taylor Hawkins]     Year: None
    Song 9:  "Priority Test"            Performers: []                              Year: None

Disambiguation fixture (local, extends populated_db):
    Song 50: "Shared Title"             Performers: [Nirvana]                       Year: 1991
    Song 51: "Shared Title"             Performers: [Foo Fighters]                  Year: 1991
    Song 52: "Shared Title"             Performers: [Dave Grohl, Taylor Hawkins]    Year: 1991
    Song 53: "Shared Title"             Performers: [Nirvana]                       Year: 2020
"""

import sqlite3
import shutil
import os
import pytest
from src.data.song_repository import SongRepository
from src.services.catalog_service import CatalogService


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    return conn


@pytest.fixture
def disambiguation_db(tmp_path, _master_populated_db):
    """Populated DB extended with same-title songs for disambiguation testing."""
    dest = tmp_path / "disambig.db"
    shutil.copy(_master_populated_db, dest)
    db_path = str(dest)

    conn = _connect(db_path)
    c = conn.cursor()

    # Song 50: "Shared Title" by Nirvana, 1991
    c.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) "
        "VALUES (50, 1, 'Shared Title', '/path/50', 200, 1)"
    )
    c.execute("INSERT INTO Songs (SourceID, RecordingYear) VALUES (50, 1991)")
    c.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (50, 20, 1)"
    )  # Nirvana Performer

    # Song 51: "Shared Title" by Foo Fighters, 1991
    c.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) "
        "VALUES (51, 1, 'Shared Title', '/path/51', 200, 1)"
    )
    c.execute("INSERT INTO Songs (SourceID, RecordingYear) VALUES (51, 1991)")
    c.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (51, 30, 1)"
    )  # Foo Fighters Performer

    # Song 52: "Shared Title" by Dave Grohl + Taylor Hawkins, 1991
    c.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) "
        "VALUES (52, 1, 'Shared Title', '/path/52', 200, 1)"
    )
    c.execute("INSERT INTO Songs (SourceID, RecordingYear) VALUES (52, 1991)")
    c.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (52, 10, 1)"
    )  # Dave Grohl Performer
    c.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (52, 40, 1)"
    )  # Taylor Hawkins Performer

    # Song 53: "Shared Title" by Nirvana, 2020 (different year)
    c.execute(
        "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, IsActive) "
        "VALUES (53, 1, 'Shared Title', '/path/53', 200, 1)"
    )
    c.execute("INSERT INTO Songs (SourceID, RecordingYear) VALUES (53, 2020)")
    c.execute(
        "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (53, 20, 1)"
    )  # Nirvana Performer

    conn.commit()
    conn.close()
    return db_path


class TestExactPerformerSetMatch:
    """find_by_metadata must match the EXACT set of Performers, not a subset or superset."""

    def test_single_artist_exact_match(self, populated_db):
        """Nirvana + SLTS + 1991 -> Song 1."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Smells Like Teen Spirit", ["Nirvana"], 1991)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 1, f"Expected id 1, got {results[0].id}"

    def test_two_performers_exact_match(self, populated_db):
        """Dave Grohl + Taylor Hawkins are both Performers on Song 8."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata(
            "Joint Venture", ["Dave Grohl", "Taylor Hawkins"], None
        )
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 8, f"Expected id 8, got {results[0].id}"

    def test_two_performers_reversed_order(self, populated_db):
        """Artist order shouldn't matter -- set comparison."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata(
            "Joint Venture", ["Taylor Hawkins", "Dave Grohl"], None
        )
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 8, f"Expected id 8, got {results[0].id}"

    def test_superset_artists_no_match(self, populated_db):
        """DB has [Nirvana] for SLTS. Searching [Nirvana, Dave Grohl] must NOT match."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata(
            "Smells Like Teen Spirit", ["Nirvana", "Dave Grohl"], 1991
        )
        assert (
            len(results) == 0
        ), f"Expected 0 results for superset artist, got {len(results)}"

    def test_subset_artists_no_match(self, populated_db):
        """DB has [Dave Grohl, Taylor Hawkins] for Joint Venture.
        Searching only [Dave Grohl] must NOT match (subset)."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Joint Venture", ["Dave Grohl"], None)
        assert (
            len(results) == 0
        ), f"Expected 0 results for subset artist, got {len(results)}"

    def test_subset_artists_no_match_other_side(self, populated_db):
        """Searching only [Taylor Hawkins] for Joint Venture must NOT match either."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Joint Venture", ["Taylor Hawkins"], None)
        assert (
            len(results) == 0
        ), f"Expected 0 results for subset artist, got {len(results)}"

    def test_wrong_artist_completely(self, populated_db):
        """Correct title + year but completely wrong artist."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata(
            "Smells Like Teen Spirit", ["Taylor Hawkins"], 1991
        )
        assert (
            len(results) == 0
        ), f"Expected 0 results for wrong artist, got {len(results)}"

    def test_composer_not_treated_as_performer(self, populated_db):
        """Song 6 has Dave Grohl(Performer) + Taylor Hawkins(Composer).
        Only Performer role should count. Searching for both as Performers must NOT match.
        """
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata(
            "Dual Credit Track", ["Dave Grohl", "Taylor Hawkins"], None
        )
        assert (
            len(results) == 0
        ), f"Expected 0 results treating Composer as Performer, got {len(results)}"

    def test_composer_ignored_single_performer_match(self, populated_db):
        """Song 6: only Dave Grohl is Performer. Searching [Dave Grohl] should match."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Dual Credit Track", ["Dave Grohl"], None)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 6, f"Expected id 6, got {results[0].id}"

    def test_duplicate_artist_in_input_collapses(self, populated_db):
        """Passing ["Nirvana", "Nirvana"] should collapse to {"nirvana"} and still match Song 1."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata(
            "Smells Like Teen Spirit", ["Nirvana", "Nirvana"], 1991
        )
        assert (
            len(results) == 1
        ), f"Expected 1 result for duplicate artist, got {len(results)}"
        assert results[0].id == 1, f"Expected id 1, got {results[0].id}"

    def test_alias_name_not_cross_matched(self, populated_db):
        """Song 4 is credited to 'Grohlton' (alias). Searching with 'Dave Grohl'
        (primary name for the same identity) must NOT match -- comparison is on
        DisplayName, not IdentityID."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Grohlton Theme", ["Dave Grohl"], None)
        assert (
            len(results) == 0
        ), f"Expected 0 results for alias cross-match, got {len(results)}"

    def test_alias_exact_name_matches(self, populated_db):
        """Searching with the actual credited alias name 'Grohlton' does match."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Grohlton Theme", ["Grohlton"], None)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 4, f"Expected id 4, got {results[0].id}"


class TestSameTitleDisambiguation:
    """Multiple songs share the same title. Verify correct one is matched/rejected."""

    def test_same_title_correct_single_artist(self, disambiguation_db):
        """'Shared Title' by Nirvana in 1991 -> Song 50 only."""
        repo = SongRepository(disambiguation_db)
        results = repo.find_by_metadata("Shared Title", ["Nirvana"], 1991)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 50, f"Expected id 50, got {results[0].id}"

    def test_same_title_correct_different_artist(self, disambiguation_db):
        """'Shared Title' by Foo Fighters in 1991 -> Song 51 only."""
        repo = SongRepository(disambiguation_db)
        results = repo.find_by_metadata("Shared Title", ["Foo Fighters"], 1991)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 51, f"Expected id 51, got {results[0].id}"

    def test_same_title_correct_multi_artist(self, disambiguation_db):
        """'Shared Title' by [Dave Grohl, Taylor Hawkins] in 1991 -> Song 52 only."""
        repo = SongRepository(disambiguation_db)
        results = repo.find_by_metadata(
            "Shared Title", ["Dave Grohl", "Taylor Hawkins"], 1991
        )
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 52, f"Expected id 52, got {results[0].id}"

    def test_same_title_same_artist_different_year(self, disambiguation_db):
        """'Shared Title' by Nirvana in 2020 -> Song 53 only (not Song 50 which is 1991)."""
        repo = SongRepository(disambiguation_db)
        results = repo.find_by_metadata("Shared Title", ["Nirvana"], 2020)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 53, f"Expected id 53, got {results[0].id}"

    def test_same_title_null_year_returns_all_matching_artists(self, disambiguation_db):
        """'Shared Title' by Nirvana with year=None -> Songs 50 AND 53 (both Nirvana, different years)."""
        repo = SongRepository(disambiguation_db)
        results = repo.find_by_metadata("Shared Title", ["Nirvana"], None)
        assert (
            len(results) == 2
        ), f"Expected 2 results for null year, got {len(results)}"
        ids = {r.id for r in results}
        assert ids == {50, 53}, f"Expected {{50, 53}}, got {ids}"

    def test_same_title_subset_of_multi_no_match(self, disambiguation_db):
        """Song 52 has [Dave Grohl, Taylor Hawkins]. Searching just [Dave Grohl] -> no match.
        Even though Song 52 exists with that title+year, the artist set doesn't match.
        """
        repo = SongRepository(disambiguation_db)
        results = repo.find_by_metadata("Shared Title", ["Dave Grohl"], 1991)
        assert len(results) == 0, f"Expected 0 results for subset, got {len(results)}"

    def test_same_title_superset_of_single_no_match(self, disambiguation_db):
        """Song 50 has [Nirvana]. Searching [Nirvana, Dave Grohl] -> no match."""
        repo = SongRepository(disambiguation_db)
        results = repo.find_by_metadata("Shared Title", ["Nirvana", "Dave Grohl"], 1991)
        assert len(results) == 0, f"Expected 0 results for superset, got {len(results)}"

    def test_same_title_wrong_artist_entirely(self, disambiguation_db):
        """No song has 'Shared Title' by 'Late!', despite the title existing."""
        repo = SongRepository(disambiguation_db)
        results = repo.find_by_metadata("Shared Title", ["Late!"], 1991)
        assert (
            len(results) == 0
        ), f"Expected 0 results for wrong artist, got {len(results)}"


class TestYearBehavior:
    """Year handling: if year is provided it must match, if None it's a wildcard."""

    def test_exact_year_match(self, populated_db):
        """Everlong by Foo Fighters in 1997 -> Song 2."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Everlong", ["Foo Fighters"], 1997)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 2, f"Expected id 2, got {results[0].id}"

    def test_wrong_year_no_match(self, populated_db):
        """Same title+artist but wrong year -> no match."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Everlong", ["Foo Fighters"], 2023)
        assert (
            len(results) == 0
        ), f"Expected 0 results for wrong year, got {len(results)}"

    def test_null_year_query_matches_any_year(self, populated_db):
        """When incoming file has year=None, year filter is skipped.
        This means it matches songs regardless of their stored year."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Everlong", ["Foo Fighters"], None)
        assert len(results) == 1, f"Expected 1 result for null year, got {len(results)}"
        assert results[0].id == 2, f"Expected id 2, got {results[0].id}"

    def test_year_provided_but_db_has_null(self, populated_db):
        """Song 4 (Grohlton Theme) has year=None in DB.
        Searching with year=2023 should NOT match because SQL NULL = 2023 is false."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Grohlton Theme", ["Grohlton"], 2023)
        assert (
            len(results) == 0
        ), f"Expected 0 results when DB has NULL year, got {len(results)}"

    def test_null_year_both_sides(self, populated_db):
        """Song 4 has year=None. Searching with year=None skips the filter -> match."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Grohlton Theme", ["Grohlton"], None)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 4, f"Expected id 4, got {results[0].id}"

    def test_year_zero_treated_as_no_year(self, populated_db):
        """year=0 is falsy in Python, so if year: skips the filter.
        This means year=0 behaves like year=None (wildcard)."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Everlong", ["Foo Fighters"], 0)
        assert len(results) == 1, f"Expected 1 result for year=0, got {len(results)}"
        assert results[0].id == 2, f"Expected id 2, got {results[0].id}"


class TestCaseSensitivity:
    """Title uses COLLATE UTF8_NOCASE, artist comparison uses .lower()."""

    def test_title_uppercase(self, populated_db):
        """EVERLONG matches Everlong."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("EVERLONG", ["Foo Fighters"], 1997)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 2, f"Expected id 2, got {results[0].id}"

    def test_title_lowercase(self, populated_db):
        """everlong matches Everlong."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("everlong", ["Foo Fighters"], 1997)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 2, f"Expected id 2, got {results[0].id}"

    def test_title_mixed_case(self, populated_db):
        """eVeRlOnG matches Everlong."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("eVeRlOnG", ["Foo Fighters"], 1997)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 2, f"Expected id 2, got {results[0].id}"

    def test_artist_lowercase(self, populated_db):
        """Artist comparison in Python uses .lower() sets."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Everlong", ["foo fighters"], 1997)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 2, f"Expected id 2, got {results[0].id}"

    def test_artist_uppercase(self, populated_db):
        """FOO FIGHTERS matches Foo Fighters."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("Everlong", ["FOO FIGHTERS"], 1997)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 2, f"Expected id 2, got {results[0].id}"

    def test_both_title_and_artist_wrong_case(self, populated_db):
        """SMELLS LIKE TEEN SPIRIT + nirvana still matches Song 1."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata("SMELLS LIKE TEEN SPIRIT", ["nirvana"], 1991)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 1, f"Expected id 1, got {results[0].id}"

    def test_multi_artist_mixed_case(self, populated_db):
        """Both artists in different case for Song 8."""
        repo = SongRepository(populated_db)
        results = repo.find_by_metadata(
            "joint venture", ["DAVE GROHL", "taylor hawkins"], None
        )
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == 8, f"Expected id 8, got {results[0].id}"


class TestPathCollision:
    """get_by_path: exact string match, case-sensitive."""

    def test_exact_path_hit(self, populated_db):
        """/path/1 matches Song 1."""
        repo = SongRepository(populated_db)
        song = repo.get_by_path("/path/1")
        assert song is not None, "Expected song for /path/1"
        assert song.id == 1, f"Expected id 1, got {song.id}"

    def test_path_case_mismatch(self, populated_db):
        """Paths are stored as-is. /PATH/1 != /path/1."""
        repo = SongRepository(populated_db)
        assert (
            repo.get_by_path("/PATH/1") is None
        ), "Expected None for case-mismatched path"

    def test_path_trailing_slash(self, populated_db):
        """/path/1/ does not match /path/1."""
        repo = SongRepository(populated_db)
        assert repo.get_by_path("/path/1/") is None, "Expected None for trailing slash"

    def test_path_whitespace(self, populated_db):
        """Leading/trailing whitespace should not match."""
        repo = SongRepository(populated_db)
        assert (
            repo.get_by_path(" /path/1") is None
        ), "Expected None for leading whitespace"
        assert (
            repo.get_by_path("/path/1 ") is None
        ), "Expected None for trailing whitespace"

    def test_similar_path(self, populated_db):
        """Similar but not equal path."""
        repo = SongRepository(populated_db)
        assert repo.get_by_path("/path/10") is None, "Expected None for /path/10"
        assert repo.get_by_path("/path/1.mp3") is None, "Expected None for /path/1.mp3"


class TestHashCollision:
    """get_by_hash: exact string match."""

    def test_exact_hash_hit(self, populated_db):
        """hash_1 matches Song 1."""
        repo = SongRepository(populated_db)
        song = repo.get_by_hash("hash_1")
        assert song is not None, "Expected song for hash_1"
        assert song.id == 1, f"Expected id 1, got {song.id}"

    def test_hash_case_sensitive(self, populated_db):
        """Hash values are case-sensitive."""
        repo = SongRepository(populated_db)
        assert repo.get_by_hash("HASH_1") is None, "Expected None for uppercase HASH_1"
        assert repo.get_by_hash("Hash_1") is None, "Expected None for mixed case Hash_1"

    def test_no_hash_in_db(self, populated_db):
        """Nonexistent hash returns None."""
        repo = SongRepository(populated_db)
        assert (
            repo.get_by_hash("nonexistent_hash") is None
        ), "Expected None for nonexistent hash"


class TestEmptyAndBoundaryInputs:
    """Edge cases: empty strings, no credits, no data."""

    def test_empty_title_returns_empty(self, populated_db):
        """Empty title returns no results."""
        repo = SongRepository(populated_db)
        assert (
            repo.find_by_metadata("", ["Nirvana"], 1991) == []
        ), "Expected [] for empty title"

    def test_empty_artist_list_returns_empty(self, populated_db):
        """Empty artist list returns no results."""
        repo = SongRepository(populated_db)
        assert (
            repo.find_by_metadata("Everlong", [], 1997) == []
        ), "Expected [] for empty artist list"

    def test_empty_artist_string_returns_empty(self, populated_db):
        """Empty artist string in list returns no results."""
        repo = SongRepository(populated_db)
        assert (
            repo.find_by_metadata("Everlong", [""], 1997) == []
        ), "Expected [] for empty artist string"

    def test_song_with_no_credits(self, populated_db):
        """Song 7 (Hollow Song) has zero credits.
        Searching for it with any artist should return nothing."""
        repo = SongRepository(populated_db)
        assert (
            repo.find_by_metadata("Hollow Song", ["Anyone"], None) == []
        ), "Expected [] for song with no credits"

    def test_nonexistent_title(self, populated_db):
        """Nonexistent title returns no results."""
        repo = SongRepository(populated_db)
        assert (
            repo.find_by_metadata("ZZZZZ_NONEXISTENT", ["Nirvana"], 1991) == []
        ), "Expected [] for nonexistent title"

    def test_empty_db(self, empty_db):
        """All queries return empty/None on empty database."""
        repo = SongRepository(empty_db)
        assert (
            repo.find_by_metadata("Anything", ["Anyone"], 2000) == []
        ), "Expected [] on empty DB"
        assert (
            repo.get_by_path("/any/path") is None
        ), "Expected None for path on empty DB"
        assert (
            repo.get_by_hash("any_hash") is None
        ), "Expected None for hash on empty DB"


# ========================================
# BATCH INGESTION TESTS
# ========================================


@pytest.fixture
def test_audio_folder(tmp_path):
    """Create a temporary folder structure with mock audio files for scanning."""
    audio_dir = tmp_path / "audio_files"
    audio_dir.mkdir()

    # Create mock .mp3 files
    (audio_dir / "song1.mp3").write_text("mock audio data 1")
    (audio_dir / "song2.mp3").write_text("mock audio data 2")
    (audio_dir / "song3.mp3").write_text("mock audio data 3")

    # Create subdirectory with more files
    subdir = audio_dir / "subfolder"
    subdir.mkdir()
    (subdir / "song4.mp3").write_text("mock audio data 4")
    (subdir / "song5.mp3").write_text("mock audio data 5")

    # Create non-audio files that should be ignored
    (audio_dir / "readme.txt").write_text("not audio")
    (audio_dir / "image.jpg").write_text("not audio")
    (subdir / "notes.doc").write_text("not audio")

    return str(audio_dir)


class TestScanFolder:
    """Tests for scan_folder() method - pure file discovery utility."""

    def test_flat_scan_finds_top_level_files_only(self, populated_db, test_audio_folder):
        """Non-recursive scan returns only top-level .mp3 files."""
        service = CatalogService(populated_db)
        files = service.scan_folder(test_audio_folder, recursive=False)

        assert len(files) == 3, f"Expected 3 files, got {len(files)}"

        # Verify all returned paths are absolute
        for f in files:
            assert os.path.isabs(f), f"Expected absolute path, got {f}"

        # Verify only top-level mp3s (not subdirectory files)
        filenames = [os.path.basename(f) for f in files]
        assert "song1.mp3" in filenames, "Expected song1.mp3 in results"
        assert "song2.mp3" in filenames, "Expected song2.mp3 in results"
        assert "song3.mp3" in filenames, "Expected song3.mp3 in results"
        assert "song4.mp3" not in filenames, "song4.mp3 should not be in flat scan"
        assert "song5.mp3" not in filenames, "song5.mp3 should not be in flat scan"

    def test_recursive_scan_finds_all_audio_files(self, populated_db, test_audio_folder):
        """Recursive scan returns all .mp3 files including subdirectories."""
        service = CatalogService(populated_db)
        files = service.scan_folder(test_audio_folder, recursive=True)

        assert len(files) == 5, f"Expected 5 files, got {len(files)}"

        filenames = [os.path.basename(f) for f in files]
        assert "song1.mp3" in filenames, "Expected song1.mp3 in results"
        assert "song2.mp3" in filenames, "Expected song2.mp3 in results"
        assert "song3.mp3" in filenames, "Expected song3.mp3 in results"
        assert "song4.mp3" in filenames, "Expected song4.mp3 in results"
        assert "song5.mp3" in filenames, "Expected song5.mp3 in results"

    def test_scan_ignores_non_audio_files(self, populated_db, test_audio_folder):
        """Only .mp3 files are returned, other file types ignored."""
        service = CatalogService(populated_db)
        files = service.scan_folder(test_audio_folder, recursive=True)

        filenames = [os.path.basename(f) for f in files]
        assert "readme.txt" not in filenames, "txt files should be ignored"
        assert "image.jpg" not in filenames, "jpg files should be ignored"
        assert "notes.doc" not in filenames, "doc files should be ignored"

    def test_nonexistent_folder_returns_empty_list(self, populated_db):
        """Scanning a nonexistent folder returns empty list."""
        service = CatalogService(populated_db)
        files = service.scan_folder("/nonexistent/path/xyz", recursive=True)

        assert files == [], f"Expected empty list, got {files}"

    def test_empty_folder_returns_empty_list(self, populated_db, tmp_path):
        """Scanning an empty folder returns empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        service = CatalogService(populated_db)
        files = service.scan_folder(str(empty_dir), recursive=True)

        assert files == [], f"Expected empty list, got {files}"

    def test_folder_with_only_non_audio_files(self, populated_db, tmp_path):
        """Folder with only non-.mp3 files returns empty list."""
        dir_path = tmp_path / "no_audio"
        dir_path.mkdir()
        (dir_path / "file1.txt").write_text("text")
        (dir_path / "file2.jpg").write_text("image")

        service = CatalogService(populated_db)
        files = service.scan_folder(str(dir_path), recursive=True)

        assert files == [], f"Expected empty list, got {files}"


class TestIngestBatch:
    """Tests for ingest_batch() method - parallel file processing."""

    def test_empty_list_returns_zero_counts(self, populated_db):
        """Batch ingesting empty list returns all zeros."""
        service = CatalogService(populated_db)
        report = service.ingest_batch([], max_workers=5)

        assert report["total_files"] == 0, f"Expected 0 total_files, got {report['total_files']}"
        assert report["ingested"] == 0, f"Expected 0 ingested, got {report['ingested']}"
        assert report["duplicates"] == 0, f"Expected 0 duplicates, got {report['duplicates']}"
        assert report["errors"] == 0, f"Expected 0 errors, got {report['errors']}"
        assert report["results"] == [], f"Expected empty results, got {report['results']}"

    def test_single_file_sequential_behavior(self, populated_db, tmp_path):
        """Single file batch behaves same as single ingest_file() call."""
        # This is a placeholder - real test would need actual audio file with metadata
        # Skipping for now since it requires MetadataService integration
        pass

    def test_max_workers_parameter_accepted(self, populated_db):
        """Verify max_workers parameter is accepted without error."""
        service = CatalogService(populated_db)

        # Should not raise
        report = service.ingest_batch([], max_workers=1)
        assert report is not None, "Expected report dict"

        report = service.ingest_batch([], max_workers=20)
        assert report is not None, "Expected report dict"

    def test_aggregate_stats_sum_correctly(self, populated_db):
        """Aggregate counts (ingested + duplicates + errors) equal total_files."""
        # This would need real staged files to test properly
        # Placeholder for now
        pass
