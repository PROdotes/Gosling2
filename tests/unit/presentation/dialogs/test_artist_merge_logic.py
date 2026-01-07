import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox

from src.presentation.dialogs.artist_manager_dialog import ArtistDetailsDialog
from src.data.models.contributor import Contributor

# Mock Service
@pytest.fixture
def mock_service():
    service = MagicMock()
    service.get_usage_count.return_value = 0
    service.get_aliases.return_value = []
    service.get_member_count.return_value = 0
    service.move_alias.return_value = True
    service.merge.return_value = True
    return service

@pytest.fixture
def dialog(mock_service):
    artist = Contributor(1, "Queen", "Queen", "group")
    # We mock parent to avoid Qt parenting issues in headless
    return ArtistDetailsDialog(artist, mock_service, parent=None)

# 1. Test Silent Merge (Dead Alias)
def test_silent_merge_dead_alias(dialog, mock_service):
    # Setup: Target has 0 songs, 0 aliases, 0 members
    target = Contributor(CONTRIBUTOR_ID=2, NAME="Ziggy", TYPE="person") 
    # NOTE: Attribute names in Contributor dataclass are lowercase: contributor_id, name, type
    target = Contributor(contributor_id=2, name="Ziggy", type="person")
    
    # Mock retrieval
    mock_service.get_by_id.return_value = target
    mock_service.get_usage_count.return_value = 0
    
    # Mock Picker to return this target
    with patch('src.presentation.dialogs.artist_manager_dialog.EntityPickerDialog') as MockPicker:
        config_mock = MockPicker.return_value
        config_mock.exec.return_value = True
        config_mock.get_selected.return_value = target
        
        # Execute
        dialog._add_alias()
        
        # Verify MERGE called (Silent)
        mock_service.merge.assert_called_with(2, 1)

# 2. Test Move Alias (Alias Link)
def test_move_alias_popup(dialog, mock_service):
    # Setup: Picker returns "Ghost" (Alias Name), but ID points to "DJ Someone" (Parent)
    parent = Contributor(contributor_id=5, name="DJ Someone", type="person")
    
    # Mock retrieval: ID 5 returns correct parent
    mock_service.get_by_id.return_value = parent
    
    # Picker returns Parent Object but with MODIFIED Name (The Alias String)
    target_proxy = Contributor(contributor_id=5, name="The Ghost", type="person")
    
    with patch('src.presentation.dialogs.artist_manager_dialog.EntityPickerDialog') as MockPicker, \
         patch('src.presentation.dialogs.artist_manager_dialog.IdentityCollisionDialog') as MockCollision:
        
        picker_mock = MockPicker.return_value
        picker_mock.exec.return_value = True
        picker_mock.get_selected.return_value = target_proxy
        
        # Mock Collision Dialog (Accept Move)
        collision_mock = MockCollision.return_value
        collision_mock.exec.return_value = 1 # Proceed
        
        # Execute
        dialog._add_alias()
        
        # Verify checks
        # "The Ghost" != "DJ Someone" -> Should trigger Move Alias path
        assert target_proxy.name != parent.name 
        
        # Verify Collision Dialog Init (Check header text)
        call_args = MockCollision.call_args[1]
        assert call_args['header'] == "ALIAS OWNERSHIP CONFLICT"
        
        # Verify MOVE called (Not Merge)
        mock_service.move_alias.assert_called_with("The Ghost", 5, 1)
        mock_service.merge.assert_not_called()

# 3. Test Destructive Merge (Data Loss)
def test_destructive_merge_warning(dialog, mock_service):
    # Setup: Target has songs
    target = Contributor(contributor_id=3, name="Bowie", type="person")
    mock_service.get_by_id.return_value = target
    mock_service.get_usage_count.return_value = 10 # ACTIVE!
    
    with patch('src.presentation.dialogs.artist_manager_dialog.EntityPickerDialog') as MockPicker, \
         patch('src.presentation.dialogs.artist_manager_dialog.IdentityCollisionDialog') as MockCollision:
        
        picker_mock = MockPicker.return_value
        picker_mock.exec.return_value = True
        picker_mock.get_selected.return_value = target
        
        # Mock Collision (Accept)
        collision_mock = MockCollision.return_value
        collision_mock.exec.return_value = 1
        
        # Execute
        dialog._add_alias()
        
        # Verify Collision Header
        call_args = MockCollision.call_args[1]
        assert call_args['header'] == "PERMANENT DATA LOSS WARNING"
        
        # Verify Merge Called
        mock_service.merge.assert_called_with(3, 1)
