"""
Tests for DeleteMutator — entity-level soft-deletes.

Data map (populated_db):
  Songs:      1-9
  Tags:       1=Grunge, 2=Energetic, 3=90s, 4=Electronic, 5=English, 6=Alt Rock, 7=Rock
  Publishers: 1=Universal, 2=Island Records, 4=Roswell, 5=Sub Pop, 10=DGC Records
  Albums:     100=Nevermind (linked: song 1), 200=The Colour and the Shape (linked: song 2)
  Identities: 1=Dave Grohl, 2=Nirvana, 3=Foo Fighters, 4=Taylor Hawkins
  Song 1 linked to publisher 10. Songs 1-9 all active.

Unlinked entities (safe to delete):
  Tag 3 (90s) is only on song 2 via song_tag — wait, it IS linked.
  Tag 4 (Electronic) is on song 4 — linked.
  Tags 3,4,5,6,7 are all linked. Only an unlinked tag can be deleted without 400.
  Publisher 4 (Roswell) — linked to album 200 only, not songs → safe for song-only check?
  Actually publisher 4 is in AlbumPublishers only, not RecordingPublishers.
  Publisher 5 (Sub Pop) — AlbumPublishers for album 100 only, not RecordingPublishers.
  Publisher 2 (Island Records) — no song or album links → safe to delete.
  Album 200 is linked to song 2 → blocked. Need an unlinked album.
"""
import sqlite3
import pytest

from src.engine.routers.mutation_models import (
    DeleteAlbumItem,
    DeleteIdentityItem,
    DeletePublisherItem,
    DeleteSongItem,
    DeleteTagItem,
)
from src.services.mutators.delete_mutator import DeleteMutator


def _make_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    return conn


def _is_deleted(conn, table, pk_col, pk_val) -> bool:
    row = conn.execute(
        f"SELECT IsDeleted FROM {table} WHERE {pk_col} = ?", (pk_val,)
    ).fetchone()
    return bool(row["IsDeleted"]) if row else True


@pytest.fixture
def mutator(populated_db):
    return DeleteMutator(populated_db)


@pytest.fixture
def conn(populated_db):
    c = _make_conn(populated_db)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Song delete
# ---------------------------------------------------------------------------

class TestDeleteSong:
    def test_soft_deletes_song(self, mutator, conn):
        mutator.apply_within("delete", DeleteSongItem(type="song", id=1), conn, None)
        conn.commit()
        assert _is_deleted(conn, "MediaSources", "SourceID", 1)

    def test_not_found_raises_lookup_error(self, mutator, conn):
        with pytest.raises(LookupError):
            mutator.apply_within("delete", DeleteSongItem(type="song", id=9999), conn, None)

    def test_wrong_action_raises_value_error(self, mutator, conn):
        with pytest.raises(ValueError):
            mutator.apply_within("remove", DeleteSongItem(type="song", id=1), conn, None)


# ---------------------------------------------------------------------------
# Tag delete
# ---------------------------------------------------------------------------

class TestDeleteTag:
    def test_soft_deletes_unlinked_tag(self, mutator, conn):
        # Insert an unlinked tag to delete
        conn.execute("INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (99, 'Orphan', 'Genre')")
        mutator.apply_within("delete", DeleteTagItem(type="tag", id=99), conn, None)
        conn.commit()
        assert _is_deleted(conn, "Tags", "TagID", 99)

    def test_linked_tag_raises_value_error(self, mutator, conn):
        # Tag 1 (Grunge) is linked to song 1
        with pytest.raises(ValueError, match="still linked"):
            mutator.apply_within("delete", DeleteTagItem(type="tag", id=1), conn, None)

    def test_not_found_raises_lookup_error(self, mutator, conn):
        with pytest.raises(LookupError):
            mutator.apply_within("delete", DeleteTagItem(type="tag", id=9999), conn, None)


# ---------------------------------------------------------------------------
# Publisher delete
# ---------------------------------------------------------------------------

class TestDeletePublisher:
    def test_soft_deletes_unlinked_publisher(self, mutator, conn):
        # Publisher 2 (Island Records) has no song or album links
        mutator.apply_within("delete", DeletePublisherItem(type="publisher", id=2), conn, None)
        conn.commit()
        assert _is_deleted(conn, "Publishers", "PublisherID", 2)

    def test_linked_publisher_raises_value_error(self, mutator, conn):
        # Publisher 10 (DGC Records) linked to song 1
        with pytest.raises(ValueError, match="still linked"):
            mutator.apply_within("delete", DeletePublisherItem(type="publisher", id=10), conn, None)

    def test_not_found_raises_lookup_error(self, mutator, conn):
        with pytest.raises(LookupError):
            mutator.apply_within("delete", DeletePublisherItem(type="publisher", id=9999), conn, None)


# ---------------------------------------------------------------------------
# Album delete
# ---------------------------------------------------------------------------

class TestDeleteAlbum:
    def test_soft_deletes_unlinked_album(self, mutator, conn):
        conn.execute("INSERT INTO Albums (AlbumID, AlbumTitle) VALUES (999, 'Orphan Album')")
        mutator.apply_within("delete", DeleteAlbumItem(type="album", id=999), conn, None)
        conn.commit()
        assert _is_deleted(conn, "Albums", "AlbumID", 999)

    def test_linked_album_raises_value_error(self, mutator, conn):
        # Album 100 linked to song 1
        with pytest.raises(ValueError, match="still linked"):
            mutator.apply_within("delete", DeleteAlbumItem(type="album", id=100), conn, None)

    def test_not_found_raises_lookup_error(self, mutator, conn):
        with pytest.raises(LookupError):
            mutator.apply_within("delete", DeleteAlbumItem(type="album", id=9999), conn, None)


# ---------------------------------------------------------------------------
# Identity delete
# ---------------------------------------------------------------------------

class TestDeleteIdentity:
    def test_soft_deletes_unlinked_identity(self, mutator, conn):
        # Insert a fresh identity with no credits
        conn.execute("INSERT INTO Identities (IdentityID, IdentityType) VALUES (999, 'person')")
        mutator.apply_within("delete", DeleteIdentityItem(type="identity", id=999), conn, None)
        conn.commit()
        assert _is_deleted(conn, "Identities", "IdentityID", 999)

    def test_linked_identity_raises_value_error(self, mutator, conn):
        # Identity 1 (Dave Grohl) credited on multiple songs
        with pytest.raises(ValueError, match="still linked"):
            mutator.apply_within("delete", DeleteIdentityItem(type="identity", id=1), conn, None)

    def test_not_found_raises_lookup_error(self, mutator, conn):
        with pytest.raises(LookupError):
            mutator.apply_within("delete", DeleteIdentityItem(type="identity", id=9999), conn, None)
