import pytest
from src.data.repositories.album_repository import AlbumRepository
from src.data.repositories.artist_name_repository import ArtistNameRepository
from src.data.database import BaseRepository
from src.data.models.album import Album
from src.data.models.artist_name import ArtistName

class TestAlbumM2M:
    """Strict TDD tests for Album Artist and Publisher M2M Schema."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create isolated temp database for each test."""
        db_path = tmp_path / "test_album_m2m.db"
        # Initialize schema
        BaseRepository(str(db_path))
        return str(db_path)

    @pytest.fixture
    def album_repo(self, temp_db):
        return AlbumRepository(temp_db)

    @pytest.fixture
    def artist_repo(self, temp_db):
        """Use ArtistNameRepository - AlbumCredits references ArtistNames.NameID."""
        return ArtistNameRepository(temp_db)

    def test_album_can_have_multiple_artists(self, album_repo, artist_repo):
        """Verify that an album can be linked to multiple artists (M2M)."""
        # 1. Create album
        album = album_repo.create("Pytest_M2M_Album")
        
        # 2. Create artists using ArtistNames (the new model)
        artist1 = ArtistName(name_id=None, display_name="Artist One", sort_name="One, Artist", is_primary_name=True)
        artist2 = ArtistName(name_id=None, display_name="Artist Two", sort_name="Two, Artist", is_primary_name=True)
        id1 = artist_repo.insert(artist1)
        id2 = artist_repo.insert(artist2)
        
        # 3. Link artists to album (CreditedNameID now references ArtistNames.NameID)
        album_repo.add_contributor_to_album(album.album_id, id1, "Performer")
        album_repo.add_contributor_to_album(album.album_id, id2, "Performer")
        
        # 4. Verify links
        contributors = album_repo.get_contributors_for_album(album.album_id)
        assert len(contributors) == 2
        names = [c.name for c in contributors]
        assert "Artist One" in names
        assert "Artist Two" in names

    def test_album_can_have_multiple_publishers(self, album_repo):
        """Verify that an album can be linked to multiple publishers (M2M)."""
        # 1. Create album
        album = album_repo.create("Pytest_M2M_Pub_Album")
        
        # 2. Add multiple publishers
        album_repo.add_publisher_to_album(album.album_id, "Publisher Alpha")
        album_repo.add_publisher_to_album(album.album_id, "Publisher Beta")
        
        # 3. Verify
        publishers = album_repo.get_publishers_for_album(album.album_id)
        assert len(publishers) == 2
        names = [p.publisher_name for p in publishers]
        assert "Publisher Alpha" in names
        assert "Publisher Beta" in names

    def test_album_artist_text_migration_fallback(self, album_repo, artist_repo):
        """
        Verify that even if AlbumArtist text field is used, 
        it can coexist or migrate to M2M.
        """
        album = album_repo.create("Pytest_Migration_Album")
        artist = ArtistName(name_id=None, display_name="Legacy Artist", sort_name="Artist, Legacy", is_primary_name=True)
        artist_id = artist_repo.insert(artist)
        album_repo.add_contributor_to_album(album.album_id, artist_id, "Performer")
        
        found = album_repo.get_by_id(album.album_id)
        assert found.album_artist == "Legacy Artist"

    def test_remove_contributor_and_publisher(self, album_repo, artist_repo):
        """Verify that we can unlink contributors and publishers."""
        album = album_repo.create("Pytest_Remove_M2M")
        artist = ArtistName(name_id=None, display_name="Artist to Remove", sort_name="Remove, Artist", is_primary_name=True)
        artist_id = artist_repo.insert(artist)
        album_repo.add_contributor_to_album(album.album_id, artist_id)
        album_repo.add_publisher_to_album(album.album_id, "Pub to Remove")
        
        # Verify initial state
        assert len(album_repo.get_contributors_for_album(album.album_id)) == 1
        assert len(album_repo.get_publishers_for_album(album.album_id)) == 1
        
        # Remove
        album_repo.remove_contributor_from_album(album.album_id, artist_id)
        album_repo.remove_publisher_from_album(album.album_id, album_repo.get_publishers_for_album(album.album_id)[0].publisher_id)
        
        # Verify final state
        assert len(album_repo.get_contributors_for_album(album.album_id)) == 0
        assert len(album_repo.get_publishers_for_album(album.album_id)) == 0

    def test_sync_publishers_prevents_ghosts(self, album_repo):
        """Verify that sync_publishers correctly updates the list without leaving orphans or ghosts."""
        album = album_repo.create("Pytest_Sync_Pubs")
        
        # 1. Initial sync
        album_repo.sync_publishers(album.album_id, ["Pub A", "Pub B"])
        pubs = album_repo.get_publishers_for_album(album.album_id)
        assert len(pubs) == 2
        names = {p.publisher_name for p in pubs}
        assert names == {"Pub A", "Pub B"}
        
        # 2. Sync to different set (Add one, remove one, keep one)
        album_repo.sync_publishers(album.album_id, ["Pub B", "Pub C"])
        pubs = album_repo.get_publishers_for_album(album.album_id)
        assert len(pubs) == 2
        names = {p.publisher_name for p in pubs}
        assert names == {"Pub B", "Pub C"}
        
        # 3. Sync to empty
        album_repo.sync_publishers(album.album_id, [])
        pubs = album_repo.get_publishers_for_album(album.album_id)
        assert len(pubs) == 0

    def test_sync_contributors(self, album_repo, artist_repo):
        """Verify that sync_contributors correctly updates the list."""
        from src.data.models.contributor import Contributor
        album = album_repo.create("Pytest_Sync_Contribs")
        
        # Create ArtistNames
        c1 = ArtistName(name_id=None, display_name="Artist A", sort_name="A", is_primary_name=True)
        c2 = ArtistName(name_id=None, display_name="Artist B", sort_name="B", is_primary_name=True)
        c3 = ArtistName(name_id=None, display_name="Artist C", sort_name="C", is_primary_name=True)
        id1 = artist_repo.insert(c1)
        id2 = artist_repo.insert(c2)
        id3 = artist_repo.insert(c3)
        
        # Create Contributor-like objects for sync_contributors (it expects Contributor model)
        contrib1 = Contributor(contributor_id=id1, name="Artist A", sort_name="A", type="person")
        contrib2 = Contributor(contributor_id=id2, name="Artist B", sort_name="B", type="person")
        contrib3 = Contributor(contributor_id=id3, name="Artist C", sort_name="C", type="person")
        
        # 1. Initial sync
        album_repo.sync_contributors(album.album_id, [contrib1, contrib2])
        contribs = album_repo.get_contributors_for_album(album.album_id)
        assert len(contribs) == 2
        ids = {c.contributor_id for c in contribs}
        assert ids == {id1, id2}
        
        # 2. Sync to different set
        album_repo.sync_contributors(album.album_id, [contrib2, contrib3])
        contribs = album_repo.get_contributors_for_album(album.album_id)
        assert len(contribs) == 2
        ids = {c.contributor_id for c in contribs}
        assert ids == {id2, id3}
        
        # 3. Sync to empty
        album_repo.sync_contributors(album.album_id, [])
        contribs = album_repo.get_contributors_for_album(album.album_id)
        assert len(contribs) == 0

