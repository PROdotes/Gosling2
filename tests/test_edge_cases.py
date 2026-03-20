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


# ===========================================================================
# Identity Fallback Display Names
# ===========================================================================
class TestIdentityFallbacks:
    """Identity display_name fallback: DisplayName -> LegalName -> 'Unknown Artist #ID'."""

    def test_no_artist_name_no_legal_name(self, edge_case_db):
        """Identity 100 has no ArtistName and no LegalName -> fallback to 'Unknown Artist #100'."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(100)
        assert identity is not None
        assert identity.display_name == "Unknown Artist #100"

    def test_legal_name_fallback(self, edge_case_db):
        """Identity 101 has LegalName='John Legal' but no primary ArtistName -> fallback to LegalName."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(101)
        assert identity is not None
        assert identity.display_name == "John Legal"

    def test_unicode_display_name(self, edge_case_db):
        """Identity 104 has display name 'Bjork'."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(104)
        assert identity is not None
        assert identity.display_name == "Bjork"


# ===========================================================================
# Song Edge Cases
# ===========================================================================
class TestSongEdgeCases:
    def test_whitespace_title(self, edge_case_db):
        """Song 101 has title ' ' (single space)."""
        repo = SongRepository(edge_case_db)
        song = repo.get_by_id(101)
        assert song is not None
        assert song.title == " "

    def test_single_char_title(self, edge_case_db):
        """Song 102 has title 'A'."""
        repo = SongRepository(edge_case_db)
        song = repo.get_by_id(102)
        assert song is not None
        assert song.title == "A"

    def test_unicode_title(self, edge_case_db):
        """Song 103 has Japanese characters in title."""
        repo = SongRepository(edge_case_db)
        song = repo.get_by_id(103)
        assert song is not None
        assert song.title == "\u65e5\u672c\u8a9e\u30bd\u30f3\u30b0"

    def test_zero_duration(self, edge_case_db):
        """Song 104 has SourceDuration=0 -> duration_ms=0."""
        repo = SongRepository(edge_case_db)
        song = repo.get_by_id(104)
        assert song is not None
        assert song.duration_ms == 0

    def test_zero_duration_formatted(self, edge_case_db):
        """Zero duration song formatted as '0:00' via SongView."""
        from src.models.view_models import SongView

        service = CatalogService(edge_case_db)
        song = service.get_song(104)
        assert song is not None
        view = SongView.from_domain(song)
        assert view.formatted_duration == "0:00"

    def test_search_unicode_title(self, edge_case_db):
        """Surface search can find unicode title."""
        repo = SongRepository(edge_case_db)
        results = repo.search_surface("\u65e5\u672c\u8a9e")
        assert len(results) == 1
        assert results[0].id == 103

    def test_search_single_char(self, edge_case_db):
        """Surface search with 'A' matches song 102."""
        repo = SongRepository(edge_case_db)
        results = repo.search_surface("A")
        ids = [s.id for s in results]
        assert 102 in ids


# ===========================================================================
# Orphaned Publisher (parent points to non-existent ID)
# ===========================================================================
class TestOrphanedPublisher:
    def test_orphan_publisher_accessible(self, edge_case_db):
        """Publisher 100 has ParentPublisherID=999 which doesn't exist."""
        repo = PublisherRepository(edge_case_db)
        pub = repo.get_by_id(100)
        assert pub is not None
        assert pub.name == "Orphan Publisher"
        assert pub.parent_id == 999
        # parent_name should be None since parent doesn't exist
        assert pub.parent_name is None

    def test_all_publishers_includes_orphan(self, edge_case_db):
        """get_all still returns the orphan publisher."""
        repo = PublisherRepository(edge_case_db)
        pubs = repo.get_all()
        names = [p.name for p in pubs]
        assert "Orphan Publisher" in names


# ===========================================================================
# Circular Group Memberships
# ===========================================================================
class TestCircularMemberships:
    """Groups A and B are members of each other. Should not crash."""

    def test_circular_group_a(self, edge_case_db):
        """Identity 102 (Circular Group A) has member 103 (Circular Group B)."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(102)
        assert identity is not None
        assert identity.display_name == "Circular Group A"

    def test_circular_group_b(self, edge_case_db):
        """Identity 103 (Circular Group B) has member 102 (Circular Group A)."""
        repo = IdentityRepository(edge_case_db)
        identity = repo.get_by_id(103)
        assert identity is not None
        assert identity.display_name == "Circular Group B"

    def test_service_handles_circular_identities(self, edge_case_db):
        """CatalogService.get_identity doesn't crash on circular references."""
        service = CatalogService(edge_case_db)
        # Should not infinite loop or crash
        identity = service.get_identity(102)
        assert identity is not None
        assert identity.display_name == "Circular Group A"

    def test_get_all_identities_with_circular(self, edge_case_db):
        """get_all_identities handles circular groups without crash."""
        service = CatalogService(edge_case_db)
        identities = service.get_all_identities()
        assert len(identities) == 5  # 100, 101, 102, 103, 104
        names = sorted([i.display_name for i in identities])
        assert "Circular Group A" in names
        assert "Circular Group B" in names


# ===========================================================================
# Song with credit pointing to identity with no primary ArtistName
# ===========================================================================
class TestCreditWithNoIdentityName:
    def test_song_with_no_identity_name_credit(self, edge_case_db):
        """Song 105 has a credit to identity 100 (no primary name)."""
        service = CatalogService(edge_case_db)
        song = service.get_song(105)
        assert song is not None
        assert song.title == "No Identity Name Song"
        # The credit should still be there (via ArtistName NameID=300, 'Ghost Artist')
        assert len(song.credits) == 1
        assert song.credits[0].display_name == "Ghost Artist"


# ===========================================================================
# Empty DB Edge Cases
# ===========================================================================
class TestEmptyDbEdgeCases:
    def test_get_song_returns_none(self, empty_db):
        service = CatalogService(empty_db)
        assert service.get_song(1) is None

    def test_search_songs_returns_empty(self, empty_db):
        service = CatalogService(empty_db)
        assert service.search_songs("anything") == []

    def test_get_all_identities_empty(self, empty_db):
        service = CatalogService(empty_db)
        assert service.get_all_identities() == []

    def test_get_all_albums_empty(self, empty_db):
        service = CatalogService(empty_db)
        assert service.get_all_albums() == []

    def test_get_all_publishers_empty(self, empty_db):
        service = CatalogService(empty_db)
        assert service.get_all_publishers() == []

    def test_search_albums_empty(self, empty_db):
        service = CatalogService(empty_db)
        assert service.search_albums("anything") == []

    def test_search_publishers_empty(self, empty_db):
        service = CatalogService(empty_db)
        assert service.search_publishers("anything") == []

    def test_search_identities_empty(self, empty_db):
        service = CatalogService(empty_db)
        assert service.search_identities("anything") == []


# ===========================================================================
# Populated DB: Songs with no album
# ===========================================================================
class TestSongsWithNoAlbum:
    def test_song_without_album_has_empty_albums(self, populated_db):
        """Song 3 (Range Rover Bitch) has no album association."""
        service = CatalogService(populated_db)
        song = service.get_song(3)
        assert song is not None
        assert song.title == "Range Rover Bitch"
        assert song.albums == []

    def test_song_without_publisher_has_empty_publishers(self, populated_db):
        """Song 2 (Everlong) has no recording publisher."""
        service = CatalogService(populated_db)
        song = service.get_song(2)
        assert song is not None
        assert song.publishers == []


# ===========================================================================
# Populated DB: Non-existent IDs
# ===========================================================================
class TestNonExistentIds:
    def test_song_not_found(self, populated_db):
        service = CatalogService(populated_db)
        assert service.get_song(999) is None

    def test_identity_not_found(self, populated_db):
        service = CatalogService(populated_db)
        assert service.get_identity(999) is None

    def test_album_not_found(self, populated_db):
        service = CatalogService(populated_db)
        assert service.get_album(999) is None

    def test_publisher_not_found(self, populated_db):
        service = CatalogService(populated_db)
        assert service.get_publisher(999) is None

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
        assert SongRepository(db).get_by_ids([]) == []
        assert SongCreditRepository(db).get_credits_for_songs([]) == []
        assert SongAlbumRepository(db).get_albums_for_songs([]) == []
        assert PublisherRepository(db).get_publishers_for_songs([]) == []
        assert PublisherRepository(db).get_publishers_for_albums([]) == []
        assert TagRepository(db).get_tags_for_songs([]) == []

    def test_song_display_artist_composer_only(self, populated_db):
        """Domain coverage: Song with credits but NO performers returns None."""
        import sqlite3
        from src.services.catalog_service import CatalogService
        from src.models.view_models import SongView

        # Insert a song with only a Composer
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath, SourceDuration) VALUES (99, 1, 'Composer Only', '/path/99', 100)"
        )
        cursor.execute("INSERT INTO Songs (SourceID) VALUES (99)")
        cursor.execute(
            "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (99, 10, 2)"
        )  # Dave as Composer
        conn.commit()
        conn.close()

        service = CatalogService(populated_db)
        song = service.get_song(99)
        assert song is not None
        view = SongView.from_domain(song)
        assert view.display_artist is None

    def test_song_credit_repository_integrity_failure_mock(self, populated_db):
        """Repo coverage: Mocked DB integrity error for NULL RoleID."""
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
        assert "RoleID cannot be NULL" in str(excinfo.value)
