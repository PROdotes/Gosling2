import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox
from src.presentation.dialogs.album_manager_dialog import AlbumManagerDialog
from src.data.models.album import Album



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
def mock_contributor_service():
    service = MagicMock()
    # Ensure get_or_create returns a tuple (Artist, Created)
    artist = MagicMock(contributor_id=1, type="person")
    artist.name = "Test Artist" # Explicit assignment because 'name' kwarg is reserved
    service.get_or_create.return_value = (artist, False)
    service.get_by_id.return_value = artist
    service.get_by_name.return_value = artist
    return service

@pytest.fixture
def mock_publisher_service():
    service = MagicMock()
    pub = MagicMock(publisher_id=2, publisher_name="Test Pub")
    service.get_by_id.return_value = pub
    service.get_or_create.return_value = (pub, False)
    return service

@pytest.fixture
def sample_album():
    return Album(album_id=50, title="Highway to Heck", album_artist="AC/BC", release_year=1979, album_type="Album")



def test_album_manager_init_with_id(qtbot, mock_album_service, mock_publisher_service, mock_contributor_service, sample_album):
    with patch('src.data.repositories.album_repository.AlbumRepository') as mock_repo_cls:
        # Setup Mock Repo
        mock_repo = mock_repo_cls.return_value
        # Initial load of contributors
        c = MagicMock()
        c.contributor_id = 1
        c.name = "Test Artist"
        c.type = "person"
        mock_repo.get_contributors_for_album.return_value = [c]
        mock_repo.get_publishers_for_album.return_value = []
        
        mock_album_service.get_by_id.return_value = sample_album
        mock_album_service.search.return_value = [sample_album]
        
        initial_data = {'album_id': 50, 'title': 'Highway to Heck'}
        dialog = AlbumManagerDialog(mock_album_service, mock_publisher_service, mock_contributor_service, initial_data=initial_data)
        qtbot.addWidget(dialog)
        
        qtbot.wait(50)
        
        assert dialog.inp_title.text() == "Highway to Heck"
        assert dialog.tray_artist.get_names() == ["Test Artist"]
        assert dialog.inp_year.text() == "1979"
        assert dialog.cmb_type.currentText() == "Album"

def test_album_manager_search_and_select(qtbot, mock_album_service, mock_publisher_service, mock_contributor_service, sample_album):
    with patch('src.data.repositories.album_repository.AlbumRepository') as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        c = MagicMock()
        c.contributor_id = 1
        c.name = "Test Artist"
        c.type = "person"
        mock_repo.get_contributors_for_album.return_value = [c]
        mock_repo.get_publishers_for_album.return_value = []
        
        mock_album_service.search.return_value = [sample_album]
        mock_album_service.get_by_id.return_value = sample_album
        
        dialog = AlbumManagerDialog(mock_album_service, mock_publisher_service, mock_contributor_service)
        qtbot.addWidget(dialog)
        
        dialog.txt_search.setText("Highway")
        dialog._on_search_text_changed("Highway")
        
        assert dialog.list_vault.count() == 1
        
        item = dialog.list_vault.item(0)
        dialog.list_vault.setCurrentItem(item)
        dialog._on_vault_item_clicked(item)
        
        assert dialog.inp_title.text() == "Highway to Heck"
        assert dialog.current_album == sample_album

def test_album_manager_save_existing(qtbot, mock_album_service, mock_publisher_service, mock_contributor_service, sample_album):
    with patch('src.data.repositories.album_repository.AlbumRepository') as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_contributors_for_album.return_value = []
        mock_repo.get_publishers_for_album.return_value = []
        
        mock_album_service.get_by_id.return_value = sample_album
        mock_album_service.search.return_value = [sample_album]
        dialog = AlbumManagerDialog(mock_album_service, mock_publisher_service, mock_contributor_service, initial_data={'album_id': 50})
        qtbot.addWidget(dialog)
        
        dialog.inp_title.setText("Highway to Heaven")
        sample_album.album_artist = "Angels"
        
        mock_album_service.update.return_value = True
        
        with patch.object(dialog, 'accept') as mock_accept:
            dialog._save_inspector()
            
            assert sample_album.title == "Highway to Heaven"
            assert sample_album.album_artist == "Angels"
            mock_album_service.update.assert_called_with(sample_album)
            
            mock_repo.sync_contributors.assert_not_called()
    
def test_album_manager_create_new(qtbot, mock_album_service, mock_publisher_service, mock_contributor_service):
    with patch('src.data.repositories.album_repository.AlbumRepository') as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        
        dialog = AlbumManagerDialog(mock_album_service, mock_publisher_service, mock_contributor_service)
        qtbot.addWidget(dialog)
        
        dialog._toggle_create_mode()
        assert dialog.is_creating_new is True
        
        dialog.inp_title.setText("New Album")
        
        new_album = Album(album_id=99, title="New Album")
        mock_album_service.get_or_create.return_value = (new_album, True)
        
        with patch.object(dialog, 'accept') as mock_accept:
            dialog._save_inspector()
            mock_album_service.get_or_create.assert_called()
            mock_accept.assert_not_called() 
            mock_repo.sync_contributors.assert_called()

def test_album_manager_delete(qtbot, mock_album_service, mock_publisher_service, mock_contributor_service, sample_album):
    with patch('src.data.repositories.album_repository.AlbumRepository') as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_contributors_for_album.return_value = []
        mock_repo.get_publishers_for_album.return_value = []

        mock_album_service.get_by_id.return_value = sample_album
        mock_album_service.search.return_value = [sample_album]
        dialog = AlbumManagerDialog(mock_album_service, mock_publisher_service, mock_contributor_service, initial_data={'album_id': 50})
        qtbot.addWidget(dialog)
        
        item = dialog.list_vault.item(0)
        dialog.list_vault.setCurrentItem(item)
        
        mock_album_service.delete.return_value = True 
        dialog._on_delete()
        mock_album_service.delete.assert_called_with(50)
