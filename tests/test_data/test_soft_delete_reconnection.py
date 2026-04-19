"""
Tests for Soft-Delete Reconnection (Upsert Wake-Up)
====================================================
When an entity is soft-deleted (IsDeleted=1) and then re-ingested,
the insert logic must reconnect (SET IsDeleted=0) instead of creating a duplicate.

Each test follows the pattern:
    1. Soft-delete an entity (UPDATE SET IsDeleted = 1)
    2. Re-insert via the normal get-or-create path
    3. Assert: same row ID reused, IsDeleted flipped back to 0, no duplicates

Uses populated_db and empty_db fixtures from conftest.py.
"""

import sqlite3
from tests.conftest import _connect
from src.data.tag_repository import TagRepository
from src.data.publisher_repository import PublisherRepository
from src.data.song_credit_repository import SongCreditRepository
from src.data.song_album_repository import SongAlbumRepository
from src.models.domain import Tag, Publisher, SongCredit, SongAlbum, AlbumCredit


class TestTagReconnection:
    """TagRepository.insert_tags must wake up soft-deleted tags."""

    def test_soft_deleted_tag_is_reconnected_not_duplicated(self, populated_db):
        """
        Grunge/Genre (TagID=1) exists in populated_db.
        Soft-delete it, then re-insert onto Song 7.
        Should reuse TagID=1 with IsDeleted=0, not create TagID=7.
        """
        repo = TagRepository(populated_db)

        # 1. Soft-delete Grunge
        conn = _connect(populated_db)
        conn.execute("UPDATE Tags SET IsDeleted = 1 WHERE TagID = 1")
        conn.commit()
        conn.close()

        # 2. Re-insert via normal path
        tags = [Tag(name="Grunge", category="Genre")]
        with repo._get_connection() as conn:
            repo.insert_tags(7, tags, conn)
            conn.commit()

        # 3. Assert reconnection
        conn = _connect(populated_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT TagID, IsDeleted FROM Tags WHERE TagName = 'Grunge' AND TagCategory = 'Genre'"
        ).fetchall()
        conn.close()

        assert len(rows) == 1, f"Expected 1 Grunge/Genre row (reused), got {len(rows)}"
        assert (
            rows[0]["TagID"] == 1
        ), f"Expected TagID=1 (original), got {rows[0]['TagID']}"
        assert (
            rows[0]["IsDeleted"] == 0
        ), f"Expected IsDeleted=0 (woken up), got {rows[0]['IsDeleted']}"

    def test_soft_deleted_tag_case_insensitive_reconnection(self, populated_db):
        """
        Soft-delete 'Grunge'/Genre (TagID=1), then re-insert as 'grunge'/Genre.
        Case-insensitive match should still reconnect.
        """
        repo = TagRepository(populated_db)

        conn = _connect(populated_db)
        conn.execute("UPDATE Tags SET IsDeleted = 1 WHERE TagID = 1")
        conn.commit()
        conn.close()

        tags = [Tag(name="grunge", category="Genre")]
        with repo._get_connection() as conn:
            repo.insert_tags(7, tags, conn)
            conn.commit()

        conn = _connect(populated_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT TagID, IsDeleted FROM Tags WHERE TagName = 'Grunge' COLLATE NOCASE AND TagCategory = 'Genre'"
        ).fetchall()
        conn.close()

        assert (
            len(rows) == 1
        ), f"Expected 1 row (case-insensitive reuse), got {len(rows)}"
        assert rows[0]["TagID"] == 1
        assert rows[0]["IsDeleted"] == 0

    def test_active_tag_not_affected_by_reconnection_logic(self, populated_db):
        """
        Grunge/Genre (TagID=1) is active (IsDeleted=0).
        Re-inserting should reuse it without any UPDATE — just the normal get-or-create.
        """
        repo = TagRepository(populated_db)

        tags = [Tag(name="Grunge", category="Genre")]
        with repo._get_connection() as conn:
            repo.insert_tags(3, tags, conn)
            conn.commit()

        conn = _connect(populated_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT TagID, IsDeleted FROM Tags WHERE TagName = 'Grunge' AND TagCategory = 'Genre'"
        ).fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0]["TagID"] == 1
        assert rows[0]["IsDeleted"] == 0


class TestPublisherReconnection:
    """PublisherRepository.insert_song_publishers must wake up soft-deleted publishers."""

    def test_soft_deleted_publisher_is_reconnected_not_duplicated(self, populated_db):
        """
        DGC Records (PublisherID=10) exists in populated_db.
        Soft-delete it, then re-insert onto Song 3.
        Should reuse PublisherID=10 with IsDeleted=0.
        """
        repo = PublisherRepository(populated_db)

        conn = _connect(populated_db)
        conn.execute("UPDATE Publishers SET IsDeleted = 1 WHERE PublisherID = 10")
        conn.commit()
        conn.close()

        publishers = [Publisher(name="DGC Records")]
        with repo._get_connection() as conn:
            repo.insert_song_publishers(3, publishers, conn)
            conn.commit()

        conn = _connect(populated_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT PublisherID, IsDeleted FROM Publishers WHERE PublisherName = 'DGC Records' COLLATE UTF8_NOCASE"
        ).fetchall()
        conn.close()

        assert len(rows) == 1, f"Expected 1 DGC Records row (reused), got {len(rows)}"
        assert rows[0]["PublisherID"] == 10
        assert rows[0]["IsDeleted"] == 0

    def test_soft_deleted_publisher_case_insensitive_reconnection(self, populated_db):
        """
        Soft-delete 'DGC Records', re-insert as 'dgc records'.
        Case-insensitive match should reconnect.
        """
        repo = PublisherRepository(populated_db)

        conn = _connect(populated_db)
        conn.execute("UPDATE Publishers SET IsDeleted = 1 WHERE PublisherID = 10")
        conn.commit()
        conn.close()

        publishers = [Publisher(name="dgc records")]
        with repo._get_connection() as conn:
            repo.insert_song_publishers(3, publishers, conn)
            conn.commit()

        conn = _connect(populated_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT PublisherID, IsDeleted FROM Publishers WHERE PublisherName = 'DGC Records' COLLATE UTF8_NOCASE"
        ).fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0]["PublisherID"] == 10
        assert rows[0]["IsDeleted"] == 0


class TestArtistNameReconnection:
    """SongCreditRepository.insert_credits must wake up soft-deleted ArtistNames."""

    def test_soft_deleted_artist_name_is_reconnected_via_credit_insert(
        self, populated_db
    ):
        """
        Dave Grohl (NameID=10) exists in populated_db.
        Soft-delete it, then insert a credit for 'Dave Grohl' on Song 7.
        Should reuse NameID=10 with IsDeleted=0.
        """
        repo = SongCreditRepository(populated_db)

        conn = _connect(populated_db)
        conn.execute("UPDATE ArtistNames SET IsDeleted = 1 WHERE NameID = 10")
        conn.commit()
        conn.close()

        credits = [SongCredit(role_name="Performer", display_name="Dave Grohl")]
        with repo._get_connection() as conn:
            repo.insert_credits(7, credits, conn)
            conn.commit()

        conn = _connect(populated_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT NameID, IsDeleted FROM ArtistNames WHERE DisplayName = 'Dave Grohl'"
        ).fetchall()
        conn.close()

        assert len(rows) == 1, f"Expected 1 'Dave Grohl' row (reused), got {len(rows)}"
        assert rows[0]["NameID"] == 10
        assert rows[0]["IsDeleted"] == 0

    def test_soft_deleted_artist_name_reconnected_via_album_credit_insert(
        self, populated_db
    ):
        """
        Same reconnection but through SongAlbumRepository._insert_album_credits path.
        Soft-delete 'Nirvana' (NameID=20), insert a new album with Nirvana credit on Song 7.
        Should reuse NameID=20.
        """
        repo = SongAlbumRepository(populated_db)

        conn = _connect(populated_db)
        conn.execute("UPDATE ArtistNames SET IsDeleted = 1 WHERE NameID = 20")
        conn.commit()
        conn.close()

        albums = [
            SongAlbum(
                album_title="Reconnection Album",
                release_year=2026,
                track_number=1,
                credits=[AlbumCredit(role_name="Performer", display_name="Nirvana")],
            )
        ]
        with repo._get_connection() as conn:
            repo.insert_albums(7, albums, conn)
            conn.commit()

        conn = _connect(populated_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT NameID, IsDeleted FROM ArtistNames WHERE DisplayName = 'Nirvana'"
        ).fetchall()
        conn.close()

        assert len(rows) == 1, f"Expected 1 'Nirvana' row (reused), got {len(rows)}"
        assert rows[0]["NameID"] == 20
        assert rows[0]["IsDeleted"] == 0

    def test_soft_deleted_artist_name_reactivates_soft_deleted_identity(
        self, populated_db
    ):
        """
        Dave Grohl (NameID=10, OwnerIdentityID=1) exists in populated_db.
        Soft-delete both the ArtistName and Identity, then insert a credit.
        Both should be reactivated.
        """
        repo = SongCreditRepository(populated_db)

        conn = _connect(populated_db)
        conn.execute("UPDATE ArtistNames SET IsDeleted = 1 WHERE NameID = 10")
        conn.execute("UPDATE Identities SET IsDeleted = 1 WHERE IdentityID = 1")
        conn.commit()
        conn.close()

        credits = [SongCredit(role_name="Performer", display_name="Dave Grohl")]
        with repo._get_connection() as conn:
            repo.insert_credits(7, credits, conn)
            conn.commit()

        conn = _connect(populated_db)
        conn.row_factory = sqlite3.Row
        name_row = conn.execute(
            "SELECT NameID, IsDeleted FROM ArtistNames WHERE NameID = 10"
        ).fetchone()
        identity_row = conn.execute(
            "SELECT IdentityID, IsDeleted FROM Identities WHERE IdentityID = 1"
        ).fetchone()
        conn.close()

        assert name_row["IsDeleted"] == 0, "ArtistName should be reactivated"
        assert identity_row["IsDeleted"] == 0, "Identity should be reactivated"

    def test_new_artist_reactivates_soft_deleted_identity(self, populated_db):
        """
        Create an Identity with LegalName, soft-delete it, then insert a credit
        with a matching display_name. Should reactivate the Identity and link to it.
        """
        repo = SongCreditRepository(populated_db)

        conn = _connect(populated_db)
        conn.execute(
            "INSERT INTO Identities (IdentityID, IdentityType, LegalName, IsDeleted) "
            "VALUES (99, 'person', 'Ghost Person', 1)"
        )
        conn.commit()
        conn.close()

        credits = [SongCredit(role_name="Performer", display_name="Ghost Person")]
        with repo._get_connection() as conn:
            repo.insert_credits(7, credits, conn)
            conn.commit()

        conn = _connect(populated_db)
        conn.row_factory = sqlite3.Row
        identity_row = conn.execute(
            "SELECT IdentityID, IsDeleted FROM Identities WHERE IdentityID = 99"
        ).fetchone()
        name_row = conn.execute(
            "SELECT OwnerIdentityID, IsPrimaryName FROM ArtistNames WHERE DisplayName = 'Ghost Person'"
        ).fetchone()
        # Should not have created a duplicate Identity
        identity_count = conn.execute(
            "SELECT COUNT(*) FROM Identities WHERE LegalName = 'Ghost Person'"
        ).fetchone()[0]
        conn.close()

        assert identity_row["IsDeleted"] == 0, "Identity should be reactivated"
        assert (
            name_row["OwnerIdentityID"] == 99
        ), "ArtistName should link to reactivated Identity"
        assert name_row["IsPrimaryName"] == 1
        assert identity_count == 1, "Should reuse, not duplicate"


class TestAlbumReconnection:
    """SongAlbumRepository.insert_albums must wake up soft-deleted albums."""

    def test_soft_deleted_album_is_reconnected_not_duplicated(self, populated_db):
        """
        Nevermind (AlbumID=100, 1991) exists in populated_db.
        Soft-delete it, then re-insert onto Song 3.
        Should reuse AlbumID=100 with IsDeleted=0.
        """
        repo = SongAlbumRepository(populated_db)

        conn = _connect(populated_db)
        conn.execute("UPDATE Albums SET IsDeleted = 1 WHERE AlbumID = 100")
        conn.commit()
        conn.close()

        albums = [
            SongAlbum(
                album_title="Nevermind",
                release_year=1991,
                track_number=10,
                disc_number=1,
            )
        ]
        with repo._get_connection() as conn:
            repo.insert_albums(3, albums, conn)
            conn.commit()

        conn = _connect(populated_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT AlbumID, IsDeleted FROM Albums WHERE AlbumTitle = 'Nevermind' AND ReleaseYear = 1991"
        ).fetchall()
        conn.close()

        assert len(rows) == 1, f"Expected 1 Nevermind row (reused), got {len(rows)}"
        assert rows[0]["AlbumID"] == 100
        assert rows[0]["IsDeleted"] == 0

    def test_soft_deleted_album_link_is_created_after_reconnection(self, populated_db):
        """
        After reconnecting a soft-deleted album, the SongAlbums link must also be created.
        """
        repo = SongAlbumRepository(populated_db)

        conn = _connect(populated_db)
        conn.execute("UPDATE Albums SET IsDeleted = 1 WHERE AlbumID = 100")
        conn.commit()
        conn.close()

        albums = [
            SongAlbum(
                album_title="Nevermind",
                release_year=1991,
                track_number=10,
                disc_number=1,
            )
        ]
        with repo._get_connection() as conn:
            repo.insert_albums(3, albums, conn)
            conn.commit()

        result = repo.get_albums_for_songs([3])
        assert len(result) == 1, f"Expected 1 album on Song 3, got {len(result)}"
        assert result[0].album_id == 100
        assert result[0].track_number == 10
