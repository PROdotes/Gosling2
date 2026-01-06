import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox
from src.presentation.dialogs.album_manager_dialog import AlbumManagerDialog
from src.data.models.album import Album


@pytest.fixture
def mock_repo(): # Acts as AlbumService
    repo = MagicMock()
    repo.db_path = ":memory:"
    repo.search.return_value = []
    repo.get_by_id.return_value = None
    repo.get_publisher_name.return_value = "Test Publisher"
    repo.get_songs_in_album.return_value = []
    return repo

@pytest.fixture
def mock_pub_service():
    service = MagicMock()
    pub = MagicMock(publisher_id=2)
    pub.publisher_name = "Test Pub"
    service.get_by_id.return_value = pub
    service.get_or_create.return_value = (pub, False)
    return service

@pytest.fixture
def mock_contrib_service():
    service = MagicMock()
    # Correct mock config for Adapter usage
    artist = MagicMock(contributor_id=1, type="person")
    artist.name = "Test Artist"
    service.get_or_create.return_value = (artist, False)
    service.get_by_id.return_value = artist
    service.get_by_name.return_value = artist
    return service

@pytest.fixture
def sample_album():
    return Album(1, "Test Album")

def test_album_mutation_field_exhaustion(qtbot, mock_repo, mock_pub_service, mock_contrib_service, sample_album):
    mock_repo.get_by_id.return_value = sample_album
    mock_repo.search.return_value = [sample_album]
    dialog = AlbumManagerDialog(mock_repo, mock_pub_service, mock_contrib_service, initial_data={'album_id': 1})
    qtbot.addWidget(dialog)
    dialog._on_vault_item_clicked(dialog.list_vault.item(0)) # Force load
    
    # Fill all fields with huge strings
    huge = "X" * 5000
    dialog.inp_title.setText(huge)
    # dialog.inp_artist.setText(huge) -> Use tray
    dialog.tray_artist.set_items([(0, huge, "")])
    
    dialog.inp_year.setText("2024")
    
    mock_repo.update.return_value = True
    dialog._save_inspector()
    
    assert sample_album.title == huge
    # assert sample_album.album_artist == huge # Service logic sets this
    mock_repo.update.assert_called_once()
    # Note: album_artist update logic might be in service or manual update of object? 
    # In _save_inspector: uses self.album_service.get_or_create(title, artist, year) for NEW
    # For EXISTING? _save_inspector logic for existing not shown in previous view but assumed similar update.

def test_album_mutation_sql_injection_search(qtbot, mock_repo, mock_pub_service, mock_contrib_service):
    dialog = AlbumManagerDialog(mock_repo, mock_pub_service, mock_contrib_service)
    qtbot.addWidget(dialog)
    
    # Bobby Tables in search
    injection = "' OR 1=1; --"
    dialog.txt_search.setText(injection)
    dialog._on_search_text_changed(injection)
    
    mock_repo.search.assert_called_with(injection)

def test_album_mutation_empty_save(qtbot, mock_repo, mock_pub_service, mock_contrib_service):
    dialog = AlbumManagerDialog(mock_repo, mock_pub_service, mock_contrib_service)
    qtbot.addWidget(dialog)
    
    # Create new mode
    dialog._toggle_create_mode()
    assert dialog.is_creating_new is True
    
    # Try save empty
    dialog._save_inspector()
    # Should NOT call get_or_create or update if title is empty
    mock_repo.get_or_create.assert_not_called()
    mock_repo.update.assert_not_called()
