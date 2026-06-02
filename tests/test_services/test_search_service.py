import urllib.parse
from src.services.search_service import SearchService
from src.models.domain import Song, SongCredit


def test_get_search_url_spotify():
    service = SearchService()
    song = Song(
        id=1,
        type_id=1,
        media_name="Pravda za Vedrana",
        source_path="Z:\\Songs\\Pravda.mp3",
        duration_s=180.0,
        processing_status=1,
        credits=[
            SongCredit(role_name="Performer", display_name="Dubioza kolektiv"),
            SongCredit(role_name="Composer", display_name="Brano Jakubovic"),
        ],
    )
    url = service.get_search_url(song, engine="spotify")
    assert "spotify.com/search/" in url
    # Should include performers only for Spotify search by default if they exist
    assert "Dubioza" in url
    assert "Pravda%20za%20Vedrana" in url


def test_get_search_url_spotify_multiple_artists():
    service = SearchService()
    song = Song(
        id=1,
        type_id=1,
        media_name="Test Song",
        source_path="Z:\\test.mp3",
        duration_s=180.0,
        processing_status=1,
        credits=[
            SongCredit(role_name="Performer", display_name="Artist A"),
            SongCredit(role_name="Performer", display_name="Artist B"),
        ],
    )
    url = service.get_search_url(song, engine="spotify")
    assert "Artist%20A" in url
    assert "Artist%20B" in url


def test_get_search_url_google():
    service = SearchService()
    song = Song(
        id=1,
        type_id=1,
        media_name="Pravda za Vedrana",
        source_path="Z:\\Songs\\Pravda.mp3",
        duration_s=180.0,
        processing_status=1,
        credits=[SongCredit(role_name="Performer", display_name="Dubioza kolektiv")],
    )
    url = service.get_search_url(song, engine="google")
    assert "google.com/search?q=" in url
    assert "Dubioza" in url


def test_get_search_url_youtube():
    service = SearchService()
    song = Song(
        id=1,
        type_id=1,
        media_name="Pravda za Vedrana",
        source_path="Z:\\Songs\\Pravda.mp3",
        duration_s=180.0,
        processing_status=1,
        credits=[SongCredit(role_name="Performer", display_name="Dubioza kolektiv")],
    )
    url = service.get_search_url(song, engine="youtube")
    assert "youtube.com/results?search_query=" in url
    assert "Dubioza" in url
    assert "Pravda%20za%20Vedrana" in url


def test_get_search_url_musicbrainz():
    service = SearchService()
    song = Song(
        id=1,
        type_id=1,
        media_name="Pravda za Vedrana",
        source_path="Z:\\Songs\\Pravda.mp3",
        duration_s=180.0,
        processing_status=1,
        credits=[SongCredit(role_name="Performer", display_name="Dubioza kolektiv")],
    )
    url = service.get_search_url(song, engine="musicbrainz")
    assert url.startswith("https://musicbrainz.org/search?")
    # type=recording targets songs/tracks, not albums (type=release)
    assert "type=recording" in url
    # method=advanced is required for MusicBrainz to parse the field syntax
    assert "method=advanced" in url
    # Fielded Lucene query: title scoped to recording:, performer to artist:,
    # joined with AND so the search narrows instead of loose OR-matching.
    decoded = urllib.parse.unquote_plus(url)
    assert 'recording:"Pravda za Vedrana"' in decoded
    assert 'artist:"Dubioza kolektiv"' in decoded
    assert " AND " in decoded


def test_get_search_url_musicbrainz_multiple_artists():
    service = SearchService()
    song = Song(
        id=1,
        type_id=1,
        media_name="Test Song",
        source_path="Z:\\test.mp3",
        duration_s=180.0,
        processing_status=1,
        credits=[
            SongCredit(role_name="Performer", display_name="Artist A"),
            SongCredit(role_name="Performer", display_name="Artist B"),
        ],
    )
    url = service.get_search_url(song, engine="musicbrainz")
    decoded = urllib.parse.unquote_plus(url)
    # Each performer gets its own artist: clause, all ANDed together.
    assert 'recording:"Test Song"' in decoded
    assert 'artist:"Artist A"' in decoded
    assert 'artist:"Artist B"' in decoded
    assert decoded.count(" AND ") == 2
