"""
Tests for SongAlbumRepository.insert_albums (RED phase)
=======================================================
Verifies get-or-create logic for Albums table and link insertion into SongAlbums.
Uses populated_db which already has:
    Albums: 100=Nevermind/1991, 200=The Colour and the Shape/1997
    Songs: 1-9 (various)
    SongAlbums: Song 1 -> Nevermind Track 1, Song 2 -> TCATS Track 11
"""

import sqlite3
from src.data.song_album_repository import SongAlbumRepository
from src.models.domain import SongAlbum, AlbumCredit


class TestInsertAlbums:
    def test_insert_new_album_creates_album_row_and_link(self, populated_db):
        """Insert a brand-new album onto Song 3 (Range Rover Bitch, currently no album)."""
        repo = SongAlbumRepository(populated_db)

        albums = [
            SongAlbum(
                album_title="Get the Money",
                release_year=2019,
                track_number=5,
                disc_number=1,
            ),
        ]

        with repo._get_connection() as conn:
            repo.insert_albums(3, albums, conn)
            conn.commit()

        # Verify Albums table
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT AlbumID, AlbumTitle, ReleaseYear FROM Albums WHERE AlbumTitle = 'Get the Money'"
            ).fetchone()
            assert row is not None, "Expected 'Get the Money' album row to exist"
            assert row["AlbumTitle"] == "Get the Money", f"Expected 'Get the Money', got '{row['AlbumTitle']}'"
            assert row["ReleaseYear"] == 2019, f"Expected 2019, got {row['ReleaseYear']}"
        
        # Verify SongAlbums link
        result = repo.get_albums_for_songs([3])
        assert len(result) == 1, f"Expected 1 album on Song 3, got {len(result)}"
        assert result[0].album_title == "Get the Money", f"Expected 'Get the Money', got '{result[0].album_title}'"
        assert result[0].track_number == 5, f"Expected track 5, got {result[0].track_number}"
        assert result[0].disc_number == 1, f"Expected disc 1, got {result[0].disc_number}"

    def test_insert_existing_album_reuses_album_id(self, populated_db):
        """Insert 'Nevermind'/1991 (already AlbumID=100) onto Song 3 — should reuse, not duplicate."""
        repo = SongAlbumRepository(populated_db)

        albums = [
            SongAlbum(
                album_title="Nevermind",
                release_year=1991,
                track_number=10,
                disc_number=1,
            ),
        ]

        with repo._get_connection() as conn:
            repo.insert_albums(3, albums, conn)
            conn.commit()

        # Verify no duplicate Album row
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT AlbumID FROM Albums WHERE AlbumTitle = 'Nevermind' AND ReleaseYear = 1991"
            ).fetchall()
            assert len(rows) == 1, f"Expected 1 'Nevermind' album row (reused), got {len(rows)}"
            assert rows[0]["AlbumID"] == 100, f"Expected AlbumID=100 (original), got {rows[0]['AlbumID']}"

        # Verify link was created for Song 3
        result = repo.get_albums_for_songs([3])
        assert len(result) == 1, f"Expected 1 album on Song 3, got {len(result)}"
        assert result[0].album_id == 100, f"Expected AlbumID=100, got {result[0].album_id}"
        assert result[0].track_number == 10, f"Expected track 10, got {result[0].track_number}"

    def test_same_title_different_year_creates_separate_albums(self, populated_db):
        """Two 'Greatest Hits' with different years should be different albums."""
        repo = SongAlbumRepository(populated_db)

        albums_song3 = [
            SongAlbum(album_title="Greatest Hits", release_year=2005, track_number=1),
        ]
        albums_song4 = [
            SongAlbum(album_title="Greatest Hits", release_year=2015, track_number=3),
        ]

        with repo._get_connection() as conn:
            repo.insert_albums(3, albums_song3, conn)
            repo.insert_albums(4, albums_song4, conn)
            conn.commit()

        # Should be 2 separate album rows
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT AlbumID, ReleaseYear FROM Albums WHERE AlbumTitle = 'Greatest Hits' ORDER BY ReleaseYear"
            ).fetchall()
            assert len(rows) == 2, f"Expected 2 'Greatest Hits' albums, got {len(rows)}"
            assert rows[0]["ReleaseYear"] == 2005, f"Expected 2005, got {rows[0]['ReleaseYear']}"
            assert rows[1]["ReleaseYear"] == 2015, f"Expected 2015, got {rows[1]['ReleaseYear']}"
            assert rows[0]["AlbumID"] != rows[1]["AlbumID"], "Expected different AlbumIDs"

    def test_track_and_disc_numbers_persist(self, populated_db):
        """Track and disc numbers should survive the round-trip."""
        repo = SongAlbumRepository(populated_db)

        albums = [
            SongAlbum(
                album_title="Double Disc Album",
                release_year=2020,
                track_number=7,
                disc_number=2,
            ),
        ]

        with repo._get_connection() as conn:
            repo.insert_albums(7, albums, conn)
            conn.commit()

        result = repo.get_albums_for_songs([7])
        assert len(result) == 1, f"Expected 1 album on Song 7, got {len(result)}"
        assert result[0].track_number == 7, f"Expected track 7, got {result[0].track_number}"
        assert result[0].disc_number == 2, f"Expected disc 2, got {result[0].disc_number}"

    def test_insert_empty_list_is_noop(self, populated_db):
        """Passing empty list should not crash or create any rows."""
        repo = SongAlbumRepository(populated_db)

        # Song 7 has no albums before
        before = repo.get_albums_for_songs([7])
        assert len(before) == 0, f"Expected 0 albums on Song 7 before, got {len(before)}"

        with repo._get_connection() as conn:
            repo.insert_albums(7, [], conn)
            conn.commit()

        after = repo.get_albums_for_songs([7])
        assert len(after) == 0, f"Expected 0 albums on Song 7 after empty insert, got {len(after)}"

    def test_insert_album_with_null_year(self, populated_db):
        """Album with no release year should still create correctly."""
        repo = SongAlbumRepository(populated_db)

        albums = [
            SongAlbum(album_title="Mystery Album", release_year=None, track_number=1),
        ]

        with repo._get_connection() as conn:
            repo.insert_albums(7, albums, conn)
            conn.commit()

        result = repo.get_albums_for_songs([7])
        assert len(result) == 1, f"Expected 1 album on Song 7, got {len(result)}"
        assert result[0].album_title == "Mystery Album", f"Expected 'Mystery Album', got '{result[0].album_title}'"
        assert result[0].release_year is None, f"Expected None release_year, got {result[0].release_year}"

    def test_insert_album_case_insensitive_reuses_existing(self, populated_db):
        """'nevermind'/1991 should match 'Nevermind'/1991 (AlbumID=100), not create a duplicate."""
        repo = SongAlbumRepository(populated_db)

        albums = [
            SongAlbum(
                album_title="nevermind",
                release_year=1991,
                track_number=12,
                disc_number=1,
            ),
        ]

        with repo._get_connection() as conn:
            repo.insert_albums(3, albums, conn)
            conn.commit()

        # Should reuse AlbumID=100, not create a new row
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT AlbumID FROM Albums WHERE AlbumTitle = 'Nevermind' COLLATE UTF8_NOCASE AND ReleaseYear = 1991"
            ).fetchall()
            assert len(rows) == 1, f"Expected 1 'Nevermind' album (reused), got {len(rows)}"
            assert rows[0]["AlbumID"] == 100, f"Expected AlbumID=100, got {rows[0]['AlbumID']}"

    def test_same_title_same_year_different_artist_creates_separate_albums(self, populated_db):
        """'Greatest Hits'/1992 by ABBA and 'Greatest Hits'/1992 by Queen should be 2 albums."""
        repo = SongAlbumRepository(populated_db)

        abba_album = [
            SongAlbum(
                album_title="Greatest Hits",
                release_year=1992,
                track_number=1,
                credits=[AlbumCredit(role_name="Album Artist", display_name="ABBA")],
            ),
        ]
        queen_album = [
            SongAlbum(
                album_title="Greatest Hits",
                release_year=1992,
                track_number=1,
                credits=[AlbumCredit(role_name="Album Artist", display_name="Queen")],
            ),
        ]

        with repo._get_connection() as conn:
            repo.insert_albums(7, abba_album, conn)
            repo.insert_albums(9, queen_album, conn)
            conn.commit()

        # Should be 2 separate album rows
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT AlbumID FROM Albums WHERE AlbumTitle = 'Greatest Hits' AND ReleaseYear = 1992"
            ).fetchall()
            assert len(rows) == 2, f"Expected 2 'Greatest Hits'/1992 albums (different artists), got {len(rows)}"
            assert rows[0]["AlbumID"] != rows[1]["AlbumID"], "Expected different AlbumIDs"

    def test_same_title_same_year_same_artist_reuses_album(self, populated_db):
        """Two songs on 'Greatest Hits'/1992 by ABBA should share one album row."""
        repo = SongAlbumRepository(populated_db)

        abba_credits = [AlbumCredit(role_name="Album Artist", display_name="ABBA")]

        album_song7 = [
            SongAlbum(
                album_title="Greatest Hits",
                release_year=1992,
                track_number=1,
                credits=abba_credits,
            ),
        ]
        album_song9 = [
            SongAlbum(
                album_title="Greatest Hits",
                release_year=1992,
                track_number=2,
                credits=abba_credits,
            ),
        ]

        with repo._get_connection() as conn:
            repo.insert_albums(7, album_song7, conn)
            repo.insert_albums(9, album_song9, conn)
            conn.commit()

        # Should be 1 album row, reused
        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT AlbumID FROM Albums WHERE AlbumTitle = 'Greatest Hits' AND ReleaseYear = 1992"
            ).fetchall()
            assert len(rows) == 1, f"Expected 1 'Greatest Hits'/1992 album (reused), got {len(rows)}"

        # Both songs should link to it
        result7 = repo.get_albums_for_songs([7])
        result9 = repo.get_albums_for_songs([9])
        assert len(result7) == 1
        assert len(result9) == 1
        assert result7[0].album_id == result9[0].album_id, "Expected same AlbumID for both songs"

    def test_multi_artist_same_set_reuses_album(self, populated_db):
        """'Collab Album'/2020 by [ABBA, Queen] inserted twice should reuse one album."""
        repo = SongAlbumRepository(populated_db)

        credits = [
            AlbumCredit(role_name="Album Artist", display_name="ABBA"),
            AlbumCredit(role_name="Album Artist", display_name="Queen"),
        ]

        album1 = [SongAlbum(album_title="Collab Album", release_year=2020, track_number=1, credits=credits)]
        album2 = [SongAlbum(album_title="Collab Album", release_year=2020, track_number=2, credits=credits)]

        with repo._get_connection() as conn:
            repo.insert_albums(7, album1, conn)
            repo.insert_albums(9, album2, conn)
            conn.commit()

        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT AlbumID FROM Albums WHERE AlbumTitle = 'Collab Album' AND ReleaseYear = 2020"
            ).fetchall()
            assert len(rows) == 1, f"Expected 1 'Collab Album' (same artist set), got {len(rows)}"

    def test_multi_artist_different_order_reuses_album(self, populated_db):
        """[Queen, ABBA] should match [ABBA, Queen] — order doesn't matter."""
        repo = SongAlbumRepository(populated_db)

        credits_ab = [
            AlbumCredit(role_name="Album Artist", display_name="ABBA"),
            AlbumCredit(role_name="Album Artist", display_name="Queen"),
        ]
        credits_ba = [
            AlbumCredit(role_name="Album Artist", display_name="Queen"),
            AlbumCredit(role_name="Album Artist", display_name="ABBA"),
        ]

        album1 = [SongAlbum(album_title="Collab Album", release_year=2020, track_number=1, credits=credits_ab)]
        album2 = [SongAlbum(album_title="Collab Album", release_year=2020, track_number=2, credits=credits_ba)]

        with repo._get_connection() as conn:
            repo.insert_albums(7, album1, conn)
            repo.insert_albums(9, album2, conn)
            conn.commit()

        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT AlbumID FROM Albums WHERE AlbumTitle = 'Collab Album' AND ReleaseYear = 2020"
            ).fetchall()
            assert len(rows) == 1, f"Expected 1 'Collab Album' (order-independent match), got {len(rows)}"

    def test_multi_artist_superset_creates_separate_album(self, populated_db):
        """[ABBA, Queen] vs [ABBA, Queen, Freddie Mercury] — overlapping but not equal, should be 2 albums."""
        repo = SongAlbumRepository(populated_db)

        credits_two = [
            AlbumCredit(role_name="Album Artist", display_name="ABBA"),
            AlbumCredit(role_name="Album Artist", display_name="Queen"),
        ]
        credits_three = [
            AlbumCredit(role_name="Album Artist", display_name="ABBA"),
            AlbumCredit(role_name="Album Artist", display_name="Queen"),
            AlbumCredit(role_name="Album Artist", display_name="Freddie Mercury"),
        ]

        album1 = [SongAlbum(album_title="Collab Album", release_year=2020, track_number=1, credits=credits_two)]
        album2 = [SongAlbum(album_title="Collab Album", release_year=2020, track_number=1, credits=credits_three)]

        with repo._get_connection() as conn:
            repo.insert_albums(7, album1, conn)
            repo.insert_albums(9, album2, conn)
            conn.commit()

        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT AlbumID FROM Albums WHERE AlbumTitle = 'Collab Album' AND ReleaseYear = 2020"
            ).fetchall()
            assert len(rows) == 2, f"Expected 2 'Collab Album' (superset != original set), got {len(rows)}"
            assert rows[0]["AlbumID"] != rows[1]["AlbumID"], "Expected different AlbumIDs"

    def test_no_credits_still_matches_by_title_year_only(self, populated_db):
        """Albums with no credits should fall back to Title+Year matching (backwards compat)."""
        repo = SongAlbumRepository(populated_db)

        album1 = [SongAlbum(album_title="Untitled", release_year=2020, track_number=1)]
        album2 = [SongAlbum(album_title="Untitled", release_year=2020, track_number=2)]

        with repo._get_connection() as conn:
            repo.insert_albums(7, album1, conn)
            repo.insert_albums(9, album2, conn)
            conn.commit()

        with repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT AlbumID FROM Albums WHERE AlbumTitle = 'Untitled' AND ReleaseYear = 2020"
            ).fetchall()
            assert len(rows) == 1, f"Expected 1 'Untitled'/2020 album (reused, no credits), got {len(rows)}"
