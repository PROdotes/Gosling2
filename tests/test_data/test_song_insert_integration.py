"""
Integration test: SongRepository.insert() persists full metadata
=================================================================
Verifies that inserting a Song with tags, albums, publishers, and credits
writes everything in a single transaction and is readable via the existing read repos.
"""

import sqlite3
from src.data.song_repository import SongRepository
from src.data.tag_repository import TagRepository
from src.data.song_album_repository import SongAlbumRepository
from src.data.publisher_repository import PublisherRepository
from src.data.song_credit_repository import SongCreditRepository
from src.models.domain import Song, Tag, SongAlbum, Publisher, SongCredit


class TestInsertFullSong:
    def test_insert_song_with_all_metadata_persists_everything(self, populated_db):
        """
        Insert a Song that has tags, albums, publishers, and credits.
        Tags, albums, publishers, and credits should all persist.
        """
        song_repo = SongRepository(populated_db)
        tag_repo = TagRepository(populated_db)
        album_repo = SongAlbumRepository(populated_db)
        pub_repo = PublisherRepository(populated_db)
        credit_repo = SongCreditRepository(populated_db)

        song = Song(
            media_name="Integration Test Song",
            source_path="/test/integration.mp3",
            duration_s=210.5,
            audio_hash="integration_hash_001",
            bpm=128,
            year=2025,
            isrc="US-INT-25-00001",
            tags=[
                Tag(name="Pop", category="Genre", is_primary=True),
                Tag(name="Happy", category="Mood"),
            ],
            albums=[
                SongAlbum(
                    album_title="Test Album",
                    release_year=2025,
                    track_number=3,
                    disc_number=1,
                ),
            ],
            publishers=[
                Publisher(name="Test Records"),
            ],
            credits=[
                SongCredit(role_name="Performer", display_name="Test Artist"),
            ],
        )

        # Insert within a transaction
        conn = song_repo.get_connection()
        new_id = song_repo.insert(song, conn)
        conn.commit()
        conn.close()

        # --- Verify core song persisted ---
        saved = song_repo.get_by_id(new_id)
        assert saved is not None, "Expected song to be saved"
        assert saved.id == new_id, f"Expected id={new_id}, got {saved.id}"
        assert (
            saved.media_name == "Integration Test Song"
        ), f"Expected 'Integration Test Song', got '{saved.media_name}'"
        assert (
            saved.source_path == "/test/integration.mp3"
        ), f"Expected '/test/integration.mp3', got '{saved.source_path}'"
        assert saved.duration_s == 210.5, f"Expected 210.5, got {saved.duration_s}"
        assert (
            saved.audio_hash == "integration_hash_001"
        ), f"Expected 'integration_hash_001', got '{saved.audio_hash}'"
        assert saved.bpm == 128, f"Expected 128, got {saved.bpm}"
        assert saved.year == 2025, f"Expected 2025, got {saved.year}"
        assert (
            saved.isrc == "US-INT-25-00001"
        ), f"Expected 'US-INT-25-00001', got '{saved.isrc}'"

        # --- Verify tags persisted ---
        tags = tag_repo.get_tags_for_songs([new_id])
        assert len(tags) == 2, f"Expected 2 tags, got {len(tags)}"
        tag_map = {t.name: t for _, t in tags}
        assert "Pop" in tag_map, f"Expected 'Pop' tag, got {list(tag_map.keys())}"
        assert (
            tag_map["Pop"].category == "Genre"
        ), f"Expected category 'Genre', got '{tag_map['Pop'].category}'"
        assert (
            tag_map["Pop"].is_primary is True
        ), f"Expected Pop.is_primary=True, got {tag_map['Pop'].is_primary}"
        assert "Happy" in tag_map, f"Expected 'Happy' tag, got {list(tag_map.keys())}"
        assert (
            tag_map["Happy"].category == "Mood"
        ), f"Expected category 'Mood', got '{tag_map['Happy'].category}'"

        # --- Verify album persisted ---
        albums = album_repo.get_albums_for_songs([new_id])
        assert len(albums) == 1, f"Expected 1 album, got {len(albums)}"
        assert (
            albums[0].album_title == "Test Album"
        ), f"Expected 'Test Album', got '{albums[0].album_title}'"
        assert (
            albums[0].release_year == 2025
        ), f"Expected 2025, got {albums[0].release_year}"
        assert (
            albums[0].track_number == 3
        ), f"Expected track 3, got {albums[0].track_number}"
        assert (
            albums[0].disc_number == 1
        ), f"Expected disc 1, got {albums[0].disc_number}"

        # --- Verify publisher persisted ---
        pubs = pub_repo.get_publishers_for_songs([new_id])
        assert len(pubs) == 1, f"Expected 1 publisher, got {len(pubs)}"
        _, pub = pubs[0]
        assert pub.name == "Test Records", f"Expected 'Test Records', got '{pub.name}'"

        # --- Verify credits persisted ---
        credits = credit_repo.get_credits_for_songs([new_id])
        assert len(credits) == 1, f"Expected 1 credit, got {len(credits)}"
        assert (
            credits[0].display_name == "Test Artist"
        ), f"Expected 'Test Artist', got '{credits[0].display_name}'"
        assert (
            credits[0].role_name == "Performer"
        ), f"Expected 'Performer', got '{credits[0].role_name}'"

    def test_insert_song_with_no_metadata_still_works(self, populated_db):
        """A bare-bones song with no tags/albums/publishers should insert fine."""
        song_repo = SongRepository(populated_db)

        song = Song(
            media_name="Bare Song",
            source_path="/test/bare.mp3",
            duration_s=60.0,
        )

        conn = song_repo.get_connection()
        new_id = song_repo.insert(song, conn)
        conn.commit()
        conn.close()

        saved = song_repo.get_by_id(new_id)
        assert saved is not None, "Expected song to be saved"
        assert (
            saved.media_name == "Bare Song"
        ), f"Expected 'Bare Song', got '{saved.media_name}'"
        assert saved.bpm is None, f"Expected None bpm, got {saved.bpm}"
        assert saved.year is None, f"Expected None year, got {saved.year}"

    def test_insert_song_reuses_existing_album_and_tag(self, populated_db):
        """Insert a song referencing 'Nevermind'/1991 and 'Grunge' — should reuse existing rows."""
        song_repo = SongRepository(populated_db)

        song = Song(
            media_name="Another Nevermind Track",
            source_path="/test/nevermind_bonus.mp3",
            duration_s=180.0,
            year=1991,
            tags=[Tag(name="Grunge", category="Genre")],
            albums=[
                SongAlbum(album_title="Nevermind", release_year=1991, track_number=99)
            ],
        )

        conn = song_repo.get_connection()
        song_repo.insert(song, conn)
        conn.commit()
        conn.close()

        # Verify album reused (AlbumID=100)
        with song_repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT AlbumID FROM Albums WHERE AlbumTitle = 'Nevermind' AND ReleaseYear = 1991"
            ).fetchall()
            assert (
                len(rows) == 1
            ), f"Expected 1 'Nevermind' album (reused), got {len(rows)}"
            assert (
                rows[0]["AlbumID"] == 100
            ), f"Expected AlbumID=100, got {rows[0]['AlbumID']}"

        # Verify tag reused (TagID=1)
        with song_repo._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT TagID FROM Tags WHERE TagName = 'Grunge'"
            ).fetchall()
            assert len(rows) == 1, f"Expected 1 'Grunge' tag (reused), got {len(rows)}"
            assert rows[0]["TagID"] == 1, f"Expected TagID=1, got {rows[0]['TagID']}"
