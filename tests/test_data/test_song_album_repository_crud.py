"""
Tests for SongAlbumRepository CRUD methods
============================================
add_album, remove_album, update_track_info

populated_db albums:
  AlbumID=100: "Nevermind" (1991)   -> Song 1 (Track 1, Disc 1)
  AlbumID=200: "The Colour and the Shape" (1997) -> Song 2 (Track 11, Disc 1)

Songs with no album links: 3, 4, 5, 6, 7, 8, 9
"""

import sqlite3
from src.data.song_album_repository import SongAlbumRepository


class TestAddAlbum:
    def test_add_album_link(self, populated_db):
        """Link Song 3 to Nevermind (100) — should create SongAlbums row."""
        repo = SongAlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_album(3, 100, track_number=5, disc_number=1, conn=conn)
            conn.commit()

        albums = repo.get_albums_for_songs([3])
        assert len(albums) == 1, f"Expected 1 album on Song 3, got {len(albums)}"
        assert (
            albums[0].album_id == 100
        ), f"Expected AlbumID=100, got {albums[0].album_id}"
        assert (
            albums[0].track_number == 5
        ), f"Expected TrackNumber=5, got {albums[0].track_number}"
        assert (
            albums[0].disc_number == 1
        ), f"Expected DiscNumber=1, got {albums[0].disc_number}"
        assert (
            albums[0].source_id == 3
        ), f"Expected SourceID=3, got {albums[0].source_id}"

    def test_add_album_idempotent_on_duplicate(self, populated_db):
        """Adding the same album link twice should not create duplicate SongAlbums rows."""
        repo = SongAlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_album(3, 100, track_number=5, disc_number=1, conn=conn)
            repo.add_album(3, 100, track_number=5, disc_number=1, conn=conn)
            conn.commit()

        albums = repo.get_albums_for_songs([3])
        assert (
            len(albums) == 1
        ), f"Expected 1 album link (idempotent), got {len(albums)}"

    def test_add_album_does_not_affect_other_songs(self, populated_db):
        """Linking Song 3 to an album should not affect Song 1's album links."""
        repo = SongAlbumRepository(populated_db)
        before = repo.get_albums_for_songs([1])

        with repo._get_connection() as conn:
            repo.add_album(3, 200, track_number=1, disc_number=1, conn=conn)
            conn.commit()

        after = repo.get_albums_for_songs([1])
        assert len(after) == len(
            before
        ), f"Song 1 album count should not change: expected {len(before)}, got {len(after)}"
        assert (
            after[0].album_id == 100
        ), f"Song 1 should still link to Nevermind (100), got {after[0].album_id}"

    def test_add_album_keeps_album_record(self, populated_db):
        """Album record itself should not be modified by adding a link."""
        repo = SongAlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.add_album(3, 100, track_number=2, disc_number=1, conn=conn)
            conn.commit()

        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT AlbumTitle FROM Albums WHERE AlbumID = 100"
            ).fetchone()
            assert (
                row["AlbumTitle"] == "Nevermind"
            ), f"Expected album title 'Nevermind' unchanged, got '{row['AlbumTitle']}'"


class TestRemoveAlbum:
    def test_remove_album_deletes_link(self, populated_db):
        """Remove Song 1's link to Nevermind — link should be gone, Album record should remain."""
        repo = SongAlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.remove_album(1, 100, conn)
            conn.commit()

        albums = repo.get_albums_for_songs([1])
        assert (
            len(albums) == 0
        ), f"Expected 0 albums on Song 1 after remove, got {len(albums)}"

        # Album record persists
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT AlbumID FROM Albums WHERE AlbumID = 100"
            ).fetchone()
            assert (
                row is not None
            ), "Expected Album record (ID=100) to persist after link removal"

    def test_remove_album_does_not_affect_other_songs(self, populated_db):
        """Removing Song 1's link to Nevermind should not affect Song 2's album link."""
        repo = SongAlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.remove_album(1, 100, conn)
            conn.commit()

        albums_song2 = repo.get_albums_for_songs([2])
        assert (
            len(albums_song2) == 1
        ), f"Expected Song 2 to still have 1 album, got {len(albums_song2)}"
        assert (
            albums_song2[0].album_id == 200
        ), f"Expected AlbumID=200, got {albums_song2[0].album_id}"


class TestUpdateTrackInfo:
    def test_update_track_number(self, populated_db):
        """Update track number for Song 1 -> Nevermind link."""
        repo = SongAlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_track_info(1, 100, track_number=3, disc_number=1, conn=conn)
            conn.commit()

        albums = repo.get_albums_for_songs([1])
        assert len(albums) == 1, f"Expected 1 album on Song 1, got {len(albums)}"
        assert (
            albums[0].track_number == 3
        ), f"Expected TrackNumber=3, got {albums[0].track_number}"
        assert (
            albums[0].disc_number == 1
        ), f"Expected DiscNumber=1 unchanged, got {albums[0].disc_number}"

    def test_update_disc_number(self, populated_db):
        """Update disc number for Song 2 -> TCATS link."""
        repo = SongAlbumRepository(populated_db)

        with repo._get_connection() as conn:
            repo.update_track_info(2, 200, track_number=11, disc_number=2, conn=conn)
            conn.commit()

        albums = repo.get_albums_for_songs([2])
        assert (
            albums[0].disc_number == 2
        ), f"Expected DiscNumber=2, got {albums[0].disc_number}"
        assert (
            albums[0].track_number == 11
        ), f"Expected TrackNumber=11 unchanged, got {albums[0].track_number}"

    def test_update_track_info_does_not_affect_other_songs(self, populated_db):
        """Updating Song 1's track info should not affect Song 2's track info."""
        repo = SongAlbumRepository(populated_db)
        before_song2 = repo.get_albums_for_songs([2])[0]

        with repo._get_connection() as conn:
            repo.update_track_info(1, 100, track_number=99, disc_number=3, conn=conn)
            conn.commit()

        after_song2 = repo.get_albums_for_songs([2])[0]
        assert (
            after_song2.track_number == before_song2.track_number
        ), f"Song 2 track number should not change, got {after_song2.track_number}"
        assert (
            after_song2.disc_number == before_song2.disc_number
        ), f"Song 2 disc number should not change, got {after_song2.disc_number}"
