"""
View Model Transform Contract Tests
=====================================
Standalone tests for SongView, AlbumView, IdentityView, SongAlbumView.
Tests the from_domain() factories and computed fields in isolation.

These complement test_catalog.py (which tests views via CatalogService)
by verifying transform logic with controlled domain model inputs.
"""

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
from src.models.view_models import SongView, AlbumView, IdentityView, SongAlbumView


# ===========================================================================
# SongView.from_domain
# ===========================================================================
class TestSongViewFromDomain:
    """Test the SongView factory method with hand-built domain objects."""

    def _make_song(self, **overrides):
        """Helper to build a Song with sane defaults."""
        defaults = dict(
            id=1,
            type_id=1,
            media_name="Test Song",
            source_path="/test/path",
            duration_ms=200000,
            is_active=True,
            credits=[],
            albums=[],
            publishers=[],
            tags=[],
        )
        defaults.update(overrides)
        return Song(**defaults)

    def test_basic_fields(self):
        song = self._make_song(id=42, media_name="Hello World", duration_ms=185000)
        view = SongView.from_domain(song)
        assert view.id == 42
        assert view.title == "Hello World"
        assert view.media_name == "Hello World"
        assert view.duration_ms == 185000
        assert view.source_path == "/test/path"

    def test_formatted_duration_standard(self):
        """3 min 20 sec = 200000ms -> '3:20'."""
        view = SongView.from_domain(self._make_song(duration_ms=200000))
        assert view.formatted_duration == "3:20"

    def test_formatted_duration_exact_minute(self):
        """Exactly 4 min = 240000ms -> '4:00'."""
        view = SongView.from_domain(self._make_song(duration_ms=240000))
        assert view.formatted_duration == "4:00"

    def test_formatted_duration_zero(self):
        """Zero duration -> '0:00'."""
        view = SongView.from_domain(self._make_song(duration_ms=0))
        assert view.formatted_duration == "0:00"

    def test_formatted_duration_short(self):
        """10 seconds = 10000ms -> '0:10'."""
        view = SongView.from_domain(self._make_song(duration_ms=10000))
        assert view.formatted_duration == "0:10"

    def test_formatted_duration_one_second(self):
        """1 second = 1000ms -> '0:01'."""
        view = SongView.from_domain(self._make_song(duration_ms=1000))
        assert view.formatted_duration == "0:01"

    def test_formatted_duration_long(self):
        """10 min 5 sec = 605000ms -> '10:05'."""
        view = SongView.from_domain(self._make_song(duration_ms=605000))
        assert view.formatted_duration == "10:05"

    # --- display_artist ---
    def test_display_artist_single_performer(self):
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
        assert view.display_artist == "Alice"

    def test_display_artist_multiple_performers(self):
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
        assert view.display_artist == "Alice, Bob"

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
        assert view.display_artist is None

    def test_display_artist_no_credits(self):
        view = SongView.from_domain(self._make_song(credits=[]))
        assert view.display_artist is None

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
        assert view.display_artist == "Alice"

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
        assert view.display_artist == "Alice"

    # --- primary_genre ---
    def test_primary_genre_explicit_primary(self):
        song = self._make_song(
            tags=[
                Tag(id=1, name="Rock", category="Genre", is_primary=False),
                Tag(id=2, name="Alternative", category="Genre", is_primary=True),
            ]
        )
        view = SongView.from_domain(song)
        assert view.primary_genre == "Alternative"

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
        assert view.primary_genre == "Rock"

    def test_primary_genre_no_genre_tags(self):
        """Only non-Genre tags -> None."""
        song = self._make_song(
            tags=[
                Tag(id=1, name="Energetic", category="Mood", is_primary=False),
            ]
        )
        view = SongView.from_domain(song)
        assert view.primary_genre is None

    def test_primary_genre_no_tags(self):
        view = SongView.from_domain(self._make_song(tags=[]))
        assert view.primary_genre is None

    def test_primary_genre_ignores_non_genre_is_primary(self):
        """A Mood tag marked is_primary=True does NOT become primary_genre. Moods are not Genres."""
        song = self._make_song(
            tags=[
                Tag(id=1, name="Rock", category="Genre", is_primary=False),
                Tag(id=2, name="Happy", category="Mood", is_primary=True),
            ]
        )
        view = SongView.from_domain(song)
        assert view.primary_genre == "Rock"

    # --- display_master_publisher ---
    def test_display_master_publisher_single(self):
        song = self._make_song(
            publishers=[Publisher(id=1, name="Universal", parent_name=None)]
        )
        view = SongView.from_domain(song)
        assert view.display_master_publisher == "Universal"

    def test_display_master_publisher_with_parent(self):
        song = self._make_song(
            publishers=[Publisher(id=10, name="DGC Records", parent_name="Universal")]
        )
        view = SongView.from_domain(song)
        assert view.display_master_publisher == "DGC Records (Universal)"

    def test_display_master_publisher_multiple(self):
        song = self._make_song(
            publishers=[
                Publisher(id=10, name="DGC Records", parent_name="Universal"),
                Publisher(id=5, name="Sub Pop", parent_name=None),
            ]
        )
        view = SongView.from_domain(song)
        assert view.display_master_publisher == "DGC Records (Universal), Sub Pop"

    def test_display_master_publisher_empty(self):
        view = SongView.from_domain(self._make_song(publishers=[]))
        assert view.display_master_publisher == ""

    # --- albums mapping ---
    def test_albums_mapped_to_song_album_views(self):
        """SongAlbum domain objects become SongAlbumView objects."""
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
        assert len(view.albums) == 1
        assert isinstance(view.albums[0], SongAlbumView)
        assert view.albums[0].album_title == "Nevermind"
        assert view.albums[0].track_number == 5


# ===========================================================================
# SongAlbumView computed fields
# ===========================================================================
class TestSongAlbumViewComputed:
    def test_display_title_with_track(self):
        v = SongAlbumView(album_title="Nevermind", track_number=5, disc_number=1)
        assert v.display_title == "[05] Nevermind"

    def test_display_title_with_disc_and_track(self):
        v = SongAlbumView(album_title="Nevermind", track_number=3, disc_number=2)
        assert v.display_title == "[2-03] Nevermind"

    def test_display_title_no_track(self):
        v = SongAlbumView(album_title="Nevermind", track_number=None, disc_number=1)
        assert v.display_title == "Nevermind"

    def test_display_publisher_single(self):
        v = SongAlbumView(
            album_title="Test",
            album_publishers=[
                Publisher(id=1, name="DGC Records", parent_name="Universal")
            ],
        )
        assert v.display_publisher == "DGC Records (Universal)"

    def test_display_publisher_empty(self):
        v = SongAlbumView(album_title="Test", album_publishers=[])
        assert v.display_publisher == ""

    def test_display_publisher_multiple(self):
        v = SongAlbumView(
            album_title="Test",
            album_publishers=[
                Publisher(id=1, name="DGC", parent_name="UMG"),
                Publisher(id=2, name="Sub Pop", parent_name=None),
            ],
        )
        assert v.display_publisher == "DGC (UMG), Sub Pop"


# ===========================================================================
# AlbumView.from_domain
# ===========================================================================
class TestAlbumViewFromDomain:
    def _make_album(self, **overrides):
        defaults = dict(
            id=100,
            title="Test Album",
            release_year=2000,
            publishers=[],
            credits=[],
            songs=[],
        )
        defaults.update(overrides)
        return Album(**defaults)

    def _make_song(self, **overrides):
        defaults = dict(
            id=1,
            type_id=1,
            media_name="Song",
            source_path="/p",
            duration_ms=180000,
            is_active=True,
        )
        defaults.update(overrides)
        return Song(**defaults)

    def test_basic_fields(self):
        album = self._make_album(id=42, title="My Album", release_year=1999)
        view = AlbumView.from_domain(album)
        assert view.id == 42
        assert view.title == "My Album"
        assert view.release_year == 1999

    def test_song_count(self):
        album = self._make_album(
            songs=[
                self._make_song(id=1, media_name="A"),
                self._make_song(id=2, media_name="B"),
            ]
        )
        view = AlbumView.from_domain(album)
        assert view.song_count == 2

    def test_song_count_zero(self):
        view = AlbumView.from_domain(self._make_album(songs=[]))
        assert view.song_count == 0

    def test_songs_are_song_views(self):
        album = self._make_album(songs=[self._make_song(id=1, media_name="Track One")])
        view = AlbumView.from_domain(album)
        assert len(view.songs) == 1
        assert isinstance(view.songs[0], SongView)
        assert view.songs[0].title == "Track One"

    def test_display_publisher_with_parent(self):
        album = self._make_album(
            publishers=[Publisher(id=10, name="DGC", parent_name="Universal")]
        )
        view = AlbumView.from_domain(album)
        assert view.display_publisher == "DGC (Universal)"

    def test_display_publisher_empty(self):
        view = AlbumView.from_domain(self._make_album(publishers=[]))
        assert view.display_publisher == ""

    def test_display_artist_single_performer(self):
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
        assert view.display_artist == "Nirvana"

    def test_display_artist_multiple_performers(self):
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
        assert view.display_artist == "Alice, Bob"

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
        assert view.display_artist is None

    def test_display_artist_no_credits(self):
        view = AlbumView.from_domain(self._make_album(credits=[]))
        assert view.display_artist is None


# ===========================================================================
# IdentityView.from_domain
# ===========================================================================
class TestIdentityViewFromDomain:
    def test_person_basic(self):
        identity = Identity(
            id=1,
            type="person",
            display_name="Dave Grohl",
            aliases=[],
            members=[],
            groups=[],
        )
        view = IdentityView.from_domain(identity)
        assert view.id == 1
        assert view.type == "person"
        assert view.display_name == "Dave Grohl"
        assert view.members == []
        assert view.groups == []

    def test_aliases_preserved(self):
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
        alias_names = sorted([a.display_name for a in view.aliases])
        assert alias_names == ["Grohlton", "Late!"]

    def test_group_with_members(self):
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
        assert view.type == "group"
        assert len(view.members) == 1
        assert isinstance(view.members[0], IdentityView)
        assert view.members[0].display_name == "Dave Grohl"

    def test_person_with_groups(self):
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
        assert len(view.groups) == 1
        assert isinstance(view.groups[0], IdentityView)
        assert view.groups[0].display_name == "Nirvana"

    def test_recursive_depth(self):
        """Members and groups are IdentityViews, not plain Identities."""
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
        assert view.members[0].display_name == "Middle"
        assert view.members[0].members[0].display_name == "Inner"
        assert isinstance(view.members[0].members[0], IdentityView)

    def test_legal_name_preserved(self):
        identity = Identity(
            id=1,
            type="person",
            display_name="Dave Grohl",
            legal_name="David Eric Grohl",
        )
        view = IdentityView.from_domain(identity)
        assert view.legal_name == "David Eric Grohl"
