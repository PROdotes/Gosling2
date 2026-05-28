"""
Tests for CatalogService orphan deletion — Tags (Step 1), Albums (Step 2),
Publishers (Step 3), Identities (Step 4)
=========================================================
delete_unlinked_tags(tag_ids: List[int]) -> int

populated_db tags:
  TagID=1: Grunge/Genre    -> Song 1 (primary), Song 9 (not primary)
  TagID=2: Energetic/Mood  -> Song 1
  TagID=3: 90s/Era         -> Song 2
  TagID=4: Electronic/Style -> Song 4
  TagID=5: English/Jezik   -> Song 1
  TagID=6: Alt Rock/Genre  -> Song 9 (primary)
  Song 7: no tags

Orphan tags (zero active song links): none in populated_db by default.
Tests that need an orphan insert one directly via SQL.
"""

import pytest
from src.services.catalog_service import CatalogService
from src.services.mutation_coordinator import MutationCoordinator
from src.engine.routers.mutation_models import (
    MutationRequest,
    DeleteSongItem,
    DeleteTagItem,
    DeleteAlbumItem,
    DeletePublisherItem,
)


def _coord(db_path):
    return MutationCoordinator(db_path)


def _delete_song(db_path, song_id):
    _coord(db_path).apply(
        MutationRequest(delete=[DeleteSongItem(type="song", id=song_id)])
    )


def _delete_tag(db_path, tag_id):
    _coord(db_path).apply(
        MutationRequest(delete=[DeleteTagItem(type="tag", id=tag_id)])
    )


def _delete_album(db_path, album_id):
    _coord(db_path).apply(
        MutationRequest(delete=[DeleteAlbumItem(type="album", id=album_id)])
    )


def _delete_publisher(db_path, publisher_id):
    _coord(db_path).apply(
        MutationRequest(delete=[DeletePublisherItem(type="publisher", id=publisher_id)])
    )


def _insert_orphan_tag(db_path: str, tag_id: int, name: str, category: str) -> None:
    """Insert a tag with no MediaSourceTags links."""
    from src.data.tag_repository import TagRepository

    repo = TagRepository(db_path)
    with repo._get_connection() as conn:
        conn.execute(
            "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (?, ?, ?)",
            (tag_id, name, category),
        )
        conn.commit()


class TestDeleteUnlinkedTagsSingle:
    """Single tag delete via MutationCoordinator."""

    def test_unlinked_tag_is_deleted(self, populated_db):
        """An orphan tag is soft-deleted successfully."""
        _insert_orphan_tag(populated_db, 100, "Orphan", "Test")
        service = CatalogService(populated_db)

        _delete_tag(populated_db, 100)

        assert (
            service.get_tag(100) is None
        ), "Expected get_tag to return None after deletion"

    def test_linked_tag_raises(self, populated_db):
        """A tag with active song links raises ValueError."""
        with pytest.raises(ValueError):
            _delete_tag(populated_db, 1)  # Grunge -> Song 1, Song 9

    def test_linked_tag_remains_in_db(self, populated_db):
        """A linked tag must still exist after a failed delete attempt."""
        service = CatalogService(populated_db)

        with pytest.raises(ValueError):
            _delete_tag(populated_db, 1)

        tag = service.get_tag(1)
        assert tag is not None, "Expected linked tag to remain after rejected delete"
        assert tag.name == "Grunge", f"Expected 'Grunge', got '{tag.name}'"

    def test_nonexistent_tag_raises(self, populated_db):
        """A tag ID that doesn't exist raises LookupError."""
        with pytest.raises(LookupError):
            _delete_tag(populated_db, 9999)

    def test_tag_linked_only_to_deleted_song_is_deletable(self, populated_db):
        """A tag whose only song is soft-deleted counts as unlinked — delete succeeds."""
        service = CatalogService(populated_db)

        _delete_song(populated_db, 2)  # Tag 3 (90s) is only on Song 2

        _delete_tag(populated_db, 3)

        assert (
            service.get_tag(3) is None
        ), "Expected tag 3 deleted after its only song was removed"


class TestDeleteUnlinkedTagsBulk:
    """Multiple tag deletions via MutationCoordinator."""

    def test_bulk_deletes_all_orphans(self, populated_db):
        """Multiple orphan tags can be deleted in sequence."""
        _insert_orphan_tag(populated_db, 100, "Orphan A", "Test")
        _insert_orphan_tag(populated_db, 101, "Orphan B", "Test")
        service = CatalogService(populated_db)

        _delete_tag(populated_db, 100)
        _delete_tag(populated_db, 101)

        assert service.get_tag(100) is None, "Expected tag 100 to be deleted"
        assert service.get_tag(101) is None, "Expected tag 101 to be deleted"

    def test_orphan_deleted_linked_preserved(self, populated_db):
        """Orphan tag deleted; linked tag raises and remains."""
        _insert_orphan_tag(populated_db, 100, "Orphan", "Test")
        service = CatalogService(populated_db)

        _delete_tag(populated_db, 100)
        with pytest.raises(ValueError):
            _delete_tag(populated_db, 1)  # Grunge (linked)

        assert service.get_tag(1) is not None, "Expected linked tag 1 to survive"
        assert service.get_tag(100) is None, "Expected orphan tag 100 to be deleted"

    def test_all_linked_raises(self, populated_db):
        """All linked tags raise ValueError."""
        with pytest.raises(ValueError):
            _delete_tag(populated_db, 1)
        with pytest.raises(ValueError):
            _delete_tag(populated_db, 2)
        with pytest.raises(ValueError):
            _delete_tag(populated_db, 3)


# ---------------------------------------------------------------------------
# Step 2: Albums
# ---------------------------------------------------------------------------
# populated_db albums:
#   AlbumID=100: "Nevermind"               -> Song 1 (Track 1)
#   AlbumID=200: "The Colour and the Shape" -> Song 2 (Track 11)
#   Publishers on 100: DGC(10), Sub Pop(5)   Credits on 100: Nirvana(NameID=20)
#   Publishers on 200: Roswell(4)            Credits on 200: Foo Fighters(NameID=30)
# Orphan albums: none by default — insert via SQL.


def _insert_orphan_album(db_path: str, album_id: int, title: str) -> None:
    """Insert an album with no SongAlbums links."""
    from src.data.album_repository import AlbumRepository

    repo = AlbumRepository(db_path)
    with repo._get_connection() as conn:
        conn.execute(
            "INSERT INTO Albums (AlbumID, AlbumTitle, ReleaseYear) VALUES (?, ?, 2000)",
            (album_id, title),
        )
        conn.commit()


class TestDeleteUnlinkedAlbums:
    """Album delete via MutationCoordinator."""

    def test_unlinked_album_is_deleted(self, populated_db):
        _insert_orphan_album(populated_db, 999, "Orphan Album")
        service = CatalogService(populated_db)
        _delete_album(populated_db, 999)
        assert service.get_album(999) is None

    def test_linked_album_raises(self, populated_db):
        with pytest.raises(ValueError):
            _delete_album(populated_db, 100)  # Nevermind -> Song 1

    def test_linked_album_remains_in_db(self, populated_db):
        service = CatalogService(populated_db)
        with pytest.raises(ValueError):
            _delete_album(populated_db, 100)
        album = service.get_album(100)
        assert album is not None
        assert album.title == "Nevermind"

    def test_nonexistent_album_raises(self, populated_db):
        with pytest.raises(LookupError):
            _delete_album(populated_db, 9999)

    def test_album_linked_only_to_deleted_song_is_deletable(self, populated_db):
        service = CatalogService(populated_db)
        _delete_song(populated_db, 1)
        _delete_album(populated_db, 100)
        assert service.get_album(100) is None

    def test_delete_album_purges_album_credits(self, populated_db):
        from src.data.album_repository import AlbumRepository

        _delete_song(populated_db, 1)
        _delete_album(populated_db, 100)
        repo = AlbumRepository(populated_db)
        with repo._get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM AlbumCredits WHERE AlbumID = 100"
            ).fetchone()[0]
        assert count == 0

    def test_delete_album_purges_album_publishers(self, populated_db):
        from src.data.album_repository import AlbumRepository

        _delete_song(populated_db, 1)
        _delete_album(populated_db, 100)
        repo = AlbumRepository(populated_db)
        with repo._get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM AlbumPublishers WHERE AlbumID = 100"
            ).fetchone()[0]
        assert count == 0

    def test_bulk_deletes_all_orphan_albums(self, populated_db):
        _insert_orphan_album(populated_db, 997, "Orphan A")
        _insert_orphan_album(populated_db, 998, "Orphan B")
        service = CatalogService(populated_db)
        _delete_album(populated_db, 997)
        _delete_album(populated_db, 998)
        assert service.get_album(997) is None
        assert service.get_album(998) is None

    def test_orphan_deleted_linked_preserved(self, populated_db):
        _insert_orphan_album(populated_db, 999, "Orphan")
        service = CatalogService(populated_db)
        _delete_album(populated_db, 999)
        with pytest.raises(ValueError):
            _delete_album(populated_db, 100)
        assert service.get_album(100) is not None
        assert service.get_album(999) is None


# ---------------------------------------------------------------------------
# Step 3: Publishers
# ---------------------------------------------------------------------------
# populated_db publishers:
#   1: Universal Music Group  — no direct song/album links
#   2: Island Records         — no direct links (parent=1)
#   3: Island Def Jam         — no direct links (parent=2)
#   4: Roswell Records        — AlbumPublishers: album 200
#   5: Sub Pop                — AlbumPublishers: album 100
#  10: DGC Records            — RecordingPublishers: song 1; AlbumPublishers: album 100


def _insert_orphan_publisher(db_path: str, publisher_id: int, name: str) -> None:
    """Insert a publisher with no song or album links."""
    from src.data.publisher_repository import PublisherRepository

    repo = PublisherRepository(db_path)
    with repo._get_connection() as conn:
        conn.execute(
            "INSERT INTO Publishers (PublisherID, PublisherName) VALUES (?, ?)",
            (publisher_id, name),
        )
        conn.commit()


class TestDeleteUnlinkedPublishers:
    """Publisher delete via MutationCoordinator."""

    def test_publisher_with_no_links_is_deleted(self, populated_db):
        _insert_orphan_publisher(populated_db, 999, "Orphan Publisher")
        service = CatalogService(populated_db)
        _delete_publisher(populated_db, 999)
        assert service.get_publisher(999) is None

    def test_publisher_linked_to_active_song_raises(self, populated_db):
        with pytest.raises(ValueError):
            _delete_publisher(populated_db, 10)  # DGC -> song 1

    def test_publisher_linked_to_active_album_raises(self, populated_db):
        with pytest.raises(ValueError):
            _delete_publisher(populated_db, 4)  # Roswell -> album 200

    def test_publisher_linked_to_deleted_song_and_deleted_album_is_deletable(
        self, populated_db
    ):
        service = CatalogService(populated_db)
        _delete_song(populated_db, 1)
        _delete_album(populated_db, 100)
        _delete_publisher(populated_db, 10)
        assert service.get_publisher(10) is None

    def test_nonexistent_publisher_raises(self, populated_db):
        with pytest.raises(LookupError):
            _delete_publisher(populated_db, 9999)

    def test_bulk_deletes_orphan_publishers(self, populated_db):
        _insert_orphan_publisher(populated_db, 997, "Orphan A")
        _insert_orphan_publisher(populated_db, 998, "Orphan B")
        service = CatalogService(populated_db)
        _delete_publisher(populated_db, 997)
        _delete_publisher(populated_db, 998)
        assert service.get_publisher(997) is None
        assert service.get_publisher(998) is None

    def test_orphan_deleted_song_linked_preserved(self, populated_db):
        _insert_orphan_publisher(populated_db, 999, "Orphan")
        service = CatalogService(populated_db)
        _delete_publisher(populated_db, 999)
        with pytest.raises(ValueError):
            _delete_publisher(populated_db, 10)
        assert service.get_publisher(10) is not None

    def test_orphan_deleted_album_linked_preserved(self, populated_db):
        _insert_orphan_publisher(populated_db, 999, "Orphan")
        service = CatalogService(populated_db)
        _delete_publisher(populated_db, 999)
        with pytest.raises(ValueError):
            _delete_publisher(populated_db, 4)
        assert service.get_publisher(4) is not None


# ---------------------------------------------------------------------------
# Step 4: Identities
# ---------------------------------------------------------------------------
# populated_db identities:
#   1: Dave Grohl (aliases: Dave Grohl/10, Grohlton/11, Late!/12, Ines Prajo/33)
#      Songs via NameID=10: songs 6, 8
#      Songs via NameID=11 (Grohlton): song 4
#      Songs via NameID=12 (Late!): song 5
#   2: Nirvana (alias: NameID=20) — song 1, album 100 credit
#   3: Foo Fighters (alias: NameID=30) — song 2, album 200 credit
#   4: Taylor Hawkins (alias: NameID=40) — songs 3, 6, 8
# Orphan identities: none by default — insert via SQL.


def _insert_orphan_identity(db_path: str, identity_id: int) -> None:
    """Insert an identity with no credits."""
    from src.data.identity_repository import IdentityRepository

    repo = IdentityRepository(db_path)
    with repo._get_connection() as conn:
        conn.execute(
            "INSERT INTO Identities (IdentityID, IdentityType) VALUES (?, 'person')",
            (identity_id,),
        )
        # Give it a primary alias so get_identity can resolve it
        conn.execute(
            "INSERT INTO ArtistNames (OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (?, ?, 1)",
            (identity_id, f"Orphan Artist {identity_id}"),
        )
        conn.commit()
