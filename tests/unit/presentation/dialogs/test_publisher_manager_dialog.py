import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QMessageBox, QMenu
from PyQt6.QtCore import Qt, QPoint
from src.presentation.dialogs.publisher_manager_dialog import (
    PublisherDetailsDialog, PublisherPickerDialog, PublisherCreatorDialog
)
from src.data.models.publisher import Publisher

@pytest.fixture
def mock_pub_repo():
    repo = MagicMock()
    return repo

@pytest.fixture
def sample_publisher():
    return Publisher(publisher_id=200, publisher_name="Original Name", parent_publisher_id=None)

def test_publisher_creator_dialog_init(qtbot):
    dialog = PublisherCreatorDialog(initial_name="Existing", title="Rename Title", button_text="RenameBtn")
    qtbot.addWidget(dialog)
    
    assert dialog.windowTitle() == "Rename Title"
    assert dialog.inp_name.text() == "Existing"
    assert dialog.btn_save.text() == "RenameBtn"

def test_publisher_picker_dialog_populate(qtbot, mock_pub_repo):
    pubs = [
        Publisher(1, "Pub 1", None),
        Publisher(2, "Pub 2", None),
        Publisher(3, "Exclude Me", None)
    ]
    mock_pub_repo.search.return_value = pubs
    
    dialog = PublisherPickerDialog(mock_pub_repo, exclude_ids={3})
    qtbot.addWidget(dialog)
    
    # GlowComboBox.count() should return 2
    assert dialog.cmb.count() == 2
    assert dialog.cmb.itemText(0) == "Pub 1"
    assert dialog.cmb.itemText(1) == "Pub 2"

def test_publisher_details_dialog_save_rename(qtbot, mock_pub_repo, sample_publisher):
    mock_pub_repo.search.return_value = []
    dialog = PublisherDetailsDialog(sample_publisher, mock_pub_repo)
    qtbot.addWidget(dialog)
    
    dialog.txt_name.setText("New Named Publisher")
    mock_pub_repo.update.return_value = True
    
    with patch.object(dialog, 'accept') as mock_accept:
        # Trigger save directly to avoid UI lookup issues in tests
        dialog._save()
        
        assert sample_publisher.publisher_name == "New Named Publisher"
        mock_pub_repo.update.assert_called_with(sample_publisher)
        mock_accept.assert_called_once()

def test_publisher_details_dialog_circular_check(qtbot, mock_pub_repo, sample_publisher):
    # Setup: sample(200) -> parent(100) -> grandparent(200) [Cycle!]
    parent = Publisher(100, "Parent", 200)
    mock_pub_repo.get_by_id.side_effect = lambda id: parent if id == 100 else None
    mock_pub_repo.search.return_value = [parent]
    
    dialog = PublisherDetailsDialog(sample_publisher, mock_pub_repo)
    qtbot.addWidget(dialog)
    
    # Try to set parent to 100
    idx = dialog.cmb_parent.findData(100)
    dialog.cmb_parent.setCurrentIndex(idx)
    
    with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warn:
        dialog._save()
        mock_warn.assert_called_once()
        # Verify repo.update was NOT called
        mock_pub_repo.update.assert_not_called()

def test_publisher_details_dialog_add_child_cycle_prevention(qtbot, mock_pub_repo, sample_publisher):
    # Setup: 300 -> 200 (sample)
    # We want to prevent adding 300 as a child of 200 if 300 is already an ancestor.
    sample_publisher.parent_publisher_id = 300
    ancestor = Publisher(300, "Grandpa", None)
    
    def mock_get(id):
        if id == 300: return ancestor
        if id == 200: return sample_publisher
        return None
        
    mock_pub_repo.get_by_id.side_effect = mock_get
    mock_pub_repo.search.return_value = [ancestor]
    
    dialog = PublisherDetailsDialog(sample_publisher, mock_pub_repo)
    qtbot.addWidget(dialog)
    
    with patch('src.presentation.dialogs.publisher_manager_dialog.PublisherPickerDialog.exec', return_value=True), \
         patch('src.presentation.dialogs.publisher_manager_dialog.PublisherPickerDialog.get_selected', return_value=ancestor), \
         patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warn:
        
        dialog._add_child()
        mock_warn.assert_called_once()
        mock_pub_repo.update.assert_not_called()

def test_publisher_details_dialog_remove_child(qtbot, mock_pub_repo, sample_publisher):
    child = Publisher(500, "Son", 200)
    mock_pub_repo.search.return_value = [child]
    # Critical: ensure repo returns the SAME object we are checking
    mock_pub_repo.get_by_id.return_value = child 
    
    dialog = PublisherDetailsDialog(sample_publisher, mock_pub_repo)
    qtbot.addWidget(dialog)
    
    # Find child item in list
    item = dialog.list_children.item(0)
    assert "Son" in item.text()
    
    dialog._remove_child_link(item)
    
    assert child.parent_publisher_id is None
    mock_pub_repo.update.assert_called_with(child)

def test_publisher_details_dialog_rename_child(qtbot, mock_pub_repo, sample_publisher):
    child = Publisher(500, "Son", 200)
    mock_pub_repo.search.return_value = [child]
    mock_pub_repo.get_by_id.return_value = child
    
    dialog = PublisherDetailsDialog(sample_publisher, mock_pub_repo)
    qtbot.addWidget(dialog)
    item = dialog.list_children.item(0)
    
    with patch('src.presentation.dialogs.publisher_manager_dialog.PublisherCreatorDialog.exec', return_value=True), \
         patch('src.presentation.dialogs.publisher_manager_dialog.PublisherCreatorDialog.get_name', return_value="New Son"):
        
        dialog._on_child_double_clicked(item)
        
        assert child.publisher_name == "New Son"
        mock_pub_repo.update.assert_called_with(child)
