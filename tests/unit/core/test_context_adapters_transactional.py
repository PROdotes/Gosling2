
import pytest
from unittest.mock import MagicMock
from src.core.context_adapters import (
    SongFieldAdapter, 
    AlbumContributorAdapter, 
    AlbumPublisherAdapter
)

class TestContextAdaptersTransactional:
    """
    Law of Direct Manipulation:
    Chips (Entities) must interact directly with the database services.
    Staging/Draft logic is strictly forbidden for Entity adapters.
    """

    def test_song_adapter_performer_immediate_write(self):
        """Verify SongFieldAdapter calls service.add_song_role immediately for performers."""
        mock_service = MagicMock()
        mock_song = MagicMock()
        mock_song.source_id = 101
        
        # Setup: Performer field (args: songs, field_name, service)
        adapter = SongFieldAdapter([mock_song], 'performers', mock_service)
        
        # Action: Link Artist ID 50
        adapter.link(50)
        
        # Assert: Service called immediately
        mock_service.add_song_role.assert_called_with(101, 50, 'Performer')
        
    def test_song_adapter_album_immediate_write(self):
        """Verify SongFieldAdapter calls set_primary_album immediately."""
        mock_service = MagicMock()
        mock_song = MagicMock()
        mock_song.source_id = 101
        
        adapter = SongFieldAdapter([mock_song], 'album', mock_service)
        
        # Action: Link Album ID 200
        adapter.link(200)
        
        # Assert: Immediate DB write
        mock_service.set_primary_album.assert_called_with(101, 200)

    def test_song_adapter_tag_immediate_write(self):
        """Verify SongFieldAdapter calls add_tag_to_source immediately."""
        mock_service = MagicMock()
        mock_song = MagicMock()
        mock_song.source_id = 101
        
        adapter = SongFieldAdapter([mock_song], 'tags', mock_service)
        
        # Action: Link Tag ID 30
        adapter.link(30)
        
        # Assert: Immediate DB write
        mock_service.add_tag_to_source.assert_called_with(101, 30)

    def test_album_contributor_adapter_immediate_write(self):
        """Verify AlbumContributorAdapter uses repository directly, bypassing staging."""
        mock_service = MagicMock() # Not used for linking here, repo is used
        mock_album = MagicMock()
        mock_album.album_id = 500
        mock_stage_fn = MagicMock()
        
        # We need to mock the AlbumRepository import or patch it
        with pytest.MonkeyPatch.context() as m:
            mock_repo = MagicMock()
            m.setattr("src.data.repositories.album_repository.AlbumRepository", lambda: mock_repo)
            
            adapter = AlbumContributorAdapter(
                mock_album, 
                mock_service, 
                stage_change_fn=mock_stage_fn # Pass it to verify it's IGNORED
            )
            
            # Action
            adapter.link(99)
            
            # Assert: Repository called
            mock_repo.add_contributor_to_album.assert_called_with(500, 99)
            
            # Assert: Staging NOT called
            mock_stage_fn.assert_not_called()

    def test_album_publisher_adapter_immediate_write(self):
        """Verify AlbumPublisherAdapter uses repository directly, bypassing staging."""
        mock_service = MagicMock()
        # Mock service.get_by_id to return a publisher object with a name
        mock_pub = MagicMock()
        mock_pub.publisher_name = "Test Pub"
        mock_service.get_by_id.return_value = mock_pub
        
        mock_album = MagicMock()
        mock_album.album_id = 500
        mock_stage_fn = MagicMock()
        
        with pytest.MonkeyPatch.context() as m:
            mock_repo = MagicMock()
            m.setattr("src.data.repositories.album_repository.AlbumRepository", lambda: mock_repo)
            
            adapter = AlbumPublisherAdapter(
                mock_album, 
                mock_service, 
                stage_change_fn=mock_stage_fn
            )
            
            # Action
            adapter.link(77)
            
            # Assert: Repository called with Name (Legacy/Repo API) 
            # Note: Adapter calls add_publisher_to_album(id, name)
            mock_repo.add_publisher_to_album.assert_called_with(500, "Test Pub")
            
            # Assert: Staging NOT called
            mock_stage_fn.assert_not_called()
