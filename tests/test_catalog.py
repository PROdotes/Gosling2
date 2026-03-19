"""
Contract tests for CatalogService.
Every assertion verifies EXACT values from the populated_db fixture.
No mocking. Real SQLite. Exact value verification.
"""

from src.models.view_models import SongView, AlbumView


# ===================================================================
# CatalogService.get_song
# ===================================================================
class TestGetSong:
    """CatalogService.get_song contracts (single song fetch + full hydration)."""

    def test_basic_fields(self, catalog_service):
        """Song 2 (Everlong): exact core fields."""
        song = catalog_service.get_song(2)

        assert song is not None
        assert song.id == 2
        assert song.title == "Everlong"
        assert song.media_name == "Everlong"
        assert song.source_path == "/path/2"
        assert song.duration_ms == 240000
        assert song.is_active is True
        assert song.type_id == 1

    def test_credits_hydration(self, catalog_service):
        """Song 2: exactly 1 credit - Foo Fighters as Performer."""
        song = catalog_service.get_song(2)
        assert song is not None
        assert len(song.credits) == 1

        credit = song.credits[0]
        assert credit.display_name == "Foo Fighters"
        assert credit.role_id == 1
        assert credit.role_name == "Performer"
        assert credit.identity_id == 3  # Foo Fighters identity
        assert credit.is_primary is True

    def test_multiple_credits(self, catalog_service):
        """Song 6 (Dual Credit): Dave Grohl(Performer) + Taylor Hawkins(Composer)."""
        song = catalog_service.get_song(6)
        assert song is not None
        assert len(song.credits) == 2

        credit_map = {c.display_name: c for c in song.credits}
        assert credit_map["Dave Grohl"].role_name == "Performer"
        assert credit_map["Dave Grohl"].role_id == 1
        assert credit_map["Dave Grohl"].is_primary is True
        assert credit_map["Taylor Hawkins"].role_name == "Composer"
        assert credit_map["Taylor Hawkins"].role_id == 2
        assert credit_map["Taylor Hawkins"].is_primary is True

    def test_zero_credits(self, catalog_service):
        """Song 7 (Hollow Song): no credits."""
        song = catalog_service.get_song(7)
        assert song is not None
        assert song.title == "Hollow Song"
        assert song.credits == []

    def test_album_hydration(self, catalog_service):
        """Song 1 (SLTS): 1 album (Nevermind), Track 1, with publishers."""
        song = catalog_service.get_song(1)
        assert song is not None
        assert len(song.albums) == 1

        album = song.albums[0]
        assert album.album_id == 100
        assert album.album_title == "Nevermind"
        assert album.track_number == 1
        assert album.is_primary is True
        assert album.release_year == 1991

        # Album publishers hydrated
        assert len(album.album_publishers) == 2
        pub_names = {p.name for p in album.album_publishers}
        assert pub_names == {"DGC Records", "Sub Pop"}

    def test_song_with_no_album(self, catalog_service):
        """Song 4 (Grohlton Theme): no album."""
        song = catalog_service.get_song(4)
        assert song is not None
        assert song.albums == []

    def test_master_publisher_hydration(self, catalog_service):
        """Song 1: has DGC Records as recording publisher with parent_name resolved."""
        song = catalog_service.get_song(1)
        assert song is not None
        assert len(song.publishers) == 1
        assert song.publishers[0].name == "DGC Records"
        assert song.publishers[0].parent_name == "Universal Music Group"

    def test_song_without_publisher(self, catalog_service):
        """Song 2 has no RecordingPublisher."""
        song = catalog_service.get_song(2)
        assert song is not None
        assert song.publishers == []

    def test_tag_hydration(self, catalog_service):
        """Song 1: Grunge(Genre), Energetic(Mood), English(Jezik)."""
        song = catalog_service.get_song(1)
        assert song is not None
        assert len(song.tags) == 3
        tag_map = {t.name: t for t in song.tags}
        assert tag_map["Grunge"].category == "Genre"
        assert tag_map["Energetic"].category == "Mood"
        assert tag_map["English"].category == "Jezik"

    def test_song_with_no_tags(self, catalog_service):
        """Song 7 (Hollow Song): no tags."""
        song = catalog_service.get_song(7)
        assert song is not None
        assert song.tags == []

    def test_not_found(self, catalog_service):
        song = catalog_service.get_song(999)
        assert song is None

    def test_all_nine_songs_retrievable(self, catalog_service):
        """Every song in the fixture should be individually retrievable."""
        expected = {
            1: "Smells Like Teen Spirit",
            2: "Everlong",
            3: "Range Rover Bitch",
            4: "Grohlton Theme",
            5: "Pocketwatch Demo",
            6: "Dual Credit Track",
            7: "Hollow Song",
            8: "Joint Venture",
            9: "Priority Test",
        }
        for song_id, expected_title in expected.items():
            song = catalog_service.get_song(song_id)
            assert song is not None, f"Song {song_id} should exist"
            assert song.title == expected_title


# ===================================================================
# CatalogService.search_songs
# ===================================================================
class TestSearchSongs:
    """CatalogService.search_songs contracts (title + album + identity resolution)."""

    def test_title_match(self, catalog_service):
        """Searching 'Spirit' matches Song 1 by title."""
        results = catalog_service.search_songs("Spirit")
        assert len(results) == 1
        assert results[0].title == "Smells Like Teen Spirit"

    def test_album_match(self, catalog_service):
        """Searching 'Nevermind' matches Song 1 via album title."""
        results = catalog_service.search_songs("Nevermind")
        assert len(results) == 1
        assert results[0].title == "Smells Like Teen Spirit"

    def test_identity_match_expands_to_group_songs(self, catalog_service):
        """Searching 'Dave Grohl' should find songs credited to Dave directly,
        PLUS songs credited to his groups (Nirvana, Foo Fighters)."""
        results = catalog_service.search_songs("Dave Grohl")
        titles = {s.title for s in results}

        # Dave's direct songs (NameID 10): Dual Credit Track, Joint Venture
        assert "Dual Credit Track" in titles
        assert "Joint Venture" in titles
        # Dave's alias songs (Grohlton=11, Late!=12): Grohlton Theme, Pocketwatch Demo
        assert "Grohlton Theme" in titles
        assert "Pocketwatch Demo" in titles
        # Dave's group songs: SLTS (Nirvana), Everlong (Foo Fighters)
        assert "Smells Like Teen Spirit" in titles
        assert "Everlong" in titles

        # Taylor's solo song should NOT be here
        assert "Range Rover Bitch" not in titles

    def test_alias_match_resolves_to_group_songs(self, catalog_service):
        """Searching 'Grohlton' should find Grohlton Theme + group songs."""
        results = catalog_service.search_songs("Grohlton")
        titles = {s.title for s in results}

        assert "Grohlton Theme" in titles
        # Because Grohlton resolves to Dave (identity 1), which is in Nirvana/Foo Fighters
        assert "Smells Like Teen Spirit" in titles
        assert "Everlong" in titles

    def test_group_match(self, catalog_service):
        """Searching 'Nirvana' should find SLTS directly."""
        results = catalog_service.search_songs("Nirvana")
        titles = {s.title for s in results}
        assert "Smells Like Teen Spirit" in titles

    def test_no_results(self, catalog_service):
        results = catalog_service.search_songs("ZZZZNONEXISTENT")
        assert results == []

    def test_results_are_hydrated(self, catalog_service):
        """Search results should have credits, albums, tags filled in."""
        results = catalog_service.search_songs("Everlong")
        assert len(results) == 1
        song = results[0]
        assert len(song.credits) == 1
        assert song.credits[0].display_name == "Foo Fighters"
        assert len(song.albums) == 1
        assert song.albums[0].album_title == "The Colour and the Shape"

    def test_no_duplicates(self, catalog_service):
        """Search should not return duplicate songs even if matched via multiple paths."""
        results = catalog_service.search_songs("Dave Grohl")
        ids = [s.id for s in results]
        assert len(ids) == len(set(ids)), "Duplicate song IDs in search results"


# ===================================================================
# CatalogService.get_songs_by_identity
# ===================================================================
class TestGetSongsByIdentity:
    """CatalogService.get_songs_by_identity contracts (reverse credit lookup)."""

    def test_dave_grohl_full_tree(self, catalog_service):
        """Dave Grohl (ID=1): person in Nirvana(2) and Foo Fighters(3).
        Should return all songs credited to Dave, his aliases, AND his groups."""
        songs = catalog_service.get_songs_by_identity(1)
        song_ids = {s.id for s in songs}

        # Direct/alias credits: 4, 5, 6, 8
        assert 4 in song_ids  # Grohlton Theme
        assert 5 in song_ids  # Pocketwatch Demo
        assert 6 in song_ids  # Dual Credit Track
        assert 8 in song_ids  # Joint Venture

        # Group credits: 1 (Nirvana), 2 (Foo Fighters)
        assert 1 in song_ids  # SLTS
        assert 2 in song_ids  # Everlong

        # NOT Taylor's solo
        assert 3 not in song_ids  # Range Rover Bitch

    def test_taylor_hawkins(self, catalog_service):
        """Taylor (ID=4): person in Foo Fighters(3).
        Solo + Foo Fighters songs + any credited."""
        songs = catalog_service.get_songs_by_identity(4)
        song_ids = {s.id for s in songs}

        assert 3 in song_ids  # Range Rover Bitch (solo)
        assert 2 in song_ids  # Everlong (Foo Fighters)
        assert 6 in song_ids  # Dual Credit Track (Taylor credited)
        assert 8 in song_ids  # Joint Venture (Taylor credited)

    def test_nirvana_as_group(self, catalog_service):
        """Nirvana (ID=2, group): has member Dave(1).
        Should return Nirvana songs + Dave's solo/alias songs."""
        songs = catalog_service.get_songs_by_identity(2)
        song_ids = {s.id for s in songs}

        assert 1 in song_ids  # SLTS (Nirvana direct)
        # Members expanded: Dave (1)
        assert 4 in song_ids  # Grohlton Theme
        assert 5 in song_ids  # Pocketwatch Demo
        assert 6 in song_ids  # Dual Credit Track
        assert 8 in song_ids  # Joint Venture

    def test_not_found_identity(self, catalog_service):
        songs = catalog_service.get_songs_by_identity(999)
        assert songs == []

    def test_results_are_hydrated(self, catalog_service):
        """Songs returned by get_songs_by_identity should be fully hydrated."""
        songs = catalog_service.get_songs_by_identity(2)  # Nirvana
        slts = next((s for s in songs if s.id == 1), None)
        assert slts is not None
        assert len(slts.credits) == 1
        assert slts.credits[0].display_name == "Nirvana"
        assert len(slts.albums) == 1
        assert slts.albums[0].album_title == "Nevermind"


# ===================================================================
# CatalogService.get_identity / get_all_identities / search_identities
# ===================================================================
class TestGetIdentity:
    """CatalogService.get_identity contracts."""

    def test_person_with_full_tree(self, catalog_service):
        """Dave Grohl (ID=1): aliases, groups, no members."""
        identity = catalog_service.get_identity(1)
        assert identity is not None
        assert identity.display_name == "Dave Grohl"
        assert identity.type == "person"

        # Aliases
        alias_names = {a.display_name for a in identity.aliases}
        assert alias_names == {"Dave Grohl", "Grohlton", "Late!", "Ines Prajo"}

        # Groups
        group_names = {g.display_name for g in identity.groups}
        assert group_names == {"Nirvana", "Foo Fighters"}

        # No members (person)
        assert identity.members == []

    def test_group_with_members(self, catalog_service):
        """Foo Fighters (ID=3): members Dave + Taylor, no groups."""
        identity = catalog_service.get_identity(3)
        assert identity is not None
        assert identity.display_name == "Foo Fighters"
        assert identity.type == "group"

        member_names = {m.display_name for m in identity.members}
        assert member_names == {"Dave Grohl", "Taylor Hawkins"}

        # No groups
        assert identity.groups == []

    def test_not_found(self, catalog_service):
        assert catalog_service.get_identity(999) is None


class TestGetAllIdentities:
    """CatalogService.get_all_identities contracts."""

    def test_returns_all_four_sorted(self, catalog_service):
        identities = catalog_service.get_all_identities()
        assert len(identities) == 4
        names = [i.display_name for i in identities]
        assert names == ["Dave Grohl", "Foo Fighters", "Nirvana", "Taylor Hawkins"]

    def test_identities_are_hydrated(self, catalog_service):
        """Identities should have aliases/members/groups filled in."""
        identities = catalog_service.get_all_identities()
        dave = next(i for i in identities if i.display_name == "Dave Grohl")
        assert len(dave.aliases) == 4
        assert len(dave.groups) == 2

    def test_empty_db(self, catalog_service_empty):
        assert catalog_service_empty.get_all_identities() == []


class TestSearchIdentities:
    """CatalogService.search_identities contracts."""

    def test_by_name(self, catalog_service):
        results = catalog_service.search_identities("Nirvana")
        assert len(results) == 1
        assert results[0].display_name == "Nirvana"

    def test_by_alias(self, catalog_service):
        """Searching 'Grohlton' returns Dave Grohl (hydrated)."""
        results = catalog_service.search_identities("Grohlton")
        assert len(results) == 1
        assert results[0].display_name == "Dave Grohl"
        # Should be hydrated
        assert len(results[0].aliases) == 4

    def test_no_results(self, catalog_service):
        assert catalog_service.search_identities("ZZZZ") == []


# ===================================================================
# CatalogService.get_all_albums / get_album / search_albums
# ===================================================================
class TestGetAllAlbums:
    """CatalogService.get_all_albums contracts."""

    def test_returns_both_albums(self, catalog_service):
        albums = catalog_service.get_all_albums()
        assert len(albums) == 2
        titles = [a.title for a in albums]
        assert titles == ["Nevermind", "The Colour and the Shape"]

    def test_nevermind_hydration(self, catalog_service):
        albums = catalog_service.get_all_albums()
        nevermind = next(a for a in albums if a.title == "Nevermind")

        assert nevermind.id == 100
        assert nevermind.release_year == 1991

        # Publishers
        assert len(nevermind.publishers) == 2
        pub_names = {p.name for p in nevermind.publishers}
        assert pub_names == {"DGC Records", "Sub Pop"}

        # Credits
        assert len(nevermind.credits) == 1
        assert nevermind.credits[0].display_name == "Nirvana"

        # Songs
        assert len(nevermind.songs) == 1
        assert nevermind.songs[0].title == "Smells Like Teen Spirit"

    def test_empty_db(self, catalog_service_empty):
        assert catalog_service_empty.get_all_albums() == []


class TestGetAlbum:
    """CatalogService.get_album contracts."""

    def test_tcats(self, catalog_service):
        album = catalog_service.get_album(200)
        assert album is not None
        assert album.title == "The Colour and the Shape"
        assert album.release_year == 1997
        assert album.album_type is None
        assert len(album.publishers) == 1
        assert album.publishers[0].name == "Roswell Records"
        assert len(album.credits) == 1
        assert album.credits[0].display_name == "Foo Fighters"
        assert len(album.songs) == 1
        assert album.songs[0].title == "Everlong"

    def test_not_found(self, catalog_service):
        assert catalog_service.get_album(999) is None


class TestSearchAlbums:
    def test_partial_match(self, catalog_service):
        albums = catalog_service.search_albums("Never")
        assert len(albums) == 1
        assert albums[0].title == "Nevermind"

    def test_no_match(self, catalog_service):
        assert catalog_service.search_albums("ZZZZZ") == []


# ===================================================================
# CatalogService.get_all_publishers / get_publisher / search_publishers / get_publisher_songs
# ===================================================================
class TestGetAllPublishers:
    def test_returns_all_six_sorted(self, catalog_service):
        pubs = catalog_service.get_all_publishers()
        assert len(pubs) == 6
        names = [p.name for p in pubs]
        assert names == [
            "DGC Records",
            "Island Def Jam",
            "Island Records",
            "Roswell Records",
            "Sub Pop",
            "Universal Music Group",
        ]

    def test_parent_names_hydrated(self, catalog_service):
        pubs = catalog_service.get_all_publishers()
        pub_map = {p.name: p for p in pubs}
        assert pub_map["DGC Records"].parent_name == "Universal Music Group"
        assert pub_map["Island Records"].parent_name == "Universal Music Group"
        assert pub_map["Island Def Jam"].parent_name == "Island Records"
        assert pub_map["Universal Music Group"].parent_name is None
        assert pub_map["Roswell Records"].parent_name is None
        assert pub_map["Sub Pop"].parent_name is None

    def test_empty_db(self, catalog_service_empty):
        assert catalog_service_empty.get_all_publishers() == []


class TestGetPublisher:
    def test_with_children(self, catalog_service):
        """UMG (1) should have children: Island Records(2), DGC Records(10)."""
        pub = catalog_service.get_publisher(1)
        assert pub is not None
        assert pub.name == "Universal Music Group"
        assert pub.parent_name is None
        child_names = {c.name for c in pub.sub_publishers}
        assert child_names == {"Island Records", "DGC Records"}

    def test_hierarchy_resolution(self, catalog_service):
        """Island Def Jam (3): parent_name should be 'Island Records'."""
        pub = catalog_service.get_publisher(3)
        assert pub is not None
        assert pub.name == "Island Def Jam"
        assert pub.parent_name == "Island Records"

    def test_dgc_parent(self, catalog_service):
        """DGC Records (10): parent_name should be 'Universal Music Group'."""
        pub = catalog_service.get_publisher(10)
        assert pub is not None
        assert pub.parent_name == "Universal Music Group"

    def test_leaf_publisher(self, catalog_service):
        """Sub Pop (5): no parent, no children."""
        pub = catalog_service.get_publisher(5)
        assert pub is not None
        assert pub.parent_name is None
        assert pub.sub_publishers == []

    def test_not_found(self, catalog_service):
        assert catalog_service.get_publisher(999) is None


class TestSearchPublishers:
    def test_partial_match(self, catalog_service):
        results = catalog_service.search_publishers("Island")
        assert len(results) == 2
        names = {p.name for p in results}
        assert names == {"Island Records", "Island Def Jam"}

    def test_hydration_in_search(self, catalog_service):
        results = catalog_service.search_publishers("Island Def")
        assert len(results) == 1
        assert results[0].parent_name == "Island Records"

    def test_no_match(self, catalog_service):
        assert catalog_service.search_publishers("ZZZZ") == []


class TestGetPublisherSongs:
    def test_dgc_songs(self, catalog_service):
        """DGC Records (10) has Song 1 via RecordingPublishers."""
        songs = catalog_service.get_publisher_songs(10)
        assert len(songs) == 1
        assert songs[0].title == "Smells Like Teen Spirit"
        # Song should be hydrated
        assert len(songs[0].credits) == 1

    def test_publisher_with_no_songs(self, catalog_service):
        """Sub Pop (5) has no RecordingPublisher entries."""
        songs = catalog_service.get_publisher_songs(5)
        assert songs == []


# ===================================================================
# View model integration (SongView, AlbumView)
# ===================================================================
class TestSongViewFromCatalog:
    """Verify SongView.from_domain produces correct computed fields from CatalogService output."""

    def test_display_artist_single(self, catalog_service):
        """Song 1 (SLTS): single performer -> 'Nirvana'."""
        song = catalog_service.get_song(1)
        view = SongView.from_domain(song)
        assert view.display_artist == "Nirvana"

    def test_display_artist_multiple_performers(self, catalog_service):
        """Song 8 (Joint Venture): two performers -> 'Dave Grohl, Taylor Hawkins'."""
        song = catalog_service.get_song(8)
        view = SongView.from_domain(song)
        assert view.display_artist == "Dave Grohl, Taylor Hawkins"

    def test_display_artist_no_credits(self, catalog_service):
        """Song 7 (Hollow Song): no credits -> None."""
        song = catalog_service.get_song(7)
        view = SongView.from_domain(song)
        assert view.display_artist is None

    def test_formatted_duration(self, catalog_service):
        """Song 1 (200s=200000ms): '3:20'."""
        song = catalog_service.get_song(1)
        view = SongView.from_domain(song)
        assert view.formatted_duration == "3:20"

    def test_formatted_duration_exact_minute(self, catalog_service):
        """Song 3 (180s=180000ms): '3:00'."""
        song = catalog_service.get_song(3)
        view = SongView.from_domain(song)
        assert view.formatted_duration == "3:00"

    def test_formatted_duration_short(self, catalog_service):
        """Song 7 (10s=10000ms): '0:10'."""
        song = catalog_service.get_song(7)
        view = SongView.from_domain(song)
        assert view.formatted_duration == "0:10"

    def test_primary_genre_explicit_primary(self, catalog_service):
        """Song 9: has Alt Rock (primary=True) and Grunge (primary=False). Should be 'Alt Rock'."""
        song = catalog_service.get_song(9)
        view = SongView.from_domain(song)
        assert view.primary_genre == "Alt Rock"

    def test_primary_genre_implicit(self, catalog_service):
        """Song 1: no explicit primary, first Genre tag wins -> 'Grunge'."""
        song = catalog_service.get_song(1)
        view = SongView.from_domain(song)
        assert view.primary_genre == "Grunge"

    def test_primary_genre_no_genre_tags(self, catalog_service):
        """Song 2: has '90s' (Era) only -> no Genre -> None."""
        song = catalog_service.get_song(2)
        view = SongView.from_domain(song)
        assert view.primary_genre is None

    def test_primary_genre_no_tags(self, catalog_service):
        """Song 7: no tags at all -> None."""
        song = catalog_service.get_song(7)
        view = SongView.from_domain(song)
        assert view.primary_genre is None

    def test_master_publisher_display(self, catalog_service):
        """Song 1: DGC Records (parent UMG) -> 'DGC Records (Universal Music Group)'."""
        song = catalog_service.get_song(1)
        view = SongView.from_domain(song)
        assert view.display_master_publisher == "DGC Records (Universal Music Group)"

    def test_master_publisher_empty(self, catalog_service):
        """Song 2: no recording publisher -> empty string."""
        song = catalog_service.get_song(2)
        view = SongView.from_domain(song)
        assert view.display_master_publisher == ""


class TestAlbumViewFromCatalog:
    """Verify AlbumView.from_domain produces correct computed fields."""

    def test_nevermind_view(self, catalog_service):
        album = catalog_service.get_album(100)
        view = AlbumView.from_domain(album)

        assert view.display_artist == "Nirvana"
        assert view.song_count == 1
        # Publisher display: Sub Pop has no parent, DGC has parent UMG
        # Exact order may vary by DB, but split by ', ' should give exact set
        pub_parts = set(view.display_publisher.split(", "))
        assert pub_parts == {"Sub Pop", "DGC Records (Universal Music Group)"}

    def test_tcats_view(self, catalog_service):
        album = catalog_service.get_album(200)
        view = AlbumView.from_domain(album)

        assert view.display_artist == "Foo Fighters"
        assert view.display_publisher == "Roswell Records"
        assert view.song_count == 1
