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

from src.services.catalog_service import CatalogService


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
    """Single-delete behaviour: pass [tag_id]."""

    def test_unlinked_tag_is_deleted(self, populated_db):
        """An orphan tag passed as a single-item list is soft-deleted. Returns 1."""
        _insert_orphan_tag(populated_db, 100, "Orphan", "Test")
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([100])

        assert result == 1, f"Expected 1 deleted, got {result}"

    def test_deleted_tag_is_hidden_from_get_tag(self, populated_db):
        """After deletion, get_tag returns None for the deleted tag."""
        _insert_orphan_tag(populated_db, 100, "Orphan", "Test")
        service = CatalogService(populated_db)

        service.delete_unlinked_tags([100])

        assert service.get_tag(100) is None, (
            "Expected get_tag to return None after deletion"
        )

    def test_linked_tag_is_not_deleted(self, populated_db):
        """A tag with active song links returns 0 — not deleted."""
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([1])  # Grunge -> Song 1, Song 9

        assert result == 0, f"Expected 0 (linked tag rejected), got {result}"

    def test_linked_tag_remains_in_db(self, populated_db):
        """A linked tag must still exist after a failed delete attempt."""
        service = CatalogService(populated_db)

        service.delete_unlinked_tags([1])

        tag = service.get_tag(1)
        assert tag is not None, "Expected linked tag to remain after rejected delete"
        assert tag.name == "Grunge", f"Expected 'Grunge', got '{tag.name}'"

    def test_nonexistent_tag_returns_zero(self, populated_db):
        """A tag ID that doesn't exist returns 0."""
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([9999])

        assert result == 0, f"Expected 0 for nonexistent tag, got {result}"

    def test_tag_linked_only_to_deleted_song_is_deletable(self, populated_db):
        """A tag whose only song is soft-deleted counts as unlinked — delete succeeds."""
        service = CatalogService(populated_db)

        # Tag 3 (90s) is only on Song 2 — soft-delete Song 2 first
        service.delete_song(2)

        result = service.delete_unlinked_tags([3])

        assert result == 1, (
            f"Expected 1 (tag unlinked after song deleted), got {result}"
        )


class TestDeleteUnlinkedTagsBulk:
    """Bulk behaviour: pass multiple IDs."""

    def test_bulk_deletes_all_orphans_in_list(self, populated_db):
        """All orphan IDs in the list are deleted. Returns count."""
        _insert_orphan_tag(populated_db, 100, "Orphan A", "Test")
        _insert_orphan_tag(populated_db, 101, "Orphan B", "Test")
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([100, 101])

        assert result == 2, f"Expected 2 deleted, got {result}"
        assert service.get_tag(100) is None, "Expected tag 100 to be deleted"
        assert service.get_tag(101) is None, "Expected tag 101 to be deleted"

    def test_bulk_skips_linked_tags_in_list(self, populated_db):
        """Mixed list: orphans deleted, linked tags skipped. Returns only orphan count."""
        _insert_orphan_tag(populated_db, 100, "Orphan", "Test")
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([100, 1])  # 100=orphan, 1=Grunge (linked)

        assert result == 1, f"Expected 1 deleted (orphan only), got {result}"
        assert service.get_tag(1) is not None, "Expected linked tag 1 to survive"
        assert service.get_tag(100) is None, "Expected orphan tag 100 to be deleted"

    def test_bulk_empty_list_returns_zero(self, populated_db):
        """Empty list is a no-op. Returns 0."""
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([])

        assert result == 0, f"Expected 0 for empty list, got {result}"

    def test_bulk_all_linked_returns_zero(self, populated_db):
        """All tags in list are linked — nothing deleted."""
        service = CatalogService(populated_db)

        result = service.delete_unlinked_tags([1, 2, 3])

        assert result == 0, f"Expected 0 (all linked), got {result}"


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
    """CatalogService.delete_unlinked_albums"""

    def test_unlinked_album_is_deleted(self, populated_db):
        _insert_orphan_album(populated_db, 999, "Orphan Album")
        service = CatalogService(populated_db)
        result = service.delete_unlinked_albums([999])
        assert result == 1

    def test_deleted_album_hidden_from_get_album(self, populated_db):
        _insert_orphan_album(populated_db, 999, "Orphan Album")
        service = CatalogService(populated_db)
        service.delete_unlinked_albums([999])
        assert service.get_album(999) is None

    def test_linked_album_is_not_deleted(self, populated_db):
        service = CatalogService(populated_db)
        result = service.delete_unlinked_albums([100])  # Nevermind -> Song 1
        assert result == 0

    def test_linked_album_remains_in_db(self, populated_db):
        service = CatalogService(populated_db)
        service.delete_unlinked_albums([100])
        album = service.get_album(100)
        assert album is not None
        assert album.title == "Nevermind"

    def test_nonexistent_album_returns_zero(self, populated_db):
        service = CatalogService(populated_db)
        result = service.delete_unlinked_albums([9999])
        assert result == 0

    def test_album_linked_only_to_deleted_song_is_deletable(self, populated_db):
        service = CatalogService(populated_db)
        service.delete_song(1)  # soft-delete Song 1 (the only song on album 100)
        result = service.delete_unlinked_albums([100])
        assert result == 1

    def test_delete_album_purges_album_credits(self, populated_db):
        from src.data.album_repository import AlbumRepository

        service = CatalogService(populated_db)
        service.delete_song(1)
        service.delete_unlinked_albums([100])
        repo = AlbumRepository(populated_db)
        with repo._get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM AlbumCredits WHERE AlbumID = 100"
            ).fetchone()[0]
        assert count == 0

    def test_delete_album_purges_album_publishers(self, populated_db):
        from src.data.album_repository import AlbumRepository

        service = CatalogService(populated_db)
        service.delete_song(1)
        service.delete_unlinked_albums([100])
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
        result = service.delete_unlinked_albums([997, 998])
        assert result == 2
        assert service.get_album(997) is None
        assert service.get_album(998) is None

    def test_bulk_skips_linked_albums(self, populated_db):
        _insert_orphan_album(populated_db, 999, "Orphan")
        service = CatalogService(populated_db)
        result = service.delete_unlinked_albums([999, 100])  # 999=orphan, 100=linked
        assert result == 1
        assert service.get_album(100) is not None
        assert service.get_album(999) is None

    def test_bulk_empty_list_returns_zero(self, populated_db):
        service = CatalogService(populated_db)
        assert service.delete_unlinked_albums([]) == 0


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
    """CatalogService.delete_unlinked_publishers"""

    def test_publisher_with_no_links_is_deleted(self, populated_db):
        _insert_orphan_publisher(populated_db, 999, "Orphan Publisher")
        service = CatalogService(populated_db)
        result = service.delete_unlinked_publishers([999])
        assert result == 1

    def test_deleted_publisher_hidden_from_get_publisher(self, populated_db):
        _insert_orphan_publisher(populated_db, 999, "Orphan Publisher")
        service = CatalogService(populated_db)
        service.delete_unlinked_publishers([999])
        assert service.get_publisher(999) is None

    def test_publisher_linked_to_active_song_is_rejected(self, populated_db):
        service = CatalogService(populated_db)
        result = service.delete_unlinked_publishers([10])  # DGC -> song 1
        assert result == 0

    def test_publisher_linked_to_active_album_is_rejected(self, populated_db):
        service = CatalogService(populated_db)
        result = service.delete_unlinked_publishers([4])  # Roswell -> album 200
        assert result == 0

    def test_publisher_linked_to_deleted_song_and_deleted_album_is_deletable(
        self, populated_db
    ):
        # DGC (10) is on song 1 and album 100. Delete both, then publisher should be deletable.
        service = CatalogService(populated_db)
        service.delete_song(1)
        # Now delete album 100 (song 1 was its only song)
        service.delete_unlinked_albums([100])
        result = service.delete_unlinked_publishers([10])
        assert result == 1

    def test_nonexistent_publisher_returns_zero(self, populated_db):
        service = CatalogService(populated_db)
        result = service.delete_unlinked_publishers([9999])
        assert result == 0

    def test_bulk_deletes_orphan_publishers(self, populated_db):
        _insert_orphan_publisher(populated_db, 997, "Orphan A")
        _insert_orphan_publisher(populated_db, 998, "Orphan B")
        service = CatalogService(populated_db)
        result = service.delete_unlinked_publishers([997, 998])
        assert result == 2

    def test_bulk_skips_publishers_with_song_links(self, populated_db):
        _insert_orphan_publisher(populated_db, 999, "Orphan")
        service = CatalogService(populated_db)
        result = service.delete_unlinked_publishers([999, 10])  # 10=DGC (song link)
        assert result == 1
        assert service.get_publisher(10) is not None

    def test_bulk_skips_publishers_with_album_links(self, populated_db):
        _insert_orphan_publisher(populated_db, 999, "Orphan")
        service = CatalogService(populated_db)
        result = service.delete_unlinked_publishers([999, 4])  # 4=Roswell (album link)
        assert result == 1
        assert service.get_publisher(4) is not None

    def test_bulk_empty_list_returns_zero(self, populated_db):
        service = CatalogService(populated_db)
        assert service.delete_unlinked_publishers([]) == 0


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


class TestDeleteUnlinkedIdentities:
    """CatalogService.delete_unlinked_identities"""

    def test_identity_with_no_links_is_deleted(self, populated_db):
        _insert_orphan_identity(populated_db, 999)
        service = CatalogService(populated_db)
        result = service.delete_unlinked_identities([999])
        assert result == 1

    def test_deleted_identity_hidden_from_get_identity(self, populated_db):
        _insert_orphan_identity(populated_db, 999)
        service = CatalogService(populated_db)
        service.delete_unlinked_identities([999])
        assert service.get_identity(999) is None

    def test_identity_with_active_song_via_primary_alias_is_rejected(
        self, populated_db
    ):
        # Nirvana (2) is credited on song 1 via NameID=20
        service = CatalogService(populated_db)
        result = service.delete_unlinked_identities([2])
        assert result == 0

    def test_identity_with_active_song_via_secondary_alias_is_rejected(
        self, populated_db
    ):
        # Dave Grohl (1) credited on song 4 via Grohlton alias (NameID=11)
        service = CatalogService(populated_db)
        result = service.delete_unlinked_identities([1])
        assert result == 0

    def test_identity_with_active_album_credit_is_rejected(self, populated_db):
        # Foo Fighters (3) has an AlbumCredit on album 200 (active)
        # First delete all song links so only album link remains
        service = CatalogService(populated_db)
        service.delete_song(2)  # Remove song 2 (Foo Fighters' song)
        result = service.delete_unlinked_identities([3])
        assert result == 0

    def test_identity_linked_only_to_deleted_songs_is_deletable(self, populated_db):
        # Nirvana (2): only song is song 1, no album credit (album 100 credit blocks it until album deleted)
        # Delete song 1 first, then delete album 100, then Nirvana should be deletable
        service = CatalogService(populated_db)
        service.delete_song(1)
        service.delete_unlinked_albums([100])
        result = service.delete_unlinked_identities([2])
        assert result == 1

    def test_delete_identity_soft_deletes_all_aliases(self, populated_db):
        from src.data.identity_repository import IdentityRepository

        _insert_orphan_identity(populated_db, 999)
        service = CatalogService(populated_db)
        service.delete_unlinked_identities([999])
        repo = IdentityRepository(populated_db)
        with repo._get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM ArtistNames WHERE OwnerIdentityID = 999 AND IsDeleted = 0"
            ).fetchone()[0]
        assert count == 0

    def test_bulk_deletes_orphan_identities(self, populated_db):
        _insert_orphan_identity(populated_db, 997)
        _insert_orphan_identity(populated_db, 998)
        service = CatalogService(populated_db)
        result = service.delete_unlinked_identities([997, 998])
        assert result == 2

    def test_bulk_skips_linked_identities(self, populated_db):
        _insert_orphan_identity(populated_db, 999)
        service = CatalogService(populated_db)
        result = service.delete_unlinked_identities([999, 2])  # 2=Nirvana (linked)
        assert result == 1
        assert service.get_identity(2) is not None
        assert service.get_identity(999) is None

    def test_bulk_empty_list_returns_zero(self, populated_db):
        service = CatalogService(populated_db)
        assert service.delete_unlinked_identities([]) == 0
