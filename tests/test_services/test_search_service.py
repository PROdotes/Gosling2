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
            SongCredit(role_name="Composer", display_name="Brano Jakubovic")
        ]
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
            SongCredit(role_name="Performer", display_name="Artist B")
        ]
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
        credits=[
            SongCredit(role_name="Performer", display_name="Dubioza kolektiv")
        ]
    )
    url = service.get_search_url(song, engine="google")
    assert "google.com/search?q=" in url
    assert "Dubioza" in url
    assert "metadata" in url
