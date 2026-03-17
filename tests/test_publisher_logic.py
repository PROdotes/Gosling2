from src.models.domain import Song, SongAlbum, Publisher
from src.models.view_models import SongView


def test_publisher_strict_context_case_1():
    """
    Test Case 1: Song has publishers A, B.
    Albums have None, A, and A, B, C.
    Expected: No fallbacks. Each album shows only its own publishers.
    """
    pub_a = Publisher(id=1, name="Publisher A")
    pub_b = Publisher(id=2, name="Publisher B")
    pub_c = Publisher(id=3, name="Publisher C")

    song = Song(
        id=101,
        type_id=1,
        media_name="Test Song",
        source_path="test/path.mp3",
        duration_ms=180000,
        publishers=[pub_a, pub_b],
        albums=[
            SongAlbum(album_title="Album None", album_publishers=[]),
            SongAlbum(album_title="Album A", album_publishers=[pub_a]),
            SongAlbum(album_title="Album ABC", album_publishers=[pub_a, pub_b, pub_c]),
        ],
    )

    view = SongView.from_domain(song)

    # Master Publisher check
    assert view.display_master_publisher == "Publisher A, Publisher B"

    # Album 1: None
    assert view.albums[0].display_publisher == ""

    # Album 2: A
    assert view.albums[1].display_publisher == "Publisher A"

    # Album 3: ABC
    assert view.albums[2].display_publisher == "Publisher A, Publisher B, Publisher C"


def test_publisher_strict_context_case_2():
    """
    Test Case 2: Song has no publishers.
    Album has publisher A.
    Expected: Album shows A.
    """
    pub_a = Publisher(id=1, name="Publisher A")

    song = Song(
        id=102,
        type_id=1,
        media_name="Test Song 2",
        source_path="test/path2.mp3",
        duration_ms=180000,
        publishers=[],
        albums=[
            SongAlbum(album_title="Album A", album_publishers=[pub_a]),
        ],
    )

    view = SongView.from_domain(song)

    # Master Publisher check
    assert view.display_master_publisher == ""

    # Album Card check
    assert view.albums[0].display_publisher == "Publisher A"
