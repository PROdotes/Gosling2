import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox
from src.presentation.dialogs.album_manager_dialog import AlbumManagerDialog
from src.data.models.album import Album

@pytest.fixture(autouse=True)
def mock_pub_repo_instantiation():
    # Patch PublisherRepository at the source of import to avoid real DB access
    with patch("src.presentation.dialogs.album_manager_dialog.PublisherRepository") as mock:
        yield mock

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.db_path = ":memory:"
    repo.search.return_value = []
    repo.get_by_id.return_value = None
    repo.get_publisher.return_value = "Test Publisher"
    return repo

@pytest.fixture
def sample_album():
    return Album(1, "Test Album")

def test_album_mutation_field_exhaustion(qtbot, mock_repo, sample_album):
    mock_repo.get_by_id.return_value = sample_album
    dialog = AlbumManagerDialog(mock_repo, initial_data={'album_id': 1})
    qtbot.addWidget(dialog)
    
    # Fill all fields with huge strings
    huge = "X" * 5000
    dialog.inp_title.setText(huge)
    dialog.inp_artist.setText(huge)
    dialog.inp_year.setText("2024")
    
    mock_repo.update.return_value = True
    dialog._save_inspector()
    
    assert sample_album.title == huge
    assert sample_album.album_artist == huge
    mock_repo.update.assert_called_once()

def test_album_mutation_sql_injection_search(qtbot, mock_repo):
    dialog = AlbumManagerDialog(mock_repo)
    qtbot.addWidget(dialog)
    
    # Bobby Tables in search
    injection = "' OR 1=1; --"
    dialog.txt_search.setText(injection)
    dialog._on_search_text_changed(injection)
    
    mock_repo.search.assert_called_with(injection)

def test_album_mutation_empty_save(qtbot, mock_repo):
    dialog = AlbumManagerDialog(mock_repo)
    qtbot.addWidget(dialog)
    
    # Create new mode
    dialog._toggle_create_mode()
    assert dialog.is_creating_new is True
    
    # Try save empty
    dialog._save_inspector()
    # Should NOT call get_or_create or update if title is empty
    mock_repo.get_or_create.assert_not_called()
    mock_repo.update.assert_not_called()
