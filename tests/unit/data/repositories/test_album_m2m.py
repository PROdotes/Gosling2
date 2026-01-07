import pytest
from src.data.repositories.album_repository import AlbumRepository
from src.data.repositories.contributor_repository import ContributorRepository
from src.data.models.album import Album
from src.data.models.contributor import Contributor

class TestAlbumM2M:
    """Strict TDD tests for Album Artist and Publisher M2M Schema."""

    @pytest.fixture
    def album_repo(self):
        repo = AlbumRepository()
        with repo.get_connection() as conn:
            conn.execute("DELETE FROM Albums WHERE AlbumTitle LIKE 'Pytest_%'")
            conn.execute("DELETE FROM Contributors WHERE ContributorName LIKE 'Artist %' OR ContributorName = 'Legacy Artist'")
        return repo

    @pytest.fixture
    def contrib_repo(self):
        return ContributorRepository()

    def test_album_can_have_multiple_artists(self, album_repo, contrib_repo):
        """Verify that an album can be linked to multiple artists (M2M)."""
        # 1. Create album
        album = album_repo.create("Pytest_M2M_Album")
        
        # 2. Create artists
        artist1 = contrib_repo.create("Artist One")
        artist2 = contrib_repo.create("Artist Two")
        
        # 3. Link artists to album as 'Album Artist' (or 'Performer' role)
        # We need a new method for this in AlbumRepository
        album_repo.add_contributor_to_album(album.album_id, artist1.contributor_id, "Performer")
        album_repo.add_contributor_to_album(album.album_id, artist2.contributor_id, "Performer")
        
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
        # Current set_publisher replaces. We need a way to add multiple.
        album_repo.add_publisher_to_album(album.album_id, "Publisher Alpha")
        album_repo.add_publisher_to_album(album.album_id, "Publisher Beta")
        
        # 3. Verify
        publishers = album_repo.get_publishers_for_album(album.album_id)
        assert len(publishers) == 2
        names = [p['name'] for p in publishers]
        assert "Publisher Alpha" in names
        assert "Publisher Beta" in names

    def test_album_artist_text_migration_fallback(self, album_repo, contrib_repo):
        """
        Verify that even if AlbumArtist text field is used, 
        it can coexist or migrate to M2M.
        """
        # This test might depend on how we implement the migration.
        # For now, let's ensure we can still get 'Album Artist' as a string 
        # even if it comes from the M2M table.
        album = album_repo.create("Pytest_Migration_Album")
        artist = contrib_repo.create("Legacy Artist")
        album_repo.add_contributor_to_album(album.album_id, artist.contributor_id, "Performer")
        
        found = album_repo.get_by_id(album.album_id)
        # The new Album model should probably return a list of artists or a joined string
        assert found.album_artist == "Legacy Artist"

    def test_remove_contributor_and_publisher(self, album_repo, contrib_repo):
        """Verify that we can unlink contributors and publishers."""
        album = album_repo.create("Pytest_Remove_M2M")
        artist = contrib_repo.create("Artist to Remove")
        album_repo.add_contributor_to_album(album.album_id, artist.contributor_id)
        album_repo.add_publisher_to_album(album.album_id, "Pub to Remove")
        
        # Verify initial state
        assert len(album_repo.get_contributors_for_album(album.album_id)) == 1
        assert len(album_repo.get_publishers_for_album(album.album_id)) == 1
        
        # Remove
        album_repo.remove_contributor_from_album(album.album_id, artist.contributor_id)
        album_repo.remove_publisher_from_album(album.album_id, album_repo.get_publishers_for_album(album.album_id)[0]['id'])
        
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
        names = {p['name'] for p in pubs}
        assert names == {"Pub A", "Pub B"}
        
        # 2. Sync to different set (Add one, remove one, keep one)
        album_repo.sync_publishers(album.album_id, ["Pub B", "Pub C"])
        pubs = album_repo.get_publishers_for_album(album.album_id)
        assert len(pubs) == 2
        names = {p['name'] for p in pubs}
        assert names == {"Pub B", "Pub C"}
        
        # 3. Sync to empty
        album_repo.sync_publishers(album.album_id, [])
        pubs = album_repo.get_publishers_for_album(album.album_id)
        assert len(pubs) == 0

    def test_sync_contributors(self, album_repo, contrib_repo):
        """Verify that sync_contributors correctly updates the list."""
        album = album_repo.create("Pytest_Sync_Contribs")
        c1 = contrib_repo.create("Artist A")
        c2 = contrib_repo.create("Artist B")
        c3 = contrib_repo.create("Artist C")
        
        # 1. Initial sync
        album_repo.sync_contributors(album.album_id, [c1, c2])
        contribs = album_repo.get_contributors_for_album(album.album_id)
        assert len(contribs) == 2
        ids = {c.contributor_id for c in contribs}
        assert ids == {c1.contributor_id, c2.contributor_id}
        
        # 2. Sync to different set
        album_repo.sync_contributors(album.album_id, [c2, c3])
        contribs = album_repo.get_contributors_for_album(album.album_id)
        assert len(contribs) == 2
        ids = {c.contributor_id for c in contribs}
        assert ids == {c2.contributor_id, c3.contributor_id}
        
        # 3. Sync to empty
        album_repo.sync_contributors(album.album_id, [])
        contribs = album_repo.get_contributors_for_album(album.album_id)
        assert len(contribs) == 0
