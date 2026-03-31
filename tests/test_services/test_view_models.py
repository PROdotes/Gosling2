"""
View Model Transform Contract Tests
=====================================
Standalone tests for SongView, AlbumView, IdentityView, SongAlbumView.
Tests the from_domain() factories and computed fields in isolation.

These complement test_catalog.py (which tests views via CatalogService)
by verifying transform logic with controlled domain model inputs.
"""

from typing import Any
from src.models.domain import (
    Song,
    SongCredit,
    SongAlbum,
    Album,
    AlbumCredit,
    Publisher,
    Tag,
    Identity,
    ArtistName,
)
from src.models.view_models import (
    SongView,
    AlbumView,
    IdentityView,
    SongAlbumView,
    SongSlimView,
    AlbumSlimView,
)


# ===========================================================================
# SongView.from_domain
# ===========================================================================
class TestSongViewFromDomain:
    """Test the SongView factory method with hand-built domain objects."""

    def _make_song(self, **overrides: Any) -> Song:
        """Build a Song with sane defaults."""
        defaults: dict[str, Any] = dict(
            id=1,
            type_id=1,
            media_name="Test Song",
            source_path="/test/path",
            duration_s=200.0,
            processing_status=0,
            is_active=True,
            credits=[],
            albums=[],
            publishers=[],
            tags=[],
        )
        defaults.update(overrides)
        return Song(**defaults)  # type: ignore[arg-type]

    def _assert_song_view_defaults(self, view, song):
        """Assert all basic fields are mapped correctly from domain to view."""
        assert view.id == song.id, f"Expected id={song.id}, got {view.id}"
        assert (
            view.title == song.media_name
        ), f"Expected title={song.media_name}, got {view.title}"
        assert (
            view.media_name == song.media_name
        ), f"Expected media_name={song.media_name}, got {view.media_name}"
        assert (
            view.source_path == song.source_path
        ), f"Expected source_path={song.source_path}, got {view.source_path}"
        assert (
            view.duration_s == song.duration_s
        ), f"Expected duration_s={song.duration_s}, got {view.duration_s}"
        assert (
            view.duration_ms == song.duration_ms
        ), f"Expected duration_ms={song.duration_ms}, got {view.duration_ms}"
        assert (
            view.is_active == song.is_active
        ), f"Expected is_active={song.is_active}, got {view.is_active}"
        assert (
            view.audio_hash == song.audio_hash
        ), f"Expected audio_hash={song.audio_hash}, got {view.audio_hash}"
        assert (
            view.processing_status == song.processing_status
        ), f"Expected processing_status={song.processing_status}, got {view.processing_status}"
        assert (
            view.notes == song.notes
        ), f"Expected notes={song.notes}, got {view.notes}"
        assert view.bpm == song.bpm, f"Expected bpm={song.bpm}, got {view.bpm}"
        assert view.year == song.year, f"Expected year={song.year}, got {view.year}"
        assert view.isrc == song.isrc, f"Expected isrc={song.isrc}, got {view.isrc}"
        assert (
            view.raw_tags == song.raw_tags
        ), f"Expected raw_tags={song.raw_tags}, got {view.raw_tags}"

    def test_basic_fields(self):
        """All core fields are mapped from domain Song to SongView."""
        song = self._make_song(id=42, media_name="Hello World", duration_s=185.0)
        view = SongView.from_domain(song)
        self._assert_song_view_defaults(view, song)

    def test_basic_fields_default_optional_values(self):
        """Optional fields (except workflow status) default correctly when not provided."""
        song = self._make_song(
            bpm=None,
            year=None,
            isrc=None,
            notes=None,
            audio_hash=None,
            processing_status=0,
        )
        view = SongView.from_domain(song)
        assert view.bpm is None, f"Expected bpm=None, got {view.bpm}"
        assert view.year is None, f"Expected year=None, got {view.year}"
        assert view.isrc is None, f"Expected isrc=None, got {view.isrc}"
        assert view.notes is None, f"Expected notes=None, got {view.notes}"
        assert (
            view.audio_hash is None
        ), f"Expected audio_hash=None, got {view.audio_hash}"
        assert (
            view.processing_status == 0
        ), f"Expected processing_status=0, got {view.processing_status}"

    def test_formatted_duration_standard(self):
        """3 min 20 sec = 200.0s -> '3:20'."""
        view = SongView.from_domain(self._make_song(duration_s=200.0))
        assert (
            view.formatted_duration == "3:20"
        ), f"Expected '3:20', got '{view.formatted_duration}'"

    def test_formatted_duration_exact_minute(self):
        """Exactly 4 min = 240.0s -> '4:00'."""
        view = SongView.from_domain(self._make_song(duration_s=240.0))
        assert (
            view.formatted_duration == "4:00"
        ), f"Expected '4:00', got '{view.formatted_duration}'"

    def test_formatted_duration_zero(self):
        """Zero duration -> '0:00'."""
        view = SongView.from_domain(self._make_song(duration_s=0.0))
        assert (
            view.formatted_duration == "0:00"
        ), f"Expected '0:00', got '{view.formatted_duration}'"

    def test_formatted_duration_short(self):
        """10 seconds = 10.0s -> '0:10'."""
        view = SongView.from_domain(self._make_song(duration_s=10.0))
        assert (
            view.formatted_duration == "0:10"
        ), f"Expected '0:10', got '{view.formatted_duration}'"

    def test_formatted_duration_one_second(self):
        """1 second = 1.0s -> '0:01'."""
        view = SongView.from_domain(self._make_song(duration_s=1.0))
        assert (
            view.formatted_duration == "0:01"
        ), f"Expected '0:01', got '{view.formatted_duration}'"

    def test_formatted_duration_long(self):
        """10 min 5 sec = 605.0s -> '10:05'."""
        view = SongView.from_domain(self._make_song(duration_s=605.0))
        assert (
            view.formatted_duration == "10:05"
        ), f"Expected '10:05', got '{view.formatted_duration}'"

    # --- display_artist ---
    def test_display_artist_single_performer(self):
        """Single Performer credit yields that performer's name."""
        song = self._make_song(
            credits=[
                SongCredit(
                    source_id=1,
                    name_id=10,
                    identity_id=1,
                    role_id=1,
                    role_name="Performer",
                    display_name="Alice",
                )
            ]
        )
        view = SongView.from_domain(song)
        assert (
            view.display_artist == "Alice"
        ), f"Expected 'Alice', got {view.display_artist}"

    def test_display_artist_multiple_performers(self):
        """Multiple Performer credits are joined with ', '."""
        song = self._make_song(
            credits=[
                SongCredit(
                    source_id=1,
                    name_id=10,
                    identity_id=1,
                    role_id=1,
                    role_name="Performer",
                    display_name="Alice",
                ),
                SongCredit(
                    source_id=1,
                    name_id=20,
                    identity_id=2,
                    role_id=1,
                    role_name="Performer",
                    display_name="Bob",
                ),
            ]
        )
        view = SongView.from_domain(song)
        assert (
            view.display_artist == "Alice, Bob"
        ), f"Expected 'Alice, Bob', got {view.display_artist}"

    def test_display_artist_no_performer_returns_none(self):
        """If no Performer role, display_artist is None. Composers are not Performers."""
        song = self._make_song(
            credits=[
                SongCredit(
                    source_id=1,
                    name_id=10,
                    identity_id=1,
                    role_id=2,
                    role_name="Composer",
                    display_name="Charlie",
                )
            ]
        )
        view = SongView.from_domain(song)
        assert view.display_artist is None, f"Expected None, got {view.display_artist}"

    def test_display_artist_no_credits(self):
        """No credits yields None for display_artist."""
        view = SongView.from_domain(self._make_song(credits=[]))
        assert view.display_artist is None, f"Expected None, got {view.display_artist}"

    def test_display_artist_deduplicates_performers(self):
        """Same performer name appears twice -> only shown once."""
        song = self._make_song(
            credits=[
                SongCredit(
                    source_id=1,
                    name_id=10,
                    identity_id=1,
                    role_id=1,
                    role_name="Performer",
                    display_name="Alice",
                ),
                SongCredit(
                    source_id=1,
                    name_id=11,
                    identity_id=1,
                    role_id=1,
                    role_name="Performer",
                    display_name="Alice",
                ),
            ]
        )
        view = SongView.from_domain(song)
        assert (
            view.display_artist == "Alice"
        ), f"Expected 'Alice', got {view.display_artist}"

    def test_display_artist_only_includes_performers(self):
        """Performer + Composer: display_artist only shows the Performer."""
        song = self._make_song(
            credits=[
                SongCredit(
                    source_id=1,
                    name_id=10,
                    identity_id=1,
                    role_id=1,
                    role_name="Performer",
                    display_name="Alice",
                ),
                SongCredit(
                    source_id=1,
                    name_id=20,
                    identity_id=2,
                    role_id=2,
                    role_name="Composer",
                    display_name="Bob",
                ),
            ]
        )
        view = SongView.from_domain(song)
        assert (
            view.display_artist == "Alice"
        ), f"Expected 'Alice', got {view.display_artist}"

    # --- display_composer ---
    def test_display_composer_single(self):
        """Single Composer credit yields that composer's name."""
        song = self._make_song(
            credits=[
                SongCredit(
                    source_id=1,
                    name_id=20,
                    identity_id=2,
                    role_id=2,
                    role_name="Composer",
                    display_name="Charlie",
                )
            ]
        )
        view = SongView.from_domain(song)
        assert (
            view.display_composer == "Charlie"
        ), f"Expected 'Charlie', got {view.display_composer}"

    def test_display_composer_multiple(self):
        """Multiple Composer credits are joined with ', '."""
        song = self._make_song(
            credits=[
                SongCredit(
                    source_id=1,
                    name_id=10,
                    identity_id=1,
                    role_id=2,
                    role_name="Composer",
                    display_name="Alice",
                ),
                SongCredit(
                    source_id=1,
                    name_id=20,
                    identity_id=2,
                    role_id=2,
                    role_name="Composer",
                    display_name="Bob",
                ),
            ]
        )
        view = SongView.from_domain(song)
        assert (
            view.display_composer == "Alice, Bob"
        ), f"Expected 'Alice, Bob', got {view.display_composer}"

    def test_display_composer_none(self):
        """No composers yields None."""
        view = SongView.from_domain(self._make_song(credits=[]))
        assert view.display_composer is None

    # --- primary_genre ---
    def test_primary_genre_explicit_primary(self):
        """A Genre tag with is_primary=True is selected over other Genre tags."""
        song = self._make_song(
            tags=[
                Tag(id=1, name="Rock", category="Genre", is_primary=False),
                Tag(id=2, name="Alternative", category="Genre", is_primary=True),
            ]
        )
        view = SongView.from_domain(song)
        assert (
            view.primary_genre == "Alternative"
        ), f"Expected 'Alternative', got {view.primary_genre}"

    def test_primary_genre_first_genre_tag(self):
        """No explicit primary -> first 'Genre' category tag wins."""
        song = self._make_song(
            tags=[
                Tag(id=1, name="Energetic", category="Mood", is_primary=False),
                Tag(id=2, name="Rock", category="Genre", is_primary=False),
                Tag(id=3, name="Pop", category="Genre", is_primary=False),
            ]
        )
        view = SongView.from_domain(song)
        assert (
            view.primary_genre == "Rock"
        ), f"Expected 'Rock', got {view.primary_genre}"

    def test_primary_genre_no_genre_tags(self):
        """Only non-Genre tags -> None."""
        song = self._make_song(
            tags=[
                Tag(id=1, name="Energetic", category="Mood", is_primary=False),
            ]
        )
        view = SongView.from_domain(song)
        assert view.primary_genre is None, f"Expected None, got {view.primary_genre}"

    def test_primary_genre_no_tags(self):
        """No tags at all -> None."""
        view = SongView.from_domain(self._make_song(tags=[]))
        assert view.primary_genre is None, f"Expected None, got {view.primary_genre}"

    def test_primary_genre_ignores_non_genre_is_primary(self):
        """A Mood tag marked is_primary=True does NOT become primary_genre. Moods are not Genres."""
        song = self._make_song(
            tags=[
                Tag(id=1, name="Rock", category="Genre", is_primary=False),
                Tag(id=2, name="Happy", category="Mood", is_primary=True),
            ]
        )
        view = SongView.from_domain(song)
        assert (
            view.primary_genre == "Rock"
        ), f"Expected 'Rock', got {view.primary_genre}"

    # --- display_genres ---
    def test_display_genres_single(self):
        """Single Genre tag yields its name."""
        song = self._make_song(
            tags=[Tag(id=1, name="Rock", category="Genre")]
        )
        view = SongView.from_domain(song)
        assert view.display_genres == "Rock"

    def test_display_genres_multiple(self):
        """Multiple Genre tags are joined with ', '."""
        song = self._make_song(
            tags=[
                Tag(id=1, name="Rock", category="Genre"),
                Tag(id=2, name="Pop", category="Genre"),
            ]
        )
        view = SongView.from_domain(song)
        assert view.display_genres == "Rock, Pop"

    def test_display_genres_none(self):
        """No Genre tags yields None."""
        view = SongView.from_domain(self._make_song(tags=[]))
        assert view.display_genres is None

    # --- display_master_publisher ---
    def test_display_master_publisher_single(self):
        """Single publisher without parent yields just the name."""
        song = self._make_song(
            publishers=[Publisher(id=1, name="Universal", parent_name=None)]
        )
        view = SongView.from_domain(song)
        assert (
            view.display_master_publisher == "Universal"
        ), f"Expected 'Universal', got {view.display_master_publisher}"

    def test_display_master_publisher_with_parent(self):
        """Publisher with parent yields 'Name (Parent)'."""
        song = self._make_song(
            publishers=[Publisher(id=10, name="DGC Records", parent_name="Universal")]
        )
        view = SongView.from_domain(song)
        assert (
            view.display_master_publisher == "DGC Records (Universal)"
        ), f"Expected 'DGC Records (Universal)', got {view.display_master_publisher}"

    def test_display_master_publisher_multiple(self):
        """Multiple publishers are joined with ', '."""
        song = self._make_song(
            publishers=[
                Publisher(id=10, name="DGC Records", parent_name="Universal"),
                Publisher(id=5, name="Sub Pop", parent_name=None),
            ]
        )
        view = SongView.from_domain(song)
        assert (
            view.display_master_publisher == "DGC Records (Universal), Sub Pop"
        ), f"Expected 'DGC Records (Universal), Sub Pop', got {view.display_master_publisher}"

    def test_display_master_publisher_empty(self):
        """No publishers yields empty string."""
        view = SongView.from_domain(self._make_song(publishers=[]))
        assert (
            view.display_master_publisher == ""
        ), f"Expected '', got {view.display_master_publisher}"

    # --- albums mapping ---
    def test_albums_mapped_to_song_album_views(self):
        """SongAlbum domain objects become SongAlbumView objects with all fields."""
        song = self._make_song(
            albums=[
                SongAlbum(
                    source_id=1,
                    album_id=100,
                    album_title="Nevermind",
                    track_number=5,
                    disc_number=1,
                    release_year=1991,
                )
            ]
        )
        view = SongView.from_domain(song)
        assert len(view.albums) == 1, f"Expected 1 album, got {len(view.albums)}"
        album_view = view.albums[0]
        assert isinstance(
            album_view, SongAlbumView
        ), f"Expected SongAlbumView, got {type(album_view)}"
        assert (
            album_view.source_id == 1
        ), f"Expected source_id=1, got {album_view.source_id}"
        assert (
            album_view.album_id == 100
        ), f"Expected album_id=100, got {album_view.album_id}"
        assert (
            album_view.album_title == "Nevermind"
        ), f"Expected album_title='Nevermind', got {album_view.album_title}"
        assert (
            album_view.track_number == 5
        ), f"Expected track_number=5, got {album_view.track_number}"
        assert (
            album_view.disc_number == 1
        ), f"Expected disc_number=1, got {album_view.disc_number}"
        assert (
            album_view.release_year == 1991
        ), f"Expected release_year=1991, got {album_view.release_year}"
        assert (
            album_view.album_type is None
        ), f"Expected album_type=None, got {album_view.album_type}"
        assert (
            album_view.album_publishers == []
        ), f"Expected album_publishers=[], got {album_view.album_publishers}"
        assert (
            album_view.credits == []
        ), f"Expected credits=[], got {album_view.credits}"

    def test_albums_empty(self):
        """No albums yields empty list."""
        view = SongView.from_domain(self._make_song(albums=[]))
        assert view.albums == [], f"Expected albums=[], got {view.albums}"

    # --- empty collections ---
    def test_credits_empty(self):
        """No credits yields empty list."""
        view = SongView.from_domain(self._make_song(credits=[]))
        assert view.credits == [], f"Expected credits=[], got {view.credits}"

    def test_publishers_empty(self):
        """No publishers yields empty list."""
        view = SongView.from_domain(self._make_song(publishers=[]))
        assert view.publishers == [], f"Expected publishers=[], got {view.publishers}"

    def test_tags_empty(self):
        """No tags yields empty list."""
        view = SongView.from_domain(self._make_song(tags=[]))
        assert view.tags == [], f"Expected tags=[], got {view.tags}"


# ===========================================================================
# SongView.review_blockers
# ===========================================================================
class TestSongViewReviewWorkflow:
    """Tests the review_blockers logic from SONG_WORKFLOW_SPEC.md."""

    def _make_song_view(self, **overrides) -> SongView:
        defaults = {
            "id": 1,
            "media_name": "Test Song",
            "title": "Test Song",
            "source_path": "/test/path",
            "duration_s": 180.0,
            "year": 2024,
            "credits": [
                SongCredit(role_name="Performer", display_name="Artist A"),
                SongCredit(role_name="Composer", display_name="Artist B"),
            ],
            "tags": [Tag(name="Rock", category="Genre")],
            "publishers": [Publisher(name="Pub A")],
            "processing_status": 1,
        }
        defaults.update(overrides)
        return SongView(**defaults)

    def test_ready_flow_all_fields_present(self):
        """Standard valid song has no blockers."""
        view = self._make_song_view()
        assert view.review_blockers == []

    def test_ready_flow_missing_performer(self):
        """Required: at least 1 Performer."""
        view = self._make_song_view(
            credits=[SongCredit(role_name="Composer", display_name="Artist B")]
        )
        assert "performers" in view.review_blockers

    def test_ready_flow_missing_composer(self):
        """Required: at least 1 Composer."""
        view = self._make_song_view(
            credits=[SongCredit(role_name="Performer", display_name="Artist A")]
        )
        assert "composers" in view.review_blockers

    def test_ready_flow_missing_genre(self):
        """Required: at least 1 Genre tag."""
        view = self._make_song_view(tags=[Tag(name="Fast", category="Tempo")])
        assert "genres" in view.review_blockers

    def test_ready_flow_missing_publisher(self):
        """Required: at least 1 Publisher."""
        view = self._make_song_view(publishers=[])
        assert "publishers" in view.review_blockers

    def test_ready_flow_missing_year(self):
        """Required: Year."""
        view = self._make_song_view(year=None)
        assert "year" in view.review_blockers

    def test_ready_flow_already_approved(self):
        """Songs already at status 0 still report blockers correctly."""
        view = self._make_song_view(processing_status=0)
        assert view.review_blockers == []


# ===========================================================================
# SongAlbumView computed fields
# ===========================================================================
class TestSongAlbumViewComputed:
    """Test SongAlbumView computed fields with hand-built instances."""

    def test_display_title_with_track(self):
        """Track number only (disc=1) yields '[05] Title'."""
        v = SongAlbumView(album_title="Nevermind", track_number=5, disc_number=1)
        assert (
            v.display_title == "[05] Nevermind"
        ), f"Expected '[05] Nevermind', got '{v.display_title}'"

    def test_display_title_with_disc_and_track(self):
        """Disc > 1 yields '[2-03] Title'."""
        v = SongAlbumView(album_title="Nevermind", track_number=3, disc_number=2)
        assert (
            v.display_title == "[2-03] Nevermind"
        ), f"Expected '[2-03] Nevermind', got '{v.display_title}'"

    def test_display_title_no_track(self):
        """No track number yields bare title."""
        v = SongAlbumView(album_title="Nevermind", track_number=None, disc_number=1)
        assert (
            v.display_title == "Nevermind"
        ), f"Expected 'Nevermind', got '{v.display_title}'"

    def test_display_publisher_single(self):
        """Single publisher with parent yields 'Name (Parent)'."""
        v = SongAlbumView(
            album_title="Test",
            album_publishers=[
                Publisher(id=1, name="DGC Records", parent_name="Universal")
            ],
        )
        assert (
            v.display_publisher == "DGC Records (Universal)"
        ), f"Expected 'DGC Records (Universal)', got '{v.display_publisher}'"

    def test_display_publisher_empty(self):
        """No publishers yields empty string."""
        v = SongAlbumView(album_title="Test", album_publishers=[])
        assert v.display_publisher == "", f"Expected '', got '{v.display_publisher}'"

    def test_display_publisher_multiple(self):
        """Multiple publishers are joined with ', '."""
        v = SongAlbumView(
            album_title="Test",
            album_publishers=[
                Publisher(id=1, name="DGC", parent_name="UMG"),
                Publisher(id=2, name="Sub Pop", parent_name=None),
            ],
        )
        assert (
            v.display_publisher == "DGC (UMG), Sub Pop"
        ), f"Expected 'DGC (UMG), Sub Pop', got '{v.display_publisher}'"

    def test_all_fields_default(self):
        """SongAlbumView defaults are correct when only album_title is set."""
        v = SongAlbumView(album_title="Test")
        assert v.source_id is None, f"Expected source_id=None, got {v.source_id}"
        assert v.album_id is None, f"Expected album_id=None, got {v.album_id}"
        assert (
            v.album_title == "Test"
        ), f"Expected album_title='Test', got {v.album_title}"
        assert (
            v.track_number is None
        ), f"Expected track_number=None, got {v.track_number}"
        assert v.disc_number is None, f"Expected disc_number=None, got {v.disc_number}"
        assert v.album_type is None, f"Expected album_type=None, got {v.album_type}"
        assert (
            v.release_year is None
        ), f"Expected release_year=None, got {v.release_year}"
        assert (
            v.album_publishers == []
        ), f"Expected album_publishers=[], got {v.album_publishers}"
        assert v.credits == [], f"Expected credits=[], got {v.credits}"

    def test_display_title_disc_1_no_prefix(self):
        """Disc number 1 does NOT add disc prefix."""
        v = SongAlbumView(album_title="Nevermind", track_number=7, disc_number=1)
        assert (
            v.display_title == "[07] Nevermind"
        ), f"Expected '[07] Nevermind', got '{v.display_title}'"


# ===========================================================================
# AlbumView.from_domain
# ===========================================================================
class TestAlbumViewFromDomain:
    """Test AlbumView factory with hand-built domain Album objects."""

    def _make_album(self, **overrides: Any) -> Album:
        """Build an Album with sane defaults."""
        defaults: dict[str, Any] = dict(
            id=100,
            title="Test Album",
            release_year=2000,
            publishers=[],
            credits=[],
            songs=[],
        )
        defaults.update(overrides)
        return Album(**defaults)  # type: ignore[arg-type]

    def _make_song(self, **overrides: Any) -> Song:
        """Build a Song with sane defaults."""
        defaults: dict[str, Any] = dict(
            id=1,
            type_id=1,
            media_name="Song",
            source_path="/p",
            duration_s=180.0,
            processing_status=0,
            is_active=True,
        )
        defaults.update(overrides)
        return Song(**defaults)  # type: ignore[arg-type]

    def test_basic_fields(self):
        """Core AlbumView fields are mapped from domain Album."""
        album = self._make_album(id=42, title="My Album", release_year=1999)
        view = AlbumView.from_domain(album)
        assert view.id == 42, f"Expected id=42, got {view.id}"
        assert view.title == "My Album", f"Expected title='My Album', got {view.title}"
        assert (
            view.release_year == 1999
        ), f"Expected release_year=1999, got {view.release_year}"
        assert (
            view.album_type is None
        ), f"Expected album_type=None, got {view.album_type}"
        assert view.publishers == [], f"Expected publishers=[], got {view.publishers}"
        assert view.credits == [], f"Expected credits=[], got {view.credits}"

    def test_basic_fields_with_album_type(self):
        """album_type is preserved when provided."""
        album = self._make_album(id=10, title="Deluxe", album_type="LP")
        view = AlbumView.from_domain(album)
        assert (
            view.album_type == "LP"
        ), f"Expected album_type='LP', got {view.album_type}"

    def test_song_count(self):
        """song_count reflects the number of songs in the album."""
        album = self._make_album(
            songs=[
                self._make_song(id=1, media_name="A"),
                self._make_song(id=2, media_name="B"),
            ]
        )
        view = AlbumView.from_domain(album)
        assert view.song_count == 2, f"Expected song_count=2, got {view.song_count}"

    def test_song_count_zero(self):
        """song_count is 0 when there are no songs."""
        view = AlbumView.from_domain(self._make_album(songs=[]))
        assert view.song_count == 0, f"Expected song_count=0, got {view.song_count}"

    def test_songs_are_song_views(self):
        """Domain Songs are converted to SongView objects."""
        album = self._make_album(songs=[self._make_song(id=1, media_name="Track One")])
        view = AlbumView.from_domain(album)
        assert len(view.songs) == 1, f"Expected 1 song, got {len(view.songs)}"
        song_view = view.songs[0]
        assert isinstance(
            song_view, SongView
        ), f"Expected SongView, got {type(song_view)}"
        assert song_view.id == 1, f"Expected song id=1, got {song_view.id}"
        assert (
            song_view.title == "Track One"
        ), f"Expected title='Track One', got {song_view.title}"
        assert (
            song_view.media_name == "Track One"
        ), f"Expected media_name='Track One', got {song_view.media_name}"
        assert (
            song_view.source_path == "/p"
        ), f"Expected source_path='/p', got {song_view.source_path}"
        assert (
            song_view.duration_s == 180.0
        ), f"Expected duration_s=180.0, got {song_view.duration_s}"
        assert (
            song_view.is_active is True
        ), f"Expected is_active=True, got {song_view.is_active}"

    def test_display_publisher_with_parent(self):
        """Publisher with parent yields 'Name (Parent)'."""
        album = self._make_album(
            publishers=[Publisher(id=10, name="DGC", parent_name="Universal")]
        )
        view = AlbumView.from_domain(album)
        assert (
            view.display_publisher == "DGC (Universal)"
        ), f"Expected 'DGC (Universal)', got {view.display_publisher}"

    def test_display_publisher_empty(self):
        """No publishers yields empty string."""
        view = AlbumView.from_domain(self._make_album(publishers=[]))
        assert (
            view.display_publisher == ""
        ), f"Expected '', got {view.display_publisher}"

    def test_display_artist_single_performer(self):
        """Single Performer credit yields that performer's name."""
        album = self._make_album(
            credits=[
                AlbumCredit(
                    album_id=100,
                    name_id=20,
                    identity_id=2,
                    role_id=1,
                    role_name="Performer",
                    display_name="Nirvana",
                )
            ]
        )
        view = AlbumView.from_domain(album)
        assert (
            view.display_artist == "Nirvana"
        ), f"Expected 'Nirvana', got {view.display_artist}"

    def test_display_artist_multiple_performers(self):
        """Multiple Performer credits are joined with ', '."""
        album = self._make_album(
            credits=[
                AlbumCredit(
                    album_id=100,
                    name_id=20,
                    identity_id=2,
                    role_id=1,
                    role_name="Performer",
                    display_name="Alice",
                ),
                AlbumCredit(
                    album_id=100,
                    name_id=30,
                    identity_id=3,
                    role_id=1,
                    role_name="Performer",
                    display_name="Bob",
                ),
            ]
        )
        view = AlbumView.from_domain(album)
        assert (
            view.display_artist == "Alice, Bob"
        ), f"Expected 'Alice, Bob', got {view.display_artist}"

    def test_display_artist_no_performer_returns_none(self):
        """Composers are not Performers. display_artist should be None."""
        album = self._make_album(
            credits=[
                AlbumCredit(
                    album_id=100,
                    name_id=20,
                    identity_id=2,
                    role_id=2,
                    role_name="Composer",
                    display_name="Composer X",
                )
            ]
        )
        view = AlbumView.from_domain(album)
        assert view.display_artist is None, f"Expected None, got {view.display_artist}"

    def test_display_artist_no_credits(self):
        """No credits yields None for display_artist."""
        view = AlbumView.from_domain(self._make_album(credits=[]))
        assert view.display_artist is None, f"Expected None, got {view.display_artist}"


# ===========================================================================
# IdentityView.from_domain
# ===========================================================================
class TestIdentityViewFromDomain:
    """Test IdentityView factory with hand-built domain Identity objects."""

    def test_person_basic(self):
        """A person Identity maps all core fields to IdentityView."""
        identity = Identity(
            id=1,
            type="person",
            display_name="Dave Grohl",
            aliases=[],
            members=[],
            groups=[],
        )
        view = IdentityView.from_domain(identity)
        assert view.id == 1, f"Expected id=1, got {view.id}"
        assert view.type == "person", f"Expected type='person', got {view.type}"
        assert (
            view.display_name == "Dave Grohl"
        ), f"Expected display_name='Dave Grohl', got {view.display_name}"
        assert (
            view.legal_name is None
        ), f"Expected legal_name=None, got {view.legal_name}"
        assert view.aliases == [], f"Expected aliases=[], got {view.aliases}"
        assert view.members == [], f"Expected members=[], got {view.members}"
        assert view.groups == [], f"Expected groups=[], got {view.groups}"

    def test_person_with_legal_name(self):
        """legal_name is preserved when provided."""
        identity = Identity(
            id=1,
            type="person",
            display_name="Dave Grohl",
            legal_name="David Eric Grohl",
        )
        view = IdentityView.from_domain(identity)
        assert view.id == 1, f"Expected id=1, got {view.id}"
        assert view.type == "person", f"Expected type='person', got {view.type}"
        assert (
            view.display_name == "Dave Grohl"
        ), f"Expected display_name='Dave Grohl', got {view.display_name}"
        assert (
            view.legal_name == "David Eric Grohl"
        ), f"Expected legal_name='David Eric Grohl', got {view.legal_name}"
        assert view.aliases == [], f"Expected aliases=[], got {view.aliases}"
        assert view.members == [], f"Expected members=[], got {view.members}"
        assert view.groups == [], f"Expected groups=[], got {view.groups}"

    def test_aliases_preserved(self):
        """Aliases are mapped as ArtistName domain objects."""
        identity = Identity(
            id=1,
            type="person",
            display_name="Dave Grohl",
            aliases=[
                ArtistName(id=11, display_name="Grohlton", is_primary=False),
                ArtistName(id=12, display_name="Late!", is_primary=False),
            ],
        )
        view = IdentityView.from_domain(identity)
        assert len(view.aliases) == 2, f"Expected 2 aliases, got {len(view.aliases)}"
        assert isinstance(
            view.aliases[0], ArtistName
        ), f"Expected ArtistName, got {type(view.aliases[0])}"
        assert (
            view.aliases[0].id == 11
        ), f"Expected alias id=11, got {view.aliases[0].id}"
        assert (
            view.aliases[0].display_name == "Grohlton"
        ), f"Expected 'Grohlton', got {view.aliases[0].display_name}"
        assert (
            view.aliases[0].is_primary is False
        ), f"Expected is_primary=False, got {view.aliases[0].is_primary}"
        assert (
            view.aliases[1].id == 12
        ), f"Expected alias id=12, got {view.aliases[1].id}"
        assert (
            view.aliases[1].display_name == "Late!"
        ), f"Expected 'Late!', got {view.aliases[1].display_name}"
        assert (
            view.aliases[1].is_primary is False
        ), f"Expected is_primary=False, got {view.aliases[1].is_primary}"

    def test_group_with_members(self):
        """Group Identity maps members as recursive IdentityView objects."""
        member = Identity(
            id=1,
            type="person",
            display_name="Dave Grohl",
            aliases=[],
            members=[],
            groups=[],
        )
        group = Identity(
            id=2,
            type="group",
            display_name="Nirvana",
            aliases=[],
            members=[member],
            groups=[],
        )
        view = IdentityView.from_domain(group)
        assert view.id == 2, f"Expected id=2, got {view.id}"
        assert view.type == "group", f"Expected type='group', got {view.type}"
        assert (
            view.display_name == "Nirvana"
        ), f"Expected display_name='Nirvana', got {view.display_name}"
        assert len(view.members) == 1, f"Expected 1 member, got {len(view.members)}"
        assert isinstance(
            view.members[0], IdentityView
        ), f"Expected IdentityView, got {type(view.members[0])}"
        assert (
            view.members[0].id == 1
        ), f"Expected member id=1, got {view.members[0].id}"
        assert (
            view.members[0].type == "person"
        ), f"Expected member type='person', got {view.members[0].type}"
        assert (
            view.members[0].display_name == "Dave Grohl"
        ), f"Expected 'Dave Grohl', got {view.members[0].display_name}"
        assert (
            view.members[0].members == []
        ), f"Expected member members=[], got {view.members[0].members}"
        assert (
            view.members[0].groups == []
        ), f"Expected member groups=[], got {view.members[0].groups}"
        assert view.groups == [], f"Expected groups=[], got {view.groups}"

    def test_person_with_groups(self):
        """Person Identity maps groups as recursive IdentityView objects."""
        group = Identity(
            id=2,
            type="group",
            display_name="Nirvana",
            aliases=[],
            members=[],
            groups=[],
        )
        person = Identity(
            id=1,
            type="person",
            display_name="Dave Grohl",
            aliases=[],
            members=[],
            groups=[group],
        )
        view = IdentityView.from_domain(person)
        assert view.id == 1, f"Expected id=1, got {view.id}"
        assert view.type == "person", f"Expected type='person', got {view.type}"
        assert (
            view.display_name == "Dave Grohl"
        ), f"Expected display_name='Dave Grohl', got {view.display_name}"
        assert view.members == [], f"Expected members=[], got {view.members}"
        assert len(view.groups) == 1, f"Expected 1 group, got {len(view.groups)}"
        assert isinstance(
            view.groups[0], IdentityView
        ), f"Expected IdentityView, got {type(view.groups[0])}"
        assert view.groups[0].id == 2, f"Expected group id=2, got {view.groups[0].id}"
        assert (
            view.groups[0].type == "group"
        ), f"Expected group type='group', got {view.groups[0].type}"
        assert (
            view.groups[0].display_name == "Nirvana"
        ), f"Expected 'Nirvana', got {view.groups[0].display_name}"
        assert (
            view.groups[0].members == []
        ), f"Expected group members=[], got {view.groups[0].members}"
        assert (
            view.groups[0].groups == []
        ), f"Expected group groups=[], got {view.groups[0].groups}"

    def test_recursive_depth(self):
        """Members and groups are IdentityViews at all nesting levels."""
        inner = Identity(
            id=3,
            type="person",
            display_name="Inner",
            aliases=[],
            members=[],
            groups=[],
        )
        middle = Identity(
            id=2,
            type="group",
            display_name="Middle",
            aliases=[],
            members=[inner],
            groups=[],
        )
        outer = Identity(
            id=1,
            type="group",
            display_name="Outer",
            aliases=[],
            members=[middle],
            groups=[],
        )
        view = IdentityView.from_domain(outer)
        assert view.id == 1, f"Expected id=1, got {view.id}"
        assert view.type == "group", f"Expected type='group', got {view.type}"
        assert (
            view.display_name == "Outer"
        ), f"Expected display_name='Outer', got {view.display_name}"
        assert len(view.members) == 1, f"Expected 1 member, got {len(view.members)}"
        assert (
            view.members[0].display_name == "Middle"
        ), f"Expected 'Middle', got {view.members[0].display_name}"
        assert isinstance(
            view.members[0], IdentityView
        ), f"Expected IdentityView, got {type(view.members[0])}"
        assert (
            len(view.members[0].members) == 1
        ), f"Expected 1 inner member, got {len(view.members[0].members)}"
        assert (
            view.members[0].members[0].display_name == "Inner"
        ), f"Expected 'Inner', got {view.members[0].members[0].display_name}"
        assert isinstance(
            view.members[0].members[0], IdentityView
        ), f"Expected IdentityView, got {type(view.members[0].members[0])}"
        assert (
            view.members[0].members[0].members == []
        ), f"Expected empty members at deepest level, got {view.members[0].members[0].members}"
        assert view.groups == [], f"Expected groups=[], got {view.groups}"

    def test_group_no_display_name(self):
        """IdentityView handles None display_name."""
        identity = Identity(
            id=99,
            type="placeholder",
            display_name=None,
        )
        view = IdentityView.from_domain(identity)
        assert view.id == 99, f"Expected id=99, got {view.id}"
        assert (
            view.type == "placeholder"
        ), f"Expected type='placeholder', got {view.type}"
        assert (
            view.display_name is None
        ), f"Expected display_name=None, got {view.display_name}"
        assert (
            view.legal_name is None
        ), f"Expected legal_name=None, got {view.legal_name}"
        assert view.aliases == [], f"Expected aliases=[], got {view.aliases}"
        assert view.members == [], f"Expected members=[], got {view.members}"
        assert view.groups == [], f"Expected groups=[], got {view.groups}"


# ===========================================================================
# SongSlimView.from_row
# ===========================================================================
class TestSongSlimViewFromRow:
    """SongSlimView.from_row mapper contracts."""

    def _make_row(self, **overrides) -> dict:
        base = {
            "SourceID": 1,
            "MediaName": "Smells Like Teen Spirit",
            "SourcePath": "/path/1",
            "SourceDuration": 200,
            "RecordingYear": 1991,
            "TempoBPM": 120,
            "ISRC": "USRC17607839",
            "IsActive": 1,
            "ProcessingStatus": 1,
            "DisplayArtist": "Nirvana",
            "PrimaryGenre": "Grunge",
        }
        base.update(overrides)
        return base

    def test_all_fields_present(self):
        """from_row maps all fields correctly from a complete row."""
        row = self._make_row()
        view = SongSlimView.from_row(row)

        assert view.id == 1, f"Expected id=1, got {view.id}"
        assert (
            view.media_name == "Smells Like Teen Spirit"
        ), f"Expected 'Smells Like Teen Spirit', got '{view.media_name}'"
        assert (
            view.title == "Smells Like Teen Spirit"
        ), f"Expected title='Smells Like Teen Spirit', got '{view.title}'"
        assert (
            view.source_path == "/path/1"
        ), f"Expected '/path/1', got '{view.source_path}'"
        assert view.duration_s == 200.0, f"Expected 200.0, got {view.duration_s}"
        assert view.year == 1991, f"Expected 1991, got {view.year}"
        assert view.bpm == 120, f"Expected 120, got {view.bpm}"
        assert (
            view.isrc == "USRC17607839"
        ), f"Expected 'USRC17607839', got '{view.isrc}'"
        assert view.is_active is True, f"Expected True, got {view.is_active}"
        assert (
            view.processing_status == 1
        ), f"Expected processing_status=1, got {view.processing_status}"
        assert (
            view.display_artist == "Nirvana"
        ), f"Expected 'Nirvana', got '{view.display_artist}'"
        assert (
            view.primary_genre == "Grunge"
        ), f"Expected 'Grunge', got '{view.primary_genre}'"

    def test_null_optional_fields_map_to_none(self):
        """NULL optional fields (year, bpm, isrc, artist, genre) become None."""
        row = self._make_row(
            RecordingYear=None,
            TempoBPM=None,
            ISRC=None,
            DisplayArtist=None,
            PrimaryGenre=None,
        )
        view = SongSlimView.from_row(row)

        assert view.year is None, f"Expected None for NULL year, got {view.year}"
        assert view.bpm is None, f"Expected None for NULL bpm, got {view.bpm}"
        assert view.isrc is None, f"Expected None for NULL isrc, got {view.isrc}"
        assert (
            view.display_artist is None
        ), f"Expected None for NULL artist, got {view.display_artist}"
        assert (
            view.primary_genre is None
        ), f"Expected None for NULL genre, got {view.primary_genre}"

    def test_is_active_int_to_bool(self):
        """IsActive=1 maps to True, IsActive=0 maps to False."""
        active_view = SongSlimView.from_row(self._make_row(IsActive=1))
        inactive_view = SongSlimView.from_row(self._make_row(IsActive=0))

        assert (
            active_view.is_active is True
        ), f"Expected True for IsActive=1, got {active_view.is_active}"
        assert (
            inactive_view.is_active is False
        ), f"Expected False for IsActive=0, got {inactive_view.is_active}"

    def test_status_mapping(self):
        """ProcessingStatus maps directly; missing key defaults to 0."""
        status_0_view = SongSlimView.from_row(self._make_row(ProcessingStatus=0))
        assert (
            status_0_view.processing_status == 0
        ), f"Expected 0, got {status_0_view.processing_status}"

        # Test that missing key raises KeyError (Fail-Fast)
        row = self._make_row()
        del row["ProcessingStatus"]
        import pytest

        with pytest.raises(KeyError):
            SongSlimView.from_row(row)

    def test_null_duration_defaults_to_zero(self):
        """NULL SourceDuration maps to 0.0 (never raises)."""
        row = self._make_row(SourceDuration=None)
        view = SongSlimView.from_row(row)

        assert (
            view.duration_s == 0.0
        ), f"Expected 0.0 for NULL duration, got {view.duration_s}"

    def test_formatted_duration_computed(self):
        """formatted_duration converts seconds to M:SS string."""
        row = self._make_row(SourceDuration=200)
        view = SongSlimView.from_row(row)

        assert (
            view.formatted_duration == "3:20"
        ), f"Expected '3:20' for 200s, got '{view.formatted_duration}'"

    def test_formatted_duration_zero(self):
        """formatted_duration returns '0:00' when duration is 0."""
        row = self._make_row(SourceDuration=0)
        view = SongSlimView.from_row(row)

        assert (
            view.formatted_duration == "0:00"
        ), f"Expected '0:00' for 0s, got '{view.formatted_duration}'"


# ===========================================================================
# AlbumSlimView.from_row
# ===========================================================================
class TestAlbumSlimViewFromRow:
    """AlbumSlimView.from_row mapper contracts."""

    def _make_row(self, **overrides) -> dict:
        base = {
            "AlbumID": 100,
            "AlbumTitle": "Nevermind",
            "AlbumType": None,
            "ReleaseYear": 1991,
            "DisplayArtist": "Nirvana",
            "DisplayPublisher": "DGC Records",
            "SongCount": 5,
        }
        base.update(overrides)
        return base

    def test_all_fields_present(self):
        """from_row maps all fields correctly from a complete row."""
        row = self._make_row()
        view = AlbumSlimView.from_row(row)

        assert view.id == 100, f"Expected id=100, got {view.id}"
        assert view.title == "Nevermind", f"Expected 'Nevermind', got '{view.title}'"
        assert (
            view.album_type is None
        ), f"Expected album_type=None, got {view.album_type!r}"
        assert view.release_year == 1991, f"Expected 1991, got {view.release_year}"
        assert (
            view.display_artist == "Nirvana"
        ), f"Expected 'Nirvana', got '{view.display_artist}'"
        assert (
            view.display_publisher == "DGC Records"
        ), f"Expected 'DGC Records', got '{view.display_publisher}'"
        assert view.song_count == 5, f"Expected 5, got {view.song_count}"

    def test_null_optional_fields_map_to_none(self):
        """NULL optional fields (album_type, year, artist, publisher) become None."""
        row = self._make_row(
            AlbumType=None,
            ReleaseYear=None,
            DisplayArtist=None,
            DisplayPublisher=None,
        )
        view = AlbumSlimView.from_row(row)

        assert (
            view.album_type is None
        ), f"Expected None for NULL album_type, got {view.album_type!r}"
        assert (
            view.release_year is None
        ), f"Expected None for NULL year, got {view.release_year}"
        assert (
            view.display_artist is None
        ), f"Expected None for NULL artist, got {view.display_artist}"
        assert (
            view.display_publisher is None
        ), f"Expected None for NULL publisher, got {view.display_publisher}"

    def test_song_count_zero(self):
        """SongCount=0 maps to song_count=0."""
        row = self._make_row(SongCount=0)
        view = AlbumSlimView.from_row(row)

        assert view.song_count == 0, f"Expected 0, got {view.song_count}"
