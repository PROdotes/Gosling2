"""
Edge Case Tests
================
Tests using the edge_case_db fixture for orphans, nulls, unicode, boundary values.
Verifies the system handles degenerate data gracefully without crashes.

Also tests specific edge conditions with the populated_db where appropriate.
"""

from src.data.song_repository import SongRepository
from src.data.identity_repository import IdentityRepository
from src.data.publisher_repository import PublisherRepository
from src.services.catalog_service import CatalogService
from tests.conftest import _connect


# ===========================================================================
# Identity Fallback Display Names
# ===========================================================================
class TestIdentityFallbacks:
    """Identity display_name fallback: DisplayName -> LegalName -> 'Unknown Artist #ID'."""

    def test_no_artist_name_no_legal_name(self, edge_case_db):
        """Identity 100 has no ArtistName and no LegalName -> fallback to 'Unknown Artist #100'."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(100)
        assert identity is not None, "Identity 100 should exist in edge_case_db"
        assert identity.id == 100, f"Expected id=100, got {identity.id}"
        assert identity.type == "person", f"Expected type='person', got {identity.type}"
        assert (
            identity.display_name == "Unknown Artist #100"
        ), f"Expected 'Unknown Artist #100', got {identity.display_name}"
        assert (
            identity.legal_name is None
        ), f"Expected legal_name=None, got {identity.legal_name}"
        assert identity.aliases == [], f"Expected no aliases, got {identity.aliases}"
        assert identity.members == [], f"Expected no members, got {identity.members}"
        assert identity.groups == [], f"Expected no groups, got {identity.groups}"

    def test_legal_name_fallback(self, edge_case_db):
        """Identity 101 has LegalName='John Legal' but no primary ArtistName -> fallback to LegalName."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(101)
        assert identity is not None, "Identity 101 should exist in edge_case_db"
        assert identity.id == 101, f"Expected id=101, got {identity.id}"
        assert identity.type == "person", f"Expected type='person', got {identity.type}"
        assert (
            identity.display_name == "John Legal"
        ), f"Expected 'John Legal', got {identity.display_name}"
        assert (
            identity.legal_name == "John Legal"
        ), f"Expected legal_name='John Legal', got {identity.legal_name}"
        assert identity.aliases == [], f"Expected no aliases, got {identity.aliases}"
        assert identity.members == [], f"Expected no members, got {identity.members}"
        assert identity.groups == [], f"Expected no groups, got {identity.groups}"

    def test_unicode_display_name(self, edge_case_db):
        """Identity 104 has display name 'Bjork'."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(104)
        assert identity is not None, "Identity 104 should exist in edge_case_db"
        assert identity.id == 104, f"Expected id=104, got {identity.id}"
        assert identity.type == "person", f"Expected type='person', got {identity.type}"
        assert (
            identity.display_name == "Bjork"
        ), f"Expected 'Bjork', got {identity.display_name}"
        assert (
            identity.legal_name is None
        ), f"Expected legal_name=None, got {identity.legal_name}"
        assert identity.aliases == [], f"Expected no aliases, got {identity.aliases}"
        assert identity.members == [], f"Expected no members, got {identity.members}"
        assert identity.groups == [], f"Expected no groups, got {identity.groups}"


# ===========================================================================
# Song Edge Cases
# ===========================================================================
class TestSongEdgeCases:
    def test_whitespace_title(self, edge_case_db):
        """Song 101 has title ' ' (single space)."""
        repo = SongRepository(edge_case_db)
        song = repo.get_by_id(101)
        assert song is not None, "Song 101 should exist in edge_case_db"
        assert song.id == 101, f"Expected id=101, got {song.id}"
        assert song.title == " ", f"Expected title=' ', got {song.title}"
        assert song.media_name == " ", f"Expected media_name=' ', got {song.media_name}"
        assert (
            song.source_path == "/edge/2"
        ), f"Expected source_path='/edge/2', got {song.source_path}"
        assert (
            song.duration_s == 60.0
        ), f"Expected duration_s=60.0, got {song.duration_ms}"
        assert (
            song.audio_hash is None
        ), f"Expected audio_hash=None, got {song.audio_hash}"
        assert (
            song.processing_status == 1
        ), f"Expected processing_status=1, got {song.processing_status}"
        assert song.is_active is True, f"Expected is_active=True, got {song.is_active}"
        assert song.notes is None, f"Expected notes=None, got {song.notes}"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.year is None, f"Expected year=None, got {song.year}"
        assert song.isrc is None, f"Expected isrc=None, got {song.isrc}"
        assert song.credits == [], f"Expected no credits, got {song.credits}"
        assert song.albums == [], f"Expected no albums, got {song.albums}"
        assert song.publishers == [], f"Expected no publishers, got {song.publishers}"
        assert song.tags == [], f"Expected no tags, got {song.tags}"
        assert song.raw_tags == {}, f"Expected no raw_tags, got {song.raw_tags}"

    def test_single_char_title(self, edge_case_db):
        """Song 102 has title 'A'."""
        repo = SongRepository(edge_case_db)
        song = repo.get_by_id(102)
        assert song is not None, "Song 102 should exist in edge_case_db"
        assert song.id == 102, f"Expected id=102, got {song.id}"
        assert song.title == "A", f"Expected title='A', got {song.title}"
        assert song.media_name == "A", f"Expected media_name='A', got {song.media_name}"
        assert (
            song.source_path == "/edge/3"
        ), f"Expected source_path='/edge/3', got {song.source_path}"
        assert (
            song.duration_s == 30.0
        ), f"Expected duration_s=30.0, got {song.duration_ms}"
        assert (
            song.audio_hash is None
        ), f"Expected audio_hash=None, got {song.audio_hash}"
        assert (
            song.processing_status == 1
        ), f"Expected processing_status=1, got {song.processing_status}"
        assert song.is_active is True, f"Expected is_active=True, got {song.is_active}"
        assert song.notes is None, f"Expected notes=None, got {song.notes}"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.year is None, f"Expected year=None, got {song.year}"
        assert song.isrc is None, f"Expected isrc=None, got {song.isrc}"
        assert song.credits == [], f"Expected no credits, got {song.credits}"
        assert song.albums == [], f"Expected no albums, got {song.albums}"
        assert song.publishers == [], f"Expected no publishers, got {song.publishers}"
        assert song.tags == [], f"Expected no tags, got {song.tags}"
        assert song.raw_tags == {}, f"Expected no raw_tags, got {song.raw_tags}"

    def test_unicode_title(self, edge_case_db):
        """Song 103 has Japanese characters in title."""
        repo = SongRepository(edge_case_db)
        song = repo.get_by_id(103)
        assert song is not None, "Song 103 should exist in edge_case_db"
        assert song.id == 103, f"Expected id=103, got {song.id}"
        assert (
            song.title == "\u65e5\u672c\u8a9e\u30bd\u30f3\u30b0"
        ), f"Expected unicode title, got {song.title}"
        assert (
            song.media_name == "\u65e5\u672c\u8a9e\u30bd\u30f3\u30b0"
        ), f"Expected unicode media_name, got {song.media_name}"
        assert (
            song.source_path == "/edge/4"
        ), f"Expected source_path='/edge/4', got {song.source_path}"
        assert (
            song.duration_s == 200.0
        ), f"Expected duration_s=200.0, got {song.duration_ms}"
        assert (
            song.audio_hash is None
        ), f"Expected audio_hash=None, got {song.audio_hash}"
        assert (
            song.processing_status == 1
        ), f"Expected processing_status=1, got {song.processing_status}"
        assert song.is_active is True, f"Expected is_active=True, got {song.is_active}"
        assert song.notes is None, f"Expected notes=None, got {song.notes}"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.year is None, f"Expected year=None, got {song.year}"
        assert song.isrc is None, f"Expected isrc=None, got {song.isrc}"
        assert song.credits == [], f"Expected no credits, got {song.credits}"
        assert song.albums == [], f"Expected no albums, got {song.albums}"
        assert song.publishers == [], f"Expected no publishers, got {song.publishers}"
        assert song.tags == [], f"Expected no tags, got {song.tags}"
        assert song.raw_tags == {}, f"Expected no raw_tags, got {song.raw_tags}"

    def test_zero_duration(self, edge_case_db):
        """Song 104 has SourceDuration=0 -> duration_s=0.0."""
        repo = SongRepository(edge_case_db)
        song = repo.get_by_id(104)
        assert song is not None, "Song 104 should exist in edge_case_db"
        assert song.id == 104, f"Expected id=104, got {song.id}"
        assert (
            song.title == "Zero Duration"
        ), f"Expected title='Zero Duration', got {song.title}"
        assert (
            song.media_name == "Zero Duration"
        ), f"Expected media_name='Zero Duration', got {song.media_name}"
        assert (
            song.source_path == "/edge/5"
        ), f"Expected source_path='/edge/5', got {song.source_path}"
        assert (
            song.duration_s == 0.0
        ), f"Expected duration_s=0.0, got {song.duration_ms}"
        assert (
            song.audio_hash is None
        ), f"Expected audio_hash=None, got {song.audio_hash}"
        assert (
            song.processing_status == 1
        ), f"Expected processing_status=1, got {song.processing_status}"
        assert song.is_active is True, f"Expected is_active=True, got {song.is_active}"
        assert song.notes is None, f"Expected notes=None, got {song.notes}"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.year is None, f"Expected year=None, got {song.year}"
        assert song.isrc is None, f"Expected isrc=None, got {song.isrc}"
        assert song.credits == [], f"Expected no credits, got {song.credits}"
        assert song.albums == [], f"Expected no albums, got {song.albums}"
        assert song.publishers == [], f"Expected no publishers, got {song.publishers}"
        assert song.tags == [], f"Expected no tags, got {song.tags}"
        assert song.raw_tags == {}, f"Expected no raw_tags, got {song.raw_tags}"

    def test_zero_duration_formatted(self, edge_case_db):
        """Zero duration song formatted as '0:00' via SongView."""
        from src.models.view_models import SongView

        service = CatalogService(edge_case_db)
        song = service.get_song(104)
        assert song is not None, "Song 104 should exist in edge_case_db"
        view = SongView.from_domain(song)
        assert (
            view.formatted_duration == "0:00"
        ), f"Expected '0:00', got {view.formatted_duration}"
        assert view.id == 104, f"Expected id=104, got {view.id}"
        assert (
            view.title == "Zero Duration"
        ), f"Expected title='Zero Duration', got {view.title}"
        assert (
            view.media_name == "Zero Duration"
        ), f"Expected media_name='Zero Duration', got {view.media_name}"
        assert (
            view.source_path == "/edge/5"
        ), f"Expected source_path='/edge/5', got {view.source_path}"
        assert (
            view.duration_s == 0.0
        ), f"Expected duration_s=0.0, got {view.duration_ms}"
        assert (
            view.audio_hash is None
        ), f"Expected audio_hash=None, got {view.audio_hash}"
        assert (
            view.processing_status == 1
        ), f"Expected processing_status=1, got {view.processing_status}"
        assert view.is_active is True, f"Expected is_active=True, got {view.is_active}"
        assert view.notes is None, f"Expected notes=None, got {view.notes}"
        assert view.bpm is None, f"Expected bpm=None, got {view.bpm}"
        assert view.year is None, f"Expected year=None, got {view.year}"
        assert view.isrc is None, f"Expected isrc=None, got {view.isrc}"
        assert view.credits == [], f"Expected no credits, got {view.credits}"
        assert view.albums == [], f"Expected no albums, got {view.albums}"
        assert view.publishers == [], f"Expected no publishers, got {view.publishers}"
        assert view.tags == [], f"Expected no tags, got {view.tags}"
        assert view.raw_tags == {}, f"Expected no raw_tags, got {view.raw_tags}"
        assert (
            view.display_artist is None
        ), f"Expected display_artist=None, got {view.display_artist}"
        assert (
            view.display_master_publisher == ""
        ), f"Expected display_master_publisher='', got {view.display_master_publisher}"
        assert (
            view.primary_genre is None
        ), f"Expected primary_genre=None, got {view.primary_genre}"

    def test_search_unicode_title(self, edge_case_db):
        """search_slim can find a unicode title."""
        repo = SongRepository(edge_case_db)
        rows = repo.search_slim("\u65e5\u672c\u8a9e")
        assert len(rows) == 1, f"Expected 1 result, got {len(rows)}"
        row = rows[0]
        assert row["SourceID"] == 103, f"Expected SourceID=103, got {row['SourceID']}"
        assert (
            row["MediaName"] == "\u65e5\u672c\u8a9e\u30bd\u30f3\u30b0"
        ), f"Expected unicode MediaName, got '{row['MediaName']}'"
        assert (
            row["SourcePath"] == "/edge/4"
        ), f"Expected SourcePath='/edge/4', got '{row['SourcePath']}'"
        assert (
            row["SourceDuration"] == 200
        ), f"Expected SourceDuration=200, got {row['SourceDuration']}"
        assert row["IsActive"] == 1, f"Expected IsActive=1, got {row['IsActive']}"
        assert (
            row["RecordingYear"] is None
        ), f"Expected RecordingYear=None, got {row['RecordingYear']}"
        assert row["ISRC"] is None, f"Expected ISRC=None, got {row['ISRC']}"

    def test_search_single_char(self, edge_case_db):
        """search_slim with 'A' finds at least song 102."""
        repo = SongRepository(edge_case_db)
        rows = repo.search_slim("A")
        ids = [r["SourceID"] for r in rows]
        assert 102 in ids, f"Expected SourceID=102 in results, got ids={ids}"
        for row in rows:
            assert row["SourceID"] is not None, "Expected SourceID to be set"
            assert row["MediaName"] is not None, "Expected MediaName to be set"
            assert row["SourcePath"] is not None, "Expected SourcePath to be set"


# ===========================================================================
# Orphaned Publisher (parent points to non-existent ID)
# ===========================================================================
class TestOrphanedPublisher:
    def test_orphan_publisher_accessible(self, edge_case_db):
        """Publisher 100 has ParentPublisherID=999 which doesn't exist."""
        repo = PublisherRepository(edge_case_db)
        pub = repo.get_by_id(100)
        assert pub is not None, "Publisher 100 should exist in edge_case_db"
        assert pub.id == 100, f"Expected id=100, got {pub.id}"
        assert (
            pub.name == "Orphan Publisher"
        ), f"Expected name='Orphan Publisher', got {pub.name}"
        assert pub.parent_id == 999, f"Expected parent_id=999, got {pub.parent_id}"
        assert (
            pub.parent_name is None
        ), f"Expected parent_name=None (orphan), got {pub.parent_name}"
        assert (
            pub.sub_publishers == []
        ), f"Expected no sub_publishers, got {pub.sub_publishers}"

    def test_all_publishers_includes_orphan(self, edge_case_db):
        """get_all still returns the orphan publisher."""
        repo = PublisherRepository(edge_case_db)
        pubs = repo.get_all()
        assert len(pubs) == 1, f"Expected 1 publisher, got {len(pubs)}"
        pub = pubs[0]
        assert pub.id == 100, f"Expected id=100, got {pub.id}"
        assert (
            pub.name == "Orphan Publisher"
        ), f"Expected name='Orphan Publisher', got {pub.name}"
        assert pub.parent_id == 999, f"Expected parent_id=999, got {pub.parent_id}"
        assert (
            pub.parent_name is None
        ), f"Expected parent_name=None, got {pub.parent_name}"
        assert (
            pub.sub_publishers == []
        ), f"Expected no sub_publishers, got {pub.sub_publishers}"


# ===========================================================================
# Circular Group Memberships
# ===========================================================================
class TestCircularMemberships:
    """Groups A and B are members of each other. Should not crash."""

    def test_circular_group_a(self, edge_case_db):
        """Identity 102 (Circular Group A) has member 103 (Circular Group B)."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(102)
        assert identity is not None, "Identity 102 should exist in edge_case_db"
        assert identity.id == 102, f"Expected id=102, got {identity.id}"
        assert identity.type == "group", f"Expected type='group', got {identity.type}"
        assert (
            identity.display_name == "Circular Group A"
        ), f"Expected 'Circular Group A', got {identity.display_name}"
        assert (
            identity.legal_name is None
        ), f"Expected legal_name=None, got {identity.legal_name}"
        assert identity.aliases == [], f"Expected no aliases, got {identity.aliases}"

    def test_circular_group_b(self, edge_case_db):
        """Identity 103 (Circular Group B) has member 102 (Circular Group A)."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(103)
        assert identity is not None, "Identity 103 should exist in edge_case_db"
        assert identity.id == 103, f"Expected id=103, got {identity.id}"
        assert identity.type == "group", f"Expected type='group', got {identity.type}"
        assert (
            identity.display_name == "Circular Group B"
        ), f"Expected 'Circular Group B', got {identity.display_name}"
        assert (
            identity.legal_name is None
        ), f"Expected legal_name=None, got {identity.legal_name}"
        assert identity.aliases == [], f"Expected no aliases, got {identity.aliases}"

    def test_service_handles_circular_identities(self, edge_case_db):
        """CatalogService.get_identity doesn't crash on circular references."""
        service = CatalogService(edge_case_db)
        identity = service.get_identity(102)
        assert identity is not None, "Identity 102 should exist via CatalogService"
        assert identity.id == 102, f"Expected id=102, got {identity.id}"
        assert identity.type == "group", f"Expected type='group', got {identity.type}"
        assert (
            identity.display_name == "Circular Group A"
        ), f"Expected 'Circular Group A', got {identity.display_name}"
        assert (
            identity.legal_name is None
        ), f"Expected legal_name=None, got {identity.legal_name}"

    def test_get_all_identities_with_circular(self, edge_case_db):
        """get_all_identities handles circular groups without crash."""
        service = CatalogService(edge_case_db)
        identities = service.get_all_identities()
        assert (
            len(identities) == 5
        ), f"Expected 5 identities (100-104), got {len(identities)}"
        names = sorted(
            [i.display_name for i in identities if i.display_name is not None]
        )
        assert "Circular Group A" in names, f"Expected 'Circular Group A' in {names}"
        assert "Circular Group B" in names, f"Expected 'Circular Group B' in {names}"
        for identity in identities:
            assert (
                identity.id is not None
            ), f"Expected identity.id to be set, got {identity.id}"
            assert identity.type in (
                "person",
                "group",
                "placeholder",
            ), f"Unexpected type: {identity.type}"


# ===========================================================================
# Song with credit pointing to identity with no primary ArtistName
# ===========================================================================
class TestCreditWithNoIdentityName:
    def test_song_with_no_identity_name_credit(self, edge_case_db):
        """Song 105 has a credit to identity 100 (no primary name)."""
        service = CatalogService(edge_case_db)
        song = service.get_song(105)
        assert song is not None, "Song 105 should exist in edge_case_db"
        assert song.id == 105, f"Expected id=105, got {song.id}"
        assert (
            song.title == "No Identity Name Song"
        ), f"Expected 'No Identity Name Song', got {song.title}"
        assert (
            song.media_name == "No Identity Name Song"
        ), f"Expected 'No Identity Name Song', got {song.media_name}"
        assert (
            song.source_path == "/edge/6"
        ), f"Expected source_path='/edge/6', got {song.source_path}"
        assert (
            song.duration_s == 120.0
        ), f"Expected duration_s=120.0, got {song.duration_ms}"
        assert (
            song.audio_hash is None
        ), f"Expected audio_hash=None, got {song.audio_hash}"
        assert (
            song.processing_status == 1
        ), f"Expected processing_status=1, got {song.processing_status}"
        assert song.is_active is True, f"Expected is_active=True, got {song.is_active}"
        assert song.notes is None, f"Expected notes=None, got {song.notes}"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.year is None, f"Expected year=None, got {song.year}"
        assert song.isrc is None, f"Expected isrc=None, got {song.isrc}"
        assert song.albums == [], f"Expected no albums, got {song.albums}"
        assert song.publishers == [], f"Expected no publishers, got {song.publishers}"
        assert song.tags == [], f"Expected no tags, got {song.tags}"
        assert song.raw_tags == {}, f"Expected no raw_tags, got {song.raw_tags}"
        assert len(song.credits) == 1, f"Expected 1 credit, got {len(song.credits)}"
        credit = song.credits[0]
        assert (
            credit.source_id == 105
        ), f"Expected source_id=105, got {credit.source_id}"
        assert credit.name_id == 300, f"Expected name_id=300, got {credit.name_id}"
        assert (
            credit.identity_id == 100
        ), f"Expected identity_id=100, got {credit.identity_id}"
        assert (
            credit.role_id == 1
        ), f"Expected role_id=1 (Performer), got {credit.role_id}"
        assert (
            credit.role_name == "Performer"
        ), f"Expected role_name='Performer', got {credit.role_name}"
        assert (
            credit.display_name == "Ghost Artist"
        ), f"Expected 'Ghost Artist', got {credit.display_name}"
        assert (
            credit.is_primary is False
        ), f"Expected is_primary=False, got {credit.is_primary}"


# ===========================================================================
# Empty DB Edge Cases
# ===========================================================================
class TestEmptyDbEdgeCases:
    def test_get_song_returns_none(self, empty_db):
        """get_song returns None for non-existent ID on empty DB."""
        service = CatalogService(empty_db)
        result = service.get_song(1)
        assert (
            result is None
        ), f"Expected None for non-existent song on empty DB, got {result}"

    def test_search_songs_slim_returns_empty(self, empty_db):
        """search_songs_slim returns empty list on empty DB."""
        service = CatalogService(empty_db)
        results = service.search_songs_slim("anything")
        assert results == [], f"Expected empty list, got {results}"

    def test_get_all_identities_empty(self, empty_db):
        """get_all_identities returns empty list on empty DB."""
        service = CatalogService(empty_db)
        identities = service.get_all_identities()
        assert identities == [], f"Expected empty list, got {identities}"

    def test_get_all_albums_empty(self, empty_db):
        """get_all_albums returns empty list on empty DB."""
        service = CatalogService(empty_db)
        albums = service.get_all_albums()
        assert albums == [], f"Expected empty list, got {albums}"

    def test_get_all_publishers_empty(self, empty_db):
        """get_all_publishers returns empty list on empty DB."""
        service = CatalogService(empty_db)
        publishers = service.get_all_publishers()
        assert publishers == [], f"Expected empty list, got {publishers}"

    def test_search_albums_empty(self, empty_db):
        """search_albums_slim returns empty list on empty DB."""
        service = CatalogService(empty_db)
        results = service.search_albums_slim("anything")
        assert results == [], f"Expected empty list, got {results}"

    def test_search_publishers_empty(self, empty_db):
        """search_publishers returns empty list on empty DB."""
        service = CatalogService(empty_db)
        results = service.search_publishers("anything")
        assert results == [], f"Expected empty list, got {results}"

    def test_search_identities_empty(self, empty_db):
        """search_identities returns empty list on empty DB."""
        service = CatalogService(empty_db)
        results = service.search_identities("anything")
        assert results == [], f"Expected empty list, got {results}"


# ===========================================================================
# Populated DB: Songs with no album
# ===========================================================================
class TestSongsWithNoAlbum:
    def test_song_without_album_has_empty_albums(self, populated_db):
        """Song 3 (Range Rover Bitch) has no album association."""
        service = CatalogService(populated_db)
        song = service.get_song(3)
        assert song is not None, "Song 3 should exist in populated_db"
        assert song.id == 3, f"Expected id=3, got {song.id}"
        assert (
            song.title == "Range Rover Bitch"
        ), f"Expected 'Range Rover Bitch', got {song.title}"
        assert (
            song.media_name == "Range Rover Bitch"
        ), f"Expected 'Range Rover Bitch', got {song.media_name}"
        assert (
            song.source_path == "/path/3"
        ), f"Expected source_path='/path/3', got {song.source_path}"
        assert (
            song.duration_s == 180.0
        ), f"Expected duration_s=180.0, got {song.duration_ms}"
        assert (
            song.audio_hash is None
        ), f"Expected audio_hash=None, got {song.audio_hash}"
        assert (
            song.processing_status == 0
        ), f"Expected processing_status=0, got {song.processing_status}"
        assert song.is_active is True, f"Expected is_active=True, got {song.is_active}"
        assert song.notes is None, f"Expected notes=None, got {song.notes}"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.year == 2016, f"Expected year=2016, got {song.year}"
        assert song.isrc is None, f"Expected isrc=None, got {song.isrc}"
        assert song.albums == [], f"Expected no albums, got {song.albums}"
        assert song.publishers == [], f"Expected no publishers, got {song.publishers}"
        assert song.tags == [], f"Expected no tags, got {song.tags}"
        assert song.raw_tags == {}, f"Expected no raw_tags, got {song.raw_tags}"
        assert len(song.credits) == 1, f"Expected 1 credit, got {len(song.credits)}"
        credit = song.credits[0]
        assert (
            credit.display_name == "Taylor Hawkins"
        ), f"Expected 'Taylor Hawkins', got {credit.display_name}"
        assert (
            credit.role_name == "Performer"
        ), f"Expected role_name='Performer', got {credit.role_name}"
        assert credit.role_id == 1, f"Expected role_id=1, got {credit.role_id}"
        assert credit.name_id == 40, f"Expected name_id=40, got {credit.name_id}"
        assert (
            credit.identity_id == 4
        ), f"Expected identity_id=4, got {credit.identity_id}"
        assert (
            credit.is_primary is True
        ), f"Expected is_primary=True, got {credit.is_primary}"

    def test_song_without_publisher_has_empty_publishers(self, populated_db):
        """Song 2 (Everlong) has no recording publisher."""
        service = CatalogService(populated_db)
        song = service.get_song(2)
        assert song is not None, "Song 2 should exist in populated_db"
        assert song.id == 2, f"Expected id=2, got {song.id}"
        assert song.title == "Everlong", f"Expected 'Everlong', got {song.title}"
        assert (
            song.media_name == "Everlong"
        ), f"Expected 'Everlong', got {song.media_name}"
        assert (
            song.source_path == "/path/2"
        ), f"Expected source_path='/path/2', got {song.source_path}"
        assert (
            song.duration_s == 240.0
        ), f"Expected duration_s=240.0, got {song.duration_ms}"
        assert (
            song.audio_hash is None
        ), f"Expected audio_hash=None, got {song.audio_hash}"
        assert (
            song.processing_status == 0
        ), f"Expected processing_status=0, got {song.processing_status}"
        assert song.is_active is True, f"Expected is_active=True, got {song.is_active}"
        assert song.notes is None, f"Expected notes=None, got {song.notes}"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.year == 1997, f"Expected year=1997, got {song.year}"
        assert song.isrc is None, f"Expected isrc=None, got {song.isrc}"
        assert song.publishers == [], f"Expected no publishers, got {song.publishers}"
        assert len(song.tags) == 2, f"Expected 2 tags on Song 2 (90s, Rock), got {len(song.tags)}"
        tag = song.tags[0]
        assert tag.id == 3, f"Expected tag id=3, got {tag.id}"
        assert tag.name == "90s", f"Expected tag name='90s', got {tag.name}"
        assert tag.category == "Era", f"Expected tag category='Era', got {tag.category}"
        assert (
            tag.is_primary is False
        ), f"Expected is_primary=False, got {tag.is_primary}"
        assert song.raw_tags == {}, f"Expected no raw_tags, got {song.raw_tags}"


# ===========================================================================
# Populated DB: Non-existent IDs
# ===========================================================================
class TestNonExistentIds:
    def test_song_not_found(self, populated_db):
        """get_song returns None for non-existent ID."""
        service = CatalogService(populated_db)
        result = service.get_song(999)
        assert result is None, f"Expected None for non-existent song 999, got {result}"

    def test_identity_not_found(self, populated_db):
        """get_identity returns None for non-existent ID."""
        service = CatalogService(populated_db)
        result = service.get_identity(999)
        assert (
            result is None
        ), f"Expected None for non-existent identity 999, got {result}"

    def test_album_not_found(self, populated_db):
        """get_album returns None for non-existent ID."""
        service = CatalogService(populated_db)
        result = service.get_album(999)
        assert result is None, f"Expected None for non-existent album 999, got {result}"

    def test_publisher_not_found(self, populated_db):
        """get_publisher returns None for non-existent ID."""
        service = CatalogService(populated_db)
        result = service.get_publisher(999)
        assert (
            result is None
        ), f"Expected None for non-existent publisher 999, got {result}"


# ===========================================================================
# Repository/Domain Coverage: Misc (Migrated from test_coverage_gap.py)
# ===========================================================================
class TestGeneralEdgeCases:
    def test_repositories_empty_inputs(self, populated_db):
        """Repo coverage: Empty inputs return empty results."""
        from src.data.song_repository import SongRepository
        from src.data.song_credit_repository import SongCreditRepository
        from src.data.song_album_repository import SongAlbumRepository
        from src.data.publisher_repository import PublisherRepository
        from src.data.tag_repository import TagRepository

        db = populated_db
        assert (
            SongRepository(db).get_by_ids([]) == []
        ), "Expected empty list from get_by_ids([])"
        assert (
            SongCreditRepository(db).get_credits_for_songs([]) == []
        ), "Expected empty list from get_credits_for_songs([])"
        assert (
            SongAlbumRepository(db).get_albums_for_songs([]) == []
        ), "Expected empty list from get_albums_for_songs([])"
        assert (
            PublisherRepository(db).get_publishers_for_songs([]) == []
        ), "Expected empty list from get_publishers_for_songs([])"
        assert (
            PublisherRepository(db).get_publishers_for_albums([]) == []
        ), "Expected empty list from get_publishers_for_albums([])"
        assert (
            TagRepository(db).get_tags_for_songs([]) == []
        ), "Expected empty list from get_tags_for_songs([])"

    def test_song_display_artist_composer_only(self, populated_db):
        """Domain coverage: Song with credits but NO performers returns None."""
        from src.services.catalog_service import CatalogService
        from src.models.view_models import SongView

        conn = _connect(populated_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration, ProcessingStatus) VALUES (99, 1, 'Composer Only', '/path/99', 100, 0)"
        )
        cursor.execute("INSERT INTO Songs (SourceID) VALUES (99)")
        cursor.execute(
            "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (99, 10, 2)"
        )
        conn.commit()
        conn.close()

        service = CatalogService(populated_db)
        song = service.get_song(99)
        assert song is not None, "Song 99 should exist after insert"
        assert song.id == 99, f"Expected id=99, got {song.id}"
        assert (
            song.title == "Composer Only"
        ), f"Expected 'Composer Only', got {song.title}"
        assert (
            song.media_name == "Composer Only"
        ), f"Expected 'Composer Only', got {song.media_name}"
        assert (
            song.source_path == "/path/99"
        ), f"Expected source_path='/path/99', got {song.source_path}"
        assert (
            song.duration_s == 100.0
        ), f"Expected duration_s=100.0, got {song.duration_ms}"
        assert (
            song.audio_hash is None
        ), f"Expected audio_hash=None, got {song.audio_hash}"
        assert (
            song.is_active is False
        ), f"Expected is_active=False, got {song.is_active}"
        assert song.notes is None, f"Expected notes=None, got {song.notes}"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.year is None, f"Expected year=None, got {song.year}"
        assert song.isrc is None, f"Expected isrc=None, got {song.isrc}"
        assert song.albums == [], f"Expected no albums, got {song.albums}"
        assert song.publishers == [], f"Expected no publishers, got {song.publishers}"
        assert song.tags == [], f"Expected no tags, got {song.tags}"
        assert song.raw_tags == {}, f"Expected no raw_tags, got {song.raw_tags}"
        assert len(song.credits) == 1, f"Expected 1 credit, got {len(song.credits)}"
        credit = song.credits[0]
        assert (
            credit.role_name == "Composer"
        ), f"Expected role_name='Composer', got {credit.role_name}"
        assert (
            credit.display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got {credit.display_name}"
        assert credit.role_id == 2, f"Expected role_id=2, got {credit.role_id}"
        assert credit.name_id == 10, f"Expected name_id=10, got {credit.name_id}"
        assert (
            credit.identity_id == 1
        ), f"Expected identity_id=1, got {credit.identity_id}"
        assert (
            credit.is_primary is True
        ), f"Expected is_primary=True (primary stage name), got {credit.is_primary}"
        view = SongView.from_domain(song)
        assert (
            view.display_artist is None
        ), f"Expected display_artist=None (no Performers), got {view.display_artist}"

    def test_song_credit_repository_integrity_failure_mock(self, populated_db):
        """Repo coverage: NULL RoleID raises ValueError."""
        from src.data.song_credit_repository import SongCreditRepository
        import pytest

        repo = SongCreditRepository(populated_db)
        mock_row = {
            "SourceID": 1,
            "CreditedNameID": 10,
            "RoleID": None,
            "RoleName": "P",
            "DisplayName": "D",
            "IsPrimaryName": 1,
        }
        with pytest.raises(ValueError) as excinfo:
            repo._row_to_song_credit(mock_row)
        assert "RoleID cannot be NULL" in str(
            excinfo.value
        ), f"Expected 'RoleID cannot be NULL' in error, got {excinfo.value}"
