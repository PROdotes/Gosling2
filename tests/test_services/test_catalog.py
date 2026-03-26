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

        assert song is not None, "Song 2 should exist"
        assert song.id == 2, f"Expected id 2, got {song.id}"
        assert song.title == "Everlong", f"Expected title 'Everlong', got {song.title}"
        assert (
            song.media_name == "Everlong"
        ), f"Expected media_name 'Everlong', got {song.media_name}"
        assert (
            song.source_path == "/path/2"
        ), f"Expected source_path '/path/2', got {song.source_path}"
        assert (
            song.duration_s == 240.0
        ), f"Expected duration_ms 240000, got {song.duration_ms}"
        assert song.is_active is True, f"Expected is_active True, got {song.is_active}"
        assert song.type_id == 1, f"Expected type_id 1, got {song.type_id}"

    def test_credits_hydration(self, catalog_service):
        """Song 2: exactly 1 credit - Foo Fighters as Performer."""
        song = catalog_service.get_song(2)
        assert song is not None, "Song 2 should exist"
        assert len(song.credits) == 1, f"Expected 1 credit, got {len(song.credits)}"

        credit = song.credits[0]
        assert (
            credit.display_name == "Foo Fighters"
        ), f"Expected display_name 'Foo Fighters', got {credit.display_name}"
        assert credit.role_id == 1, f"Expected role_id 1, got {credit.role_id}"
        assert (
            credit.role_name == "Performer"
        ), f"Expected role_name 'Performer', got {credit.role_name}"
        assert (
            credit.identity_id == 3
        ), f"Expected identity_id 3 (Foo Fighters), got {credit.identity_id}"
        assert (
            credit.is_primary is True
        ), f"Expected is_primary True, got {credit.is_primary}"

    def test_multiple_credits(self, catalog_service):
        """Song 6 (Dual Credit): Dave Grohl(Performer) + Taylor Hawkins(Composer)."""
        song = catalog_service.get_song(6)
        assert song is not None, "Song 6 should exist"
        assert len(song.credits) == 2, f"Expected 2 credits, got {len(song.credits)}"

        credit_map = {c.display_name: c for c in song.credits}
        assert (
            "Dave Grohl" in credit_map
        ), f"Expected 'Dave Grohl' in credits, got {list(credit_map.keys())}"
        assert (
            credit_map["Dave Grohl"].role_name == "Performer"
        ), f"Expected Dave role 'Performer', got {credit_map['Dave Grohl'].role_name}"
        assert (
            credit_map["Dave Grohl"].role_id == 1
        ), f"Expected Dave role_id 1, got {credit_map['Dave Grohl'].role_id}"
        assert (
            credit_map["Dave Grohl"].is_primary is True
        ), f"Expected Dave is_primary True, got {credit_map['Dave Grohl'].is_primary}"
        assert (
            "Taylor Hawkins" in credit_map
        ), f"Expected 'Taylor Hawkins' in credits, got {list(credit_map.keys())}"
        assert (
            credit_map["Taylor Hawkins"].role_name == "Composer"
        ), f"Expected Taylor role 'Composer', got {credit_map['Taylor Hawkins'].role_name}"
        assert (
            credit_map["Taylor Hawkins"].role_id == 2
        ), f"Expected Taylor role_id 2, got {credit_map['Taylor Hawkins'].role_id}"
        assert (
            credit_map["Taylor Hawkins"].is_primary is True
        ), f"Expected Taylor is_primary True, got {credit_map['Taylor Hawkins'].is_primary}"

    def test_zero_credits(self, catalog_service):
        """Song 7 (Hollow Song): no credits."""
        song = catalog_service.get_song(7)
        assert song is not None, "Song 7 should exist"
        assert (
            song.title == "Hollow Song"
        ), f"Expected title 'Hollow Song', got {song.title}"
        assert song.credits == [], f"Expected empty credits, got {song.credits}"

    def test_album_hydration(self, catalog_service):
        """Song 1 (SLTS): 1 album (Nevermind), Track 1, with publishers."""
        song = catalog_service.get_song(1)
        assert song is not None, "Song 1 should exist"
        assert len(song.albums) == 1, f"Expected 1 album, got {len(song.albums)}"

        album = song.albums[0]
        assert album.album_id == 100, f"Expected album_id 100, got {album.album_id}"
        assert (
            album.album_title == "Nevermind"
        ), f"Expected album_title 'Nevermind', got {album.album_title}"
        assert (
            album.track_number == 1
        ), f"Expected track_number 1, got {album.track_number}"
        assert (
            album.is_primary is True
        ), f"Expected is_primary True, got {album.is_primary}"
        assert (
            album.release_year == 1991
        ), f"Expected release_year 1991, got {album.release_year}"

        # Album publishers hydrated
        assert (
            len(album.album_publishers) == 2
        ), f"Expected 2 album publishers, got {len(album.album_publishers)}"
        pub_names = {p.name for p in album.album_publishers}
        assert pub_names == {
            "DGC Records",
            "Sub Pop",
        }, f"Expected publishers {{'DGC Records', 'Sub Pop'}}, got {pub_names}"

    def test_song_with_no_album(self, catalog_service):
        """Song 4 (Grohlton Theme): no album."""
        song = catalog_service.get_song(4)
        assert song is not None, "Song 4 should exist"
        assert song.albums == [], f"Expected empty albums, got {song.albums}"

    def test_master_publisher_hydration(self, catalog_service):
        """Song 1: has DGC Records as recording publisher with parent_name resolved."""
        song = catalog_service.get_song(1)
        assert song is not None, "Song 1 should exist"
        assert (
            len(song.publishers) == 1
        ), f"Expected 1 publisher, got {len(song.publishers)}"
        assert (
            song.publishers[0].name == "DGC Records"
        ), f"Expected publisher name 'DGC Records', got {song.publishers[0].name}"
        assert (
            song.publishers[0].parent_name == "Universal Music Group"
        ), f"Expected parent_name 'Universal Music Group', got {song.publishers[0].parent_name}"

    def test_song_without_publisher(self, catalog_service):
        """Song 2 has no RecordingPublisher."""
        song = catalog_service.get_song(2)
        assert song is not None, "Song 2 should exist"
        assert (
            song.publishers == []
        ), f"Expected empty publishers, got {song.publishers}"

    def test_tag_hydration(self, catalog_service):
        """Song 1: Grunge(Genre), Energetic(Mood), English(Jezik)."""
        song = catalog_service.get_song(1)
        assert song is not None, "Song 1 should exist"
        assert len(song.tags) == 3, f"Expected 3 tags, got {len(song.tags)}"
        tag_map = {t.name: t for t in song.tags}
        assert (
            tag_map["Grunge"].category == "Genre"
        ), f"Expected Grunge category 'Genre', got {tag_map['Grunge'].category}"
        assert (
            tag_map["Energetic"].category == "Mood"
        ), f"Expected Energetic category 'Mood', got {tag_map['Energetic'].category}"
        assert (
            tag_map["English"].category == "Jezik"
        ), f"Expected English category 'Jezik', got {tag_map['English'].category}"

    def test_song_with_no_tags(self, catalog_service):
        """Song 7 (Hollow Song): no tags."""
        song = catalog_service.get_song(7)
        assert song is not None, "Song 7 should exist"
        assert song.tags == [], f"Expected empty tags, got {song.tags}"

    def test_not_found(self, catalog_service):
        """Non-existent song ID returns None."""
        song = catalog_service.get_song(999)
        assert song is None, f"Expected None for non-existent song, got {song}"

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
            assert (
                song.title == expected_title
            ), f"Expected song {song_id} title '{expected_title}', got {song.title}"


# ===================================================================
# CatalogService.search_songs
# ===================================================================
class TestSearchSongs:
    """CatalogService.search_songs contracts (title + album + identity resolution)."""

    def test_title_match(self, catalog_service):
        """Searching 'Spirit' matches Song 1 by title."""
        results = catalog_service.search_songs("Spirit")
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert (
            results[0].title == "Smells Like Teen Spirit"
        ), f"Expected title 'Smells Like Teen Spirit', got {results[0].title}"

    def test_album_match(self, catalog_service):
        """Searching 'Nevermind' matches Song 1 via album title."""
        results = catalog_service.search_songs("Nevermind")
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert (
            results[0].title == "Smells Like Teen Spirit"
        ), f"Expected title 'Smells Like Teen Spirit', got {results[0].title}"

    def test_identity_match_surface_only(self, catalog_service):
        """Searching 'Dave Grohl' in Normal mode should find songs where he is DIRECTLY credited,
        but NOT resolve to his groups (Nirvana, Foo Fighters)."""
        results = catalog_service.search_songs("Dave Grohl")
        titles = {s.title for s in results}

        # Dave's direct songs (NameID 10): Dual Credit Track, Joint Venture
        assert "Dual Credit Track" in titles
        assert "Joint Venture" in titles
        
        # Dave's aliases (Grohlton, Late!) - These should ideally still fail/pass depending on if aliases are 'surface'.
        # For now, let's stick to the 'Spice Girls' logic: No Group Redirection.
        assert "Smells Like Teen Spirit" not in titles, "Nirvana should not be in surface search for Dave."
        assert "Everlong" not in titles, "Foo Fighters should not be in surface search for Dave."

class TestSearchSongsDeep:
    """CatalogService.search_songs_deep contracts (Full Metadata + Hierarchical resolution)."""

    def test_identity_match_expands_to_group_songs(self, catalog_service):
        """Searching 'Dave Grohl' in DEEP mode should find songs credited to Dave directly,
        PLUS songs credited to his groups (Nirvana, Foo Fighters)."""
        results = catalog_service.search_songs_deep("Dave Grohl")
        titles = {s.title for s in results}

        # Dave's direct songs
        assert "Dual Credit Track" in titles
        assert "Joint Venture" in titles

        # Dave's group songs (The Expansion)
        assert "Smells Like Teen Spirit" in titles
        assert "Everlong" in titles

    def test_metadata_and_hierarchy_combined(self, catalog_service):
        """Deep search matches across metadata tags and labels."""
        # 'Universal' is the parent of DGC (SLTS).
        results = catalog_service.search_songs_deep("Universal")
        titles = {s.title for s in results}
        assert "Smells Like Teen Spirit" in titles

        # Taylor's solo song should NOT be here
        assert (
            "Range Rover Bitch" not in titles
        ), f"Did not expect 'Range Rover Bitch' in results, got {titles}"

    def test_alias_match_resolves_to_group_songs(self, catalog_service):
        """Searching 'Grohlton' via Deep should find Grohlton Theme + group songs."""
        results = catalog_service.search_songs_deep("Grohlton")
        titles = {s.title for s in results}

        assert (
            "Grohlton Theme" in titles
        ), f"Expected 'Grohlton Theme' in results, got {titles}"
        # Because Grohlton resolves to Dave (identity 1), which is in Nirvana/Foo Fighters
        assert (
            "Smells Like Teen Spirit" in titles
        ), f"Expected 'Smells Like Teen Spirit' in results, got {titles}"
        assert "Everlong" in titles, f"Expected 'Everlong' in results, got {titles}"

    def test_group_match(self, catalog_service):
        """Searching 'Nirvana' should find SLTS directly."""
        results = catalog_service.search_songs("Nirvana")
        titles = {s.title for s in results}
        assert (
            "Smells Like Teen Spirit" in titles
        ), f"Expected 'Smells Like Teen Spirit' in results, got {titles}"

    def test_no_results(self, catalog_service):
        """Searching non-existent term returns empty list."""
        results = catalog_service.search_songs("ZZZZNONEXISTENT")
        assert results == [], f"Expected empty results, got {results}"

    def test_results_are_hydrated(self, catalog_service):
        """Search results should have credits, albums, tags filled in."""
        results = catalog_service.search_songs("Everlong")
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        song = results[0]
        assert len(song.credits) == 1, f"Expected 1 credit, got {len(song.credits)}"
        assert (
            song.credits[0].display_name == "Foo Fighters"
        ), f"Expected credit 'Foo Fighters', got {song.credits[0].display_name}"
        assert len(song.albums) == 1, f"Expected 1 album, got {len(song.albums)}"
        assert (
            song.albums[0].album_title == "The Colour and the Shape"
        ), f"Expected album 'The Colour and the Shape', got {song.albums[0].album_title}"

    def test_no_duplicates(self, catalog_service):
        """Search should not return duplicate songs even if matched via multiple paths."""
        results = catalog_service.search_songs("Dave Grohl")
        ids = [s.id for s in results]
        assert len(ids) == len(set(ids)), f"Duplicate song IDs in search results: {ids}"


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
        assert (
            4 in song_ids
        ), f"Expected song 4 (Grohlton Theme) in results, got {song_ids}"
        assert (
            5 in song_ids
        ), f"Expected song 5 (Pocketwatch Demo) in results, got {song_ids}"
        assert (
            6 in song_ids
        ), f"Expected song 6 (Dual Credit Track) in results, got {song_ids}"
        assert (
            8 in song_ids
        ), f"Expected song 8 (Joint Venture) in results, got {song_ids}"

        # Group credits: 1 (Nirvana), 2 (Foo Fighters)
        assert 1 in song_ids, f"Expected song 1 (SLTS) in results, got {song_ids}"
        assert 2 in song_ids, f"Expected song 2 (Everlong) in results, got {song_ids}"

        # NOT Taylor's solo
        assert (
            3 not in song_ids
        ), f"Did not expect song 3 (Range Rover Bitch) in results, got {song_ids}"

    def test_taylor_hawkins(self, catalog_service):
        """Taylor (ID=4): person in Foo Fighters(3).
        Solo + Foo Fighters songs + any credited."""
        songs = catalog_service.get_songs_by_identity(4)
        song_ids = {s.id for s in songs}

        assert (
            3 in song_ids
        ), f"Expected song 3 (Range Rover Bitch) in results, got {song_ids}"
        assert 2 in song_ids, f"Expected song 2 (Everlong) in results, got {song_ids}"
        assert (
            6 in song_ids
        ), f"Expected song 6 (Dual Credit Track) in results, got {song_ids}"
        assert (
            8 in song_ids
        ), f"Expected song 8 (Joint Venture) in results, got {song_ids}"

    def test_nirvana_as_group(self, catalog_service):
        """Nirvana (ID=2, group): has member Dave(1).
        Should return Nirvana songs + Dave's solo/alias songs."""
        songs = catalog_service.get_songs_by_identity(2)
        song_ids = {s.id for s in songs}

        assert 1 in song_ids, f"Expected song 1 (SLTS) in results, got {song_ids}"
        # Members expanded: Dave (1)
        assert (
            4 in song_ids
        ), f"Expected song 4 (Grohlton Theme) in results, got {song_ids}"
        assert (
            5 in song_ids
        ), f"Expected song 5 (Pocketwatch Demo) in results, got {song_ids}"
        assert (
            6 in song_ids
        ), f"Expected song 6 (Dual Credit Track) in results, got {song_ids}"
        assert (
            8 in song_ids
        ), f"Expected song 8 (Joint Venture) in results, got {song_ids}"

    def test_not_found_identity(self, catalog_service):
        """Non-existent identity ID returns empty list."""
        songs = catalog_service.get_songs_by_identity(999)
        assert (
            songs == []
        ), f"Expected empty list for non-existent identity, got {songs}"

    def test_results_are_hydrated(self, catalog_service):
        """Songs returned by get_songs_by_identity should be fully hydrated."""
        songs = catalog_service.get_songs_by_identity(2)  # Nirvana
        slts = next((s for s in songs if s.id == 1), None)
        assert slts is not None, "Song 1 (SLTS) should be in Nirvana results"
        assert (
            len(slts.credits) == 1
        ), f"Expected 1 credit for SLTS, got {len(slts.credits)}"
        assert (
            slts.credits[0].display_name == "Nirvana"
        ), f"Expected credit 'Nirvana', got {slts.credits[0].display_name}"
        assert (
            len(slts.albums) == 1
        ), f"Expected 1 album for SLTS, got {len(slts.albums)}"
        assert (
            slts.albums[0].album_title == "Nevermind"
        ), f"Expected album 'Nevermind', got {slts.albums[0].album_title}"


# ===================================================================
# CatalogService.get_identity / get_all_identities / search_identities
# ===================================================================
class TestGetIdentity:
    """CatalogService.get_identity contracts."""

    def test_person_with_full_tree(self, catalog_service):
        """Dave Grohl (ID=1): aliases, groups, no members."""
        identity = catalog_service.get_identity(1)
        assert identity is not None, "Identity 1 (Dave Grohl) should exist"
        assert (
            identity.display_name == "Dave Grohl"
        ), f"Expected display_name 'Dave Grohl', got {identity.display_name}"
        assert identity.type == "person", f"Expected type 'person', got {identity.type}"

        # Aliases
        alias_names = {a.display_name for a in identity.aliases}
        assert alias_names == {
            "Dave Grohl",
            "Grohlton",
            "Late!",
            "Ines Prajo",
        }, f"Expected aliases {{'Dave Grohl', 'Grohlton', 'Late!', 'Ines Prajo'}}, got {alias_names}"

        # Groups
        group_names = {g.display_name for g in identity.groups}
        assert group_names == {
            "Nirvana",
            "Foo Fighters",
        }, f"Expected groups {{'Nirvana', 'Foo Fighters'}}, got {group_names}"

        # No members (person)
        assert (
            identity.members == []
        ), f"Expected no members for person, got {identity.members}"

    def test_group_with_members(self, catalog_service):
        """Foo Fighters (ID=3): members Dave + Taylor, no groups."""
        identity = catalog_service.get_identity(3)
        assert identity is not None, "Identity 3 (Foo Fighters) should exist"
        assert (
            identity.display_name == "Foo Fighters"
        ), f"Expected display_name 'Foo Fighters', got {identity.display_name}"
        assert identity.type == "group", f"Expected type 'group', got {identity.type}"

        member_names = {m.display_name for m in identity.members}
        assert member_names == {
            "Dave Grohl",
            "Taylor Hawkins",
        }, f"Expected members {{'Dave Grohl', 'Taylor Hawkins'}}, got {member_names}"

        # No groups
        assert (
            identity.groups == []
        ), f"Expected no groups for group entity, got {identity.groups}"

    def test_not_found(self, catalog_service):
        """Non-existent identity ID returns None."""
        result = catalog_service.get_identity(999)
        assert result is None, f"Expected None for non-existent identity, got {result}"


class TestGetAllIdentities:
    """CatalogService.get_all_identities contracts."""

    def test_returns_all_four_sorted(self, catalog_service):
        """All 4 identities returned in sorted order by display_name."""
        identities = catalog_service.get_all_identities()
        assert len(identities) == 4, f"Expected 4 identities, got {len(identities)}"
        names = [i.display_name for i in identities]
        assert names == [
            "Dave Grohl",
            "Foo Fighters",
            "Nirvana",
            "Taylor Hawkins",
        ], f"Expected sorted names, got {names}"

    def test_identities_are_hydrated(self, catalog_service):
        """Identities should have aliases/members/groups filled in."""
        identities = catalog_service.get_all_identities()
        dave = next((i for i in identities if i.display_name == "Dave Grohl"), None)
        assert dave is not None, "Dave Grohl should be in all identities"
        assert (
            len(dave.aliases) == 4
        ), f"Expected 4 aliases for Dave, got {len(dave.aliases)}"
        assert (
            len(dave.groups) == 2
        ), f"Expected 2 groups for Dave, got {len(dave.groups)}"

    def test_empty_db(self, catalog_service_empty):
        """Empty database returns empty list."""
        result = catalog_service_empty.get_all_identities()
        assert result == [], f"Expected empty list, got {result}"


class TestSearchIdentities:
    """CatalogService.search_identities contracts."""

    def test_by_name(self, catalog_service):
        """Searching by group name returns the identity."""
        results = catalog_service.search_identities("Nirvana")
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert (
            results[0].display_name == "Nirvana"
        ), f"Expected display_name 'Nirvana', got {results[0].display_name}"

    def test_by_alias(self, catalog_service):
        """Searching 'Grohlton' returns Dave Grohl (hydrated)."""
        results = catalog_service.search_identities("Grohlton")
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert (
            results[0].display_name == "Dave Grohl"
        ), f"Expected display_name 'Dave Grohl', got {results[0].display_name}"
        # Should be hydrated
        assert (
            len(results[0].aliases) == 4
        ), f"Expected 4 aliases, got {len(results[0].aliases)}"

    def test_no_results(self, catalog_service):
        """Searching non-existent term returns empty list."""
        result = catalog_service.search_identities("ZZZZ")
        assert result == [], f"Expected empty list, got {result}"


# ===================================================================
# CatalogService.get_all_albums / get_album / search_albums
# ===================================================================
class TestGetAllAlbums:
    """CatalogService.get_all_albums contracts."""

    def test_returns_both_albums(self, catalog_service):
        """Both albums returned in sorted order by title."""
        albums = catalog_service.get_all_albums()
        assert len(albums) == 2, f"Expected 2 albums, got {len(albums)}"
        titles = [a.title for a in albums]
        assert titles == [
            "Nevermind",
            "The Colour and the Shape",
        ], f"Expected sorted titles, got {titles}"

    def test_nevermind_hydration(self, catalog_service):
        """Nevermind album should have full publisher, credit, and song hydration."""
        albums = catalog_service.get_all_albums()
        nevermind = next((a for a in albums if a.title == "Nevermind"), None)
        assert nevermind is not None, "Nevermind should be in all albums"

        assert nevermind.id == 100, f"Expected id 100, got {nevermind.id}"
        assert (
            nevermind.release_year == 1991
        ), f"Expected release_year 1991, got {nevermind.release_year}"

        # Publishers
        assert (
            len(nevermind.publishers) == 2
        ), f"Expected 2 publishers, got {len(nevermind.publishers)}"
        pub_names = {p.name for p in nevermind.publishers}
        assert pub_names == {
            "DGC Records",
            "Sub Pop",
        }, f"Expected publishers {{'DGC Records', 'Sub Pop'}}, got {pub_names}"

        # Credits
        assert (
            len(nevermind.credits) == 1
        ), f"Expected 1 credit, got {len(nevermind.credits)}"
        assert (
            nevermind.credits[0].display_name == "Nirvana"
        ), f"Expected credit 'Nirvana', got {nevermind.credits[0].display_name}"

        # Songs
        assert len(nevermind.songs) == 1, f"Expected 1 song, got {len(nevermind.songs)}"
        assert (
            nevermind.songs[0].title == "Smells Like Teen Spirit"
        ), f"Expected song 'Smells Like Teen Spirit', got {nevermind.songs[0].title}"

    def test_empty_db(self, catalog_service_empty):
        """Empty database returns empty list."""
        result = catalog_service_empty.get_all_albums()
        assert result == [], f"Expected empty list, got {result}"


class TestGetAlbum:
    """CatalogService.get_album contracts."""

    def test_tcats(self, catalog_service):
        """The Colour and the Shape (ID=200): full hydration of all fields."""
        album = catalog_service.get_album(200)
        assert album is not None, "Album 200 should exist"
        assert (
            album.title == "The Colour and the Shape"
        ), f"Expected title 'The Colour and the Shape', got {album.title}"
        assert (
            album.release_year == 1997
        ), f"Expected release_year 1997, got {album.release_year}"
        assert (
            album.album_type is None
        ), f"Expected album_type None, got {album.album_type}"
        assert (
            len(album.publishers) == 1
        ), f"Expected 1 publisher, got {len(album.publishers)}"
        assert (
            album.publishers[0].name == "Roswell Records"
        ), f"Expected publisher 'Roswell Records', got {album.publishers[0].name}"
        assert len(album.credits) == 1, f"Expected 1 credit, got {len(album.credits)}"
        assert (
            album.credits[0].display_name == "Foo Fighters"
        ), f"Expected credit 'Foo Fighters', got {album.credits[0].display_name}"
        assert len(album.songs) == 1, f"Expected 1 song, got {len(album.songs)}"
        assert (
            album.songs[0].title == "Everlong"
        ), f"Expected song 'Everlong', got {album.songs[0].title}"

    def test_not_found(self, catalog_service):
        """Non-existent album ID returns None."""
        result = catalog_service.get_album(999)
        assert result is None, f"Expected None for non-existent album, got {result}"


class TestSearchAlbums:
    """CatalogService.search_albums contracts."""

    def test_partial_match(self, catalog_service):
        """Partial title match returns matching album."""
        albums = catalog_service.search_albums("Never")
        assert len(albums) == 1, f"Expected 1 result, got {len(albums)}"
        assert (
            albums[0].title == "Nevermind"
        ), f"Expected title 'Nevermind', got {albums[0].title}"

    def test_no_match(self, catalog_service):
        """Searching non-existent term returns empty list."""
        result = catalog_service.search_albums("ZZZZZ")
        assert result == [], f"Expected empty list, got {result}"


# ===================================================================
# CatalogService.get_all_publishers / get_publisher / search_publishers / get_publisher_songs
# ===================================================================
class TestGetAllPublishers:
    """CatalogService.get_all_publishers contracts."""

    def test_returns_all_six_sorted(self, catalog_service):
        """All 6 publishers returned in sorted order by name."""
        pubs = catalog_service.get_all_publishers()
        assert len(pubs) == 6, f"Expected 6 publishers, got {len(pubs)}"
        names = [p.name for p in pubs]
        assert names == [
            "DGC Records",
            "Island Def Jam",
            "Island Records",
            "Roswell Records",
            "Sub Pop",
            "Universal Music Group",
        ], f"Expected sorted publisher names, got {names}"

    def test_parent_names_hydrated(self, catalog_service):
        """Every publisher should have parent_name resolved (or None for roots)."""
        pubs = catalog_service.get_all_publishers()
        pub_map = {p.name: p for p in pubs}
        assert (
            pub_map["DGC Records"].parent_name == "Universal Music Group"
        ), f"Expected DGC parent 'Universal Music Group', got {pub_map['DGC Records'].parent_name}"
        assert (
            pub_map["Island Records"].parent_name == "Universal Music Group"
        ), f"Expected Island Records parent 'Universal Music Group', got {pub_map['Island Records'].parent_name}"
        assert (
            pub_map["Island Def Jam"].parent_name == "Island Records"
        ), f"Expected Island Def Jam parent 'Island Records', got {pub_map['Island Def Jam'].parent_name}"
        assert (
            pub_map["Universal Music Group"].parent_name is None
        ), f"Expected UMG parent None, got {pub_map['Universal Music Group'].parent_name}"
        assert (
            pub_map["Roswell Records"].parent_name is None
        ), f"Expected Roswell parent None, got {pub_map['Roswell Records'].parent_name}"
        assert (
            pub_map["Sub Pop"].parent_name is None
        ), f"Expected Sub Pop parent None, got {pub_map['Sub Pop'].parent_name}"

    def test_empty_db(self, catalog_service_empty):
        """Empty database returns empty list."""
        result = catalog_service_empty.get_all_publishers()
        assert result == [], f"Expected empty list, got {result}"


class TestGetPublisher:
    """CatalogService.get_publisher contracts."""

    def test_with_children(self, catalog_service):
        """UMG (1) should have children: Island Records(2), DGC Records(10)."""
        pub = catalog_service.get_publisher(1)
        assert pub is not None, "Publisher 1 (UMG) should exist"
        assert (
            pub.name == "Universal Music Group"
        ), f"Expected name 'Universal Music Group', got {pub.name}"
        assert (
            pub.parent_name is None
        ), f"Expected parent_name None, got {pub.parent_name}"
        child_names = {c.name for c in pub.sub_publishers}
        assert child_names == {
            "Island Records",
            "DGC Records",
        }, f"Expected children {{'Island Records', 'DGC Records'}}, got {child_names}"

    def test_hierarchy_resolution(self, catalog_service):
        """Island Def Jam (3): parent_name should be 'Island Records'."""
        pub = catalog_service.get_publisher(3)
        assert pub is not None, "Publisher 3 (Island Def Jam) should exist"
        assert (
            pub.name == "Island Def Jam"
        ), f"Expected name 'Island Def Jam', got {pub.name}"
        assert (
            pub.parent_name == "Island Records"
        ), f"Expected parent_name 'Island Records', got {pub.parent_name}"

    def test_dgc_parent(self, catalog_service):
        """DGC Records (10): parent_name should be 'Universal Music Group'."""
        pub = catalog_service.get_publisher(10)
        assert pub is not None, "Publisher 10 (DGC Records) should exist"
        assert (
            pub.parent_name == "Universal Music Group"
        ), f"Expected parent_name 'Universal Music Group', got {pub.parent_name}"

    def test_leaf_publisher(self, catalog_service):
        """Sub Pop (5): no parent, no children."""
        pub = catalog_service.get_publisher(5)
        assert pub is not None, "Publisher 5 (Sub Pop) should exist"
        assert (
            pub.parent_name is None
        ), f"Expected parent_name None, got {pub.parent_name}"
        assert (
            pub.sub_publishers == []
        ), f"Expected no sub_publishers, got {pub.sub_publishers}"

    def test_not_found(self, catalog_service):
        """Non-existent publisher ID returns None."""
        result = catalog_service.get_publisher(999)
        assert result is None, f"Expected None for non-existent publisher, got {result}"


class TestSearchPublishers:
    """CatalogService.search_publishers contracts."""

    def test_partial_match(self, catalog_service):
        """Searching 'Island' returns both Island Records and Island Def Jam."""
        results = catalog_service.search_publishers("Island")
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        names = {p.name for p in results}
        assert names == {
            "Island Records",
            "Island Def Jam",
        }, f"Expected {{'Island Records', 'Island Def Jam'}}, got {names}"

    def test_hydration_in_search(self, catalog_service):
        """Search results should have parent_name resolved."""
        results = catalog_service.search_publishers("Island Def")
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert (
            results[0].parent_name == "Island Records"
        ), f"Expected parent_name 'Island Records', got {results[0].parent_name}"

    def test_no_match(self, catalog_service):
        """Searching non-existent term returns empty list."""
        result = catalog_service.search_publishers("ZZZZ")
        assert result == [], f"Expected empty list, got {result}"


class TestGetPublisherSongs:
    """CatalogService.get_publisher_songs contracts."""

    def test_dgc_songs(self, catalog_service):
        """DGC Records (10) has Song 1 via RecordingPublishers."""
        songs = catalog_service.get_publisher_songs(10)
        assert len(songs) == 1, f"Expected 1 song, got {len(songs)}"
        assert (
            songs[0].title == "Smells Like Teen Spirit"
        ), f"Expected title 'Smells Like Teen Spirit', got {songs[0].title}"
        # Song should be hydrated
        assert (
            len(songs[0].credits) == 1
        ), f"Expected 1 credit, got {len(songs[0].credits)}"

    def test_publisher_with_no_songs(self, catalog_service):
        """Sub Pop (5) has no RecordingPublisher entries."""
        songs = catalog_service.get_publisher_songs(5)
        assert songs == [], f"Expected empty list, got {songs}"


# ===================================================================
# View model integration (SongView, AlbumView)
# ===================================================================
class TestSongViewFromCatalog:
    """Verify SongView.from_domain produces correct computed fields from CatalogService output."""

    def test_display_artist_single(self, catalog_service):
        """Song 1 (SLTS): single performer -> 'Nirvana'."""
        song = catalog_service.get_song(1)
        view = SongView.from_domain(song)
        assert (
            view.display_artist == "Nirvana"
        ), f"Expected display_artist 'Nirvana', got {view.display_artist}"

    def test_display_artist_multiple_performers(self, catalog_service):
        """Song 8 (Joint Venture): two performers -> 'Dave Grohl, Taylor Hawkins'."""
        song = catalog_service.get_song(8)
        view = SongView.from_domain(song)
        assert (
            view.display_artist == "Dave Grohl, Taylor Hawkins"
        ), f"Expected display_artist 'Dave Grohl, Taylor Hawkins', got {view.display_artist}"

    def test_display_artist_no_credits(self, catalog_service):
        """Song 7 (Hollow Song): no credits -> None."""
        song = catalog_service.get_song(7)
        view = SongView.from_domain(song)
        assert (
            view.display_artist is None
        ), f"Expected display_artist None, got {view.display_artist}"

    def test_formatted_duration(self, catalog_service):
        """Song 1 (200s=200000ms): '3:20'."""
        song = catalog_service.get_song(1)
        view = SongView.from_domain(song)
        assert (
            view.formatted_duration == "3:20"
        ), f"Expected formatted_duration '3:20', got {view.formatted_duration}"

    def test_formatted_duration_exact_minute(self, catalog_service):
        """Song 3 (180s=180000ms): '3:00'."""
        song = catalog_service.get_song(3)
        view = SongView.from_domain(song)
        assert (
            view.formatted_duration == "3:00"
        ), f"Expected formatted_duration '3:00', got {view.formatted_duration}"

    def test_formatted_duration_short(self, catalog_service):
        """Song 7 (10s=10000ms): '0:10'."""
        song = catalog_service.get_song(7)
        view = SongView.from_domain(song)
        assert (
            view.formatted_duration == "0:10"
        ), f"Expected formatted_duration '0:10', got {view.formatted_duration}"

    def test_primary_genre_explicit_primary(self, catalog_service):
        """Song 9: has Alt Rock (primary=True) and Grunge (primary=False). Should be 'Alt Rock'."""
        song = catalog_service.get_song(9)
        view = SongView.from_domain(song)
        assert (
            view.primary_genre == "Alt Rock"
        ), f"Expected primary_genre 'Alt Rock', got {view.primary_genre}"

    def test_primary_genre_implicit(self, catalog_service):
        """Song 1: no explicit primary, first Genre tag wins -> 'Grunge'."""
        song = catalog_service.get_song(1)
        view = SongView.from_domain(song)
        assert (
            view.primary_genre == "Grunge"
        ), f"Expected primary_genre 'Grunge', got {view.primary_genre}"

    def test_primary_genre_no_genre_tags(self, catalog_service):
        """Song 2: has '90s' (Era) only -> no Genre -> None."""
        song = catalog_service.get_song(2)
        view = SongView.from_domain(song)
        assert (
            view.primary_genre is None
        ), f"Expected primary_genre None, got {view.primary_genre}"

    def test_primary_genre_no_tags(self, catalog_service):
        """Song 7: no tags at all -> None."""
        song = catalog_service.get_song(7)
        view = SongView.from_domain(song)
        assert (
            view.primary_genre is None
        ), f"Expected primary_genre None, got {view.primary_genre}"

    def test_master_publisher_display(self, catalog_service):
        """Song 1: DGC Records (parent UMG) -> 'DGC Records (Universal Music Group)'."""
        song = catalog_service.get_song(1)
        view = SongView.from_domain(song)
        assert (
            view.display_master_publisher == "DGC Records (Universal Music Group)"
        ), f"Expected display_master_publisher 'DGC Records (Universal Music Group)', got {view.display_master_publisher}"

    def test_master_publisher_empty(self, catalog_service):
        """Song 2: no recording publisher -> empty string."""
        song = catalog_service.get_song(2)
        view = SongView.from_domain(song)
        assert (
            view.display_master_publisher == ""
        ), f"Expected display_master_publisher '', got {view.display_master_publisher}"


class TestAlbumViewFromCatalog:
    """Verify AlbumView.from_domain produces correct computed fields."""

    def test_nevermind_view(self, catalog_service):
        """Nevermind (100): display_artist, song_count, and publisher display."""
        album = catalog_service.get_album(100)
        view = AlbumView.from_domain(album)

        assert (
            view.display_artist == "Nirvana"
        ), f"Expected display_artist 'Nirvana', got {view.display_artist}"
        assert view.song_count == 1, f"Expected song_count 1, got {view.song_count}"
        # Publisher display: Sub Pop has no parent, DGC has parent UMG
        # Exact order may vary by DB, but split by ', ' should give exact set
        pub_parts = set(view.display_publisher.split(", "))
        assert pub_parts == {
            "Sub Pop",
            "DGC Records (Universal Music Group)",
        }, f"Expected publisher parts {{'Sub Pop', 'DGC Records (Universal Music Group)'}}, got {pub_parts}"

    def test_tcats_view(self, catalog_service):
        """The Colour and the Shape (200): display_artist, display_publisher, song_count."""
        album = catalog_service.get_album(200)
        view = AlbumView.from_domain(album)

        assert (
            view.display_artist == "Foo Fighters"
        ), f"Expected display_artist 'Foo Fighters', got {view.display_artist}"
        assert (
            view.display_publisher == "Roswell Records"
        ), f"Expected display_publisher 'Roswell Records', got {view.display_publisher}"
        assert view.song_count == 1, f"Expected song_count 1, got {view.song_count}"
