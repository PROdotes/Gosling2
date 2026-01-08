"""
Level 1 Logic Tests for Artist Manager Dialogs.
Per TESTING.md: Tests the happy path and polite failures.
"""
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QMessageBox

from src.presentation.dialogs.artist_manager_dialog import (
    ArtistDetailsDialog
)
from src.data.models.contributor import Contributor




class TestArtistDetailsDialog:
    """Tests for the full artist editor dialog."""

    @pytest.fixture
    def mock_repo(self):
        """Mock contributor repository with full functionality."""
        repo = MagicMock()
        repo.get_aliases.return_value = []
        repo.get_members.return_value = []
        repo.get_groups.return_value = []
        repo.update.return_value = True
        repo.get_usage_count.return_value = 0
        repo.validate_identity.return_value = (None, "")
        return repo

    @pytest.fixture
    def mock_artist(self):
        """Create a real Contributor for testing."""
        # Contributor model uses: contributor_id, name, sort_name, type
        return Contributor(
            contributor_id=1,
            name="Test Artist",
            sort_name="Artist, Test",
            type="person"
        )

    def test_initialization(self, qtbot, mock_artist, mock_repo):
        """Test details dialog initializes correctly."""
        dialog = ArtistDetailsDialog(artist=mock_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        assert dialog.artist == mock_artist
        # Note: The field is txt_name not inp_name in ArtistDetailsDialog
        assert dialog.txt_name.text() == "Test Artist"

    def test_initialization_group_type(self, qtbot, mock_repo):
        """Test details dialog shows correct UI for group."""
        group_artist = Contributor(
            contributor_id=2,
            name="The Band",
            sort_name="Band, The",
            type="group"
        )
        
        dialog = ArtistDetailsDialog(artist=group_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        assert dialog.txt_name.text() == "The Band"
        assert dialog.radio_group.isChecked()
        assert dialog.lbl_member.text() == "GROUP MEMBERS"

    def test_add_alias(self, qtbot, mock_artist, mock_repo):
        """Test adding an alias (via merge) to artist."""
        dialog = ArtistDetailsDialog(artist=mock_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        # Mock IdentityCollisionDialog, EntityPickerDialog and QMessageBox
        with patch('src.presentation.dialogs.entity_picker_dialog.EntityPickerDialog') as MockPicker, \
             patch('src.presentation.dialogs.artist_manager_dialog.IdentityCollisionDialog') as MockCollision, \
             patch('src.presentation.dialogs.artist_manager_dialog.QMessageBox') as MockMsg:
            
            # Setup Picker
            mock_dlg_instance = MockPicker.return_value
            mock_dlg_instance.exec.return_value = True
            
            # Setup Collision Dialog
            mock_collision_instance = MockCollision.return_value
            mock_collision_instance.exec.return_value = 1 # Merge/Secondary
            
            # Use a mock object that simulates a different Contributor (The Absorb Target)
            mock_target = MagicMock()
            mock_target.contributor_id = 999
            mock_target.name = "Target Artist"
            mock_target.type = "person"
            mock_repo.get_by_id.return_value = mock_target
            
            # Setup Picker to return the same identity (Primary Match)
            mock_selected = MagicMock()
            mock_selected.contributor_id = 999
            mock_selected.name = "Target Artist"
            mock_selected.type = "person"
            mock_dlg_instance.get_selected.return_value = mock_selected
            
            
            # Setup MessageBox to say YES
            # Ensure both the return value AND the constant match
            YES_VAL = 16384
            MockMsg.question.return_value = YES_VAL
            MockMsg.StandardButton.Yes = YES_VAL
            MockMsg.StandardButton.No = 0
            
            # Setup Service
            mock_repo.merge.return_value = True
            
            dialog._add_alias()
        
        # Verify merge was called (target_id, self_id)
        mock_repo.merge.assert_called_once_with(999, 1)

    def test_add_alias_cancelled(self, qtbot, mock_artist, mock_repo):
        """Test cancelling alias addition."""
        dialog = ArtistDetailsDialog(artist=mock_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        with patch('src.presentation.dialogs.entity_picker_dialog.EntityPickerDialog') as MockPicker:
            mock_dlg_instance = MockPicker.return_value
            mock_dlg_instance.exec.return_value = False  # Cancelled
            
            dialog._add_alias()
        
        mock_repo.add_alias.assert_not_called()

    def test_save_updates_name(self, qtbot, mock_artist, mock_repo):
        """Test saving updates the artist name."""
        dialog = ArtistDetailsDialog(artist=mock_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        # Change the name
        dialog.txt_name.setText("New Name")
        
        # Mock validation to pass
        mock_repo.validate_identity.return_value = (None, "")
        
        # Save (mocking accept to prevent dialog close and IdentityCollisionDialog)
        with patch.object(dialog, 'done'), \
             patch('src.presentation.dialogs.artist_manager_dialog.IdentityCollisionDialog') as MockCollision:
            dialog._save()
        
        # Verify update was called and artist was modified
        mock_repo.update.assert_called_once()
        assert mock_artist.name == "New Name"

    def test_person_shows_belongs_to_groups_label(self, qtbot, mock_artist, mock_repo):
        """Test person type shows correct membership label."""
        dialog = ArtistDetailsDialog(artist=mock_artist, service=mock_repo)
        qtbot.addWidget(dialog)
        
        assert dialog.lbl_member.text() == "BELONGS TO GROUPS"

    def test_edit_alias_rename(self, qtbot, mock_artist, mock_repo):
        """Test renaming an alias using the EntityPickerDialog."""
        dialog = ArtistDetailsDialog(artist=mock_artist, service=mock_repo)
        qtbot.addWidget(dialog)

        # Mock EntityPickerDialog
        with patch('src.presentation.dialogs.entity_picker_dialog.EntityPickerDialog') as MockPicker:
            instance = MockPicker.return_value
            instance.exec.return_value = 1 # Accept
            instance.is_rename_requested.return_value = True
            instance.get_rename_info.return_value = ("New Alias Name", "Alias")

            # Call _edit_alias
            dialog._edit_alias(alias_id=99, old_name="Old Name")

            # Verify update_alias was called with new name
            mock_repo.update_alias.assert_called_with(99, "New Alias Name")
