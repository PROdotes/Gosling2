import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox
from src.presentation.dialogs.album_manager_dialog import AlbumManagerDialog
from src.data.models.album import Album

@pytest.fixture(autouse=True)
def mock_pub_repo_instantiation():
    # Patch PublisherRepository at the source of import to avoid real DB access
    with patch("src.presentation.dialogs.album_manager_dialog.PublisherRepository") as mock:
        yield mock

@pytest.fixture
def mock_album_service():
    service = MagicMock()
    service.search.return_value = []
    service.get_by_id.return_value = None
    service.get_publisher_name.return_value = "Test Publisher"
    # Service specific methods
    service.get_songs_in_album.return_value = [] 
    return service

@pytest.fixture
def mock_publisher_service():
    return MagicMock()

@pytest.fixture
def mock_contributor_service():
    return MagicMock()

@pytest.fixture
def sample_album():
    return Album(album_id=50, title="Highway to Heck", album_artist="AC/BC", release_year=1979, album_type="Album")

def test_album_manager_init_with_id(qtbot, mock_album_service, mock_publisher_service, mock_contributor_service, sample_album):
    mock_album_service.get_by_id.return_value = sample_album
    mock_album_service.search.return_value = [sample_album]
    
    initial_data = {'album_id': 50, 'title': 'Highway to Heck'}
    dialog = AlbumManagerDialog(mock_album_service, mock_publisher_service, mock_contributor_service, initial_data=initial_data)
    qtbot.addWidget(dialog)
    
    assert dialog.inp_title.text() == "Highway to Heck"
    # assert dialog.inp_artist.text() == "AC/BC" # Removed field, now tray
    assert dialog.tray_artist.get_names() == ["AC/BC"]
    assert dialog.inp_year.text() == "1979"
    assert dialog.cmb_type.currentText() == "Album"

def test_album_manager_search_and_select(qtbot, mock_album_service, mock_publisher_service, mock_contributor_service, sample_album):
    mock_album_service.search.return_value = [sample_album]
    mock_album_service.get_by_id.return_value = sample_album # Ensure select works
    
    dialog = AlbumManagerDialog(mock_album_service, mock_publisher_service, mock_contributor_service)
    qtbot.addWidget(dialog)
    
    # Simulate typing in search
    dialog.txt_search.setText("Highway")
    dialog._on_search_text_changed("Highway")
    
    assert dialog.list_vault.count() == 1
    assert "Highway to Heck" in dialog.list_vault.item(0).text()
    
    # Select the item
    item = dialog.list_vault.item(0)
    dialog.list_vault.setCurrentItem(item)
    dialog._on_vault_item_clicked(item)
    
    assert dialog.inp_title.text() == "Highway to Heck"
    assert dialog.current_album == sample_album

def test_album_manager_save_existing(qtbot, mock_album_service, mock_publisher_service, mock_contributor_service, sample_album):
    mock_album_service.get_by_id.return_value = sample_album
    mock_album_service.search.return_value = [sample_album]
    dialog = AlbumManagerDialog(mock_album_service, mock_publisher_service, mock_contributor_service, initial_data={'album_id': 50})
    qtbot.addWidget(dialog)
    
    dialog.inp_title.setText("Highway to Heaven")
    # dialog.inp_artist.setText("Angels") -> Use tray
    dialog.tray_artist.set_chips([(0, "Angels", "")])
    
    mock_album_service.update.return_value = True
    
    with patch.object(dialog, 'accept') as mock_accept:
        dialog._save_inspector()
        
        assert sample_album.title == "Highway to Heaven"
        assert sample_album.album_artist == "Angels"
        mock_album_service.update.assert_called_with(sample_album)
    
def test_album_manager_create_new(qtbot, mock_album_service, mock_publisher_service, mock_contributor_service):
    dialog = AlbumManagerDialog(mock_album_service, mock_publisher_service, mock_contributor_service)
    qtbot.addWidget(dialog)
    
    # Click "Create New"
    dialog._toggle_create_mode()
    assert dialog.is_creating_new is True
    assert dialog.inp_title.text() == ""
    
    dialog.inp_title.setText("New Album")
    
    new_album = Album(album_id=99, title="New Album")
    mock_album_service.get_or_create.return_value = (new_album, True)
    
    with patch.object(dialog, 'accept') as mock_accept:
        dialog._save_inspector()
        mock_album_service.get_or_create.assert_called()
        mock_accept.assert_not_called() 

def test_album_manager_delete(qtbot, mock_album_service, mock_publisher_service, mock_contributor_service, sample_album):
    mock_album_service.get_by_id.return_value = sample_album
    mock_album_service.search.return_value = [sample_album]
    dialog = AlbumManagerDialog(mock_album_service, mock_publisher_service, mock_contributor_service, initial_data={'album_id': 50})
    qtbot.addWidget(dialog)
    
    # Must select the item first
    item = dialog.list_vault.item(0)
    dialog.list_vault.setCurrentItem(item)
    
    mock_album_service.delete.return_value = True 
    dialog._on_delete()
    mock_album_service.delete.assert_called_with(50)
