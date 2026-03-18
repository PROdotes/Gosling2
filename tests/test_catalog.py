from src.services.catalog_service import CatalogService
from src.models.view_models import SongView, AlbumView


def test_get_song_exists(populated_db):
    """LAW: Fetching a valid song ID returns the complete Song domain model."""
    service = CatalogService(populated_db)

    # 2 = Everlong in populated_db
    song = service.get_song(2)

    assert song is not None
    assert song.id == 2
    assert song.title == "Everlong"
    assert song.duration_ms == 240000

    # Verify credits hydration
    assert len(song.credits) == 1
    assert song.credits[0].display_name == "Foo Fighters"
    assert song.credits[0].role_id == 1
    assert song.credits[0].identity_id == 3  # Foo Fighters Identity



def test_get_song_multiple_credits(populated_db):
    """LAW: A song with multiple credits should be fully hydrated with all of them."""
    service = CatalogService(populated_db)
    song = service.get_song(6)

    assert song is not None
    assert len(song.credits) == 2

    # Check specific credits
    names = {c.display_name for c in song.credits}
    assert "Dave Grohl" in names
    assert "Taylor Hawkins" in names


def test_get_song_no_credits(populated_db):
    """LAW: A song with no credits should return an empty list of credits, not None or error."""
    service = CatalogService(populated_db)
    song = service.get_song(7)

    assert song is not None
    assert song.title == "Hollow Song"
    assert song.credits == []


def test_get_song_not_found(populated_db):
    """LAW: Fetching a non-existent ID returns None."""
    service = CatalogService(populated_db)
    song = service.get_song(999)
    assert song is None


def test_get_song_album_hydration(populated_db):
    """LAW: Songs must be hydrated with their primary album and track/disc metadata."""
    service = CatalogService(populated_db)

    # Song 1: Nevermind
    song1 = service.get_song(1)
    assert len(song1.albums) == 1
    assoc1 = song1.albums[0]
    assert assoc1.album_id == 100
    assert assoc1.album_title == "Nevermind"
    assert assoc1.is_primary is True
    # M2M: Nevermind has two publishers in conftest
    assert len(assoc1.album_publishers) == 2
    pub_names = {p.name for p in assoc1.album_publishers}
    assert "DGC Records" in pub_names
    assert "Sub Pop" in pub_names

    # Master Publisher check
    assert len(song1.publishers) == 1
    assert song1.publishers[0].name == "DGC Records"

    # Song 2: Everlong
    song2 = service.get_song(2)
    assert len(song2.albums) == 1
    assoc2 = song2.albums[0]
    assert assoc2.album_title == "The Colour and the Shape"
    assert assoc2.track_number == 11
    pub_names = {p.name for p in assoc2.album_publishers}
    assert "Roswell Records" in pub_names

    # Song with no album
    song3 = service.get_song(4)  # Grohlton Theme
    assert song3.albums == []


def test_get_song_tag_hydration(populated_db):
    """LAW: Songs must be hydrated with their tags and primary_genre derivation."""
    service = CatalogService(populated_db)

    # Song 1: Grunge + Energetic + English (Jezik)
    song1 = service.get_song(1)
    assert len(song1.tags) == 3
    tag_names = {t.name for t in song1.tags}
    assert "Grunge" in tag_names
    assert "Energetic" in tag_names
    assert "English" in tag_names
    assert SongView.from_domain(song1).primary_genre == "Grunge"

    # Song 2: 90s (Era) -> No Genre category so fallback to first
    song2 = service.get_song(2)
    assert len(song2.tags) == 1
    assert SongView.from_domain(song2).primary_genre is None

    # Song 4: Electronic Style (Not a Genre) -> No badge
    song_4 = service.get_song(4)
    view_4 = SongView.from_domain(song_4)
    assert view_4.primary_genre is None
    assert any(t.name == "Electronic" for t in song_4.tags)

    # Song 9: Multi-genre with explicit primary (Alt Rock vs Grunge)
    song_9 = service.get_song(9)
    assert SongView.from_domain(song_9).primary_genre == "Alt Rock"

    # Song with no tags
    song7 = service.get_song(7)
    assert song7.tags == []
    assert SongView.from_domain(song7).primary_genre is None


def test_song_domain_integrity(catalog_service, populated_db):
    """Deep verification of song metadata: roles, languages, and publishers."""
    # Song 1: Smells Like Teen Spirit
    song = catalog_service.get_song(1)

    # 1. Verification of Role-based formatting
    view = SongView.from_domain(song)
    assert view.display_artist == "Nirvana"
    assert "Nirvana" in [c.display_name for c in song.credits]
    assert song.credits[0].role_name == "Performer"

    # 2. Verification of Duration formatting (200s -> 3:20)
    assert view.formatted_duration == "3:20"

    # 3. Verification of Multi-source Publishers
    publisher_names = [p.name for p in song.publishers]
    assert "DGC Records" in publisher_names

    # 4. Verification of Language/Jezik tags
    assert any(t.category == "Jezik" and t.name == "English" for t in song.tags)

    # Song 6: Dual Credit Track (Dave=Performer, Taylor=Composer)
    song_6 = catalog_service.get_song(6)
    assert any(
        c.display_name == "Dave Grohl" and c.role_name == "Performer"
        for c in song_6.credits
    )
    assert any(
        c.display_name == "Taylor Hawkins" and c.role_name == "Composer"
        for c in song_6.credits
    )


def test_display_artist_multiple_performers(catalog_service, populated_db):
    """LAW: display_artist must join multiple performers with a comma."""
    song = catalog_service.get_song(8)  # Joint Venture
    assert song is not None
    view = SongView.from_domain(song)
    assert view.display_artist == "Dave Grohl, Taylor Hawkins"


def test_get_all_identities(catalog_service, populated_db):
    """LAW: get_all_identities returns a list ordered by DisplayName."""
    identities = catalog_service.get_all_identities()
    assert len(identities) == 4
    names = [i.display_name for i in identities]
    # ASCII ascending: Dave Grohl, Foo Fighters, Nirvana, Taylor Hawkins
    assert names[0] == "Dave Grohl"
    assert names[1] == "Foo Fighters"
    assert names[2] == "Nirvana"
    assert names[3] == "Taylor Hawkins"


def test_get_songs_by_identity(catalog_service, populated_db):
    """LAW: get_songs_by_identity resolves the full tree and finds all credited songs."""
    # Dave Grohl (id=1) belongs to Nirvana (id=2) and Foo Fighters (id=3). 
    # Plus his solo/aliases (Grohlton, Late!).
    dave_songs = catalog_service.get_songs_by_identity(1)
    
    # Nirvana = 1, Foo Fighters = 2, Grohlton = 4, Late! = 5, Joint Venture = 8, Dual Credit = 6
    song_ids = {s.id for s in dave_songs}
    assert 1 in song_ids  # Smells Like Teen Spirit (Nirvana)
    assert 2 in song_ids  # Everlong (Foo Fighters)
    assert 4 in song_ids  # Grohlton Theme (Alias)
    assert 5 in song_ids  # Pocketwatch Demo (Alias)
    assert 6 in song_ids  # Dual Credit
    assert 8 in song_ids  # Joint Venture
    
    assert 3 not in song_ids  # Range Rover Bitch (Taylor Solo)

def test_get_songs_by_identity_not_found(catalog_service, populated_db):
    """LAW: get_songs_by_identity returns empty list for non-existent identity."""
    res = catalog_service.get_songs_by_identity(999)
    assert res == []


def test_get_all_albums(populated_db):
    """LAW: get_all_albums returns hydrated album directory entries."""
    service = CatalogService(populated_db)

    albums = service.get_all_albums()

    assert len(albums) == 2
    titles = [album.title for album in albums]
    assert "Nevermind" in titles
    assert "The Colour and the Shape" in titles

    nevermind = next(album for album in albums if album.title == "Nevermind")
    assert len(nevermind.publishers) == 2
    assert {publisher.name for publisher in nevermind.publishers} == {
        "DGC Records",
        "Sub Pop",
    }
    assert len(nevermind.credits) == 1
    assert nevermind.credits[0].display_name == "Nirvana"
    assert [song.title for song in nevermind.songs] == ["Smells Like Teen Spirit"]


def test_get_album_exists(populated_db):
    """LAW: get_album returns a fully hydrated album."""
    service = CatalogService(populated_db)

    album = service.get_album(200)

    assert album is not None
    assert album.title == "The Colour and the Shape"
    assert album.release_year == 1997
    assert album.album_type is None
    assert len(album.publishers) == 1
    assert album.publishers[0].name == "Roswell Records"
    assert len(album.credits) == 1
    assert album.credits[0].display_name == "Foo Fighters"
    assert [song.title for song in album.songs] == ["Everlong"]


def test_search_albums(populated_db):
    """LAW: search_albums matches by album title."""
    service = CatalogService(populated_db)

    albums = service.search_albums("Never")

    assert len(albums) == 1
    assert albums[0].title == "Nevermind"


def test_get_album_not_found(populated_db):
    """LAW: get_album returns None for unknown album IDs."""
    service = CatalogService(populated_db)

    assert service.get_album(999) is None


def test_album_view_display_fields(populated_db):
    """LAW: AlbumView exposes display helpers for dashboard rendering."""
    service = CatalogService(populated_db)

    album = service.get_album(100)
    view = AlbumView.from_domain(album)

    assert view.display_artist == "Nirvana"
    assert view.display_publisher == "DGC Records, Sub Pop"
    assert view.song_count == 1
