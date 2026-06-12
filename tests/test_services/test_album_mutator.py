"""
Tests for AlbumMutator — add/remove/update song-album links and album entities.

Uses populated_db (songs 1-9, Dave Grohl fixture).

Data map used here:
  Song 1: linked to Album 100 (Nevermind, 1991), Track 1, IsPrimary=1
  Song 2: linked to Album 200 (The Colour and the Shape, 1997), Track 11, IsPrimary=1
  Song 3-9: no album links
"""

import sqlite3

import pytest

from src.engine.routers.mutation_models import (
    AddAlbumItem,
    RemoveAlbumItem,
    UpdateAlbumEntityItem,
    UpdateSongAlbumItem,
)
from src.services.mutators.album_mutator import AlbumMutator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    return conn


def _get_song_albums(conn: sqlite3.Connection, song_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT sa.AlbumID, sa.TrackNumber, sa.DiscNumber, sa.IsPrimary, a.AlbumTitle
        FROM SongAlbums sa JOIN Albums a ON sa.AlbumID = a.AlbumID
        WHERE sa.SourceID = ?
        """,
        (song_id,),
    ).fetchall()


def _get_album_row(conn: sqlite3.Connection, album_id: int) -> sqlite3.Row:
    return conn.execute(
        "SELECT AlbumID, AlbumTitle, AlbumType, ReleaseYear FROM Albums WHERE AlbumID = ?",
        (album_id,),
    ).fetchone()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mutator(populated_db):
    return AlbumMutator(populated_db)


@pytest.fixture
def conn(populated_db):
    c = _make_conn(populated_db)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


class TestAlbumMutatorAdd:
    def test_add_link_to_existing_album(self, mutator, conn):
        item = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 3,
                "name": "Nevermind",
                "id": 100,
                "track_number": 5,
                "disc_number": 1,
            }
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        links = _get_song_albums(conn, 3)
        assert any(r["AlbumID"] == 100 and r["TrackNumber"] == 5 for r in links)

    def test_add_creates_new_album_when_no_id(self, mutator, conn):
        item = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 3,
                "name": "Brand New Album",
                "track_number": 1,
                "disc_number": 1,
            }
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        links = _get_song_albums(conn, 3)
        assert any(r["AlbumTitle"] == "Brand New Album" for r in links)

    def test_add_auto_promotes_when_no_primary_exists(self, mutator, conn):
        # Song 3 has no albums — first add must become primary regardless of make_primary
        item = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 3,
                "name": "Nevermind",
                "id": 100,
                "track_number": 1,
                "disc_number": 1,
            }
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        links = _get_song_albums(conn, 3)
        match = next(r for r in links if r["AlbumID"] == 100)
        assert match["IsPrimary"] == 1

    def test_re_add_existing_link_is_noop(self, mutator, conn):
        # Song 1 already has album 100 as primary (track 1); re-adding must
        # not demote the primary flag or touch the link.
        item = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 1,
                "id": 100,
                "name": "Nevermind",
                "track_number": 7,
                "disc_number": 2,
            }
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        links = _get_song_albums(conn, 1)
        match = next(r for r in links if r["AlbumID"] == 100)
        assert match["IsPrimary"] == 1
        assert match["TrackNumber"] == 1
        assert len([r for r in links if r["AlbumID"] == 100]) == 1

    def test_re_add_with_make_primary_promotes(self, mutator, conn):
        # Give song 1 a second, non-primary album, then re-add it with
        # make_primary: it must take over the primary flag.
        first = AddAlbumItem.model_validate(
            {"type": "album", "song_id": 1, "id": 200, "name": "TCATS"}
        )
        mutator.apply_within("add", first, conn)
        again = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 1,
                "id": 200,
                "name": "TCATS",
                "make_primary": True,
            }
        )
        mutator.apply_within("add", again, conn)
        conn.commit()
        links = {r["AlbumID"]: r for r in _get_song_albums(conn, 1)}
        assert links[200]["IsPrimary"] == 1
        assert links[100]["IsPrimary"] == 0

    def test_add_make_primary_promotes_and_demotes_existing(self, mutator, conn):
        # Song 1 already has album 100 as primary — add 200 with make_primary=true
        item = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 1,
                "name": "TCATS",
                "id": 200,
                "track_number": 3,
                "disc_number": 1,
                "make_primary": True,
            }
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        links = _get_song_albums(conn, 1)
        assert next(r for r in links if r["AlbumID"] == 200)["IsPrimary"] == 1
        assert next(r for r in links if r["AlbumID"] == 100)["IsPrimary"] == 0

    def test_add_without_make_primary_does_not_displace_existing_primary(
        self, mutator, conn
    ):
        # Song 1 already has album 100 as primary — add 200 without make_primary
        item = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 1,
                "name": "TCATS",
                "id": 200,
                "track_number": 3,
                "disc_number": 1,
            }
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        links = _get_song_albums(conn, 1)
        assert next(r for r in links if r["AlbumID"] == 100)["IsPrimary"] == 1
        assert next(r for r in links if r["AlbumID"] == 200)["IsPrimary"] == 0

    def test_add_duplicate_link_is_idempotent(self, mutator, conn):
        before = _get_song_albums(conn, 1)
        item = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 1,
                "name": "Nevermind",
                "id": 100,
                "track_number": 1,
                "disc_number": 1,
            }
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        after = _get_song_albums(conn, 1)
        assert len(after) == len(before)

    def test_unsupported_action_raises(self, mutator, conn):
        item = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 3,
                "name": "X",
                "id": 100,
                "track_number": 1,
                "disc_number": 1,
            }
        )
        with pytest.raises(ValueError):
            mutator.apply_within("bad_action", item, conn)


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------


class TestAlbumMutatorRemove:
    def test_remove_deletes_link(self, mutator, conn):
        item = RemoveAlbumItem.model_validate(
            {"type": "album", "song_id": 1, "id": 100}
        )
        mutator.apply_within("remove", item, conn)
        conn.commit()
        links = _get_song_albums(conn, 1)
        assert not any(r["AlbumID"] == 100 for r in links)

    def test_remove_keeps_album_entity(self, mutator, conn):
        item = RemoveAlbumItem.model_validate(
            {"type": "album", "song_id": 1, "id": 100}
        )
        mutator.apply_within("remove", item, conn)
        conn.commit()
        assert _get_album_row(conn, 100) is not None

    def test_remove_nonexistent_link_raises(self, mutator, conn):
        item = RemoveAlbumItem.model_validate(
            {"type": "album", "song_id": 3, "id": 100}
        )
        with pytest.raises(LookupError):
            mutator.apply_within("remove", item, conn)

    def test_remove_primary_auto_promotes_next(self, mutator, conn):
        # First add a second album to song 1 so there's something to promote to
        add = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 1,
                "name": "TCATS",
                "id": 200,
                "track_number": 3,
                "disc_number": 1,
            }
        )
        mutator.apply_within("add", add, conn)
        conn.commit()

        remove = RemoveAlbumItem.model_validate(
            {"type": "album", "song_id": 1, "id": 100}
        )
        mutator.apply_within("remove", remove, conn)
        conn.commit()

        links = _get_song_albums(conn, 1)
        assert len(links) == 1
        assert links[0]["IsPrimary"] == 1

    def test_remove_primary_no_remaining_leaves_no_primary(self, mutator, conn):
        item = RemoveAlbumItem.model_validate(
            {"type": "album", "song_id": 1, "id": 100}
        )
        mutator.apply_within("remove", item, conn)
        conn.commit()
        assert _get_song_albums(conn, 1) == []


# ---------------------------------------------------------------------------
# update album entity
# ---------------------------------------------------------------------------


class TestAlbumMutatorUpdateEntity:
    def test_update_title(self, mutator, conn):
        item = UpdateAlbumEntityItem.model_validate(
            {"type": "album", "id": 100, "title": "Nevermind (Remaster)"}
        )
        mutator.apply_within("update", item, conn)
        conn.commit()
        row = _get_album_row(conn, 100)
        assert row["AlbumTitle"] == "Nevermind (Remaster)"

    def test_update_release_year(self, mutator, conn):
        item = UpdateAlbumEntityItem.model_validate(
            {"type": "album", "id": 100, "release_year": 1992}
        )
        mutator.apply_within("update", item, conn)
        conn.commit()
        row = _get_album_row(conn, 100)
        assert row["ReleaseYear"] == 1992

    def test_update_no_fields_is_noop(self, mutator, conn):
        before = _get_album_row(conn, 100)
        item = UpdateAlbumEntityItem.model_validate({"type": "album", "id": 100})
        mutator.apply_within("update", item, conn)
        conn.commit()
        after = _get_album_row(conn, 100)
        assert dict(before) == dict(after)

    def test_update_unknown_album_raises(self, mutator, conn):
        item = UpdateAlbumEntityItem.model_validate(
            {"type": "album", "id": 99999, "title": "Ghost"}
        )
        with pytest.raises(LookupError):
            mutator.apply_within("update", item, conn)


# ---------------------------------------------------------------------------
# update song-album link
# ---------------------------------------------------------------------------


class TestAlbumMutatorUpdateSongAlbum:
    def test_update_track_number(self, mutator, conn):
        item = UpdateSongAlbumItem.model_validate(
            {"type": "song_album", "song_id": 1, "album_id": 100, "track_number": 7}
        )
        mutator.apply_within("update", item, conn)
        conn.commit()
        links = _get_song_albums(conn, 1)
        match = next(r for r in links if r["AlbumID"] == 100)
        assert match["TrackNumber"] == 7

    def test_update_is_primary_true_demotes_others(self, mutator, conn):
        # Add a second album first
        add = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 1,
                "name": "TCATS",
                "id": 200,
                "track_number": 3,
                "disc_number": 1,
            }
        )
        mutator.apply_within("add", add, conn)
        conn.commit()

        item = UpdateSongAlbumItem.model_validate(
            {"type": "song_album", "song_id": 1, "album_id": 200, "is_primary": True}
        )
        mutator.apply_within("update", item, conn)
        conn.commit()
        links = _get_song_albums(conn, 1)
        assert next(r for r in links if r["AlbumID"] == 200)["IsPrimary"] == 1
        assert next(r for r in links if r["AlbumID"] == 100)["IsPrimary"] == 0

    def test_update_unlinked_song_album_raises(self, mutator, conn):
        item = UpdateSongAlbumItem.model_validate(
            {"type": "song_album", "song_id": 3, "album_id": 100, "track_number": 1}
        )
        with pytest.raises(LookupError):
            mutator.apply_within("update", item, conn)


# ---------------------------------------------------------------------------
# search-shadow columns (phase 3.1 unit C.1)
# ---------------------------------------------------------------------------


class TestAlbumMutatorSearchShadow:
    def test_add_new_album_populates_shadow(self, mutator, conn):
        item = AddAlbumItem.model_validate(
            {
                "type": "album",
                "song_id": 3,
                "name": "Šešir Profesora Koste Vujića",
                "track_number": 1,
                "disc_number": 1,
            }
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        row = conn.execute(
            "SELECT AlbumTitle, AlbumTitle_Search FROM Albums "
            "WHERE AlbumTitle = ? COLLATE UTF8_NOCASE",
            ("Šešir Profesora Koste Vujića",),
        ).fetchone()
        assert row is not None
        assert row["AlbumTitle"] == "Šešir Profesora Koste Vujića"
        assert row["AlbumTitle_Search"] == "sesir profesora koste vujica"

    def test_update_title_updates_shadow(self, mutator, conn):
        item = UpdateAlbumEntityItem.model_validate(
            {"type": "album", "id": 100, "title": "Nëvërmïnd"}
        )
        mutator.apply_within("update", item, conn)
        conn.commit()
        row = conn.execute(
            "SELECT AlbumTitle, AlbumTitle_Search FROM Albums WHERE AlbumID = 100"
        ).fetchone()
        assert row["AlbumTitle"] == "Nëvërmïnd"
        assert row["AlbumTitle_Search"] == "nevermind"
