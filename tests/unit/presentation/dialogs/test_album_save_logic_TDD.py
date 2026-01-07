
import pytest
from unittest.mock import MagicMock, patch, ANY
from PyQt6.QtCore import Qt

from src.presentation.dialogs.album_manager_dialog import AlbumManagerDialog
from src.presentation.widgets.entity_list_widget import EntityListWidget, LayoutMode
from src.core.entity_registry import EntityType

# TDD: Test Suite for Immediate Save Logic in AlbumManagerDialog

@pytest.fixture
def mock_services():
    album_service = MagicMock()
    publisher_service = MagicMock()
    contributor_service = MagicMock()
    
    # Setup mock album
    mock_album = MagicMock()
    mock_album.album_id = 1
    mock_album.title = "Test Album"
    mock_album.release_year = 2020
    mock_album.album_artist = "Old Artist"
    mock_album.album_type = "Album"
    
    # Setup service returns
    album_service.get_by_id.return_value = mock_album
    album_service.search.return_value = [mock_album]
    
    return album_service, publisher_service, contributor_service, mock_album

@patch('src.data.repositories.album_repository.AlbumRepository')
def test_add_artist_chip_triggers_immediate_save(mock_repo_cls, mock_services, qtbot):
    """
    TDD Test: Verifies that adding an artist chip in Edit mode immediately updates the database.
    """
    album_service, publisher_service, contributor_service, mock_album = mock_services
    
    # Mock Repository instance (used inside adapter)
    mock_repo = mock_repo_cls.return_value
    mock_repo.add_contributor_to_album.return_value = True
    mock_repo.get_contributors_for_album.return_value = [] # Start empty
    
    # Initialize Dialog
    dialog = AlbumManagerDialog(album_service, publisher_service, contributor_service)
    qtbot.addWidget(dialog)
    
    # Simulate selecting the album (Edit Mode)
    item = MagicMock()
    item.data.return_value = 1
    dialog._on_vault_item_clicked(item)
    
    # Mock a contributor to add
    new_artist = MagicMock()
    new_artist.contributor_id = 101
    new_artist.name = "New Artist"
    contributor_service.get_by_id.return_value = new_artist
    
    # Get the adapter attached to the tray
    adapter = dialog.tray_artist.context_adapter
    
    # Action
    success = adapter.link(101)
    
    # 1. Assert Link Success
    assert success is True
    
    # 2. Assert Repository Called (Immediate Save)
    # This should FAIL initially because the adapter is configured with staging
    mock_repo.add_contributor_to_album.assert_called_with(1, 101)
    
    # 3. Assert No Staging Function
    assert adapter._stage_change is None, "Adapter should not have a staging function in Edit mode"


@patch('src.data.repositories.album_repository.AlbumRepository')
def test_save_button_only_updates_metadata(mock_repo_cls, mock_services, qtbot):
    """
    TDD Test: Verifies that clicking Save does NOT re-sync contributors/publishers,
    but DOES update the album title/year.
    """
    album_service, publisher_service, contributor_service, mock_album = mock_services
    
    dialog = AlbumManagerDialog(album_service, publisher_service, contributor_service)
    qtbot.addWidget(dialog)
    dialog.show()
    
    # Select album
    item = MagicMock()
    item.data.return_value = 1
    dialog._on_vault_item_clicked(item)
    
    # Modify Title
    dialog.inp_title.setText("Updated Title")
    
    # Setup Mock Repo to detect calls
    mock_repo = mock_repo_cls.return_value
    
    # Action: Click Save
    success = dialog._save_inspector(silent=True)
    
    # Assertions
    assert success is True
    
    # 1. Album Service Update called
    assert mock_album.title == "Updated Title"
    album_service.update.assert_called_with(mock_album)
    
    # 2. Repo Sync methods should NOT be called (bulk sync)
    mock_repo.sync_contributors.assert_not_called()
    mock_repo.sync_publishers.assert_not_called()
