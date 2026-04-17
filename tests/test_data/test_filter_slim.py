"""
Repository tests for SongRepository.filter_slim and get_filter_values.

populated_db reference (filter-relevant data):
  Songs:
    1: "Smells Like Teen Spirit"  status=0(done) year=1991  Performer:Nirvana       Publisher:DGC Records  Tags:Grunge/Genre,Energetic/Mood,English/Jezik
    2: "Everlong"                 status=0(done) year=1997  Performer:Foo Fighters  (no song publisher)    Tags:90s/Era
    3: "Range Rover Bitch"        status=0(done) year=2016  Performer:Taylor Hawkins
    4: "Grohlton Theme"           status=0(done) year=None  Performer:Grohlton       Tags:Electronic/Style
    5: "Pocketwatch Demo"         status=0(done) year=1992  Performer:Late!
    6: "Dual Credit Track"        status=0(done)            Performer:Dave Grohl, Composer:Taylor Hawkins
    7: "Hollow Song"              status=1(not done)         NO credits, NO publisher, NO genre tag
    8: "Joint Venture"            status=0(done)            Performers:Dave Grohl+Taylor Hawkins
    9: "Priority Test"            status=1(not done)         NO credits, NO publisher   Tags:Grunge/Genre(not primary),AltRock/Genre(primary)

  Filter values:
    artists (Performer role): Dave Grohl, Foo Fighters, Grohlton, Late!, Nirvana, Taylor Hawkins
    contributors (all roles): Dave Grohl, Foo Fighters, Grohlton, Late!, Nirvana, Taylor Hawkins
    years: [2016, 1997, 1992, 1991]
    decades: [2010, 1990]
    genres: [Alt Rock, Grunge]
    albums: [Nevermind, The Colour and the Shape]
    publishers: [DGC Records]
    tag_categories: {Era: [90s], Jezik: [English], Mood: [Energetic], Style: [Electronic]}
"""

import pytest
from src.data.song_repository import SongRepository


@pytest.fixture
def repo(populated_db):
    return SongRepository(populated_db)


# ---------------------------------------------------------------------------
# get_filter_values
# ---------------------------------------------------------------------------


class TestGetFilterValues:
    def test_returns_expected_keys(self, repo):
        fv = repo.get_filter_values()
        for key in (
            "artists",
            "contributors",
            "years",
            "decades",
            "genres",
            "albums",
            "publishers",
            "tag_categories",
        ):
            assert key in fv, f"Missing key: {key}"

    def test_artists_are_performers_only(self, repo):
        fv = repo.get_filter_values()
        artists = set(fv["artists"])
        # Performer-credited names in the DB
        assert "Nirvana" in artists
        assert "Foo Fighters" in artists
        assert "Taylor Hawkins" in artists
        assert "Dave Grohl" in artists
        assert "Grohlton" in artists
        assert "Late!" in artists

    def test_contributors_includes_composers(self, repo):
        # Taylor Hawkins has a Composer credit on song 6 — must appear
        fv = repo.get_filter_values()
        assert "Taylor Hawkins" in fv["contributors"]

    def test_years_sorted_descending(self, repo):
        fv = repo.get_filter_values()
        years = fv["years"]
        assert years == sorted(years, reverse=True), f"Years not sorted desc: {years}"

    def test_years_values(self, repo):
        fv = repo.get_filter_values()
        assert set(fv["years"]) == {1991, 1992, 1997, 2016}

    def test_decades(self, repo):
        fv = repo.get_filter_values()
        assert set(fv["decades"]) == {1990, 2010}

    def test_genres_only_genre_category(self, repo):
        fv = repo.get_filter_values()
        # Only Genre-category tags
        assert set(fv["genres"]) == {"Grunge", "Alt Rock"}
        # Non-genre tags must NOT appear in genres
        assert "Energetic" not in fv["genres"]
        assert "90s" not in fv["genres"]

    def test_albums(self, repo):
        fv = repo.get_filter_values()
        assert set(fv["albums"]) == {"Nevermind", "The Colour and the Shape"}

    def test_publishers(self, repo):
        fv = repo.get_filter_values()
        # Only DGC Records has a RecordingPublishers link
        assert fv["publishers"] == ["DGC Records"]

    def test_tag_categories_excludes_genre(self, repo):
        fv = repo.get_filter_values()
        cats = fv["tag_categories"]
        # Genre is promoted to top-level genres list; must NOT appear as a tag category
        assert "Genre" not in cats
        assert "Era" in cats and "90s" in cats["Era"]
        assert "Mood" in cats and "Energetic" in cats["Mood"]
        assert "Style" in cats and "Electronic" in cats["Style"]
        assert "Jezik" in cats and "English" in cats["Jezik"]


# ---------------------------------------------------------------------------
# filter_slim – basic single-criterion
# ---------------------------------------------------------------------------


class TestFilterSlimArtist:
    def test_filter_by_artist_nirvana_returns_song_1(self, repo):
        rows = repo.filter_slim(artists=["Nirvana"])
        ids = {r["SourceID"] for r in rows}
        assert 1 in ids, f"Expected song 1 (SLTS), got {ids}"
        assert len(rows) == 1, f"Expected exactly 1 result, got {len(rows)}"

    def test_filter_by_artist_dave_grohl(self, repo):
        rows = repo.filter_slim(artists=["Dave Grohl"])
        ids = {r["SourceID"] for r in rows}
        # Songs 6 and 8 have Dave Grohl as Performer
        assert ids == {6, 8}, f"Expected {{6, 8}}, got {ids}"

    def test_filter_by_alias_grohlton(self, repo):
        rows = repo.filter_slim(artists=["Grohlton"])
        ids = {r["SourceID"] for r in rows}
        assert ids == {4}, f"Expected {{4}}, got {ids}"

    def test_unknown_artist_returns_empty(self, repo):
        rows = repo.filter_slim(artists=["Nobody"])
        assert rows == [], f"Expected [], got {rows}"


class TestFilterSlimContributors:
    def test_contributor_taylor_hawkins_includes_composer_role(self, repo):
        # Taylor is Performer on 3,8 and Composer on 6
        rows = repo.filter_slim(contributors=["Taylor Hawkins"])
        ids = {r["SourceID"] for r in rows}
        assert {3, 6, 8}.issubset(ids), f"Expected 3,6,8 in results, got {ids}"

    def test_contributor_does_not_return_uncredited_songs(self, repo):
        # Song 7 has zero credits
        rows = repo.filter_slim(contributors=["Dave Grohl"])
        ids = {r["SourceID"] for r in rows}
        assert 7 not in ids


class TestFilterSlimYear:
    def test_filter_by_year_1991(self, repo):
        rows = repo.filter_slim(years=[1991])
        ids = {r["SourceID"] for r in rows}
        assert ids == {1}, f"Expected {{1}}, got {ids}"

    def test_filter_by_multiple_years_any_mode(self, repo):
        rows = repo.filter_slim(years=[1991, 1997], mode="ANY")
        ids = {r["SourceID"] for r in rows}
        assert ids == {1, 2}, f"Expected {{1, 2}}, got {ids}"


class TestFilterSlimDecade:
    def test_filter_by_1990s_decade(self, repo):
        rows = repo.filter_slim(decades=[1990])
        ids = {r["SourceID"] for r in rows}
        # 1991, 1992, 1997 all in 1990s → songs 1, 5, 2
        assert ids == {1, 2, 5}, f"Expected {{1, 2, 5}}, got {ids}"

    def test_filter_by_2010s_decade(self, repo):
        rows = repo.filter_slim(decades=[2010])
        ids = {r["SourceID"] for r in rows}
        assert ids == {3}, f"Expected {{3}} (2016), got {ids}"


class TestFilterSlimGenre:
    def test_filter_by_grunge(self, repo):
        rows = repo.filter_slim(genres=["Grunge"])
        ids = {r["SourceID"] for r in rows}
        assert {1, 9}.issubset(ids), f"Expected 1 and 9 in results, got {ids}"

    def test_filter_by_nonexistent_genre(self, repo):
        rows = repo.filter_slim(genres=["Jazz"])
        assert rows == []


class TestFilterSlimAlbum:
    def test_filter_by_nevermind(self, repo):
        rows = repo.filter_slim(albums=["Nevermind"])
        ids = {r["SourceID"] for r in rows}
        assert ids == {1}

    def test_filter_by_tcats(self, repo):
        rows = repo.filter_slim(albums=["The Colour and the Shape"])
        ids = {r["SourceID"] for r in rows}
        assert ids == {2}


class TestFilterSlimPublisher:
    def test_filter_by_dgc_records(self, repo):
        rows = repo.filter_slim(publishers=["DGC Records"])
        ids = {r["SourceID"] for r in rows}
        assert ids == {1}

    def test_unknown_publisher_returns_empty(self, repo):
        rows = repo.filter_slim(publishers=["Nonexistent Label"])
        assert rows == []


class TestFilterSlimTags:
    def test_filter_by_era_tag(self, repo):
        rows = repo.filter_slim(tags=["Era:90s"])
        ids = {r["SourceID"] for r in rows}
        assert ids == {2}, f"Expected {{2}}, got {ids}"

    def test_filter_by_mood_tag(self, repo):
        rows = repo.filter_slim(tags=["Mood:Energetic"])
        ids = {r["SourceID"] for r in rows}
        assert ids == {1}

    def test_unknown_tag_returns_empty(self, repo):
        rows = repo.filter_slim(tags=["Mood:Chill"])
        assert rows == []


class TestFilterSlimLiveOnly:
    def test_live_only_false_returns_all_matching(self, repo):
        # All songs have IsActive=1 in populated_db, so result should be same as without flag
        all_rows = repo.filter_slim(artists=["Nirvana"])
        live_rows = repo.filter_slim(artists=["Nirvana"], live_only=True)
        assert len(all_rows) == len(live_rows)


# ---------------------------------------------------------------------------
# filter_slim – status filters
# ---------------------------------------------------------------------------


class TestFilterSlimStatus:
    def test_done_returns_only_status_0(self, repo):
        rows = repo.filter_slim(statuses=["done"])
        ids = {r["SourceID"] for r in rows}
        # Status=0: songs 1,2,3,4,5,6,8
        assert ids == {1, 2, 3, 4, 5, 6, 8}, f"Unexpected done songs: {ids}"

    def test_not_done_returns_status_nonzero(self, repo):
        rows = repo.filter_slim(statuses=["not_done"])
        ids = {r["SourceID"] for r in rows}
        assert ids == {7, 9}, f"Expected {{7, 9}}, got {ids}"

    def test_missing_data_songs_have_blockers(self, repo):
        rows = repo.filter_slim(statuses=["missing_data"])
        ids = {r["SourceID"] for r in rows}
        # Song 7: no credits, no publisher, no genre -> missing data
        # Song 9: no credits, no publisher (has genres but no publisher/performer credit)
        assert 7 in ids, (
            f"Song 7 (no credits/publisher/genre) not in missing_data: {ids}"
        )
        assert 9 in ids, f"Song 9 (no credits/publisher) not in missing_data: {ids}"
        # Done songs must NOT appear
        assert not ids.intersection({1, 2, 3, 4, 5, 6, 8}), (
            f"Done songs leaked into missing_data: {ids}"
        )

    def test_ready_to_finalize_songs_have_no_blockers(self, repo):
        # In populated_db, no not-done song has all required fields → this should be empty
        rows = repo.filter_slim(statuses=["ready_to_finalize"])
        ids = {r["SourceID"] for r in rows}
        # Done songs must not appear
        assert not ids.intersection({1, 2, 3, 4, 5, 6, 8}), (
            f"Done songs in ready_to_finalize: {ids}"
        )


# ---------------------------------------------------------------------------
# filter_slim – mode=ALL (AND) vs mode=ANY (OR)
# ---------------------------------------------------------------------------


class TestFilterSlimMode:
    def test_all_mode_two_artists_returns_intersection(self, repo):
        # Songs with BOTH Nirvana AND Foo Fighters as Performer → none
        rows = repo.filter_slim(artists=["Nirvana", "Foo Fighters"], mode="ALL")
        assert rows == [], "Expected no results for AND of two different artists"

    def test_any_mode_two_artists_returns_union(self, repo):
        rows = repo.filter_slim(artists=["Nirvana", "Foo Fighters"], mode="ANY")
        ids = {r["SourceID"] for r in rows}
        assert ids == {1, 2}, f"Expected {{1, 2}}, got {ids}"

    def test_all_mode_artist_and_year(self, repo):
        # Nirvana AND year=1991 → only song 1
        rows = repo.filter_slim(artists=["Nirvana"], years=[1991], mode="ALL")
        ids = {r["SourceID"] for r in rows}
        assert ids == {1}

    def test_all_mode_artist_and_wrong_year_returns_empty(self, repo):
        # Nirvana AND year=2000 → no match
        rows = repo.filter_slim(artists=["Nirvana"], years=[2000], mode="ALL")
        assert rows == []

    def test_any_mode_cross_category(self, repo):
        # artist=Nirvana OR year=1997 → songs 1 (Nirvana) + 2 (1997)
        rows = repo.filter_slim(artists=["Nirvana"], years=[1997], mode="ANY")
        ids = {r["SourceID"] for r in rows}
        assert ids == {1, 2}


# ---------------------------------------------------------------------------
# filter_slim – no filters → empty result (not all songs)
# ---------------------------------------------------------------------------


class TestFilterSlimNoFilters:
    def test_no_filters_returns_all_songs(self, repo):
        rows = repo.filter_slim()
        # No subqueries → id_filter = "1=1" → all 9 songs
        assert len(rows) == 9, f"Expected 9 rows with no filters, got {len(rows)}"


# ---------------------------------------------------------------------------
# filter_slim – has_publisher / has_album flags
# ---------------------------------------------------------------------------


class TestFilterSlimHasPublisherHasAlbum:
    def test_flags_present_in_rows(self, repo):
        rows = repo.filter_slim(artists=["Nirvana"])
        assert len(rows) == 1
        row = rows[0]
        assert "has_publisher" in row, "Row missing 'has_publisher'"
        assert "has_album" in row, "Row missing 'has_album'"

    def test_song_with_publisher_and_album(self, repo):
        # Song 1 (SLTS): DGC Records publisher + Nevermind album
        rows = repo.filter_slim(artists=["Nirvana"])
        row = rows[0]
        assert row["has_publisher"] == 1, "Song 1 should have has_publisher=1"
        assert row["has_album"] == 1, "Song 1 should have has_album=1"

    def test_song_without_publisher(self, repo):
        # Song 2 (Everlong): no RecordingPublishers link
        rows = repo.filter_slim(artists=["Foo Fighters"])
        assert len(rows) == 1
        assert rows[0]["has_publisher"] == 0, "Song 2 should have has_publisher=0"

    def test_song_without_album(self, repo):
        # Song 7 (Hollow Song): no SongAlbums link
        rows = repo.filter_slim(statuses=["not_done"])
        by_id = {r["SourceID"]: r for r in rows}
        assert by_id[7]["has_album"] == 0, "Song 7 should have has_album=0"
