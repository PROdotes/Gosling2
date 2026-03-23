from src.models.domain import Song, SongAlbum, Publisher
from src.models.view_models import SongView


def _assert_songview_defaults(
    view, expected_id, expected_media_name, expected_duration_ms
):
    """Assert invariant fields on SongView that must match the source Song."""
    assert view.id == expected_id, f"Expected id={expected_id}, got {view.id}"
    assert (
        view.media_name == expected_media_name
    ), f"Expected media_name='{expected_media_name}', got '{view.media_name}'"
    assert (
        view.title == expected_media_name
    ), f"Expected title='{expected_media_name}', got '{view.title}'"
    assert (
        view.duration_ms == expected_duration_ms
    ), f"Expected duration_ms={expected_duration_ms}, got {view.duration_ms}"
    assert view.audio_hash is None, f"Expected audio_hash=None, got {view.audio_hash}"
    # MediaSource.processing_status is Optional[int] = None, so from_domain passes None
    assert (
        view.processing_status is None
    ), f"Expected processing_status=None, got {view.processing_status}"
    assert view.is_active is False, f"Expected is_active=False, got {view.is_active}"
    assert view.notes is None, f"Expected notes=None, got {view.notes}"
    assert view.bpm is None, f"Expected bpm=None, got {view.bpm}"
    assert view.year is None, f"Expected year=None, got {view.year}"
    assert view.isrc is None, f"Expected isrc=None, got {view.isrc}"
    assert view.credits == [], f"Expected no credits, got {view.credits}"
    assert view.tags == [], f"Expected no tags, got {view.tags}"
    assert view.raw_tags == {}, f"Expected empty raw_tags, got {view.raw_tags}"


class TestPublisherLogic:

    def test_publisher_strict_context_case_1(self):
        """Song with publishers A, B. Albums have None, A, and A, B, C. No fallbacks per album."""
        pub_a = Publisher(id=1, name="Publisher A")
        pub_b = Publisher(id=2, name="Publisher B")
        pub_c = Publisher(id=3, name="Publisher C")

        song = Song(
            id=101,
            type_id=1,
            media_name="Test Song",
            source_path="test/path.mp3",
            duration_s=180.0,
            publishers=[pub_a, pub_b],
            albums=[
                SongAlbum(album_title="Album None", album_publishers=[]),
                SongAlbum(album_title="Album A", album_publishers=[pub_a]),
                SongAlbum(
                    album_title="Album ABC", album_publishers=[pub_a, pub_b, pub_c]
                ),
            ],
        )

        view = SongView.from_domain(song)

        _assert_songview_defaults(view, 101, "Test Song", 180000)
        assert (
            view.source_path == "test/path.mp3"
        ), f"Expected source_path='test/path.mp3', got '{view.source_path}'"
        assert (
            view.display_master_publisher == "Publisher A, Publisher B"
        ), f"Expected display_master_publisher='Publisher A, Publisher B', got '{view.display_master_publisher}'"

        assert len(view.albums) == 3, f"Expected 3 albums, got {len(view.albums)}"

        # Album 1: no publishers
        assert (
            view.albums[0].album_title == "Album None"
        ), f"Expected album[0]='Album None', got '{view.albums[0].album_title}'"
        assert (
            view.albums[0].display_publisher == ""
        ), f"Expected album[0] display_publisher='', got '{view.albums[0].display_publisher}'"
        assert (
            view.albums[0].source_id is None
        ), f"Expected album[0] source_id=None, got {view.albums[0].source_id}"
        assert (
            view.albums[0].album_id is None
        ), f"Expected album[0] album_id=None, got {view.albums[0].album_id}"
        assert (
            view.albums[0].track_number is None
        ), f"Expected album[0] track_number=None, got {view.albums[0].track_number}"
        assert (
            view.albums[0].disc_number is None
        ), f"Expected album[0] disc_number=None, got {view.albums[0].disc_number}"
        assert (
            view.albums[0].album_type is None
        ), f"Expected album[0] album_type=None, got {view.albums[0].album_type}"
        assert (
            view.albums[0].release_year is None
        ), f"Expected album[0] release_year=None, got {view.albums[0].release_year}"
        assert (
            view.albums[0].credits == []
        ), f"Expected album[0] credits=[], got {view.albums[0].credits}"

        # Album 2: A only
        assert (
            view.albums[1].album_title == "Album A"
        ), f"Expected album[1]='Album A', got '{view.albums[1].album_title}'"
        assert (
            view.albums[1].display_publisher == "Publisher A"
        ), f"Expected album[1] display_publisher='Publisher A', got '{view.albums[1].display_publisher}'"

        # Album 3: A, B, C
        assert (
            view.albums[2].album_title == "Album ABC"
        ), f"Expected album[2]='Album ABC', got '{view.albums[2].album_title}'"
        assert (
            view.albums[2].display_publisher == "Publisher A, Publisher B, Publisher C"
        ), f"Expected album[2] display_publisher='Publisher A, Publisher B, Publisher C', got '{view.albums[2].display_publisher}'"

    def test_publisher_strict_context_case_2(self):
        """Song has no publishers. Album has publisher A. Album shows A, master shows nothing."""
        pub_a = Publisher(id=1, name="Publisher A")

        song = Song(
            id=102,
            type_id=1,
            media_name="Test Song 2",
            source_path="test/path2.mp3",
            duration_s=180.0,
            publishers=[],
            albums=[
                SongAlbum(album_title="Album A", album_publishers=[pub_a]),
            ],
        )

        view = SongView.from_domain(song)

        _assert_songview_defaults(view, 102, "Test Song 2", 180000)
        assert (
            view.source_path == "test/path2.mp3"
        ), f"Expected source_path='test/path2.mp3', got '{view.source_path}'"
        assert (
            view.display_master_publisher == ""
        ), f"Expected display_master_publisher='', got '{view.display_master_publisher}'"

        assert len(view.albums) == 1, f"Expected 1 album, got {len(view.albums)}"
        assert (
            view.albums[0].album_title == "Album A"
        ), f"Expected album[0]='Album A', got '{view.albums[0].album_title}'"
        assert (
            view.albums[0].display_publisher == "Publisher A"
        ), f"Expected album[0] display_publisher='Publisher A', got '{view.albums[0].display_publisher}'"
