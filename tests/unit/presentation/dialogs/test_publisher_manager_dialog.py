import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QMessageBox, QMenu
from PyQt6.QtCore import Qt, QPoint
from src.presentation.dialogs.publisher_manager_dialog import (
    PublisherDetailsDialog, PublisherCreatorDialog
)
from src.data.models.publisher import Publisher

@pytest.fixture
def mock_service():
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

def test_publisher_details_dialog_save_rename(qtbot, mock_service, sample_publisher):
    mock_service.search.return_value = []
    dialog = PublisherDetailsDialog(sample_publisher, mock_service)
    qtbot.addWidget(dialog)
    
    dialog.txt_name.setText("New Named Publisher")
    mock_service.update.return_value = True
    # Make sure cycle check passes (False means no cycle)
    mock_service.would_create_cycle.return_value = False
    
    with patch.object(dialog, 'accept') as mock_accept:
        # Trigger save directly to avoid UI lookup issues in tests
        dialog._save()
        
        assert sample_publisher.publisher_name == "New Named Publisher"
        mock_service.update.assert_called_with(sample_publisher)
        mock_accept.assert_called_once()

def test_publisher_details_dialog_circular_check(qtbot, mock_service, sample_publisher):
    # Setup: sample(200) -> parent(100) -> grandparent(200) [Cycle!]
    parent = Publisher(100, "Parent", 200)
    mock_service.get_by_id.side_effect = lambda id: parent if id == 100 else None
    mock_service.search.return_value = [parent]
    
    # Set cycle check to True
    mock_service.would_create_cycle.return_value = True

    dialog = PublisherDetailsDialog(sample_publisher, mock_service)
    qtbot.addWidget(dialog)
    
    # Try to set parent to 100
    idx = dialog.cmb_parent.findData(100)
    dialog.cmb_parent.setCurrentIndex(idx)
    
    with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warn:
        dialog._save()
        mock_warn.assert_called_once()
        # Verify update was NOT called
        mock_service.update.assert_not_called()

def test_publisher_details_dialog_add_child_cycle_prevention(qtbot, mock_service, sample_publisher):
    # Setup: 300 -> 200 (sample)
    # We want to prevent adding 300 as a child of 200 if 300 is already an ancestor.
    sample_publisher.parent_publisher_id = 300
    ancestor = Publisher(300, "Grandpa", None)
    
    def mock_get(id):
        if id == 300: return ancestor
        if id == 200: return sample_publisher
        return None
        
    mock_service.get_by_id.side_effect = mock_get
    mock_service.search.return_value = [ancestor]
    # Simulate cycle detection when trying to add child
    mock_service.would_create_cycle.return_value = True
    
    dialog = PublisherDetailsDialog(sample_publisher, mock_service)
    qtbot.addWidget(dialog)
    
    # The EntityClickRouter uses EntityPickerDialog for publishers now
    with patch('src.presentation.dialogs.entity_picker_dialog.EntityPickerDialog.exec', return_value=1), \
         patch('src.presentation.dialogs.entity_picker_dialog.EntityPickerDialog.get_selected', return_value=ancestor), \
         patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warn:
        
        dialog.list_children.add_item_interactive()
        mock_warn.assert_called_once()
        mock_service.update.assert_not_called()

def test_publisher_details_dialog_remove_child(qtbot, mock_service, sample_publisher):
    child = Publisher(500, "Son", 200)
    # The PublisherChildAdapter uses search to find subsidiaries
    mock_service.search.return_value = [child]
    mock_service.get_by_id.return_value = child 
    
    dialog = PublisherDetailsDialog(sample_publisher, mock_service)
    qtbot.addWidget(dialog)
    
    # Verify child in list (get_names returns labels like "🏢 Son")
    names = dialog.list_children.get_names()
    assert any("Son" in n for n in names)
    
    # Simulate removal via EntityListWidget internal logic
    mock_service.update.return_value = True
    dialog.list_children._do_remove(500)
    
    assert child.parent_publisher_id is None
    mock_service.update.assert_called_with(child)

def test_publisher_details_dialog_rename_child(qtbot, mock_service, sample_publisher):
    child = Publisher(500, "Son", 200)
    mock_service.search.return_value = [child]
    mock_service.get_by_id.return_value = child
    
    dialog = PublisherDetailsDialog(sample_publisher, mock_service)
    qtbot.addWidget(dialog)
    
    # Verify clicking child triggers ClickRouter
    from src.core.entity_click_router import ClickResult, ClickAction
    # ClickResult needs (action, entity_id)
    with patch.object(dialog.list_children.click_router, 'route_click', return_value=ClickResult(ClickAction.UPDATED, 500)) as mock_route:
        dialog.list_children._on_item_clicked(500, "Son")
        mock_route.assert_called_once()
